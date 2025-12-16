import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from lunar_python import Solar, Lunar
from datetime import datetime, date, time, timedelta
import random

# ==========================================
# 1. 配置与基础数据 (包含全中国省份)
# ==========================================

st.set_page_config(
    page_title="天机 · 全息排盘系统",
    page_icon="☯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：A股风格 (红涨绿跌)，白底黑字
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #333; }
    section[data-testid="stSidebar"] { background-color: #f7f9fc; border-right: 1px solid #e6e6e6; }
    h1, h2, h3 { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #b71c1c !important; }
    
    /* 关键指标 */
    div[data-testid="stMetricValue"] { color: #d32f2f; font-weight: bold; font-family: 'Arial'; }
    
    /* 侧边栏输入框优化 */
    .stSelectbox label, .stDateInput label, .stTimeInput label { font-weight: bold; color: #555; }
</style>
""", unsafe_allow_html=True)

# 中国省级行政区坐标 (中心点模拟)
CHINA_PROVINCES = {
    "北京市": [116.40, 39.90], "天津市": [117.20, 39.08], "河北省": [114.53, 38.04], "山西省": [112.56, 37.87],
    "内蒙古自治区": [111.77, 40.82], "辽宁省": [123.43, 41.80], "吉林省": [125.32, 43.81], "黑龙江省": [126.66, 45.77],
    "上海市": [121.47, 31.23], "江苏省": [118.76, 32.06], "浙江省": [120.15, 30.27], "安徽省": [117.28, 31.86],
    "福建省": [119.30, 26.07], "江西省": [115.81, 28.68], "山东省": [117.02, 36.65], "河南省": [113.75, 34.76],
    "湖北省": [114.34, 30.55], "湖南省": [112.98, 28.11], "广东省": [113.26, 23.13], "广西壮族自治区": [108.32, 22.81],
    "海南省": [110.34, 20.01], "重庆市": [106.55, 29.56], "四川省": [104.07, 30.65], "贵州省": [106.63, 26.64],
    "云南省": [102.72, 25.04], "西藏自治区": [91.11, 29.64], "陕西省": [108.93, 34.26], "甘肃省": [103.82, 36.06],
    "青海省": [101.78, 36.62], "宁夏回族自治区": [106.25, 38.47], "新疆维吾尔自治区": [87.62, 43.79],
    "香港特别行政区": [114.16, 22.31], "澳门特别行政区": [113.54, 22.19], "台湾省": [121.50, 25.03]
}

# ==========================================
# 2. 核心计算引擎 (Engine)
# ==========================================

class DestinyEngine:
    def __init__(self, name, gender, birth_date, birth_time, province, specific_address):
        self.name = name
        self.gender = gender
        self.birth_date = birth_date
        self.birth_time = birth_time
        
        # 模拟经纬度微调 (基于地址Hash)
        base_coord = CHINA_PROVINCES.get(province, [116.40, 39.90])
        offset = sum(ord(c) for c in specific_address) % 100 * 0.001 if specific_address else 0
        self.lng = base_coord[0] + offset
        
        # 锁定随机种子
        self.seed = int(birth_date.strftime("%Y%m%d")) + birth_time.hour
        random.seed(self.seed)
        np.random.seed(self.seed)
        
        # 排盘
        self.solar = Solar.fromYmdHms(birth_date.year, birth_date.month, birth_date.day, birth_time.hour, birth_time.minute, 0)
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()

    def get_basic_info(self):
        """获取基础命理信息"""
        return {
            "bazi": f"{self.bazi.getYearGan()}{self.bazi.getYearZhi()}  {self.bazi.getMonthGan()}{self.bazi.getMonthZhi()}  {self.bazi.getDayGan()}{self.bazi.getDayZhi()}  {self.bazi.getTimeGan()}{self.bazi.getTimeZhi()}",
            "wuxing_main": self.bazi.getDayWuXing(), # 日主
            "shengxiao": self.lunar.getYearShengXiao(),
            "nongli": f"{self.lunar.getMonthInChinese()}月{self.lunar.getDayInChinese()}",
            "yun_age": self.lunar.getYear() - self.solar.getYear() + 1 # 虚岁
        }

    def generate_life_kline(self):
        """生成百年人生K线"""
        data = []
        price = 100.0
        for age in range(0, 101):
            year = self.birth_date.year + age
            # 模拟大运波动
            trend = np.sin(age / 5.0) * 5.0 
            change = np.random.normal(0, 4.0) + trend
            
            # 本命年特殊处理
            if age > 0 and age % 12 == 0: change -= 5
            
            close = max(10, price + change)
            data.append({
                "Age": age, "Year": year, 
                "Open": price, "Close": close,
                "High": max(price, close) + abs(change/2),
                "Low": min(price, close) - abs(change/2)
            })
            price = close
        
        df = pd.DataFrame(data)
        df['MA10'] = df['Close'].rolling(10).mean()
        return df

    def generate_daily_kline(self, year):
        """生成指定年份的365天日线"""
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        days = (end - start).days + 1
        
        data = []
        # 使用特定年份种子，保证每年运势不一样但固定
        year_seed = self.seed + year
        random.seed(year_seed)
        
        price = 100
        for i in range(days):
            curr_date = start + timedelta(days=i)
            # 模拟：周末运势好
            is_weekend = curr_date.weekday() >= 5
            base_change = 1.0 if is_weekend else 0.0
            
            change = random.uniform(-3, 3.5) + base_change
            close = price + change
            
            # 描述
            score = 50 + change * 5 # 映射到 0-100分
            score = max(0, min(100, score))
            
            data.append({
                "Date": curr_date,
                "Open": price, "Close": close,
                "High": max(price, close) + 1,
                "Low": min(price, close) - 1,
                "Score": int(score)
            })
            price = close
            
        return pd.DataFrame(data)

    def get_wuxing_power(self):
        """生成五行能量值 (模拟)"""
        # 真实算法需统计八字中金木水火土的个数和权重
        # 这里用随机模拟展示UI效果
        return {
            "金": random.randint(40, 90),
            "木": random.randint(40, 90),
            "水": random.randint(40, 90),
            "火": random.randint(40, 90),
            "土": random.randint(40, 90)
        }

# ==========================================
# 3. 页面渲染逻辑
# ==========================================

def main():
    # --- 侧边栏：全局信息录入 ---
    with st.sidebar:
        st.header("📂 缘主档案")
        
        # 1. 基础信息
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            name = st.text_input("姓名", "某君")
        with col_s2:
            gender = st.selectbox("性别", ["男", "女"])
            
        # 2. 农历/公历选择优化
        st.markdown("#### 📅 出生时间 (公历)")
        b_date = st.date_input("选择日期", date(1998, 8, 18))
        b_time = st.time_input("具体时辰", time(8, 30))
        
        # 实时反馈农历
        temp_solar = Solar.fromYmd(b_date.year, b_date.month, b_date.day)
        temp_lunar = temp_solar.getLunar()
        st.caption(f"对应农历: {temp_lunar.getYearInGanZhi()}年 {temp_lunar.getMonthInChinese()}月{temp_lunar.getDayInChinese()}")
        
        # 3. 详细地址选择 (全省份)
        st.markdown("#### 📍 出生地 (计算真太阳时)")
        prov = st.selectbox("选择省份/地区", list(CHINA_PROVINCES.keys()))
        
        # 下级地址 (模拟输入，不需庞大数据库)
        city_detail = st.text_input("具体市/县/医院", placeholder="如: 朝阳区协和医院")
        
        st.markdown("---")
        
        # --- 页面导航 (Sub-pages) ---
        page = st.radio("功能导航", ["📊 人生大盘 (总览)", "📅 流年日线 (详情)", "⚡ 五行能量 (分析)", "🍀 每日宜忌 (指引)"])

        st.caption("v5.0.0 | 天机运算系统")

    # 初始化引擎
    engine = DestinyEngine(name, gender, b_date, b_time, prov, city_detail)
    info = engine.get_basic_info()

    # --- 顶部通栏：基础信息 ---
    st.title(f"{page}：{name}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("八字日主", info['wuxing_main'], f"{info['shengxiao']}年")
    c2.metric("农历生日", info['nongli'])
    c3.metric("当前虚岁", f"{info['yun_age']} 岁")
    c4.metric("出生经度", f"E {engine.lng:.2f}")
    st.divider()

    # ==========================
    # 子页面 1: 人生大盘 (Life K-Line)
    # ==========================
    if "人生大盘" in page:
        st.subheader("📈 百年运势推演 (Life Asset)")
        st.info("💡 解读：此图展示您一生的运势起伏。红色代表上升期（大运流年相生），绿色代表调整期（需韬光养晦）。MA10黄线代表十年大运趋势。")
        
        df_life = engine.generate_life_kline()
        
        # 标记当前年龄
        curr_age = info['yun_age']
        current_val = df_life[df_life['Age'] == curr_age].iloc[0]['Close'] if curr_age <= 100 else 0
        
        st.metric("当前运势指数", f"{current_val:.1f}", delta="基准分 100", delta_color="normal")
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_life['Age'],
            open=df_life['Open'], high=df_life['High'],
            low=df_life['Low'], close=df_life['Close'],
            increasing_line_color='#d32f2f', # 红涨
            decreasing_line_color='#2e7d32', # 绿跌
            name='年运'
        ))
        fig.add_trace(go.Scatter(x=df_life['Age'], y=df_life['MA10'], line=dict(color='#fbc02d', width=2), name='十年大运线'))
        
        fig.update_layout(
            xaxis_title="年龄 (岁)", yaxis_title="运势能量",
            template="plotly_white", height=500, xaxis_rangeslider_visible=False
        )
        # 标记当前位置
        fig.add_vline(x=curr_age, line_dash="dash", line_color="black")
        
        st.plotly_chart(fig, use_container_width=True)

    # ==========================
    # 子页面 2: 流年日线 (Daily K-Line)
    # ==========================
    elif "流年日线" in page:
        st.subheader("📅 2025年 每日运势微观图")
        target_year = st.number_input("选择查询年份", min_value=1900, max_value=2100, value=2025)
        
        st.caption(f"展示 {target_year} 年每一天的运势波动。可用于规划择日、重大决策辅助。")
        
        df_daily = engine.generate_daily_kline(target_year)
        
        # 绘制日线图
        fig_d = go.Figure()
        fig_d.add_trace(go.Candlestick(
            x=df_daily['Date'],
            open=df_daily['Open'], high=df_daily['High'],
            low=df_daily['Low'], close=df_daily['Close'],
            increasing_line_color='#d32f2f', 
            decreasing_line_color='#2e7d32',
            name='日运'
        ))
        fig_d.update_layout(
            xaxis_title="日期", yaxis_title="能量指数",
            template="plotly_white", height=500, xaxis_rangeslider_visible=True
        )
        st.plotly_chart(fig_d, use_container_width=True)
        
        # 下方显示运势最好的月份
        st.markdown("#### 🔥 年度高光时刻 (运势最旺月份)")
        df_daily['Month'] = df_daily['Date'].apply(lambda x: x.month)
        monthly_avg = df_daily.groupby('Month')['Score'].mean()
        best_month = monthly_avg.idxmax()
        st.success(f"根据推算，{target_year}年您的最佳月份是 **{best_month}月**，平均能量高达 **{monthly_avg.max():.1f}** 分。")

    # ==========================
    # 子页面 3: 五行能量 (Elements)
    # ==========================
    elif "五行能量" in page:
        st.subheader("⚡ 五行平衡雷达 (Five Elements)")
        st.markdown("中国传统命理认为，五行（金木水火土）的平衡决定了性格与命运。")
        
        wx = engine.get_wuxing_power()
        
        # 雷达图
        df_wx = pd.DataFrame(dict(
            r=[wx['金'], wx['木'], wx['水'], wx['火'], wx['土']],
            theta=['金 (决策)', '木 (生长)', '水 (智慧)', '火 (热情)', '土 (诚信)']
        ))
        
        fig_r = px.line_polar(df_wx, r='r', theta='theta', line_close=True)
        fig_r.update_traces(fill='toself', line_color='#d32f2f')
        fig_r.update_layout(template="plotly_white", height=400)
        
        c_r1, c_r2 = st.columns([2, 1])
        with c_r1:
            st.plotly_chart(fig_r, use_container_width=True)
        with c_r2:
            max_elem = max(wx, key=wx.get)
            st.warning(f"**核心能量：{max_elem}**")
            advice = {
                "金": "您行事果断，适合从事金融、法律等刚性行业。",
                "木": "您仁慈宽厚，适合教育、医疗或文化产业。",
                "水": "您智慧灵动，适合贸易、物流或流动性强的行业。",
                "火": "您热情奔放，适合演艺、能源或餐饮行业。",
                "土": "您稳重守信，适合房地产、农业或行政管理。"
            }
            st.markdown(advice[max_elem])

    # ==========================
    # 子页面 4: 每日宜忌 (Guide)
    # ==========================
    elif "每日宜忌" in page:
        st.subheader("🍀 今日老黄历指南")
        
        today = date.today()
        q_date = st.date_input("选择查询日期", today)
        
        # 获取该日农历
        q_solar = Solar.fromYmd(q_date.year, q_date.month, q_date.day)
        q_lunar = q_solar.getLunar()
        
        # UI 卡片
        st.markdown(f"""
        <div style="background-color:#fffbf0; padding:20px; border-radius:10px; border:1px solid #ffe0b2; text-align:center;">
            <h2 style="color:#d32f2f; margin:0;">{q_date.year}年{q_date.month}月{q_date.day}日</h2>
            <p style="font-size:1.2em; color:#555;">农历 {q_lunar.getMonthInChinese()}月{q_lunar.getDayInChinese()} · {q_lunar.getYearInGanZhi()}年</p>
            <hr>
            <div style="display:flex; justify-content:space-around;">
                <div style="color:#2e7d32;">
                    <h3>🌞 宜 (Yi)</h3>
                    <p>{' '.join(q_lunar.getDayYi())}</p>
                </div>
                <div style="color:#c62828;">
                    <h3>🚫 忌 (Ji)</h3>
                    <p>{' '.join(q_lunar.getDayJi())}</p>
                </div>
            </div>
            <hr>
            <p><strong>财神方位</strong>：{q_lunar.getPositionCaiDesc()} | <strong>喜神方位</strong>：{q_lunar.getPositionXiDesc()}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🎲 今日开运建议")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info(f"**幸运色**\n\n{'🔴 红色' if q_date.day % 2 == 0 else '🔵 蓝色'}")
        with c2:
            st.info(f"**幸运数字**\n\n{random.randint(1,9)}")
        with c3:
            st.info(f"**贵人方位**\n\n{random.choice(['正北', '正南', '东南', '西北'])}")

if __name__ == "__main__":
    main()