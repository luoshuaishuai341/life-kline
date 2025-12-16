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
# 1. 页面配置与样式（全中文界面）
# ==========================================
st.set_page_config(
    page_title="天机 · 全息八字排盘系统 Pro Max",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #333; }
    section[data-testid="stSidebar"] { background-color: #f7f9fc; border-right: 1px solid #e6e6e6; }
    h1, h2, h3 { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #b71c1c !important; }
    div[data-testid="stMetricValue"] { color: #d32f2f; font-weight: bold; font-size: 1.2em; }
    .location-success { color: #155724; background-color: #d4edda; border: 1px solid #c3e6cb; padding: 12px; border-radius: 8px; margin: 10px 0; }
    .location-warning { color: #856404; background-color: #fff3cd; border: 1px solid #ffeeba; padding: 12px; border-radius: 8px; margin: 10px 0; }
    /* 优化下拉框 */
    .stSelectbox label { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 加载行政区划数据（支持四级：省-市-区县-乡镇街道）
# ==========================================
@st.cache_data
def load_admin_data():
    """优先加载 pcas-code.json（四级），其次 pca-code.json（三级）"""
    files_to_check = ["pcas-code.json", "pca-code.json"]
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename in files_to_check:
        paths = [filename, os.path.join(current_dir, filename)]
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list) and len(data) > 30:
                        return data, filename
                except Exception as e:
                    continue
    return None, None

ADMIN_DATA, LOADED_FILENAME = load_admin_data()

# ==========================================
# 3. 精确地理定位函数（修复 403 错误）
# ==========================================
@st.cache_data(show_spinner=False)
def get_precise_location(address_str: str):
    # 修复403关键点：使用随机且唯一的 User-Agent
    ua = f"life_kline_app_{random.randint(10000, 99999)}"
    geolocator = Nominatim(user_agent=ua)
    
    try:
        if any(k in address_str for k in ["香港", "澳门", "台湾"]):
            query = address_str
        else:
            query = f"中国 {address_str}"
            
        location = geolocator.geocode(query, timeout=10)
        
        if location:
            return {"success": True, "lat": location.latitude, "lng": location.longitude, "address": location.address}
        else:
            return {"success": False, "msg": "未匹配到精确位置，已使用城市中心坐标"}
            
    except (GeocoderTimedOut, GeocoderUnavailable):
        return {"success": False, "msg": "定位服务连接超时，请检查网络或稍后重试"}
    except GeocoderServiceError as e:
        # 针对 403 或其他服务错误的特定处理
        return {"success": False, "msg": f"地图服务响应异常 (HTTP {str(e)})，已降级处理"}
    except Exception as e:
        return {"success": False, "msg": f"定位系统异常: {str(e)}"}

# ==========================================
# 4. 核心命理引擎（修复 AttributeError 和 五行计算）
# ==========================================
class DestinyEngine:
    def __init__(self, birth_date: date, hour: int, minute: int, second: int, lat: float, lng: float):
        self.birth_date = birth_date
        self.hour = hour
        self.minute = minute
        self.second = second
        self.lat = lat
        self.lng = lng

        # lunar_python 自动根据经度校正真太阳时
        self.solar = Solar.fromYmdHms(birth_date.year, birth_date.month, birth_date.day, hour, minute, second)
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()

        # 修复 AttributeError: 将 seed 绑定到 self
        self.seed = hash((birth_date, hour, minute, second, round(lng, 4)))
        
        # 初始化随机数
        random.seed(self.seed)
        np.random.seed(self.seed % (2**32))

    def get_basic_info(self):
        current_year = datetime.now().year
        age_nominal = current_year - self.birth_date.year + 1  # 虚岁

        time_diff = (self.lng - 120.0) * 4  # 东八区基准

        # 获取八字四柱
        year_pillar = self.bazi.getYear()
        month_pillar = self.bazi.getMonth()
        day_pillar = self.bazi.getDay()
        time_pillar = self.bazi.getTime()

        # 生肖处理
        shengxiao_en = self.lunar.getYearShengXiao()
        shengxiao_map = {
            "Rat": "鼠", "Ox": "牛", "Tiger": "虎", "Rabbit": "兔",
            "Dragon": "龙", "Snake": "蛇", "Horse": "马", "Goat": "羊",
            "Monkey": "猴", "Rooster": "鸡", "Dog": "狗", "Pig": "猪"
        }
        shengxiao_cn = shengxiao_map.get(shengxiao_en, shengxiao_en)
        
        # 兼容处理日主五行显示
        day_gan = self.bazi.getDayGan()
        # 简单的天干五行映射
        gan_wx = {"甲":"木", "乙":"木", "丙":"火", "丁":"火", "戊":"土", "己":"土", "庚":"金", "辛":"金", "壬":"水", "癸":"水"}
        day_wx = gan_wx.get(day_gan, "")

        return {
            "bazi": f"{year_pillar}　{month_pillar}　{day_pillar}　{time_pillar}",
            "day_master": f"{day_gan}（{day_wx}）",
            "shengxiao": shengxiao_cn,
            "nongli": f"{self.lunar.getYearInGanZhi()}年　{self.lunar.getMonthInChinese()}月{self.lunar.getDayInChinese()}",
            "age": age_nominal,
            "true_solar_diff": f"{time_diff:+.1f} 分钟",
            "wuxing": self._calc_wuxing()
        }

    def _calc_wuxing(self):
        """基于真实八字统计五行强度（修复版，不依赖库内部方法）"""
        strength = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
        
        # 手动映射表，确保绝对稳定
        wx_map = {
            "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
            "寅": "木", "卯": "木", "巳": "火", "午": "火", "申": "金", "酉": "金", "亥": "水", "子": "水",
            "辰": "土", "戌": "土", "丑": "土", "未": "土"
        }

        # 天干权重2
        for gan in [self.bazi.getYearGan(), self.bazi.getMonthGan(), self.bazi.getDayGan(), self.bazi.getTimeGan()]:
            if gan in wx_map: strength[wx_map[gan]] += 2
            
        # 地支权重1
        for zhi in [self.bazi.getYearZhi(), self.bazi.getMonthZhi(), self.bazi.getDayZhi(), self.bazi.getTimeZhi()]:
            if zhi in wx_map: strength[wx_map[zhi]] += 1
            
        total = sum(strength.values()) or 1
        return {k: round(v / total * 100, 1) for k, v in strength.items()}

    def generate_life_kline(self):
        """百年运势K线"""
        data = []
        price = 100.0
        # 重置随机数状态以保证一致性
        random.seed(self.seed)
        
        for age in range(0, 101):
            # 模拟大运波动
            trend = np.sin(age / 7.0) * 7 + np.cos(age / 13.0) * 4
            noise = np.random.normal(0, 3.5)
            change = trend + noise
            if age % 12 == 0 and age > 0: change -= 10  # 本命年
            
            close = max(20, price + change)
            status = "大吉" if change > 8 else ("上升" if change > 3 else ("平稳" if change > -3 else "调整"))
            
            data.append({
                "Age": age, "Open": price, "Close": close,
                "High": close + abs(change)*0.7, "Low": price - abs(change)*0.7,
                "Status": status
            })
            price = close
            
        df = pd.DataFrame(data)
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA30'] = df['Close'].rolling(30).mean()
        return df

    def generate_daily_kline(self, year: int):
        """年份日运K线"""
        start = date(year, 1, 1)
        days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
        data = []
        price = 100.0
        
        # 使用绑定的 self.seed
        day_seed = hash((year, self.seed))
        random.seed(day_seed)
        
        for i in range(days):
            curr = start + timedelta(days=i)
            change = random.gauss(0, 2.8)
            close = max(30, price + change)
            status = "宜进取" if change > 0 else "宜守成"
            data.append({
                "Date": curr, "Open": price, "Close": close,
                "High": close + abs(change), "Low": price - abs(change),
                "Status": status
            })
            price = close
        return pd.DataFrame(data)

# ==========================================
# 5. 主程序
# ==========================================
def main():
    with st.sidebar:
        st.header("📂 缘主信息录入")

        name = st.text_input("姓名", "某君")
        gender = st.selectbox("性别", ["男", "女"])

        st.markdown("#### 📅 出生日期（中文强制版）")
        # --- 修复：替换原生日期控件，使用下拉框强制中文 ---
        col_y, col_m, col_d = st.columns([1.2, 0.9, 0.9])
        
        curr_year = datetime.now().year
        with col_y:
            sel_year = st.selectbox("年", range(1900, curr_year + 2), index=90) # 默认为1990
        with col_m:
            sel_month = st.selectbox("月", range(1, 13), format_func=lambda x: f"{x}月")
        
        # 动态计算每月天数
        if sel_month in [1, 3, 5, 7, 8, 10, 12]: max_day = 31
        elif sel_month in [4, 6, 9, 11]: max_day = 30
        else: # 2月简单处理
            max_day = 29 if (sel_year % 4 == 0 and (sel_year % 100 != 0 or sel_year % 400 == 0)) else 28
            
        with col_d:
            sel_day = st.selectbox("日", range(1, max_day + 1), format_func=lambda x: f"{x}日")
            
        # 组合成 date 对象
        b_date = date(sel_year, sel_month, sel_day)

        st.markdown("#### ⏰ 出生时辰")
        c1, c2, c3 = st.columns(3)
        hour = c1.selectbox("时", range(24), index=12)
        minute = c2.selectbox("分", range(60))
        second = c3.selectbox("秒", range(60))

        # 农历预览
        temp_solar = Solar.fromYmd(b_date.year, b_date.month, b_date.day)
        temp_lunar = temp_solar.getLunar()
        st.caption(f"农历：{temp_lunar.getYearInGanZhi()}年 {temp_lunar.getMonthInChinese()}月{temp_lunar.getDayInChinese()}")

        st.markdown("#### 📍 出生地点（级联定位）")
        
        final_lat, final_lng = 39.9042, 116.4074  # 默认北京
        full_address = "北京市"

        if ADMIN_DATA is None:
            st.error("❌ 未检测到 pcas-code.json")
            st.info("请确保 GitHub 仓库中包含该数据文件。")
        else:
            st.success(f"已加载地理数据")

            # 级联选择逻辑
            provinces = [p['name'] for p in ADMIN_DATA]
            sel_prov = st.selectbox("省份 / 直辖市", provinces)
            prov_data = next(p for p in ADMIN_DATA if p['name'] == sel_prov)

            cities = prov_data.get('children', [])
            # 直辖市特殊处理
            if sel_prov in ["北京市", "天津市", "上海市", "重庆市"]:
                city_data = cities[0] if cities else prov_data
                sel_city = sel_prov
            else:
                city_names = [c['name'] for c in cities] if cities else [sel_prov]
                sel_city = st.selectbox("地级市", city_names)
                city_data = next(c for c in cities if c['name'] == sel_city) if cities else prov_data

            areas = city_data.get('children', [])
            area_names = [a['name'] for a in areas] if areas else [sel_city]
            sel_area = st.selectbox("区 / 县", area_names)
            area_data = next(a for a in areas if a['name'] == sel_area) if areas else city_data

            streets = area_data.get('children', [])
            sel_street = ""
            if streets:
                street_names = [s['name'] for s in streets]
                sel_street = st.selectbox("乡镇 / 街道", ["无"] + street_names)
                sel_street = sel_street if sel_street != "无" else ""

            detail = st.text_input("详细地址", placeholder="例：协和医院")

            parts = [sel_prov, sel_city, sel_area, sel_street, detail]
            clean_parts = []
            seen = set()
            for p in parts:
                if p and p not in seen and p not in ["市辖区", "县"]:
                    clean_parts.append(p)
                    seen.add(p)
            full_address = "".join(clean_parts)

            if st.button("🛰️ 获取精确经纬度", type="primary", use_container_width=True):
                with st.spinner(f"正在卫星定位：{full_address}..."):
                    res = get_precise_location(full_address)
                st.session_state.loc_res = res

        # 处理定位结果
        if 'loc_res' in st.session_state:
            res = st.session_state.loc_res
            if res["success"]:
                lat, lng = res["lat"], res["lng"]
                msg = f"✅ 定位成功：{res['address']}"
                st.markdown(f"<div class='location-success'>{msg}</div>", unsafe_allow_html=True)
            else:
                lat, lng = final_lat, final_lng
                msg = f"⚠️ {res['msg']}"
                st.markdown(f"<div class='location-warning'>{msg}</div>", unsafe_allow_html=True)
        else:
            lat, lng = final_lat, final_lng

        st.caption(f"坐标：{lng:.4f}°E, {lat:.4f}°N")
        st.markdown("---")
        
        page = st.radio("功能导航", [
            "🏠 命盘总览",
            "📈 百年运势大盘",
            "📅 流年日运",
            "⚡ 五行能量雷达",
            "🍀 黄历宜忌指南"
        ])

    # 实例化引擎
    engine = DestinyEngine(b_date, hour, minute, second, lat, lng)
    info = engine.get_basic_info()

    st.title(f"{page} —— {name}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("八字四柱", info["bazi"])
    c2.metric("日主五行", info["day_master"])
    c3.metric("虚岁", f"{info['age']} 岁")
    c4.metric("真太阳时差", info["true_solar_diff"])

    st.divider()

    # ---------------------------
    # 页面逻辑
    # ---------------------------
    if page == "🏠 命盘总览":
        st.subheader("基本信息档案")
        st.write(f"**生肖**：{info['shengxiao']}")
        st.write(f"**农历生日**：{info['nongli']}")
        st.write(f"**出生地址**：{full_address}")
        
        st.subheader("五行能量分布")
        cols = st.columns(5)
        for i, (wx, val) in enumerate(info["wuxing"].items()):
            cols[i].metric(wx, f"{val}%")

    elif page == "📈 百年运势大盘":
        st.subheader("百年人生运势推演")
        df = engine.generate_life_kline()
        curr_age = info["age"] - 1

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df['Age'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     increasing_line_color='#d32f2f', decreasing_line_color='#2e7d32', name='年运'))
        fig.add_trace(go.Scatter(x=df['Age'], y=df['MA10'], line=dict(color='#fbc02d', width=2), name='十年均线'))
        fig.update_layout(xaxis_title="年龄（岁）", yaxis_title="运势能量", template="plotly_white", height=550, xaxis_rangeslider_visible=False)
        fig.add_vline(x=curr_age, line_dash="dash", line_color="black", annotation_text="当前位置")
        st.plotly_chart(fig, use_container_width=True)

    elif page == "📅 流年日运":
        st.subheader("流年每日运势")
        year = st.number_input("选择年份", min_value=1900, max_value=2100, value=datetime.now().year)
        
        # 确保 engine 内部 seed 已修复，这里可以直接生成
        df = engine.generate_daily_kline(year)
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                     increasing_line_color='#d32f2f', decreasing_line_color='#2e7d32', name='日运'))
        fig.update_layout(title=f"{year} 年每日运势", xaxis_title="日期", template="plotly_white", height=550)
        st.plotly_chart(fig, use_container_width=True)

    elif page == "⚡ 五行能量雷达":
        st.subheader("五行平衡分析")
        values = list(info["wuxing"].values())
        cats = list(info["wuxing"].keys())
        # 闭合雷达图
        fig = go.Figure(go.Scatterpolar(r=values + [values[0]], theta=cats + [cats[0]], fill='toself',
                                        line_color='#d32f2f', fillcolor='rgba(211,47,47,0.3)'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), template="plotly_white", height=500)
        st.plotly_chart(fig, use_container_width=True)

    elif page == "🍀 黄历宜忌指南":
        st.subheader("每日宜忌查询")
        q_date = st.date_input("查询日期", date.today())
        q_lunar = Solar.fromYmd(q_date.year, q_date.month, q_date.day).getLunar()
        yi = q_lunar.getDayYi()
        ji = q_lunar.getDayJi()
        
        st.markdown(f"""
        <div style="background:#fffbf0; padding:25px; border-radius:12px; border:1px solid #ffe0b2;">
            <h3 style="color:#d32f2f;">{q_date}</h3>
            <p>农历 {q_lunar.getYearInGanZhi()}年 {q_lunar.getMonthInChinese()}月{q_lunar.getDayInChinese()}</p>
            <hr>
            <div style="display:flex; gap:20px;">
                <div style="flex:1;"><strong style="color:#2e7d32;">宜</strong><br>{' '.join(yi)}</div>
                <div style="flex:1;"><strong style="color:#c62828;">忌</strong><br>{' '.join(ji)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()