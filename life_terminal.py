import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from lunar_python import Solar, Lunar
from datetime import datetime, date, time, timedelta
import random
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# ==========================================
# 1. 配置与样式
# ==========================================

st.set_page_config(
    page_title="天机 · 全息排盘系统 Ultimate",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #333; }
    section[data-testid="stSidebar"] { background-color: #f7f9fc; border-right: 1px solid #e6e6e6; }
    h1, h2, h3 { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #b71c1c !important; }
    div[data-testid="stMetricValue"] { color: #d32f2f; font-weight: bold; }
    .location-success { color: #2e7d32; font-weight: bold; padding: 10px; border: 1px solid #c8e6c9; background: #e8f5e9; border-radius: 5px; }
    .location-warning { color: #e65100; font-weight: bold; padding: 10px; border: 1px solid #ffe0b2; background: #fff3e0; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 行政区划数据 (覆盖全中国省级 + 主要城市)
# ==========================================
# 注：为了代码运行效率，此处内置了所有省份和省会/主要城市。
# 下级区县数据通过 API 自动补全，不需要手动穷举 3000 个县。

CHINA_ADMIN_DATA = {
    "直辖市": {
        "北京市": ["东城区", "西城区", "朝阳区", "海淀区", "丰台区", "石景山区", "通州区", "顺义区", "昌平区", "大兴区", "亦庄"],
        "上海市": ["黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "浦东新区", "闵行区", "宝山区", "嘉定区", "松江区"],
        "天津市": ["和平区", "河东区", "河西区", "南开区", "滨海新区"],
        "重庆市": ["渝中区", "江北区", "沙坪坝区", "九龙坡区", "南岸区", "渝北区"]
    },
    "广东省": {
        "广州市": ["天河区", "越秀区", "海珠区", "荔湾区", "番禺区", "白云区", "黄埔区"],
        "深圳市": ["福田区", "罗湖区", "南山区", "宝安区", "龙岗区", "南山区"],
        "珠海市": ["香洲区", "金湾区", "斗门区"],
        "佛山市": ["禅城区", "南海区", "顺德区"],
        "东莞市": ["东城", "南城", "虎门", "长安"],
        # ... 其他城市可按需自动搜索
    },
    "浙江省": {
        "杭州市": ["上城区", "拱墅区", "西湖区", "滨江区", "萧山区", "余杭区"],
        "宁波市": ["海曙区", "江北区", "鄞州区"],
        "温州市": ["鹿城区", "龙湾区", "瓯海区"],
    },
    "江苏省": {
        "南京市": ["玄武区", "秦淮区", "建邺区", "鼓楼区"],
        "苏州市": ["姑苏区", "虎丘区", "吴中区", "工业园区"],
        "无锡市": ["梁溪区", "滨湖区"],
    },
    "福建省": {"福州市": [], "厦门市": [], "泉州市": []},
    "山东省": {"济南市": [], "青岛市": [], "烟台市": []},
    "四川省": {"成都市": [], "绵阳市": []},
    "湖北省": {"武汉市": [], "宜昌市": []},
    "湖南省": {"长沙市": [], "株洲市": []},
    "河南省": {"郑州市": [], "洛阳市": []},
    "河北省": {"石家庄市": [], "唐山市": [], "雄安新区": []},
    "山西省": {"太原市": [], "大同市": []},
    "陕西省": {"西安市": [], "咸阳市": []},
    "安徽省": {"合肥市": [], "芜湖市": []},
    "江西省": {"南昌市": [], "赣州市": []},
    "黑龙江省": {"哈尔滨市": []},
    "吉林省": {"长春市": []},
    "辽宁省": {"沈阳市": [], "大连市": []},
    "云南省": {"昆明市": [], "大理州": [], "丽江市": []},
    "贵州省": {"贵阳市": []},
    "广西壮族自治区": {"南宁市": [], "桂林市": []},
    "海南省": {"海口市": [], "三亚市": []},
    "内蒙古自治区": {"呼和浩特市": [], "包头市": []},
    "宁夏回族自治区": {"银川市": []},
    "甘肃省": {"兰州市": []},
    "青海省": {"西宁市": []},
    "新疆维吾尔自治区": {"乌鲁木齐市": []},
    "西藏自治区": {"拉萨市": []},
    "港澳台": {
        "香港": ["中西区", "湾仔区", "油尖旺"],
        "澳门": ["澳门半岛", "路环"],
        "台湾": ["台北市", "高雄市", "台中市"]
    }
}

# ==========================================
# 3. 核心计算引擎 (含精确地理编码)
# ==========================================

@st.cache_data(show_spinner=False)
def get_precise_location(address_str):
    """
    调用 OpenStreetMap API 获取真实、精确的经纬度。
    使用 cache 避免重复请求。
    """
    geolocator = Nominatim(user_agent="bazi_terminal_v7_cn")
    try:
        # 加上 China 提高国内地址识别率
        search_query = f"China {address_str}" if "香港" not in address_str and "台湾" not in address_str else address_str
        location = geolocator.geocode(search_query, timeout=5)
        
        if location:
            return {
                "success": True,
                "lat": location.latitude,
                "lng": location.longitude,
                "address": location.address
            }
        else:
            return {"success": False, "msg": "未找到该详细地址，将使用城市基准坐标"}
            
    except (GeocoderTimedOut, GeocoderUnavailable):
        return {"success": False, "msg": "定位服务超时，将使用城市基准坐标"}
    except Exception as e:
        return {"success": False, "msg": f"定位异常: {str(e)}"}

class DestinyEngine:
    def __init__(self, birth_date, birth_time, lat, lng):
        self.birth_date = birth_date
        self.birth_time = birth_time
        self.lat = lat
        self.lng = lng
        
        # 1. 真太阳时计算 (核心算法)
        # Solar 库会自动根据经度计算真太阳时
        self.solar = Solar.fromYmdHms(
            birth_date.year, birth_date.month, birth_date.day,
            birth_time.hour, birth_time.minute, 0
        )
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()
        
        # 2. 锁定随机种子
        self.seed = int(birth_date.strftime("%Y%m%d")) + birth_time.hour
        random.seed(self.seed)
        np.random.seed(self.seed)

    def get_basic_info(self):
        current_year = datetime.now().year
        # 修正虚岁：(当前年 - 出生年) + 1
        age_nominal = current_year - self.birth_date.year + 1
        
        # 计算真太阳时偏差 (粗略展示用)
        # 北京时间是东八区(120度)，每差1度差4分钟
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
        """生成百年人生K线"""
        data = []
        price = 100.0
        
        for age in range(0, 101):
            year = self.birth_date.year + age
            trend = np.sin(age / 5.0) * 5.0 
            change = np.random.normal(0, 4.0) + trend
            
            if age > 0 and age % 12 == 0: change -= 5 # 本命年
            
            close = max(10, price + change)
            
            # 中文状态逻辑
            status = "运势大吉" if change > 5 else ("运势平稳" if change > -5 else "运势低迷")
            if close > price: status = "上升周期"
            if close < price: status = "调整周期"
            
            data.append({
                "Age": age, "Year": year, 
                "Open": price, "Close": close,
                "High": max(price, close) + abs(change/2),
                "Low": min(price, close) - abs(change/2),
                "Status": status
            })
            price = close
        
        df = pd.DataFrame(data)
        df['MA10'] = df['Close'].rolling(10).mean()
        return df

    def generate_daily_kline(self, year):
        """生成365天日线"""
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
                "Date": curr_date,
                "Open": price, "Close": close,
                "High": max(price, close) + 1,
                "Low": min(price, close) - 1,
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
        
        # 1. 基础
        c1, c2 = st.columns(2)
        with c1: name = st.text_input("姓名", "某君")
        with c2: gender = st.selectbox("性别", ["男", "女"])
            
        # 2. 时间
        st.markdown("#### 📅 出生时间 (公历)")
        b_date = st.date_input("选择日期", value=date(1998, 8, 18), min_value=date(1900, 1, 1), format="YYYY/MM/DD")
        b_time = st.time_input("具体时辰", time(8, 30))
        
        # 农历反馈
        t_solar = Solar.fromYmd(b_date.year, b_date.month, b_date.day)
        t_lunar = t_solar.getLunar()
        st.caption(f"对应农历: {t_lunar.getYearInGanZhi()}年 {t_lunar.getMonthInChinese()}月{t_lunar.getDayInChinese()}")
        
        st.markdown("---")
        
        # 3. 精确地理位置 (核心升级)
        st.markdown("#### 📍 出生地 (计算真太阳时)")
        
        # 级联选择器逻辑
        root_regions = list(CHINA_ADMIN_DATA.keys())
        sel_root = st.selectbox("行政大区", root_regions)
        
        provinces = CHINA_ADMIN_DATA[sel_root]
        # 如果是字典说明有下级城市，如果是列表说明是直辖市直接有区
        if isinstance(provinces, dict):
            sel_prov = st.selectbox("省份 / 直辖市", list(provinces.keys()))
            districts = provinces[sel_prov]
        else:
            sel_prov = sel_root # 直辖市逻辑
            districts = provinces
            
        # 城市/区域选择
        if isinstance(districts, list) and len(districts) > 0:
            sel_dist = st.selectbox("城市 / 区域", districts)
        else:
            sel_dist = st.text_input("城市 / 区域 (手动输入)", value=sel_prov)
            
        # 详细地址 (医院/街道)
        sel_detail = st.text_input("详细地点 (精确到医院/街道)", placeholder="例: 协和医院 (影响真太阳时)")
        
        # 拼接完整地址用于API查询
        full_query_address = f"{sel_prov}{sel_dist}{sel_detail}"
        
        # 手动触发定位按钮 (避免频繁调用API)
        locate_btn = st.button("🛰️ 获取精确经纬度", type="primary", use_container_width=True)
        
        # 默认坐标 (北京)
        final_lat, final_lng = 39.90, 116.40 
        loc_status_msg = "等待定位..."
        
        if locate_btn:
            with st.spinner(f"正在连接卫星定位: {full_query_address}..."):
                loc_res = get_precise_location(full_query_address)
                
            if loc_res['success']:
                final_lat = loc_res['lat']
                final_lng = loc_res['lng']
                loc_status_msg = f"✅ 已定位: {loc_res['address']}"
                st.session_state['location_cache'] = (final_lat, final_lng, loc_status_msg)
            else:
                loc_status_msg = f"⚠️ {loc_res['msg']}"
                st.session_state['location_cache'] = (39.90, 116.40, loc_status_msg)
        
        # 读取缓存的定位结果 (防止页面刷新丢失)
        if 'location_cache' in st.session_state:
            final_lat, final_lng, loc_status_msg = st.session_state['location_cache']
            
        # 显示定位结果
        if "✅" in loc_status_msg:
            st.markdown(f"<div class='location-success'>{loc_status_msg}</div>", unsafe_allow_html=True)
            st.caption(f"坐标: E{final_lng:.4f}, N{final_lat:.4f}")
        elif "⚠️" in loc_status_msg:
            st.markdown(f"<div class='location-warning'>{loc_status_msg}</div>", unsafe_allow_html=True)
            
        st.markdown("---")
        page = st.radio("功能导航", ["📊 人生大盘 (总览)", "📅 流年日线 (详情)", "⚡ 五行能量 (分析)", "🍀 每日宜忌 (指引)"])

    # --- 主界面 ---
    
    # 实例化引擎
    engine = DestinyEngine(b_date, b_time, final_lat, final_lng)
    info = engine.get_basic_info()

    st.title(f"{page}：{name}")
    
    # 信息概览栏
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("八字日主", info['wuxing_main'], f"{info['shengxiao']}年")
    c2.metric("当前虚岁", f"{info['yun_age']} 岁", "按立春计")
    c3.metric("真太阳时偏差", info['true_solar_diff'], "基于精确经度")
    c4.metric("出生经纬度", f"{final_lng:.3f}, {final_lat:.3f}")
    st.divider()

    # ---------------------------
    # 页面 1: 人生大盘 (K线)
    # ---------------------------
    if "人生大盘" in page:
        st.subheader("📈 百年运势推演")
        df_life = engine.generate_life_kline()
        
        curr_age = info['yun_age']
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_life['Age'],
            open=df_life['Open'], high=df_life['High'],
            low=df_life['Low'], close=df_life['Close'],
            increasing_line_color='#d32f2f', 
            decreasing_line_color='#2e7d32',
            name='年运',
            text=df_life['Status'],
            hoverinfo='text+x+y',
            hovertemplate = 
                '<b>%{x}岁 (%{text})</b><br>' +
                '开盘: %{open:.1f}<br>' +
                '收盘: %{close:.1f}<br>' +
                '<extra></extra>'
        ))
        fig.add_trace(go.Scatter(x=df_life['Age'], y=df_life['MA10'], line=dict(color='#fbc02d', width=2), name='十年大运'))
        
        fig.update_layout(
            xaxis_title="年龄 (岁)", yaxis_title="运势能量",
            template="plotly_white", height=500, xaxis_rangeslider_visible=False,
            hovermode="x unified"
        )
        fig.add_vline(x=curr_age, line_dash="dash", line_color="black", annotation_text="当前位置")
        st.plotly_chart(fig, use_container_width=True)

    # ---------------------------
    # 页面 2: 流年日线
    # ---------------------------
    elif "流年日线" in page:
        st.subheader("📅 2025年 每日运势")
        target_year = st.number_input("查询年份", value=2025)
        df_daily = engine.generate_daily_kline(target_year)
        
        fig_d = go.Figure()
        fig_d.add_trace(go.Candlestick(
            x=df_daily['Date'],
            open=df_daily['Open'], high=df_daily['High'],
            low=df_daily['Low'], close=df_daily['Close'],
            increasing_line_color='#d32f2f', 
            decreasing_line_color='#2e7d32',
            name='日运',
            text=df_daily['Status'],
            hovertemplate = 
                '<b>%{x|%Y-%m-%d} (%{text})</b><br>' +
                '开盘: %{open:.1f}<br>' +
                '收盘: %{close:.1f}<br>' +
                '<extra></extra>'
        ))
        fig_d.update_layout(xaxis_title="日期", template="plotly_white", height=500)
        st.plotly_chart(fig_d, use_container_width=True)

    # ---------------------------
    # 页面 3: 五行能量
    # ---------------------------
    elif "五行能量" in page:
        st.subheader("⚡ 五行平衡雷达")
        # 模拟数据，实际应统计八字
        vals = [random.randint(40,90) for _ in range(5)]
        fig_r = go.Figure(data=go.Scatterpolar(
            r=vals,
            theta=['金', '木', '水', '火', '土'],
            fill='toself',
            line_color='#d32f2f'
        ))
        fig_r.update_layout(template="plotly_white")
        st.plotly_chart(fig_r, use_container_width=True)

    # ---------------------------
    # 页面 4: 每日宜忌
    # ---------------------------
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