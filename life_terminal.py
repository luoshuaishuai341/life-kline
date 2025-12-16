import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from lunar_python import Solar, Lunar
from datetime import datetime, date, timedelta
import random
import json
import os
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# ==========================================
# 1. 页面配置与炫酷样式（花里胡哨升级）
# ==========================================
st.set_page_config(
    page_title="天机 · 全息命理终端 V16 Ultimate",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { 
        background: linear-gradient(to bottom, #e0e7ff, #f7f9fc); 
        color: #333; 
    }
    h1, h2, h3 { 
        font-family: 'KaiTi', 'PingFang SC', sans-serif; 
        color: #4a148c !important; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    /* 炫彩指标卡片 */
    .metric-box {
        background: linear-gradient(135deg, #ffffff, #f0f4ff); 
        padding: 20px; border-radius: 12px;
        border-left: 6px solid #9c27b0; box-shadow: 0 4px 12px rgba(156,39,176,0.15);
        margin-bottom: 15px; text-align: center;
    }
    .metric-title { font-size: 16px; color: #7e57c2; font-weight: bold; }
    .metric-value { font-size: 28px; font-weight: bold; color: #4a148c; margin: 10px 0; }
    
    /* 神煞标签升级 */
    .shensha-tag {
        display: inline-block; padding: 8px 16px; margin: 6px;
        border-radius: 30px; font-size: 14px; font-weight: bold; 
        color: white; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        animation: glow 2s infinite alternate;
    }
    @keyframes glow { from { box-shadow: 0 0 5px; } to { box-shadow: 0 0 15px; } }
    .tag-pink { background: linear-gradient(#e91e63, #c2185b); }
    .tag-gold { background: linear-gradient(#fbc02d, #f9a825); color: #333; }
    .tag-blue { background: linear-gradient(#2196f3, #1976d2); }
    .tag-purple { background: linear-gradient(#9c27b0, #7b1fa2); }
    .tag-gray { background: #9e9e9e; }

    /* 按钮炫光 */
    .stButton>button { 
        background: linear-gradient(#ab47bc, #7b1fa2); 
        color: white; border-radius: 30px; 
        box-shadow: 0 4px 15px rgba(171,71,188,0.4);
        transition: all 0.3s;
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(171,71,188,0.6); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据加载
# ==========================================
@st.cache_data
def load_admin_data():
    files = ["pcas-code.json", "pca-code.json"]
    curr = os.path.dirname(os.path.abspath(__file__))
    for f in files:
        p = os.path.join(curr, f)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as file: 
                    return json.load(file)
            except: continue
    return None

ADMIN_DATA = load_admin_data()

# ==========================================
# 3. 定位与 AI 接口（优化）
# ==========================================
@st.cache_data(show_spinner=False)
def get_precise_location(addr):
    ua = f"bazi_v16_{random.randint(10000,99999)}"
    try:
        query = addr if any(k in addr for k in ["香港","澳门","台湾"]) else f"中国 {addr}"
        loc = Nominatim(user_agent=ua).geocode(query, timeout=10)
        if loc: 
            return {"success": True, "lat": loc.latitude, "lng": loc.longitude, "addr": loc.address}
    except: pass
    return {"success": False, "lat": 39.9042, "lng": 116.4074, "msg": "使用默认北京坐标"}

def call_ai_analysis(api_key, base_url, context, kline_lows):
    if not api_key: return "⚠️ 请配置 API Key 启用 AI 解盘"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    prompt = f"""
你是一位融合古今的命理大师，请根据以下信息给出深刻而富有诗意的分析（控制在300字以内）：
{context}

人生K线低谷年龄段：{kline_lows}

请从格局、神煞、喜用神、大运流年四个维度给出建议，语言优美、富有哲理。
"""
    data = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.8}
    
    try:
        res = requests.post(f"{base_url.rstrip('/')}/v1/chat/completions", headers=headers, json=data, timeout=20)
        if res.status_code == 200: 
            return res.json()['choices'][0]['message']['content']
        return f"⚠️ API错误: {res.status_code}"
    except Exception as e: 
        return f"⚠️ 网络异常: {str(e)}"

# ==========================================
# 4. 核心引擎（真正动态 + 花里胡哨增强）
# ==========================================
class DestinyEngine:
    def __init__(self, b_date: date, hour: int, minute: int, lat: float, lng: float, gender: str):
        self.birth_date = b_date
        self.gender = gender
        self.hour = hour
        self.minute = minute
        
        self.solar = Solar.fromYmdHms(b_date.year, b_date.month, b_date.day, hour, minute, 0)
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()
        
        # 动态种子（每个人完全不同）
        self.seed = hash((b_date, hour, minute, lat, lng, gender, self.bazi.getDayGan()))
        random.seed(self.seed)
        np.random.seed(self.seed % (2**32))
        
        self.true_solar_diff = (lng - 120.0) * 4
        self.wuxing_strength = self._calc_wuxing()
        self.favored = self._get_favored()
        self.shen_sha = self._calc_shen_sha()
        self.pattern = self._get_pattern()  # 新增：格局判断

    def _calc_wuxing(self):
        cnt = {"金":0, "木":0, "水":0, "火":0, "土":0}
        wx_map = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
                  "子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
        for p in [self.bazi.getYearGan(), self.bazi.getYearZhi(), self.bazi.getMonthGan(), self.bazi.getMonthZhi(),
                  self.bazi.getDayGan(), self.bazi.getDayZhi(), self.bazi.getTimeGan(), self.bazi.getTimeZhi()]:
            if p in wx_map: cnt[wx_map[p]] += 1
        return cnt

    def _get_favored(self):
        day_wx = self.bazi.getDayWuXing()
        weak = min(self.wuxing_strength, key=self.wuxing_strength.get)
        return weak if self.wuxing_strength[day_wx] < 3 else "平衡"

    def _get_pattern(self):
        day_gan = self.bazi.getDayGan()
        month_zhi = self.bazi.getMonthZhi()
        patterns = {
            "正官": "官星透干，格局清正，适合从政或管理",
            "七杀": "杀星旺相，胆识过人，宜创业或军警",
            "食神": "食神生财，心宽体胖，艺术天赋",
            "伤官": "伤官佩印，才华横溢，适合创意行业",
            "偏财": "偏财格，善于投资，人缘极佳",
            "正财": "正财稳健，勤勉可靠，适合经商"
        }
        # 简易判断（实际更复杂，这里模拟）
        return random.choice(list(patterns.items())) if random.random() > 0.3 else ("从格", "随势而为，灵活变通是大智慧")

    def _calc_shen_sha(self):
        res = []
        day_zhi = self.bazi.getDayZhi()
        year_zhi = self.bazi.getYearZhi()
        day_gan = self.bazi.getDayGan()
        
        # 桃花
        taohua_pos = {"子午卯酉":"桃花在外", "寅申巳亥":"桃花在内", "辰戌丑未":"桃花暗藏"}.get(
            "".join(sorted([day_zhi] + [self.bazi.getYearZhi(), self.bazi.getMonthZhi(), self.bazi.getTimeZhi()])), None)
        if taohua_pos and random.random() > 0.4:
            res.append({"name": "桃花旺盛", "type": "pink", "desc": "魅力四射，异性缘爆棚"})

        # 天乙贵人
        if random.random() > 0.3:
            res.append({"name": "天乙贵人", "type": "gold", "desc": "贵人相助，一生顺遂"})

        # 驿马
        if random.random() > 0.5:
            res.append({"name": "驿马星动", "type": "blue", "desc": "适合外出发展，动则生财"})

        # 文昌
        if random.random() > 0.4:
            res.append({"name": "文昌贵星", "type": "purple", "desc": "聪明好学，考试升迁有利"})

        if not res:
            res.append({"name": "命宫平稳", "type": "gray", "desc": "安稳一生，福禄自来"})
        return res

    def generate_life_kline(self):
        """真正动态！每个人K线完全不同，结合喜用神、神煞、大运周期"""
        data = []
        price = 100.0
        lows = []  # 记录低谷年龄
        
        # 模拟大运五行流转（基于日主）
        day_wx_idx = ["木","火","土","金","水"].index(self.bazi.getDayWuXing())
        dayun_cycle = ["木","火","土","金","水"]
        dayun_wx_list = [dayun_cycle[(day_wx_idx + i) % 5] for i in range(10)] * 10  # 重复
        
        for age in range(0, 101):
            dayun_wx = dayun_wx_list[age // 10]
            
            # 核心：大运五行与喜用神生克关系决定基础趋势
            base_score = 0
            if dayun_wx == self.favored: base_score = 8
            elif dayun_wx in {"木":"火","火":"土","土":"金","金":"水","水":"木"}.get(self.favored, ""): base_score = 5
            elif self.favored in {"木":"火","火":"土","土":"金","金":"水","水":"木"}.get(dayun_wx, ""): base_score = -5
            
            # 神煞加成（桃花+3，贵人+6，驿马+2）
            bonus = sum(3 if "桃花" in s['name'] else 6 if "贵人" in s['name'] else 2 if "驿马" in s['name'] else 0 for s in self.shen_sha)
            
            # 随机波动 + 本命年
            noise = np.random.normal(0, 4)
            change = base_score + bonus/3 + noise
            if age % 12 == 0 and age > 0: change -= 12  # 本命年重击
            
            close = max(15, price + change)
            if change < -8: lows.append(age)
            
            status = "大吉昌盛" if change > 10 else ("顺风顺水" if change > 4 else ("低谷挑战" if change < -8 else "平稳过渡"))
            
            data.append({"Age": age, "Open": price, "Close": close, "High": close + abs(change)*1.2, "Low": price - abs(change)*1.2, "Status": status})
            price = close
        
        df = pd.DataFrame(data)
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA30'] = df['Close'].rolling(30).mean()
        self.low_ages = ", ".join(map(str, lows[:5])) + ("等" if len(lows)>5 else "")
        return df

    def generate_daily_kline(self, year):
        # 类似动态逻辑，略（保持原有即可）
        start = date(year, 1, 1)
        days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        data = []
        price = 100.0
        random.seed(self.seed + year)
        
        for i in range(days):
            curr = start + timedelta(days=i)
            change = random.gauss(0, 3.5) + (5 if random.random() > 0.7 else 0)  # 随机好日子
            close = max(30, price + change)
            data.append({"Date": curr, "Open": price, "Close": close, "High": close + abs(change), "Low": price - abs(change)})
            price = close
        return pd.DataFrame(data)

    def get_ai_context(self):
        bazi_str = f"{self.bazi.getYear()} {self.bazi.getMonth()} {self.bazi.getDay()} {self.bazi.getTime()}"
        shensha_names = [s['name'] for s in self.shen_sha]
        return f"性别:{self.gender}，出生:{self.birth_date} {self.hour}:{self.minute:02}，八字:{bazi_str}，日主:{self.bazi.getDayGan()}({self.bazi.getDayWuXing()})，喜用:{self.favored}，格局:{self.pattern[0]}，神煞:{shensha_names}"

# ==========================================
# 5. 主程序（花里胡哨满载）
# ==========================================
def main():
    with st.sidebar:
        st.markdown("<h2 style='text-align:center; color:#7b1fa2;'>🌟 天机控制台</h2>", unsafe_allow_html=True)
        
        with st.expander("🤖 AI 解盘配置（可选）", expanded=False):
            api_base = st.text_input("API Base", "https://api.openai.com/v1")
            api_key = st.text_input("API Key", type="password", help="支持 OpenAI、Groq、DeepSeek 等")
        
        st.markdown("---")
        st.subheader("📜 缘主档案")
        name = st.text_input("姓名", "神秘客人")
        gender = st.selectbox("性别", ["男", "女"])
        
        st.markdown("#### 📅 出生时间")
        col_y, col_m, col_d = st.columns(3)
        year = col_y.selectbox("年", range(1900, datetime.now().year + 1), index=70)
        month = col_m.selectbox("月", range(1,13), format_func=lambda x: f"{x}月")
        day_max = (date(year, month+1, 1) - timedelta(days=1)).day if month < 12 else 31
        day = col_d.selectbox("日", range(1, day_max+1), format_func=lambda x: f"{x}日")
        
        col_h, col_min = st.columns(2)
        hour = col_h.selectbox("时辰", range(24))
        minute = col_min.selectbox("分钟", range(60))
        
        st.markdown("#### 📍 出生地点")
        full_addr = "北京市"
        if ADMIN_DATA:
            provs = [p['name'] for p in ADMIN_DATA]
            prov = st.selectbox("省份", provs)
            prov_d = next(p for p in ADMIN_DATA if p['name']==prov)
            cities = prov_d.get('children', [])
            city = prov if prov in ["北京","上海","天津","重庆"] else st.selectbox("城市", [c['name'] for c in cities] or [prov])
            detail = st.text_input("详细（如医院）", "协和医院")
            full_addr = f"{prov}{city}{detail}"
        else:
            st.warning("未加载区划数据，使用默认")
        
        if st.button("🛰️ 精准定位 & 排盘", type="primary", use_container_width=True):
            with st.spinner("天机正在推演..."):
                loc_res = get_precise_location(full_addr)
                st.session_state.loc = loc_res
                st.success("排盘完成！")

    # 核心计算
    loc = st.session_state.get('loc', {'lat':39.9042, 'lng':116.4074})
    b_date = date(year, month, day)
    engine = DestinyEngine(b_date, hour, minute, loc['lat'], loc['lng'], gender)
    df_life = engine.generate_life_kline()

    st.markdown(f"<h1 style='text-align:center;'>🌌 {name} · 全息命盘</h1>", unsafe_allow_html=True)

    # 炫彩指标区
    col1, col2, col3, col4, col5 = st.columns(5)
    bazi_str = f"{engine.bazi.getYear()}　{engine.bazi.getMonth()}　{engine.bazi.getDay()}　{engine.bazi.getTime()}"
    col1.markdown(f"<div class='metric-box'><div class='metric-title'>八字</div><div class='metric-value'>{bazi_str}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-box'><div class='metric-title'>格局</div><div class='metric-value'>{engine.pattern[0]}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-box'><div class='metric-title'>喜用神</div><div class='metric-value'>{engine.favored}</div></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='metric-box'><div class='metric-title'>虚岁</div><div class='metric-value'>{datetime.now().year - year + 1}</div></div>", unsafe_allow_html=True)
    col5.markdown(f"<div class='metric-box'><div class='metric-title'>真太阳时差</div><div class='metric-value'>{engine.true_solar_diff:+.1f}分</div></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔮 AI 大师解盘", "📈 百年人生K线", "📅 流年日运", "🌟 神煞星耀", "🔥 运势热力图"])

    with tab1:
        st.markdown("### ✨ AI 大师 · 独家解盘")
        if st.button("🧙‍♂️ 立即呼叫大师（需配置API）", type="primary"):
            with st.spinner("大师正在观星推命..."):
                analysis = call_ai_analysis(api_key, api_base, engine.get_ai_context(), engine.low_ages)
                st.markdown(f"<div style='background:#f3e5f5; padding:20px; border-radius:15px; border-left:6px solid #9c27b0;'>{analysis}</div>", unsafe_allow_html=True)
        else:
            st.info("配置左侧 API Key 后点击按钮，即可获得专属AI解盘（支持GPT-4o、Claude等）")

    with tab2:
        st.markdown("### 📈 百年运势 · 专属K线（完全动态！）")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df_life['Age'], open=df_life['Open'], high=df_life['High'],
                                     low=df_life['Low'], close=df_life['Close'],
                                     increasing_line_color='#ff4081', decreasing_line_color='#40c4ff'))
        fig.add_trace(go.Scatter(x=df_life['Age'], y=df_life['MA10'], line=dict(color='#ffab40', width=3, dash='dot'), name='十年大运'))
        fig.add_trace(go.Scatter(x=df_life['Age'], y=df_life['MA30'], line=dict(color='#7c4dff', width=3), name='三十年趋势'))
        fig.update_layout(height=600, template="plotly_dark", title="你的人生运势曲线（独一无二）",
                          xaxis_title="年龄", yaxis_title="运势能量")
        if engine.low_ages:
            st.warning(f"⚠️ 注意低谷年龄：{engine.low_ages}")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("### 📅 流年每日运势")
        q_year = st.slider("选择年份", 1900, 2100, datetime.now().year)
        df_daily = engine.generate_daily_kline(q_year)
        fig_d = go.Figure(go.Candlestick(x=df_daily['Date'], open=df_daily['Open'], high=df_daily['High'],
                                         low=df_daily['Low'], close=df_daily['Close'],
                                         increasing_line_color='#ff1744', decreasing_line_color='#00e676'))
        fig_d.update_layout(height=500, template="plotly_white", title=f"{q_year}年 · 每日运势波动")
        st.plotly_chart(fig_d, use_container_width=True)

    with tab4:
        st.markdown("### 🌟 命中神煞星耀")
        for item in engine.shen_sha:
            st.markdown(f"<span class='shensha-tag tag-{item['type']}'>{item['name']}</span>　{item['desc']}", unsafe_allow_html=True)
        st.markdown(f"<br><small>格局评语：{engine.pattern[1]}</small>", unsafe_allow_html=True)

    with tab5:
        st.markdown("### 🔥 全年运势热力图（红旺蓝弱）")
        df_daily = engine.generate_daily_kline(datetime.now().year)
        df_daily['月'] = df_daily['Date'].dt.month
        df_daily['日'] = df_daily['Date'].dt.day
        fig_heat = px.density_heatmap(df_daily, x="日", y="月", z="Close", 
                                     color_continuous_scale="plasma", nbinsx=31, nbinsy=12,
                                     title="今年运势热力分布")
        st.plotly_chart(fig_heat, use_container_width=True)

if __name__ == "__main__":
    if 'loc' not in st.session_state:
        st.session_state.loc = {'lat':39.9042, 'lng':116.4074}
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    main()