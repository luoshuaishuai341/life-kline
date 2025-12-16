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
# 1. 页面配置与样式
# ==========================================
st.set_page_config(
    page_title="天机 · 全息命理终端 V15",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #f7f9fc; color: #333; }
    h1, h2, h3 { font-family: 'PingFang SC', sans-serif; color: #4a148c !important; }
    
    /* 关键指标卡片 */
    .metric-box {
        background: #fff; padding: 15px; border-radius: 8px;
        border-left: 4px solid #4a148c; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .metric-title { font-size: 14px; color: #666; }
    .metric-value { font-size: 20px; font-weight: bold; color: #333; }
    
    /* 神煞标签 */
    .shensha-tag {
        display: inline-block; padding: 4px 10px; margin: 2px;
        border-radius: 15px; font-size: 12px; font-weight: bold; color: white;
    }
    .tag-pink { background: #e91e63; } /* 桃花 */
    .tag-gold { background: #fbc02d; color: #333; } /* 贵人 */
    .tag-blue { background: #2196f3; } /* 驿马 */
    .tag-gray { background: #9e9e9e; } /* 无 */
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据加载 (恢复全省份支持)
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
    ua = f"life_kline_v15_{random.randint(10000,99999)}"
    try:
        loc = Nominatim(user_agent=ua).geocode(f"China {addr}" if "China" not in addr else addr, timeout=6)
        if loc: return {"success": True, "lat": loc.latitude, "lng": loc.longitude, "addr": loc.address}
    except: pass
    return {"success": False, "lat": 39.9042, "lng": 116.4074, "msg": "定位降级，使用默认坐标"}

def call_ai_analysis(api_key, base_url, context):
    if not api_key: return "⚠️ 请在左侧侧边栏输入 API Key 以启用 AI 智能分析。"
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = f"""
    作为一位精通《三命通会》与现代心理学的命理大师，请根据以下数据进行分析：
    {context}
    
    请输出：
    1. **八字格局简评** (50字以内)
    2. **未来3年运势预警** (重点看K线低谷)
    3. **人生建议** (结合神煞与喜用神)
    """
    data = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]}
    
    try:
        res = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=15)
        if res.status_code == 200: return res.json()['choices'][0]['message']['content']
        return f"AI 响应错误: {res.text}"
    except Exception as e: return f"网络错误: {e}"

# ==========================================
# 4. 核心命理引擎 (V15 增强版)
# ==========================================
class DestinyEngine:
    def __init__(self, b_date, h, m, lat, lng, gender):
        self.birth_date = b_date
        self.gender = gender
        self.solar = Solar.fromYmdHms(b_date.year, b_date.month, b_date.day, h, m, 0)
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()
        self.seed = hash((b_date, h, m, lat))
        
        self.true_solar_diff = (lng - 120.0) * 4
        self.wuxing_strength = self._calc_wuxing()
        self.favored = self._calc_favored()
        self.shen_sha = self._calc_shen_sha() # 新增神煞

    def _calc_wuxing(self):
        # 统计五行分数
        cnt = {"金":0, "木":0, "水":0, "火":0, "土":0}
        wx_map = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
                  "寅":"木","卯":"木","巳":"火","午":"火","申":"金","酉":"金","亥":"水","子":"水","辰":"土","戌":"土","丑":"土","未":"土"}
        pillars = [self.bazi.getYearGan(), self.bazi.getYearZhi(), self.bazi.getMonthGan(), self.bazi.getMonthZhi(),
                   self.bazi.getDayGan(), self.bazi.getDayZhi(), self.bazi.getTimeGan(), self.bazi.getTimeZhi()]
        for p in pillars:
            if p in wx_map: cnt[wx_map[p]] += 1
        return cnt

    def _calc_favored(self):
        # 简单喜用神：取最弱的五行 (模拟扶抑格)
        sorted_wx = sorted(self.wuxing_strength.items(), key=lambda x:x[1])
        return sorted_wx[0][0]

    def _calc_shen_sha(self):
        """(新增) 计算神煞：桃花、驿马、贵人"""
        day_zhi = self.bazi.getDayZhi()
        year_zhi = self.bazi.getYearZhi()
        day_gan = self.bazi.getDayGan()
        res = []
        
        # 1. 桃花 (以日支查) - 申子辰在酉, 寅午戌在卯, 巳酉丑在午, 亥卯未在子
        taohua_map = {"申":"酉", "子":"酉", "辰":"酉", "寅":"卯", "午":"卯", "戌":"卯", 
                      "巳":"午", "酉":"午", "丑":"午", "亥":"子", "卯":"子", "未":"子"}
        target = taohua_map.get(day_zhi)
        if target in [self.bazi.getYearZhi(), self.bazi.getMonthZhi(), self.bazi.getTimeZhi()]:
            res.append({"name": "咸池桃花", "type": "pink", "desc": "异性缘佳，魅力独特"})
            
        # 2. 驿马 (以年支查) - 变动之星
        yima_map = {"申":"寅", "子":"寅", "辰":"寅", "寅":"申", "午":"申", "戌":"申",
                    "巳":"亥", "酉":"亥", "丑":"亥", "亥":"巳", "卯":"巳", "未":"巳"}
        target = yima_map.get(year_zhi)
        if target in [self.bazi.getMonthZhi(), self.bazi.getDayZhi(), self.bazi.getTimeZhi()]:
            res.append({"name": "驿马星", "type": "blue", "desc": "奔波劳碌，利于出国/外地发展"})
            
        # 3. 天乙贵人 (以日干查) - 解难之星
        # 甲戊并牛羊, 乙己鼠猴乡, 丙丁猪鸡位, 壬癸rabbit/snake, 庚辛逢马虎
        nobleman_map = {"甲":["丑","未"], "戊":["丑","未"], "庚":["午","寅"], "辛":["午","寅"],
                        "乙":["子","申"], "己":["子","申"], "丙":["亥","酉"], "丁":["亥","酉"],
                        "壬":["卯","巳"], "癸":["卯","巳"]}
        targets = nobleman_map.get(day_gan, [])
        for t in targets:
            if t in [self.bazi.getYearZhi(), self.bazi.getMonthZhi(), self.bazi.getTimeZhi()]:
                res.append({"name": "天乙贵人", "type": "gold", "desc": "逢凶化吉，遇难呈祥"})
                break
                
        if not res: res.append({"name": "平稳", "type": "gray", "desc": "命格平实，需靠自我奋斗"})
        return res

    def get_wuxing_rel(self, wx1, wx2):
        # 生克关系判断
        gen = {"木":"火", "火":"土", "土":"金", "金":"水", "水":"木"}
        ovr = {"木":"土", "土":"水", "水":"火", "火":"金", "金":"木"}
        if wx1 == wx2: return 1 # 同
        if gen.get(wx1) == wx2: return 2 # 生
        if ovr.get(wx1) == wx2: return -2 # 克
        if gen.get(wx2) == wx1: return 0.5 # 被生
        if ovr.get(wx2) == wx1: return -1 # 被克
        return 0

    def generate_life_kline(self):
        """生成人生大运K线"""
        data = []
        price = 100.0
        random.seed(self.seed)
        
        # 大运周期 (10年一运)
        dayun_cycle = ["木", "火", "土", "金", "水"]
        
        for age in range(101):
            year = self.birth_date.year + age
            dayun_wx = dayun_cycle[(self.seed // 10 + age // 10) % 5]
            
            # 基础分：大运 vs 喜用
            score = self.get_wuxing_rel(dayun_wx, self.favored) * 3.0
            
            # 随机流年波动
            noise = random.normalvariate(0, 2.5)
            change = score + noise
            
            # 本命年打击
            if age > 0 and age % 12 == 0: change -= 6
            
            close = max(20, price + change)
            status = "大吉" if change > 5 else ("上升" if change > 2 else ("低迷" if change < -5 else "盘整"))
            
            data.append({
                "Age": age, "Year": year, "Open": price, "Close": close,
                "High": close + abs(change), "Low": price - abs(change),
                "Status": status, "Dayun": dayun_wx
            })
            price = close
        
        df = pd.DataFrame(data)
        df['MA10'] = df['Close'].rolling(10).mean()
        return df

    def generate_daily_kline(self, year):
        """(恢复功能) 生成日运K线"""
        start = date(year, 1, 1)
        days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        data = []
        price = 100.0
        
        # 每日五行模拟 (日干支太复杂，这里用模拟五行流转)
        daily_wx_cycle = ["木","火","土","金","水"]
        
        random.seed(hash((year, self.seed)))
        
        for i in range(days):
            curr_date = start + timedelta(days=i)
            day_wx = daily_wx_cycle[i % 5]
            
            # 每日运势：日五行 vs 喜用
            score = self.get_wuxing_rel(day_wx, self.favored) * 2.0
            change = score + random.gauss(0, 3.0)
            
            close = max(40, price + change)
            status = "宜进取" if change > 0 else "宜守成"
            
            data.append({
                "Date": curr_date, "Open": price, "Close": close,
                "High": close + abs(change), "Low": price - abs(change),
                "Status": status, "Score": int(close)
            })
            price = close # 价格连贯
        return pd.DataFrame(data)

    def get_context_for_ai(self):
        return f"性别:{self.gender}, 八字:{self.bazi.getYearGan()}..{self.bazi.getTimeZhi()}, 喜用神:{self.favored}, 神煞:{[s['name'] for s in self.shen_sha]}"

# ==========================================
# 5. 主程序 UI
# ==========================================
def main():
    # --- 侧边栏 ---
    with st.sidebar:
        st.header("⚙️ 终端控制")
        with st.expander("🤖 AI 接口配置"):
            api_base = st.text_input("API Base URL", "https://api.openai.com/v1")
            api_key = st.text_input("API Key", type="password")

        st.markdown("---")
        st.header("📂 档案录入")
        name = st.text_input("姓名", "某君")
        gender = st.selectbox("性别", ["男", "女"])
        
        # 日期 (中文下拉框)
        c1, c2, c3 = st.columns([1.2,1,1])
        y = c1.selectbox("年", range(1930, 2026), index=60)
        m = c2.selectbox("月", range(1, 13), format_func=lambda x:f"{x}月")
        max_d = 31 if m in [1,3,5,7,8,10,12] else (30 if m!=2 else (29 if y%4==0 else 28))
        d = c3.selectbox("日", range(1, max_d+1), format_func=lambda x:f"{x}日")
        
        # 时间
        t1, t2 = st.columns(2)
        hh = t1.selectbox("时", range(24), index=12)
        mm = t2.selectbox("分", range(60))
        
        # 地址 (级联恢复)
        st.markdown("#### 📍 出生地")
        if ADMIN_DATA:
            provs = [p['name'] for p in ADMIN_DATA]
            prov = st.selectbox("省/直辖市", provs)
            prov_d = next(p for p in ADMIN_DATA if p['name']==prov)
            
            cities = prov_d.get('children', [])
            if prov in ["北京市","上海市","天津市","重庆市"]:
                city_d = cities[0] if cities else prov_d
                city = prov
            else:
                c_names = [c['name'] for c in cities] if cities else [prov]
                city = st.selectbox("城市", c_names)
                city_d = next((c for c in cities if c['name']==city), prov_d)
                
            areas = city_d.get('children', [])
            area_names = [a['name'] for a in areas] if areas else ["市辖区"]
            area = st.selectbox("区/县", area_names)
            
            detail = st.text_input("详细地址", "第一人民医院")
            full_addr = f"{prov}{city if city!=prov else ''}{area}{detail}"
        else:
            st.error("⚠️ 缺少 pcas-code.json")
            full_addr = "北京市"

        if st.button("🛰️ 定位排盘", type="primary"):
            st.session_state.loc = get_precise_location(full_addr)

    # --- 核心逻辑 ---
    loc = st.session_state.get('loc', {'lat':39.9, 'lng':116.4, 'success':False})
    b_date = date(y, m, d)
    engine = DestinyEngine(b_date, hh, mm, loc['lat'], loc['lng'], gender)
    info = engine.get_basic_info() if hasattr(engine, 'get_basic_info') else {} # 兼容

    st.title(f"🌌 全息命盘: {name}")
    
    # 顶部指标卡
    k1, k2, k3, k4 = st.columns(4)
    bazi_str = f"{engine.bazi.getYearGan()}{engine.bazi.getYearZhi()} {engine.bazi.getMonthGan()}{engine.bazi.getMonthZhi()} {engine.bazi.getDayGan()}{engine.bazi.getDayZhi()} {engine.bazi.getTimeGan()}{engine.bazi.getTimeZhi()}"
    k1.markdown(f"<div class='metric-box'><div class='metric-title'>八字乾坤</div><div class='metric-value'>{bazi_str}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='metric-box'><div class='metric-title'>喜用神</div><div class='metric-value' style='color:#e91e63'>{engine.favored}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='metric-box'><div class='metric-title'>虚岁</div><div class='metric-value'>{datetime.now().year - y + 1}</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='metric-box'><div class='metric-title'>真太阳时差</div><div class='metric-value'>{engine.true_solar_diff:.1f}m</div></div>", unsafe_allow_html=True)

    # --- Tab 导航 (核心功能区) ---
    tab1, tab2, tab3, tab4 = st.tabs(["🔮 命盘概览 & AI", "📈 人生大势 K 线", "📅 流年日运 K 线", "🌟 神煞与热力图"])

    with tab1:
        c_l, c_r = st.columns([2, 1])
        with c_l:
            st.subheader("⚡ 五行能量分布")
            w = engine.wuxing_strength
            w_df = pd.DataFrame({"五行": w.keys(), "能量": w.values()})
            fig_bar = px.bar(w_df, x="五行", y="能量", color="五行", color_discrete_map={"金":"#FFD700","木":"#4CAF50","水":"#2196F3","火":"#F44336","土":"#795548"})
            st.plotly_chart(fig_bar, use_container_width=True)
            
            if st.button("✨ 呼叫 AI 大师解盘"):
                with st.spinner("AI 大师正在推演天机..."):
                    analysis = call_ai_analysis(api_key, api_base, engine.get_context_for_ai())
                    st.info(analysis)
        with c_r:
            st.subheader("🌌 命中神煞")
            for item in engine.shen_sha:
                st.markdown(f"""
                <div style='background:white; padding:10px; border-radius:8px; margin-bottom:10px; border-left:4px solid {item['type']}'>
                    <span class='shensha-tag tag-{item['type']}'>{item['name']}</span>
                    <br><small>{item['desc']}</small>
                </div>
                """, unsafe_allow_html=True)

    with tab2:
        st.subheader("📈 百年人生运势推演")
        df_life = engine.generate_life_kline()
        fig_life = go.Figure()
        fig_life.add_trace(go.Candlestick(
            x=df_life['Age'], open=df_life['Open'], high=df_life['High'], low=df_life['Low'], close=df_life['Close'],
            increasing_line_color='#ef5350', decreasing_line_color='#26a69a', name='年运',
            text=df_life['Status'], hovertemplate="<b>%{x}岁</b><br>状态: %{text}<br>收盘: %{close:.1f}<extra></extra>"
        ))
        fig_life.add_trace(go.Scatter(x=df_life['Age'], y=df_life['MA10'], line=dict(color='#ffb300', width=2), name='十年大运'))
        fig_life.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig_life, use_container_width=True)

    with tab3:
        st.subheader("📅 流年每日运势")
        q_year = st.number_input("选择年份", 1900, 2100, datetime.now().year)
        df_daily = engine.generate_daily_kline(q_year)
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Candlestick(
            x=df_daily['Date'], open=df_daily['Open'], high=df_daily['High'], low=df_daily['Low'], close=df_daily['Close'],
            increasing_line_color='#ef5350', decreasing_line_color='#26a69a', name='日运'
        ))
        fig_daily.update_layout(height=500, template="plotly_white", title=f"{q_year}年 每日运势波动")
        st.plotly_chart(fig_daily, use_container_width=True)

    with tab4:
        st.subheader("🔥 年度运势热力图")
        st.caption("颜色越红代表运势越旺，越蓝代表运势越低迷。")
        # 复用上面的 df_daily 数据绘制热力图
        df_daily['Month'] = df_daily['Date'].apply(lambda x: x.month)
        df_daily['Day'] = df_daily['Date'].apply(lambda x: x.day)
        
        fig_heat = px.density_heatmap(df_daily, x="Day", y="Month", z="Score", 
                                      color_continuous_scale="RdBu_r", nbinsx=31, nbinsy=12)
        fig_heat.update_layout(height=400)
        st.plotly_chart(fig_heat, use_container_width=True)

if __name__ == "__main__":
    main()