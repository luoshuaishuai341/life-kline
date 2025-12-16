import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from lunar_python import Solar
from datetime import datetime
import random

# ==========================================
# 1. 界面配置与 CSS 注入 (金融终端风格)
# ==========================================

st.set_page_config(
    page_title="LIFE ASSET TERMINAL | 人生资产终端",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：强制深色模式，模拟彭博终端/Web3交易所风格
st.markdown("""
<style>
    /* 全局背景设为纯黑 */
    .stApp {
        background-color: #050505;
        color: #e0e0e0;
    }
    
    /* 侧边栏背景 */
    section[data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid #333;
    }
    
    /* 字体统一为编程等宽字体，增加科技感 */
    * {
        font-family: 'Roboto Mono', 'Courier New', monospace !important;
    }
    
    /* 标题颜色 - 赛博青 */
    h1, h2, h3 {
        color: #00ffca !important;
    }
    
    /* 关键指标数字样式 */
    div[data-testid="stMetricValue"] {
        font-size: 26px;
        color: #ffffff;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
    }
    div[data-testid="stMetricLabel"] {
        color: #888;
        font-size: 14px;
    }
    
    /* 按钮自定义 */
    button[kind="secondary"] {
        border: 1px solid #00ffca;
        color: #00ffca;
    }
    button[kind="primary"] {
        background-color: #00ffca;
        color: #000;
        border: none;
    }
    
    /* 去除顶部留白 */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 核心量化引擎 (Quant Engine)
# ==========================================

class DestinyQuantEngine:
    """
    人生量化引擎：负责排盘、生成K线数据、计算技术指标。
    """
    def __init__(self, birth_date, birth_time, gender, longitude):
        self.birth_date = birth_date
        self.gender = gender
        
        # 1. 八字排盘 (利用 lunar_python)
        self.solar = Solar.fromYmdHms(
            birth_date.year, birth_date.month, birth_date.day,
            birth_time.hour, birth_time.minute, 0
        )
        self.lunar = self.solar.getLunar()
        self.ba_zi = self.lunar.getEightChar()
        
        # 2. 锁定随机种子 (Deterministic Randomness)
        # 核心逻辑：用生日生成一个种子，确保同一个人每次生成的图表是一样的
        seed_val = int(birth_date.strftime("%Y%m%d")) + birth_time.hour + birth_time.minute
        random.seed(seed_val)
        np.random.seed(seed_val)

    def get_profile(self):
        """获取资产(用户)基础信息"""
        return {
            "code": f"{self.ba_zi.getDayGan()}{self.ba_zi.getDayZhi()}", # 日柱作为股票代码
            "full_bazi": f"{self.ba_zi.getYear()} {self.ba_zi.getMonth()} {self.ba_zi.getDay()} {self.ba_zi.getTime()}",
            "wuxing": self.ba_zi.getDayWuXing(), # 核心五行
            "animal": self.lunar.getYearShengXiao(),
        }

    def generate_market_data(self, start_age=0, end_age=100):
        """
        生成 0-100 岁的人生市场数据 (OHLCV)
        *注*：此处逻辑为演示用，通过数学模型模拟人生波动。
        """
        data = []
        price = 100.0 # 初始发行价
        
        # 模拟不同阶段的波动率
        for age in range(start_age, end_age + 1):
            year = self.birth_date.year + age
            
            # --- 模拟算法开始 ---
            
            # 1. 基础波动 (Market Noise)
            change = np.random.normal(0, 3.0) 
            
            # 2. 周期性因子 (Cycle - 大运)
            # 假设每10年换一个大运，这里随机决定这个大运是好是坏
            cycle_idx = age // 10
            cycle_trend = np.sin(cycle_idx) * 2.5 
            change += cycle_trend
            
            # 3. 特殊年份冲击 (Shock Events)
            volatility = 1.0
            if age % 12 == 0: # 本命年
                volatility = 2.0 
                change -= 2 # 压力位
            
            if age == 18: change += 5 # 普涨
            
            # 计算 OHLC
            close_price = max(10, price + change) # 价格不能低于10
            open_price = price
            
            # 震荡区间
            high_price = max(open_price, close_price) + abs(np.random.normal(0, volatility))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, volatility))
            
            # Volume 模拟精力消耗
            volume = int(abs(change) * 100 + 500)
            
            data.append({
                "Year": year,
                "Age": age,
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Close": close_price,
                "Volume": volume
            })
            
            price = close_price
            # --- 模拟算法结束 ---

        return pd.DataFrame(data)

    @staticmethod
    def calculate_indicators(df):
        """计算技术指标: MA, MACD, RSI"""
        # MA10 (十年大运线)
        df['MA10'] = df['Close'].rolling(window=10).mean()
        
        # MACD (动能指标)
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Hist'] = df['MACD'] - df['Signal']
        
        # RSI (相对强弱 - 精力槽)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df

# ==========================================
# 3. 前端逻辑与渲染 (Main Application)
# ==========================================

def main():
    # --- 侧边栏：控制面板 ---
    with st.sidebar:
        st.header(">> TERMINAL ACCESS")
        st.markdown("---")
        
        input_name = st.text_input("USER ID (姓名/代号)", "TRADER_01")
        
        c1, c2 = st.columns(2)
        with c1:
            input_gender = st.selectbox("GENDER", ["男", "女"])
        with c2:
            input_lng = st.number_input("LNG (经度)", 120.2, help="出生地经度，用于真太阳时")
            
        input_date = st.date_input("IPO DATE (出生日期)", datetime(2000, 1, 1))
        input_time = st.time_input("IPO TIME (出生时间)", datetime(12, 0))
        
        st.markdown("---")
        generate_btn = st.button("INITIATE_SEQUENCE (生成图表)", type="primary", use_container_width=True)
        
        st.caption("v2.0.4 | Life Asset Mgt System")

    # --- 主界面逻辑 ---
    if generate_btn:
        # 1. 实例化引擎并计算
        engine = DestinyQuantEngine(input_date, input_time, input_gender, input_lng)
        profile = engine.get_profile()
        df = engine.generate_market_data()
        df = engine.calculate_indicators(df)
        
        # 2. 获取当前年份状态
        current_year = datetime.now().year
        # 容错处理
        try:
            curr_row = df[df['Year'] == current_year].iloc[0]
            # 计算同比变化
            prev_row = df[df['Year'] == current_year - 1].iloc[0]
            pct_change = ((curr_row['Close'] - prev_row['Close']) / prev_row['Close']) * 100
        except:
            curr_row = df.iloc[-1]
            pct_change = 0.0

        # --- 顶部：资产概览 Dashboard ---
        st.markdown(f"### 🧬 ASSET MONITOR: {input_name.upper()}")
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("ASSET CODE", profile['code'], f"核心五行: {profile['wuxing']}")
        k2.metric("VALUATION (运势)", f"{curr_row['Close']:.2f}", f"{pct_change:+.2f}%")
        
        # RSI 颜色逻辑
        rsi_val = curr_row['RSI']
        rsi_state = "过热 (Sell)" if rsi_val > 70 else ("超卖 (Buy)" if rsi_val < 30 else "中性 (Hold)")
        k3.metric("RSI (精力)", f"{rsi_val:.1f}", rsi_state, delta_color="inverse")
        
        # MACD 逻辑
        macd_val = curr_row['Hist']
        macd_state = "多头增强" if macd_val > 0 else "空头主导"
        k4.metric("MOMENTUM (动能)", f"{macd_val:.2f}", macd_state)
        
        st.markdown("---")

        # --- 中部：高级交互式图表 (Subplots) ---
        # 创建两行子图：上行是K线，下行是MACD
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.7, 0.3]
        )

        # Draw 1: K-Line (Candlestick)
        fig.add_trace(go.Candlestick(
            x=df['Year'],
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='运势',
            increasing_line_color='#00ffca', # 赛博绿
            decreasing_line_color='#ff0055'  # 赛博红
        ), row=1, col=1)

        # Draw 2: MA10 (Moving Average)
        fig.add_trace(go.Scatter(
            x=df['Year'], y=df['MA10'],
            mode='lines',
            line=dict(color='#ffd700', width=1.5),
            name='MA10 (大运线)'
        ), row=1, col=1)

        # Draw 3: MACD Histogram
        colors = ['#004d40' if v >= 0 else '#4d0000' for v in df['Hist']] # 深色柱体
        border_colors = ['#00ffca' if v >= 0 else '#ff0055' for v in df['Hist']] # 亮色边框
        
        fig.add_trace(go.Bar(
            x=df['Year'], y=df['Hist'],
            marker_color=colors,
            marker_line_color=border_colors,
            marker_line_width=1,
            name='动能'
        ), row=2, col=1)

        # 图表布局优化
        fig.update_layout(
            template="plotly_dark", # 使用 Plotly 自带深色模板
            paper_bgcolor='rgba(0,0,0,0)', # 透明背景融入 Streamlit
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False,
            height=650,
            hovermode="x unified",
            showlegend=False,
            margin=dict(t=30, b=30, l=30, r=30)
        )
        
        # 标记 "You Are Here"
        fig.add_vline(x=current_year, line_width=1, line_dash="dash", line_color="white")
        
        st.plotly_chart(fig, use_container_width=True)

        # --- 底部：AI 策略生成器 ---
        st.markdown("#### 🤖 AI STRATEGY ADVISOR (智能投顾)")
        
        # 简单的规则生成器 (Rule-based Generation)
        advisor_col1, advisor_col2 = st.columns([0.7, 0.3])
        
        with advisor_col1:
            # 根据 MA 位置判断
            trend = "Bullish (多头排列)" if curr_row['Close'] > curr_row['MA10'] else "Bearish (空头压制)"
            trend_desc = "当前运势运行于十年大运线之上，处于顺风期。" if curr_row['Close'] > curr_row['MA10'] else "当前运势受阻，处于调整期/蛰伏期。"
            
            st.info(f"""
            **技术面扫描**:
            * **Trend**: {trend} - {trend_desc}
            * **Signal**: MACD 柱状图为 {macd_val:.2f}，显示动能{'正在衰竭' if abs(macd_val)<1 else '强劲'}。
            """)
            
        with advisor_col2:
            # 给出具体的行动建议
            if curr_row['Close'] > curr_row['MA10'] and macd_val > 0:
                action = "STRONG BUY (重仓出击)"
                tips = "适合创业、跳槽、激进投资。"
                color = "green"
            elif curr_row['RSI'] > 80:
                action = "TAKE PROFIT (获利了结)"
                tips = "注意身体，避免过劳，见好就收。"
                color = "orange"
            elif curr_row['Close'] < curr_row['MA10']:
                action = "HODL (持币观望)"
                tips = "学习技能，等待下一个周期。"
                color = "red"
            else:
                action = "NEUTRAL (中性)"
                tips = "按部就班，平稳过渡。"
                color = "blue"
                
            st.markdown(f"""
            <div style="border:1px solid #333; padding:15px; border-radius:5px; text-align:center;">
                <h3 style="margin:0; color:{'#00ffca' if color=='green' else '#ff0055'}">{action}</h3>
                <p style="margin-top:10px; font-size:14px; color:#ccc;">{tips}</p>
            </div>
            """, unsafe_allow_html=True)

    else:
        # 初始状态
        st.markdown("""
        <div style='text-align: center; margin-top: 100px; opacity: 0.6;'>
            <h1>🧬 TERMINAL READY</h1>
            <p>Waiting for user initialization sequence...</p>
            <p style='font-size: 12px;'>Please enter data in the left sidebar.</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()