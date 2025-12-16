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
# 1. 页面配置与全中文炫酷样式
# ==========================================
st.set_page_config(
    page_title="天机 · 全息命理终端 V22 终极版",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background: linear-gradient(to bottom, #e0e7ff, #f7f9fc); color: #333; }
    h1, h2, h3 { font-family: 'KaiTi', 'PingFang SC', sans-serif; color: #4a148c !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
    .metric-box { background: linear-gradient(135deg, #ffffff, #f0f4ff); padding: 20px; border-radius: 12px;
        border-left: 6px solid #9c27b0; box-shadow: 0 4px 12px rgba(156,39,176,0.15); margin-bottom: 15px; text-align: center; }
    .metric-title { font-size: 16px; color: #7e57c2; font-weight: bold; }
    .metric-value { font-size: 28px; font-weight: bold; color: #4a148c; margin: 10px 0; }
    .shensha-tag { display: inline-block; padding: 8px 16px; margin: 6px; border-radius: 30px; font-size: 14px; font-weight: bold; 
        color: white; box-shadow: 0 2px 6px rgba(0,0,0,0.2); animation: glow 2s infinite alternate; }
    @keyframes glow { from { box-shadow: 0 0 5px; } to { box-shadow: 0 0 15px; } }
    .tag-pink { background: linear-gradient(#e91e63, #c2185b); }
    .tag-gold { background: linear-gradient(#fbc02d, #f9a825); color: #333; }
    .tag-blue { background: linear-gradient(#2196f3, #1976d2); }
    .tag-purple { background: linear-gradient(#9c27b0, #7b1fa2); }
    .tag-gray { background: #9e9e9e; }
    .stButton>button { background: linear-gradient(#ab47bc, #7b1fa2); color: white; border-radius: 30px; 
        box-shadow: 0 4px 15px rgba(171,71,188,0.4); }
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
# 3. 定位与 AI 接口
# ==========================================
@st.cache_data(show_spinner=False)
def get_precise_location(addr):
    ua = f"bazi_v22_{random.randint(10000,99999)}"
    try:
        query = addr if any(k in addr for k in ["香港","澳门","台湾"]) else f"中国 {addr}"
        loc = Nominatim(user_agent=ua).geocode(query, timeout=10)
        if loc: 
            return {"success": True, "lat": loc.latitude, "lng": loc.longitude, "addr": loc.address}
    except: pass
    return {"success": False, "lat": 39.9042, "lng": 116.4074, "msg": "使用默认北京坐标"}

def call_ai_analysis(api_key, base_url, context):
    if not api_key: return "⚠️ 请配置 API Key 启用 AI 解盘"
    
    headers = {"Authorization": f"Bearer {api_key}"}
    prompt = f"""
你是一位精通《周易》、河图洛书、三命通会的命理宗师，请根据以下信息给出深刻而富有诗意的终极分析（控制在300字以内）：
{context}

请结合河图洛书数理、八字五行生克、大运流年，总结此人一生运势轨迹，语言优美、哲理深远。
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
# 4. 核心引擎（保持不变）
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
        
        self.year_pillar = self.bazi.getYear()
        self.month_pillar = self.bazi.getMonth()
        self.day_pillar = self.bazi.getDay()
        self.time_pillar = self.bazi.getTime()
        
        self.seed = hash((self.year_pillar, self.month_pillar, self.day_pillar, self.time_pillar, hour, minute, lat, lng))
        random.seed(self.seed)
        np.random.seed(self.seed % (2**32))
        
        self.true_solar_diff = (lng - 120.0) * 4
        self.day_gan_num = self._gan_to_hetu(self.bazi.getDayGan())
        self.wuxing_strength = self._calc_wuxing()
        self.favored = self._get_favored()
        self.shen_sha = self._calc_shen_sha()
        self.pattern = self._get_pattern()

    def _gan_to_hetu(self, gan):
        map_gan = {"甲":6, "乙":1, "丙":9, "丁":4, "戊":5, "己":10, "庚":2, "辛":7, "壬":3, "癸":8}
        return map_gan.get(gan, 5)

    def _calc_wuxing(self):
        cnt = {"金":0, "木":0, "水":0, "火":0, "土":0}
        wx_map = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
                  "子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
        for p in [self.bazi.getYearGan(), self.bazi.getYearZhi(), self.bazi.getMonthGan(), self.bazi.getMonthZhi(),
                  self.bazi.getDayGan(), self.bazi.getDayZhi(), self.bazi.getTimeGan(), self.bazi.getTimeZhi()]:
            wx = wx_map.get(p)
            if wx: cnt[wx] += 1
        return cnt

    def _get_favored(self):
        day_wx = self.bazi.getDayWuXing()
        if day_wx not in self.wuxing_strength:
            day_wx = "土"
        weak = min(self.wuxing_strength, key=self.wuxing_strength.get)
        return weak

    def _get_pattern(self):
        patterns = [
            ("正官格", "一生正直清廉，宜从公职"),
            ("七杀格", "胆大心雄，宜创业开拓"),
            ("食神格", "福禄双全，享口福之乐"),
            ("伤官格", "才华横溢，名利双收"),
            ("正财格", "勤俭持家，财源稳定"),
            ("偏财格", "横财就手，人脉广阔"),
            ("印绶格", "学识渊博，贵人扶持")
        ]
        return random.choice(patterns)

    def _calc_shen_sha(self):
        res = []
        if random.random() > 0.5: res.append({"name": "天乙贵人", "type": "gold", "desc": "贵人扶助，一生多助"})
        if random.random() > 0.4: res.append({"name": "文昌贵人", "type": "purple", "desc": "聪明智慧，科名显赫"})
        if random.random() > 0.5: res.append({"name": "桃花星", "type": "pink", "desc": "人缘极佳，异性缘旺"})
        if random.random() > 0.4: res.append({"name": "驿马星", "type": "blue", "desc": "动中生财，宜远行发展"})
        if not res: res.append({"name": "命格平稳", "type": "gray", "desc": "安稳厚重，自力更生"})
        return res

    def _get_year_yun(self, age):
        base = (self.day_gan_num + age) % 10
        if base == 0: base = 10
        yun_map = {1:"水运", 2:"金运", 3:"水运", 4:"木运", 5:"土运", 6:"木运", 7:"火运", 8:"土运", 9:"金运", 10:"土运"}
        return yun_map.get(base, "土运")

    def generate_life_kline(self):
        data = []
        price = 100.0
        lows = []
        
        for age in range(0, 101):
            yun = self._get_year_yun(age)
            
            base_score = 0
            if yun[:-1] == self.favored: base_score += 10
            
            bonus = len(self.shen_sha) * 3
            hetu_wave = np.sin(age / 9 * np.pi) * 8
            noise = np.random.normal(0, 5)
            change = base_score / 2 + bonus / 4 + hetu_wave + noise
            
            if age % 12 == 0 and age > 0: change -= 16
            
            close = max(10, price + change)
            if change < -12: lows.append(age)
            
            status = "大吉大利" if change > 14 else ("亨通顺利" if change > 6 else ("低谷考验" if change < -12 else "平稳有序"))
            
            data.append({
                "年龄": age, "年份": self.birth_date.year + age, "开盘": price, "收盘": close,
                "最高": close + abs(change)*1.5, "最低": price - abs(change)*1.5,
                "状态": status, "当年大运": yun
            })
            price = close
        
        df = pd.DataFrame(data)
        df['十年均线'] = df['收盘'].rolling(10).mean()
        df['三十年趋势'] = df['收盘'].rolling(30).mean()
        self.low_ages = ", ".join(map(str, lows[:6])) + (" 等" if len(lows)>6 else "")
        return df

    def generate_daily_kline(self, year):
        start = date(year, 1, 1)
        days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        data = []
        price = 100.0
        random.seed(self.seed + year)
        for i in range(days):
            curr = start + timedelta(days=i)
            change = random.gauss(0, 3.5)
            close = max(30, price + change)
            data.append({"日期": curr, "开盘": price, "收盘": close, "最高": close + abs(change), "最低": price - abs(change)})
            price = close
        return pd.DataFrame(data)

    def get_ai_context(self):
        bazi_str = f"{self.year_pillar}　{self.month_pillar}　{self.day_pillar}　{self.time_pillar}"
        shensha_names = [s['name'] for s in self.shen_sha]
        return f"性别:{self.gender}，出生:{self.birth_date} {self.hour}:{self.minute:02}，八字:{bazi_str}，日干河图数:{self.day_gan_num}，喜用神:{self.favored}，格局:{self.pattern[0]}，神煞:{shensha_names}"

# ==========================================
# 5. 主程序（出生年倒序 + 流年日运文字中文）
# ==========================================
def main():
    with st.sidebar:
        st.markdown("<h2 style='text-align:center; color:#7b1fa2;'>🌟 天机控制台</h2>", unsafe_allow_html=True)
        
        with st.expander("🤖 AI 解盘配置（可选）"):
            api_base = st.text_input("API地址", "https://api.openai.com/v1")
            api_key = st.text_input("密钥", type="password")
        
        st.markdown("---")
        st.subheader("📜 缘主档案")
        name = st.text_input("姓名", "神秘客人")
        gender = st.selectbox("性别", ["男", "女"])
        
        st.markdown("#### 📅 出生时间")
        col_y, col_m, col_d = st.columns(3)
        current_year = datetime.now().year
        # 出生年倒序：从当前年（2025）开始到1900
        years_desc = list(range(current_year, 1899, -1))
        year = col_y.selectbox("年", years_desc, index=0)  # 默认当前年（第一个）
        month = col_m.selectbox("月", range(1,13), format_func=lambda x: f"{x}月")
        day_max = (date(year, month+1, 1) - timedelta(days=1)).day if month < 12 else 31
        day = col_d.selectbox("日", range(1, day_max+1), format_func=lambda x: f"{x}日")
        
        col_h, col_min = st.columns(2)
        hour = col_h.selectbox("时辰", range(24))
        minute = col_min.selectbox("分钟", range(60))
        
        st.markdown("#### 📍 出生地点（精确到县镇）")
        full_addr = "北京市"
        if ADMIN_DATA:
            provs = [p['name'] for p in ADMIN_DATA]
            prov = st.selectbox("省份/直辖市", provs)
            prov_d = next(p for p in ADMIN_DATA if p['name']==prov)
            
            cities = prov_d.get('children', [])
            if prov in ["北京市","上海市","天津市","重庆市"] and cities:
                city_d = cities[0]
                city = prov
            else:
                city_names = [c['name'] for c in cities] if cities else [prov]
                city = st.selectbox("地级市", city_names)
                city_d = next(c for c in cities if c['name']==city) if cities else prov_d
            
            counties = city_d.get('children', [])
            county_names = [c['name'] for c in counties] if counties else ["市辖区"]
            county = st.selectbox("区/县", county_names)
            county_d = next(c for c in counties if c['name']==county) if counties else city_d
            
            towns = county_d.get('children', [])
            town_names = [t['name'] for t in towns] if towns else ["无镇/乡"]
            town = st.selectbox("镇/乡/街道", town_names)
            
            detail = st.text_input("详细地址（如村、医院、门牌）", "人民医院")
            full_addr = f"{prov}{city}{county}{town if town != '无镇/乡' else ''}{detail}"
        else:
            st.warning("未加载区划数据，使用默认")
            full_addr = st.text_input("手动输入完整地址", "北京市朝阳区三里屯")
        
        if st.button("🛰️ 精准定位 & 排盘", type="primary", use_container_width=True):
            with st.spinner("天机正在推演..."):
                loc_res = get_precise_location(full_addr)
                st.session_state.loc = loc_res
                st.success("排盘完成！")

    loc = st.session_state.get('loc', {'lat':39.9042, 'lng':116.4074})
    b_date = date(year, month, day)
    engine = DestinyEngine(b_date, hour, minute, loc['lat'], loc['lng'], gender)
    df_life = engine.generate_life_kline()

    st.markdown(f"<h1 style='text-align:center;'>🌌 {name} · 全息命盘</h1>", unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)
    bazi_str = f"{engine.year_pillar}　{engine.month_pillar}　{engine.day_pillar}　{engine.time_pillar}"
    col1.markdown(f"<div class='metric-box'><div class='metric-title'>八字</div><div class='metric-value'>{bazi_str}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-box'><div class='metric-title'>格局</div><div class='metric-value'>{engine.pattern[0]}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-box'><div class='metric-title'>喜用神</div><div class='metric-value'>{engine.favored}</div></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='metric-box'><div class='metric-title'>虚岁</div><div class='metric-value'>{datetime.now().year - year + 1}</div></div>", unsafe_allow_html=True)
    col5.markdown(f"<div class='metric-box'><div class='metric-title'>真太阳时差</div><div class='metric-value'>{engine.true_solar_diff:+.1f}分</div></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 百年人生K线", "📅 流年日运", "🌟 神煞星耀", "🔥 运势热力图", "🔮 AI 大师解盘"])

    with tab1:
        st.markdown("### 📈 百年人生运势 · 专属K线（河图洛书 + 八字真实推演）")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_life['年龄'], open=df_life['开盘'], high=df_life['最高'],
            low=df_life['最低'], close=df_life['收盘'],
            increasing_line_color='#ff4081', decreasing_line_color='#40c4ff',
            name='人生运势', text=df_life['当年大运'] + " · " + df_life['状态'],
            hovertemplate="<b>%{x}岁（%{text}）</b><br>开盘: %{open:.1f}<br>收盘: %{close:.1f}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(x=df_life['年龄'], y=df_life['十年均线'], line=dict(color='#ffab40', width=3, dash='dot'), name='十年大运'))
        fig.add_trace(go.Scatter(x=df_life['年龄'], y=df_life['三十年趋势'], line=dict(color='#7c4dff', width=3), name='一生趋势'))
        fig.update_layout(height=600, template="plotly_dark", title="你的人生运势曲线（独一无二）",
                          xaxis_title="年龄", yaxis_title="运势能量")
        if engine.low_ages:
            st.warning(f"⚠️ 低谷年龄：{engine.low_ages}")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 每年大运示例")
        sample = df_life.iloc[::10][['年龄', '年份', '当年大运', '状态']]
        st.dataframe(sample, use_container_width=True)

    with tab2:
        st.markdown("### 📅 流年每日运势")
        # 流年查询滑块从1990开始
        q_year = st.slider("选择查询年份", min_value=1990, max_value=datetime.now().year + 20, value=datetime.now().year, step=1)
        df_daily = engine.generate_daily_kline(q_year)
        fig_d = go.Figure(go.Candlestick(x=df_daily['日期'], open=df_daily['开盘'], high=df_daily['最高'],
                                         low=df_daily['最低'], close=df_daily['收盘'],
                                         increasing_line_color='#ff1744', decreasing_line_color='#00e676',
                                         name='每日运势'))
        fig_d.update_layout(height=500, template="plotly_white", title=f"{q_year}年 · 每日运势波动")
        st.plotly_chart(fig_d, use_container_width=True)

    with tab3:
        st.markdown("### 🌟 命中神煞星耀")
        for item in engine.shen_sha:
            st.markdown(f"<span class='shensha-tag tag-{item['type']}'>{item['name']}</span>　{item['desc']}", unsafe_allow_html=True)
        st.markdown(f"<br><small>格局评语：{engine.pattern[1]}</small>", unsafe_allow_html=True)

    with tab4:
        st.markdown("### 🔥 全年运势热力图（红旺蓝弱）")
        current_year = datetime.now().year
        df_daily = engine.generate_daily_kline(current_year)
        df_daily['日期'] = pd.to_datetime(df_daily['日期'])
        df_daily['月'] = df_daily['日期'].dt.month
        df_daily['日'] = df_daily['日期'].dt.day
        fig_heat = px.density_heatmap(df_daily, x="日", y="月", z="收盘", 
                                     color_continuous_scale="plasma", nbinsx=31, nbinsy=12,
                                     title=f"{current_year}年运势热力分布")
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab5:
        st.markdown("### 🔮 AI 大师 · 终极解盘（融合河图洛书）")
        if st.button("🧙‍♂️ 呼叫大师推演天机", type="primary"):
            with st.spinner("大师正在观河图、布洛书..."):
                analysis = call_ai_analysis(api_key, api_base, engine.get_ai_context())
                st.markdown(f"<div style='background:#f3e5f5; padding:20px; border-radius:15px; border-left:6px solid #9c27b0;'>{analysis}</div>", unsafe_allow_html=True)
        else:
            st.info("配置密钥后点击，即可获得融合河图洛书数理的专属解盘")

if __name__ == "__main__":
    if 'loc' not in st.session_state:
        st.session_state.loc = {'lat':39.9042, 'lng':116.4074}
    main()