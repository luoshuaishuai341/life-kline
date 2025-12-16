import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from lunar_python import Solar, Lunar
from datetime import datetime, date, time, timedelta
import random
import json
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# ==========================================
# 1. 配置与样式
# ==========================================

st.set_page_config(
    page_title="天机 · 全息排盘系统 (高精版)",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #333; }
    section[data-testid="stSidebar"] { background-color: #f7f9fc; border-right: 1px solid #e6e6e6; }
    h1, h2, h3 { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #b71c1c !important; }
    div[data-testid="stMetricValue"] { color: #d32f2f; font-weight: bold; }
    .location-success { color: #155724; background-color: #d4edda; border-color: #c3e6cb; padding: 10px; border-radius: 5px; }
    .location-warning { color: #856404; background-color: #fff3cd; border-color: #ffeeba; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 加载 GitHub 行政区划数据 (JSON)
# ==========================================

@st.cache_data
def load_admin_data():
    """读取 pcas-code.json 文件 (增强版路径识别)"""
    # 1. 尝试直接读取 (本地开发常见)
    file_path = "pcas-code.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass

    # 2. 尝试使用当前文件的绝对路径拼接 (云端部署常见)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path_abs = os.path.join(current_dir, "pcas-code.json")
    if os.path.exists(file_path_abs):
        try:
            with open(file_path_abs, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
            
    return None

# !!! 关键点：这里必须初始化全局变量，否则 main 函数会报错 !!!
ADMIN_DATA = load_admin_data()

# ==========================================
# 3. 核心计算引擎 (含精确地理编码)
# ==========================================

@st.cache_data(show_spinner=False)
def get_precise_location(full_address_str):
    """
    调用 OpenStreetMap API 获取真实、精确的经纬度。
    """
    geolocator = Nominatim(user_agent="life_kline_v9_fix")
    try:
        # 加上 China 提高国内地址识别率
        search_query = f"China {full_address_str}"
        location = geolocator.geocode(search_query, timeout=10)
        
        if location:
            return {
                "success": True,
                "lat": location.latitude,
                "lng": location.longitude,
                "address": location.address
            }
        else:
            return {"success": False, "msg": "卫星未定位到该具体建筑，建议简化地址或手动输入坐标"}
            
    except (GeocoderTimedOut, GeocoderUnavailable):
        return {"success": False, "msg": "定位服务连接超时，请重试"}
    except Exception as e:
        return {"success": False, "msg": f"定位异常: {str(e)}"}

class DestinyEngine:
    def __init__(self, birth_date, birth_time, lat, lng):
        self.birth_date = birth_date
        self.birth_time = birth_time
        self.lat = lat
        self.lng = lng
        
        # 真太阳时计算
        self.solar = Solar.fromYmdHms(
            birth_date.year, birth_date.month, birth_date.day,
            birth_time.hour, birth_time.minute, 0
        )
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()
        
        self.seed = int(birth_date.strftime("%Y%m%d")) + birth_time.hour
        random.seed(self.seed)
        np.random.seed(self.seed)

    def get_basic_info(self):
        current_year = datetime.now().year
        age_nominal = current_year - self.birth_date.year + 1
        # 真太阳时偏差: (经度 - 120) * 4 分钟
        time_diff = (self.lng - 120.0) * 4
        
        return {
            "bazi": f"{self.bazi.getYearGan()}{self.bazi.getYearZhi()}  {self.bazi.getMonthGan()}{self.bazi.getMonthZhi()}  {self.bazi.getDayGan()}{self.bazi.getDayZhi()}  {self.bazi.getTimeGan()}{self.bazi.getTimeZhi()}",
            "wuxing_main": self.bazi.getDayWuXing(),
            "shengxiao": self.lunar.getYearShengXiao(),
            "nongli": f"{self.lunar.getMonthInChinese()}月{self.lunar.getDayInChinese()}",
            "yun_age": age_nominal,
            "true_solar_diff": f"{time_diff:+.1f} 分钟"
        }

    def generate_life_kline(self):
        data = []
        price = 100.0
        for age in range(0, 101):
            year = self.birth_date.year + age
            trend = np.sin(age / 5.0) * 5.0 
            change = np.random.normal(0, 4.0) + trend
            if age > 0 and age % 12 == 0: change -= 5 
            close = max(10, price + change)
            status = "运势大吉" if change > 5 else ("运势平稳" if change > -5 else "运势低迷")
            
            data.append({
                "Age": age, "Year": year, "Open": price, "Close": close,
                "High": max(price, close) + abs(change/2),
                "Low": min(price, close) - abs(change/2),
                "Status": status
            })
            price = close
        df = pd.DataFrame(data)
        df['MA10'] = df['Close'].rolling(10).mean()
        return df

    def generate_daily_kline(self, year):
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        days = (end - start).days + 1
        data = []
        year_seed = self.seed + year
        random.seed(year_seed)
        price = 100
        for i in range(days):
            curr_date = start + timedelta(days=i)
            change = random.uniform(-3, 3.5)
            close = price + change
            status = "宜进取" if change > 0 else "宜守成"
            data.append({
                "Date": curr_date, "Open": price, "Close": close,
                "High": max(price, close) + 1, "Low": min(price, close) - 1,
                "Status": status
            })
            price = close
        return pd.DataFrame(data)

# ==========================================
# 4. 页面渲染逻辑
# ==========================================

def main():
    # --- 侧边栏 ---
    with st.sidebar:
        st.header("📂 缘主档案录入")
        
        # 基础信息
        c1, c2 = st.columns(2)
        with c1: name = st.text_input("姓名", "某君")
        with c2: gender = st.selectbox("性别", ["男", "女"])
            
        # 出生时间
        st.markdown("#### 📅 出生时间 (公历)")
        b_date = st.date_input("日期", value=date(1998, 8, 18), min_value=date(1900, 1, 1), format="YYYY/MM/DD")
        b_time = st.time_input("时辰", time(8, 30))
        t_lunar = Solar.fromYmd(b_date.year, b_date.month, b_date.day).getLunar()
        st.caption(f"农历: {t_lunar.getYearInGanZhi()}年 {t_lunar.getMonthInChinese()}月{t_lunar.getDayInChinese()}")
        
        st.markdown("---")
        
        # --- 核心升级：4级联动地址选择 ---
        st.markdown("#### 📍 出生地 (4级联动定位)")
        
        # 检查数据是否加载成功
        if ADMIN_DATA is None:
            st.error("⚠️ 未读取到 pcas-code.json")
            st.info("请确保该文件已上传到 GitHub 仓库根目录，并点击了 commit。")
            # 降级方案，防止报错
            full_query_address = "Beijing"
            final_lat, final_lng = 39.90, 116.40
        else:
            # 1. 省
            province_names = [p['name'] for p in ADMIN_DATA]
            sel_prov_name = st.selectbox("省 / 直辖市", province_names)
            
            # 获取选中的省数据
            prov_data = next(p for p in ADMIN_DATA if p['name'] == sel_prov_name)
            
            # 2. 市
            city_list = prov_data.get('children', [])
            # 处理直辖市或没有子级的情况
            if not city_list:
                city_names = [sel_prov_name]
                city_data = prov_data # 降级处理
            else:
                city_names = [c['name'] for c in city_list]
            
            sel_city_name = st.selectbox("城市", city_names)
            # 获取选中的市数据
            if city_list:
                city_data = next(c for c in city_list if c['name'] == sel_city_name)
            else:
                city_data = prov_data

            # 3. 区/县
            area_list = city_data.get('children', [])
            if not area_list:
                area_names = ["市辖区"]
            else:
                area_names = [a['name'] for a in area_list]
                
            sel_area_name = st.selectbox("区 / 县", area_names)
            
            # 获取选中的区数据
            if area_list:
                area_data = next(a for a in area_list if a['name'] == sel_area_name)
            else:
                area_data = city_data # 降级

            # 4. 街道/乡镇
            street_list = area_data.get('children', [])
            if not street_list:
                street_names = ["默认街道"]
            else:
                street_names = [s['name'] for s in street_list]
            
            sel_street_name = st.selectbox("街道 / 乡镇", street_names)
            
            # 5. 详细地址
            st.caption("👇 输入具体建筑可提高真太阳时精度")
            sel_detail = st.text_input("详细地点", placeholder="例: 第一人民医院 / 幸福小区5号楼")
            
            # 拼接完整地址
            if sel_prov_name == sel_city_name:
                full_query_address = f"{sel_prov_name}{sel_area_name}{sel_street_name}{sel_detail}"
            else:
                full_query_address = f"{sel_prov_name}{sel_city_name}{sel_area_name}{sel_street_name}{sel_detail}"

            # 触发定位
            locate_btn = st.button("🛰️ 获取精确经纬度", type="primary", use_container_width=True)
            
            if 'location_cache' not in st.session_state:
                st.session_state['location_cache'] = (39.90, 116.40, "等待定位...")

            if locate_btn:
                with st.spinner(f"正在卫星定位: {full_query_address}..."):
                    loc_res = get_precise_location(full_query_address)
                
                if loc_res['success']:
                    st.session_state['location_cache'] = (loc_res['lat'], loc_res['lng'], f"✅ 已定位: {loc_res['address']}")
                else:
                    st.session_state['location_cache'] = (39.90, 116.40, f"⚠️ {loc_res['msg']}")
            
            final_lat, final_lng, loc_status_msg = st.session_state['location_cache']
            
            if "✅" in loc_status_msg:
                st.markdown(f"<div class='location-success'>{loc_status_msg}</div>", unsafe_allow_html=True)
            elif "⚠️" in loc_status_msg:
                st.markdown(f"<div class='location-warning'>{loc_status_msg}</div>", unsafe_allow_html=True)

        st.markdown("---")
        page = st.radio("功能导航", ["📊 人生大盘 (总览)", "📅 流年日线 (详情)", "⚡ 五行能量 (分析)", "🍀 每日宜忌 (指引)"])

    # --- 主界面 ---
    engine = DestinyEngine(b_date, b_time, final_lat, final_lng)
    info = engine.get_basic_info()

    st.title(f"{page}：{name}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("八字日主", info['wuxing_main'], f"{info['shengxiao']}年")
    c2.metric("当前虚岁", f"{info['yun_age']} 岁", "按立春计")
    c3.metric("真太阳时偏差", info['true_solar_diff'], "基于精确经度")
    c4.metric("出生经纬度", f"{final_lng:.4f}, {final_lat:.4f}")
    st.divider()

    # 1. 人生大盘
    if "人生大盘" in page:
        st.subheader("📈 百年运势推演")
        df_life = engine.generate_life_kline()
        curr_age = info['yun_age']
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_life['Age'], open=df_life['Open'], high=df_life['High'],
            low=df_life['Low'], close=df_life['Close'],
            increasing_line_color='#d32f2f', decreasing_line_color='#2e7d32',
            name='年运', text=df_life['Status'],
            hoverinfo='text+x+y',
            hovertemplate='<b>%{x}岁 (%{text})</b><br>开盘: %{open:.1f}<br>收盘: %{close:.1f}<br><extra></extra>'
        ))
        fig.add_trace(go.Scatter(x=df_life['Age'], y=df_life['MA10'], line=dict(color='#fbc02d', width=2), name='十年大运'))
        fig.update_layout(xaxis_title="年龄 (岁)", yaxis_title="运势能量", template="plotly_white", height=500, hovermode="x unified", xaxis_rangeslider_visible=False)
        fig.add_vline(x=curr_age, line_dash="dash", line_color="black", annotation_text="当前位置")
        st.plotly_chart(fig, use_container_width=True)

    # 2. 流年日线
    elif "流年日线" in page:
        st.subheader("📅 2025年 每日运势")
        target_year = st.number_input("查询年份", value=2025)
        df_daily = engine.generate_daily_kline(target_year)
        fig_d = go.Figure()
        fig_d.add_trace(go.Candlestick(
            x=df_daily['Date'], open=df_daily['Open'], high=df_daily['High'],
            low=df_daily['Low'], close=df_daily['Close'],
            increasing_line_color='#d32f2f', decreasing_line_color='#2e7d32',
            name='日运', text=df_daily['Status'],
            hovertemplate='<b>%{x|%Y-%m-%d} (%{text})</b><br>开盘: %{open:.1f}<br>收盘: %{close:.1f}<br><extra></extra>'
        ))
        fig_d.update_layout(xaxis_title="日期", template="plotly_white", height=500)
        st.plotly_chart(fig_d, use_container_width=True)

    # 3. 五行能量
    elif "五行能量" in page:
        st.subheader("⚡ 五行平衡雷达")
        vals = [random.randint(40,90) for _ in range(5)]
        fig_r = go.Figure(data=go.Scatterpolar(
            r=vals, theta=['金', '木', '水', '火', '土'], fill='toself', line_color='#d32f2f'
        ))
        fig_r.update_layout(template="plotly_white")
        st.plotly_chart(fig_r, use_container_width=True)

    # 4. 每日宜忌
    elif "每日宜忌" in page:
        st.subheader("🍀 老黄历指南")
        q_date = st.date_input("查询日期", date.today())
        q_lunar = Solar.fromYmd(q_date.year, q_date.month, q_date.day).getLunar()
        st.markdown(f"""
        <div style="background:#fffbf0; padding:20px; border:1px solid #ffe0b2; border-radius:8px;">
            <h3 style="color:#d32f2f; margin:0;">{q_date}</h3>
            <p>农历 {q_lunar.getMonthInChinese()}月{q_lunar.getDayInChinese()}</p>
            <hr>
            <div style="display:flex; gap:20px;">
                <div style="flex:1; color:#2e7d32;"><strong>宜：</strong>{' '.join(q_lunar.getDayYi())}</div>
                <div style="flex:1; color:#c62828;"><strong>忌：</strong>{' '.join(q_lunar.getDayJi())}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()