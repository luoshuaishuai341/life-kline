import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from lunar_python import Solar, Lunar, LunarYear
from datetime import datetime, time, timedelta
import random
from geopy.geocoders import Nominatim # 新增：用于地址转经纬度

# ==========================================
# 1. 界面配置与 CSS (极简白主题)
# ==========================================

st.set_page_config(
    page_title="人生K线 | 运势管理系统",
    page_icon="🏮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：白底黑字，现代简约风格
st.markdown("""
<style>
    /* 全局背景设为纯白 */
    .stApp {
        background-color: #f8f9fa;
        color: #333333;
    }
    
    /* 侧边栏背景 - 浅灰 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e0e0e0;
    }
    
    /* 字体优化 */
    * {
        font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
    }
    
    /* 标题颜色 */
    h1, h2, h3 {
        color: #1a1a1a !important;
        font-weight: 700 !important;
    }
    
    /* 关键指标卡片优化 */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #d32f2f; /* 中国红 */
        font-weight: bold;
    }
    div[data-testid="stMetricLabel"] {
        color: #666;
        font-size: 14px;
    }
    
    /* 按钮自定义 - 红色系 */
    button[kind="primary"] {
        background-color: #d32f2f;
        color: white;
        border: none;
        border-radius: 4px;
    }
    button[kind="secondary"] {
        border: 1px solid #d32f2f;
        color: #d32f2f;
        background-color: white;
    }
    
    /* 输入框优化 */
    .stTextInput input, .stDateInput input, .stTimeInput input {
        background-color: #ffffff;
        color: #333;
        border: 1px solid #ddd;
    }
    
    /* 去除顶部留白 */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心逻辑工具函数
# ==========================================

def get_location_longitude(address):
    """
    输入地址，返回经度。
    如果解析失败，默认返回北京经度 (116.4)
    """
    try:
        geolocator = Nominatim(user_agent="life_kline_app_v3")
        location = geolocator.geocode(address)
        if location:
            return location.longitude, f"已定位: {address}"
        else:
            return 116.4, "地址未找到，使用默认经度"
    except:
        return 116.4, "定位服务连接超时，使用默认经度"

class DestinyQuantEngine:
    """
    人生量化引擎：负责排盘、生成K线数据、计算技术指标。
    """
    def __init__(self, birth_date, birth_time, gender, longitude):
        self.birth_date = birth_date
        self.gender = gender
        
        # 1. 八字排盘
        self.solar = Solar.fromYmdHms(
            birth_date.year, birth_date.month, birth_date.day,
            birth_time.hour, birth_time.minute, 0
        )
        self.lunar = self.solar.getLunar()
        self.ba_zi = self.lunar.getEightChar()
        
        # 2. 锁定随机种子
        seed_val = int(birth_date.strftime("%Y%m%d")) + birth_time.hour + birth_time.minute
        random.seed(seed_val)
        np.random.seed(seed_val)

    def get_profile(self):
        """获取基础信息"""
        return {
            "code": f"{self.ba_zi.getDayGan()}{self.ba_zi.getDayZhi()}", # 日柱
            "wuxing": self.ba_zi.getDayWuXing(), # 日主五行
            "animal": self.lunar.getYearShengXiao(),
            "year_zhu": f"{self.ba_zi.getYearGan()}{self.ba_zi.getYearZhi()}",
            "month_zhu": f"{self.ba_zi.getMonthGan()}{self.ba_zi.getMonthZhi()}",
        }
    
    def get_daily_fortune(self):
        """获取今日实时运势 (基于 Lunar 库)"""
        now = datetime.now()
        today_solar = Solar.fromYmdHms(now.year, now.month, now.day, now.hour, now.minute, 0)
        today_lunar = today_solar.getLunar()
        
        return {
            "date_str": f"{now.year}年{now.month}月{now.day}日",
            "lunar_str": f"农历{today_lunar.getMonthInChinese()}月{today_lunar.getDayInChinese()}",
            "yi": " ".join(today_lunar.getDayYi()), # 宜
            "ji": " ".join(today_lunar.getDayJi()), # 忌
            "chong": f"冲{today_lunar.getDayChongDesc()}", # 冲煞
            "lucky_god": f"{today_lunar.getPositionXiDesc()}", # 喜神方位
            "wealth_god": f"{today_lunar.getPositionCaiDesc()}"  # 财神方位
        }

    def generate_market_data(self, start_age=0, end_age=100):
        """生成人生K线数据"""
        data = []
        price = 100.0
        
        for age in range(start_age, end_age + 1):
            year = self.birth_date.year + age
            
            # --- 模拟算法 (此处可替换为真实八字喜忌逻辑) ---
            # 基础波动
            change = np.random.normal(0, 3.0) 
            
            # 大运周期 (10年一运)
            cycle_idx = age // 10
            cycle_trend = np.sin(cycle_idx) * 2.8 
            change += cycle_trend
            
            # 特殊年份 (本命年、刑冲破害模拟)
            if age % 12 == 0: 
                change -= 3 # 本命年压力
            
            # 计算 OHLC
            close_price = max(10, price + change)
            open_price = price
            high_price = max(open_price, close_price) + abs(np.random.normal(0, 1.5))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, 1.5))
            
            data.append({
                "Year": year,
                "Age": age,
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Close": close_price,
            })
            price = close_price

        return pd.DataFrame(data)

    @staticmethod
    def calculate_indicators(df):
        df['MA10'] = df['Close'].rolling(window=10).mean() # 10年大运
        return df

# ==========================================
# 3. 前端逻辑
# ==========================================

def main():
    # --- 侧边栏：信息录入 ---
    with st.sidebar:
        st.header("📝 缘主信息录入")
        st.markdown("---")
        
        input_name = st.text_input("姓名", "某君")
        input_gender = st.radio("性别", ["男", "女"], horizontal=True)
        
        # 优化：地址输入转经纬度
        st.markdown("###### 出生地信息")
        input_address = st.text_input("出生城市/地址 (自动获取经度)", "北京市东城区")
        
        # 经度处理逻辑
        calc_longitude = 116.4 # 默认
        if input_address:
            # 实际调用时，可以加一个按钮避免频繁请求，或者直接计算
            # 这里为了流畅体验，我们假设用户输完地址后点击生成按钮才计算
            pass
            
        input_date = st.date_input("出生日期 (公历)", datetime(1995, 8, 18))
        input_time = st.time_input("出生时间", time(8, 30))
        
        st.markdown("---")
        generate_btn = st.button("✨ 开启人生排盘", type="primary", use_container_width=True)
        
        st.caption("版本: v3.1 | 仅供娱乐参考")

    # --- 主界面 ---
    if generate_btn:
        # 1. 获取经纬度
        with st.spinner('正在定位出生地磁场...'):
            lng, loc_msg = get_location_longitude(input_address)
        st.toast(loc_msg, icon="📍")

        # 2. 实例化引擎
        engine = DestinyQuantEngine(input_date, input_time, input_gender, lng)
        profile = engine.get_profile()
        daily_fortune = engine.get_daily_fortune()
        df = engine.generate_market_data()
        df = engine.calculate_indicators(df)
        
        # 计算当前岁数
        current_year = datetime.now().year
        current_age = current_year - input_date.year
        
        # 获取当年数据
        try:
            curr_row = df[df['Year'] == current_year].iloc[0]
            trend_val = curr_row['Close'] - curr_row['Open']
        except:
            curr_row = df.iloc[-1]
            trend_val = 0

        # --- 模块1: 个人命盘概览 ---
        st.markdown(f"## 🏮 命盘分析: {input_name}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("日主 (元神)", profile['wuxing'], f"日柱: {profile['code']}")
        c2.metric("当前运势分", f"{curr_row['Close']:.0f}", f"{trend_val:+.1f}", delta_color="normal") # normal会自动红涨绿跌
        c3.metric("当前岁数", f"{current_age} 岁", "虚岁 +1")
        c4.metric("生肖", profile['animal'], f"{profile['year_zhu']}年")
        
        st.divider()

        # --- 模块2: 每日实时运势 (新功能) ---
        st.markdown("### 📅 今日运势播报")
        
        # 使用卡片样式展示今日宜忌
        day_col1, day_col2 = st.columns([1, 2])
        
        with day_col1:
            st.info(f"""
            **{daily_fortune['date_str']}** {daily_fortune['lunar_str']}
            
            **财神方位**: {daily_fortune['wealth_god']}  
            **喜神方位**: {daily_fortune['lucky_god']}
            """)
            
        with day_col2:
            yi_ji_html = f"""
            <div style="display: flex; gap: 20px;">
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; flex: 1; border-left: 5px solid #ffc107;">
                    <h4 style="margin:0; color: #856404;">🌞 宜 (Yi)</h4>
                    <p style="margin-top:5px; color: #856404;">{daily_fortune['yi']}</p>
                </div>
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 8px; flex: 1; border-left: 5px solid #dc3545;">
                    <h4 style="margin:0; color: #721c24;">🚫 忌 (Ji)</h4>
                    <p style="margin-top:5px; color: #721c24;">{daily_fortune['ji']}</p>
                </div>
            </div>
            """
            st.markdown(yi_ji_html, unsafe_allow_html=True)
            
        st.divider()

        # --- 模块3: 人生K线图 ---
        st.markdown("### 📈 人生 K 线推演 (百年大运)")
        
        fig = make_subplots(rows=1, cols=1)

        # K线图 (中国红绿: 涨红跌绿)
        fig.add_trace(go.Candlestick(
            x=df['Age'], # X轴改为年龄，更直观
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='年运',
            increasing_line_color='#d32f2f', # 红涨
            decreasing_line_color='#00796b'  # 绿跌
        ))

        # 均线
        fig.add_trace(go.Scatter(
            x=df['Age'], y=df['MA10'],
            mode='lines',
            line=dict(color='#FFD700', width=2),
            name='十年大运线'
        ))
        
        # 布局优化
        fig.update_layout(
            template="simple_white", # 更改为白底模板
            xaxis_title="年龄 (岁)",
            yaxis_title="运势指数",
            xaxis_rangeslider_visible=False,
            height=500,
            hovermode="x unified",
            margin=dict(t=20, b=20, l=40, r=40)
        )
        
        # 标记当前年龄
        fig.add_vline(x=current_age, line_width=1, line_dash="dash", line_color="#333")
        fig.add_annotation(x=current_age, y=curr_row['High'], text="当前位置", showarrow=True, arrowhead=1)

        st.plotly_chart(fig, use_container_width=True)
        
        # 在图表下方显示当前输入的岁数
        st.caption(f"📍 当前推演对象年龄: **{current_age} 岁** (出生于 {input_date.year} 年)")
        
        st.divider()

        # --- 模块4: 详细运势解读 ---
        st.markdown("### 📜 命理师批注")
        
        # 逻辑判断生成中文文案
        trend_status = "大吉" if curr_row['Close'] > curr_row['MA10'] else "平稳"
        if curr_row['Close'] < curr_row['MA10'] and curr_row['Close'] < curr_row['Open']:
            trend_status = "需谨慎"
            
        advice_text = ""
        if trend_status == "大吉":
            advice_text = "当前运势强于大运基准，且处于上升通道。适合大胆进取，投资、创业或求职皆有良机。红鸾星动，人际关系顺畅。"
        elif trend_status == "需谨慎":
            advice_text = "运势出现回调，且低于十年平均线。建议韬光养晦，保守理财，注意身体健康，避免口舌之争。"
        else:
            advice_text = "运势平稳，无大起大落。适合积累沉淀，学习新技能，为下一轮爆发做准备。"

        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px;">
            <p><strong>【总体评价】</strong>：<span style="color: #d32f2f; font-weight: bold;">{trend_status}</span></p>
            <p><strong>【大师建议】</strong>：{advice_text}</p>
            <p style="font-size: 0.9em; color: #666; margin-top: 10px;">*注：人生运势起伏乃常态，K线仅供参考，命运掌握在自己手中。</p>
        </div>
        """, unsafe_allow_html=True)

    else:
        # 初始欢迎页 (白色简约版)
        st.markdown("""
        <div style='text-align: center; margin-top: 80px; color: #555;'>
            <h1>🏮 人生 K 线系统</h1>
            <p style='font-size: 1.1em;'>传统的八字命理 · 现代的可视化呈现</p>
            <br>
            <div style='background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #eee; display: inline-block; text-align: left;'>
                <p>👉 <strong>输入地址</strong>：自动定位经纬度，排盘更精准</p>
                <p>👉 <strong>每日运势</strong>：查看今日宜忌、财神方位</p>
                <p>👉 <strong>百年推演</strong>：红涨绿跌，一目了然</p>
            </div>
            <p style='margin-top: 30px; font-size: 12px; color: #999;'>请在左侧输入信息开始排盘</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()