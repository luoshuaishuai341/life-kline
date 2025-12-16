import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from lunar_python import Solar, Lunar
from datetime import datetime, date, timedelta
import random
import json
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError

# ==========================================
# 1. 页面配置与样式
# ==========================================
st.set_page_config(
    page_title="天机 · 全息八字排盘系统 Ultimate",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #fcfcfc; color: #333; }
    section[data-testid="stSidebar"] { background-color: #f0f2f6; border-right: 1px solid #e0e0e0; }
    h1, h2, h3 { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #8e24aa !important; }
    
    /* 仪表盘卡片样式 */
    .metric-card {
        background: white; border-radius: 10px; padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eee;
        text-align: center; margin-bottom: 15px;
    }
    .metric-label { color: #666; font-size: 0.9em; margin-bottom: 5px; }
    .metric-value { color: #8e24aa; font-size: 1.8em; font-weight: bold; }
    
    .location-success { color: #155724; background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; }
    .location-warning { color: #856404; background-color: #fff3cd; border: 1px solid #ffeeba; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 基础数据加载
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
                    return json.load(file), f
            except: continue
    return None, None

ADMIN_DATA, _ = load_admin_data()

# ==========================================
# 3. 定位服务 (修复 KeyError 核心)
# ==========================================
@st.cache_data(show_spinner=False)
def get_precise_location(addr):
    ua = f"life_kline_{random.randint(10000,99999)}"
    # 默认坐标 (北京) - 用于降级
    default_res = {"success": False, "lat": 39.9042, "lng": 116.4074, "msg": "定位失败，已使用默认坐标"}
    
    try:
        geolocator = Nominatim(user_agent=ua)
        loc = geolocator.geocode(f"China {addr}" if "China" not in addr else addr, timeout=8)
        
        if loc:
            return {
                "success": True, 
                "lat": loc.latitude, 
                "lng": loc.longitude, 
                "address": loc.address
            }
        else:
            # 即使没找到，也要返回 lat/lng，防止 KeyError
            return default_res
            
    except Exception as e: 
        # 发生异常时，同样返回带 lat/lng 的默认值
        default_res["msg"] = f"定位服务异常: {str(e)}"
        return default_res

# ==========================================
# 4. 核心命理引擎
# ==========================================
class DestinyEngine:
    def __init__(self, b_date, h, m, s, lat, lng, gender):
        self.birth_date = b_date
        self.gender = gender 
        self.solar = Solar.fromYmdHms(b_date.year, b_date.month, b_date.day, h, m, s)
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()
        self.seed = hash((b_date, h, m, s, lat))
        
        # 经度校正
        self.true_solar_time_diff = (lng - 120.0) * 4

        # 计算五行强弱
        self.wuxing_strength = self._calc_wuxing_strength()
        # 计算喜用神
        self.favored_element = self._calc_favored_element()
        # 计算本命卦
        self.ming_gua = self._calc_ming_gua()

    def _calc_wuxing_strength(self):
        """计算五行分数"""
        strength = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
        wx_map = {
            "甲":"木", "乙":"木", "寅":"木", "卯":"木",
            "丙":"火", "丁":"火", "巳":"火", "午":"火",
            "戊":"土", "己":"土", "辰":"土", "戌":"土", "丑":"土", "未":"土",
            "庚":"金", "辛":"金", "申":"金", "酉":"金",
            "壬":"水", "癸":"水", "亥":"水", "子":"水"
        }
        pillars = [
            self.bazi.getYearGan(), self.bazi.getYearZhi(),
            self.bazi.getMonthGan(), self.bazi.getMonthZhi(),
            self.bazi.getDayGan(), self.bazi.getDayZhi(),
            self.bazi.getTimeGan(), self.bazi.getTimeZhi()
        ]
        
        for char in pillars:
            if char in wx_map:
                weight = 1.5 if char == self.bazi.getMonthZhi() else 1.0
                strength[wx_map[char]] += weight
        
        total = sum(strength.values()) or 1
        return {k: round(v/total*100, 1) for k,v in strength.items()}

    def _calc_favored_element(self):
        """简单计算喜用神"""
        day_master = self.bazi.getDayGan()
        gan_wx = {"甲":"木", "乙":"木", "丙":"火", "丁":"火", "戊":"土", "己":"土", "庚":"金", "辛":"金", "壬":"水", "癸":"水"}
        dm_wx = gan_wx.get(day_master, "木")
        
        sheng_ke_map = {"木":["水","木"], "火":["木","火"], "土":["火","土"], "金":["土","金"], "水":["金","水"]}
        friends = sheng_ke_map.get(dm_wx, [])
        friend_score = sum(self.wuxing_strength[wx] for wx in friends)
        
        is_strong = friend_score > 45 
        
        generate = {"木":"火", "火":"土", "土":"金", "金":"水", "水":"木"}
        if is_strong:
            return generate[dm_wx] 
        else:
            reverse_gen = {v:k for k,v in generate.items()}
            return reverse_gen[dm_wx]

    def _calc_ming_gua(self):
        """计算本命卦"""
        year = self.birth_date.year
        digits_sum = sum(int(d) for d in str(year))
        while digits_sum > 9: digits_sum = sum(int(d) for d in str(digits_sum))
        
        if self.gender == "男":
            res = 11 - digits_sum
        else:
            res = 4 + digits_sum
            
        while res > 9: res -= 9
        if res == 0: res = 9
        if res == 5: res = 2 if self.gender == "男" else 8
        
        gua_map = {1:"坎水", 2:"坤土", 3:"震木", 4:"巽木", 6:"乾金", 7:"兑金", 8:"艮土", 9:"离火"}
        return gua_map.get(res, "未知")

    def _get_year_wuxing(self, year):
        wuxing_cycle = ["金", "水", "木", "火", "土"]
        return wuxing_cycle[year % 5]

    def generate_optimized_life_kline(self):
        """五行生克生成人生K线"""
        data = []
        price = 100.0
        favored = self.favored_element 
        
        generate = {"木":"火", "火":"土", "土":"金", "金":"水", "水":"木"} 
        overcome = {"木":"土", "土":"水", "水":"火", "火":"金", "金":"木"}
        
        random.seed(self.seed)
        
        for age in range(101):
            year = self.birth_date.year + age
            current_year_wx = self._get_year_wuxing(year)
            
            change_pct = 0
            reason = ""
            
            if current_year_wx == favored:
                change_pct = 4.0 
                reason = f"流年{current_year_wx} 助旺喜用神"
            elif generate[current_year_wx] == favored:
                change_pct = 6.0 
                reason = f"流年{current_year_wx} 生扶喜用神"
            elif generate[favored] == current_year_wx:
                change_pct = 1.0 
                reason = f"喜用生流年"
            elif overcome[current_year_wx] == favored:
                change_pct = -5.0 
                reason = f"流年{current_year_wx} 克制喜用神"
            elif overcome[favored] == current_year_wx:
                change_pct = 2.0 
                reason = f"喜用克流年"
            
            noise = random.normalvariate(0, 1.5)
            final_change = change_pct + noise
            
            if age > 0 and age % 12 == 0:
                final_change -= 4
                reason = "本命年值太岁"
                
            close = max(30, price + final_change)
            
            if final_change > 4: status = "大吉"
            elif final_change > 1: status = "上升"
            elif final_change > -2: status = "平稳"
            else: status = "调整"
            
            data.append({
                "Age": age, "Year": year,
                "Open": price, "Close": close,
                "High": close + abs(final_change)*0.6,
                "Low": price - abs(final_change)*0.6,
                "Status": status,
                "Reason": reason
            })
            price = close
            
        df = pd.DataFrame(data)
        df['MA10'] = df['Close'].rolling(10).mean()
        return df

    def get_basic_info(self):
        return {
            "bazi_text": f"{self.bazi.getYearGan()}{self.bazi.getYearZhi()} {self.bazi.getMonthGan()}{self.bazi.getMonthZhi()} {self.bazi.getDayGan()}{self.bazi.getDayZhi()} {self.bazi.getTimeGan()}{self.bazi.getTimeZhi()}",
            "day_master": self.bazi.getDayGan(),
            "wuxing": self.wuxing_strength,
            "favored": self.favored_element,
            "ming_gua": self.ming_gua,
            "age": datetime.now().year - self.birth_date.year + 1,
            "nongli": f"{self.lunar.getYearInGanZhi()}年 {self.lunar.getMonthInChinese()}月{self.lunar.getDayInChinese()}",
            "shengxiao": self.lunar.getYearShengXiao(),
            "solar_diff": f"{self.true_solar_time_diff:.1f}min"
        }

# ==========================================
# 5. 主程序逻辑
# ==========================================
def main():
    with st.sidebar:
        st.header("📂 缘主信息")
        name = st.text_input("姓名", "某君")
        gender = st.selectbox("性别", ["男", "女"])
        
        st.markdown("#### 📅 出生信息")
        c1, c2, c3 = st.columns([1.2, 1, 1])
        curr_year = datetime.now().year
        y = c1.selectbox("年", range(1930, curr_year + 1), index=60)
        m = c2.selectbox("月", range(1, 13), format_func=lambda x:f"{x}月")
        
        # 动态计算天数
        if m in [1, 3, 5, 7, 8, 10, 12]: max_d = 31
        elif m in [4, 6, 9, 11]: max_d = 30
        else: max_d = 29 if (y%4==0 and (y%100!=0 or y%400==0)) else 28
        
        d = c3.selectbox("日", range(1, max_d + 1), format_func=lambda x:f"{x}日")
        
        t1, t2 = st.columns(2)
        hh = t1.selectbox("时", range(24), index=12)
        mm = t2.selectbox("分", range(60))
        
        st.markdown("#### 📍 地点定位")
        provs = [p['name'] for p in ADMIN_DATA] if ADMIN_DATA else ["北京市"]
        prov = st.selectbox("省份", provs)
        detail = st.text_input("详细地址", "市辖区")
        
        if st.button("🛰️ 排盘", type="primary", use_container_width=True):
            with st.spinner("正在测算天机..."):
                res = get_precise_location(f"{prov}{detail}")
                st.session_state.loc = res
    
    # 修复 KeyError：安全获取 lat/lng，如果不存在则使用默认值
    loc_state = st.session_state.get('loc', {})
    
    # 无论定位是否成功，这里都必须保证有值，否则 DestinyEngine 初始化会崩
    final_lat = loc_state.get('lat', 39.9042)
    final_lng = loc_state.get('lng', 116.4074)
    loc_msg = loc_state.get('msg', '等待定位')
    loc_success = loc_state.get('success', False)

    # 显示定位状态提示
    if loc_success:
        st.sidebar.markdown(f"<div class='location-success'>✅ {loc_state.get('address', '定位成功')}</div>", unsafe_allow_html=True)
    elif "失败" in loc_msg or "异常" in loc_msg:
         st.sidebar.markdown(f"<div class='location-warning'>⚠️ {loc_msg}</div>", unsafe_allow_html=True)
    
    # 实例化引擎
    b_date = date(y, m, d)
    # 这里传入的是安全的 final_lat/final_lng，绝对不会报错
    engine = DestinyEngine(b_date, hh, mm, 0, final_lat, final_lng, gender)
    info = engine.get_basic_info()
    
    # 页面标题
    st.title(f"🔮 天机命盘: {name}")
    
    # 顶部状态栏
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("八字", info['bazi_text'])
    c2.metric("本命卦", info['ming_gua'])
    c3.metric("喜用神", f"喜 {info['favored']}")
    c4.metric("真太阳时差", info['solar_diff'])
    st.divider()

    # --- 核心：命盘总览 Dashboard ---
    
    # 左侧：K线大势
    st.subheader("📈 人生大势走势 (五行生克推演)")
    
    df_life = engine.generate_optimized_life_kline()
    curr_age = info['age']
    
    fig = go.Figure()
    
    # K线
    fig.add_trace(go.Candlestick(
        x=df_life['Age'], open=df_life['Open'], high=df_life['High'], low=df_life['Low'], close=df_life['Close'],
        increasing_line_color='#8e24aa', decreasing_line_color='#2e7d32', 
        name='运势',
        text=df_life['Reason'], 
        hovertemplate=(
            "<b>%{x}岁 (%{text})</b><br>"
            "开盘: %{open:.1f}<br>"
            "收盘: %{close:.1f}<br>"
            "状态: %{text}<br>" 
            "<extra></extra>"
        )
    ))
    # 均线
    fig.add_trace(go.Scatter(x=df_life['Age'], y=df_life['MA10'], line=dict(color='#ffb300', width=2), name='十年大运'))
    
    fig.update_layout(
        height=450, template="plotly_white", xaxis_rangeslider_visible=False,
        title=dict(text=f"喜用神 [{info['favored']}] 生克流年推演图", x=0.5),
        hovermode="x unified"
    )
    # 标记当前
    fig.add_vline(x=curr_age, line_dash="dash", line_color="black")
    st.plotly_chart(fig, use_container_width=True)
    
    # 下方：五行八卦详情
    c_left, c_right = st.columns([1, 1])
    
    with c_left:
        st.subheader("⚡ 五行强弱分布")
        w = info['wuxing']
        
        w1, w2, w3, w4, w5 = st.columns(5)
        w1.markdown(f"<div class='metric-card'><div class='metric-label'>金</div><div class='metric-value'>{w['金']}%</div></div>", unsafe_allow_html=True)
        w2.markdown(f"<div class='metric-card'><div class='metric-label'>木</div><div class='metric-value'>{w['木']}%</div></div>", unsafe_allow_html=True)
        w3.markdown(f"<div class='metric-card'><div class='metric-label'>水</div><div class='metric-value'>{w['水']}%</div></div>", unsafe_allow_html=True)
        w4.markdown(f"<div class='metric-card'><div class='metric-label'>火</div><div class='metric-value'>{w['火']}%</div></div>", unsafe_allow_html=True)
        w5.markdown(f"<div class='metric-card'><div class='metric-label'>土</div><div class='metric-value'>{w['土']}%</div></div>", unsafe_allow_html=True)
        
        # 雷达图
        vals = list(w.values())
        cats = list(w.keys())
        fig_r = go.Figure(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]], fill='toself', line_color='#8e24aa'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=300, margin=dict(t=20,b=20))
        st.plotly_chart(fig_r, use_container_width=True)

    with c_right:
        st.subheader("☯️ 八卦命理解析")
        
        gua_img_map = {
            "乾金": "☰", "兑金": "☱", "离火": "☲", "震木": "☳", 
            "巽木": "☴", "坎水": "☵", "艮土": "☶", "坤土": "☷"
        }
        gua_icon = gua_img_map.get(info['ming_gua'], "☯️")
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color: white; padding: 30px; border-radius: 15px; text-align: center;">
            <h1 style="color:white; font-size: 80px; margin: 0;">{gua_icon}</h1>
            <h2 style="color:white; margin: 10px 0;">{info['ming_gua']} 命</h2>
            <p style="opacity: 0.8;">东四命 / 西四命 自动推演</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        st.info(f"**五行喜忌建议**：\n\n您的八字喜 **{info['favored']}**。建议多穿戴对应颜色的服饰，或往对应方位发展。\n\n"
                f"例如：喜火者宜穿红，往南方发展；喜水者宜穿黑，往北方发展。")

if __name__ == "__main__":
    main()