import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from lunar_python import Solar, Lunar
from datetime import datetime, date, timedelta
import random
import json
import os
import requests  # 新增：用于调用外部AI
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# ==========================================
# 1. 页面配置与样式
# ==========================================
st.set_page_config(
    page_title="天机 · AI 命理量化终端",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #f5f7f9; color: #333; }
    h1, h2, h3 { font-family: 'PingFang SC', sans-serif; color: #2c3e50 !important; }
    
    /* AI 分析框样式 */
    .ai-box {
        background-color: #ffffff; border-left: 5px solid #6c5ce7;
        padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-top: 20px; font-family: 'Microsoft YaHei', sans-serif;
    }
    
    /* 熊市/牛市 标签 */
    .trend-bull { color: #d32f2f; font-weight: bold; background: #ffebee; padding: 2px 5px; border-radius: 3px; }
    .trend-bear { color: #2e7d32; font-weight: bold; background: #e8f5e9; padding: 2px 5px; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 基础组件 (数据加载 & 定位)
# ==========================================
@st.cache_data
def load_admin_data():
    files = ["pcas-code.json", "pca-code.json"]
    curr = os.path.dirname(os.path.abspath(__file__))
    for f in files:
        p = os.path.join(curr, f)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as file: return json.load(file)
            except: continue
    return None

ADMIN_DATA = load_admin_data()

@st.cache_data(show_spinner=False)
def get_precise_location(addr):
    ua = f"life_ai_{random.randint(10000,99999)}"
    try:
        loc = Nominatim(user_agent=ua).geocode(f"China {addr}" if "China" not in addr else addr, timeout=5)
        if loc: return {"success": True, "lat": loc.latitude, "lng": loc.longitude, "addr": loc.address}
    except: pass
    return {"success": False, "lat": 39.90, "lng": 116.40, "msg": "定位失败，使用默认坐标"}

# ==========================================
# 3. 外部 AI 调用接口 (核心新增)
# ==========================================
def call_friend_ai(api_key, base_url, prompt):
    """
    通用接口：调用外部 AI (如 DeepSeek, ChatGPT, 或你朋友的本地模型)
    """
    if not api_key:
        return mock_ai_analysis(prompt) # 如果没填Key，使用模拟分析

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo", # 这里可以让你朋友提供模型名称
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    try:
        # 假设你朋友的接口兼容 OpenAI 格式
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ 连接朋友AI失败 (Code {response.status_code}): {response.text}"
    except Exception as e:
        return f"⚠️ 网络请求异常: {str(e)}"

def mock_ai_analysis(context):
    """本地规则模拟 AI (当用户没有 API Key 时使用)"""
    import time
    time.sleep(1.5) # 模拟思考时间
    return f"""
    【本地 AI 模拟分析】
    根据命盘数据分析：
    1. **格局判断**：{context[:50]}...
    2. **大运走势**：检测到K线在30-40岁区间有剧烈波动，往往对应事业转折。
    3. **建议**：这是本地模拟数据。如需真实分析，请在左侧填入 API Key 连接云端大脑。
    """

# ==========================================
# 4. 命理引擎 (重构算法：引入大运盛衰)
# ==========================================
class DestinyEngine:
    def __init__(self, b_date, h, m, lat, lng, gender):
        self.birth_date = b_date
        self.gender = gender
        self.solar = Solar.fromYmdHms(b_date.year, b_date.month, b_date.day, h, m, 0)
        self.lunar = self.solar.getLunar()
        self.bazi = self.lunar.getEightChar()
        self.seed = hash((b_date, h, m, lat))
        
        self.wuxing_strength = self._calc_wuxing()
        self.favored = self._calc_favored() # 喜用神
        
    def _calc_wuxing(self):
        # 简化版五行统计
        cnt = {"金":0, "木":0, "水":0, "火":0, "土":0}
        map_wx = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水",
                  "寅":"木","卯":"木","巳":"火","午":"火","申":"金","酉":"金","亥":"水","子":"水","辰":"土","戌":"土","丑":"土","未":"土"}
        for p in [self.bazi.getYearGan(), self.bazi.getYearZhi(), self.bazi.getMonthGan(), self.bazi.getMonthZhi(),
                  self.bazi.getDayGan(), self.bazi.getDayZhi(), self.bazi.getTimeGan(), self.bazi.getTimeZhi()]:
            if p in map_wx: cnt[map_wx[p]] += 1
        return cnt

    def _calc_favored(self):
        # 简单逻辑：缺什么喜什么，或者抑制过强的
        # 真实逻辑极复杂，这里用 simplified logic 保证演示效果
        sorted_wx = sorted(self.wuxing_strength.items(), key=lambda x:x[1])
        weakest = sorted_wx[0][0] # 最弱的作为喜神
        return weakest

    def _get_dayun_wuxing(self, age):
        """模拟十年大运的五行属性"""
        # 每10年换一个大运五行
        cycle = ["木", "火", "土", "金", "水"]
        # 根据出生种子偏移
        start_idx = self.seed % 5
        idx = (start_idx + (age // 10)) % 5
        return cycle[idx]

    def generate_realistic_kline(self):
        """
        [核心重构] 生成真实起伏的K线
        逻辑：大运五行 vs 喜用神
        """
        data = []
        price = 100.0 # 初始人生资本
        favored = self.favored
        
        # 生克关系
        # key 生 value
        generate = {"木":"火", "火":"土", "土":"金", "金":"水", "水":"木"}
        # key 克 value
        overcome = {"木":"土", "土":"水", "水":"火", "火":"金", "金":"木"}
        
        random.seed(self.seed)
        
        for age in range(101):
            year = self.birth_date.year + age
            
            # 1. 获取当前大运 (10年一个基调)
            dayun = self._get_dayun_wuxing(age)
            
            # 2. 获取流年 (1年一个波动)
            liunian_idx = (year - 4) % 10 
            liunian_map = ["木","木","火","火","土","土","金","金","水","水"]
            liunian = liunian_map[liunian_idx]
            
            # 3. 计算趋势分 (Trend Score)
            trend = 0
            reason = ""
            
            # --- 大运决定长期趋势 ---
            if dayun == favored:
                trend += 3.0 # 大运助我 -> 牛市基础
                base_status = "大运得势"
            elif generate.get(dayun) == favored:
                trend += 2.0 # 大运生我 -> 慢牛
                base_status = "贵人相助"
            elif overcome.get(dayun) == favored:
                trend -= 3.0 # 大运克喜神 -> 熊市基础 (关键！这会导致下跌)
                base_status = "大运受阻"
            elif overcome.get(favored) == dayun:
                trend -= 1.0 # 喜神克大运 -> 辛苦
                base_status = "劳碌奔波"
            else:
                trend -= 0.5 # 消耗
                base_status = "平庸过渡"

            # --- 流年决定短期波动 ---
            if liunian == favored:
                trend += 3.0 # 流年给力
                reason = f"{base_status} + 流年{liunian}生旺"
            elif overcome.get(liunian) == favored:
                trend -= 4.0 # 流年破局 (关键！暴跌来源)
                reason = f"{base_status} + 流年{liunian}克破"
            else:
                reason = f"{base_status} + 流年{liunian}平稳"

            # 4. 随机扰动 (黑天鹅事件)
            noise = random.normalvariate(0, 2.0)
            
            # 5. 计算最终涨跌
            change = trend + noise
            
            # 6. 价格迭代 (允许跌破开盘价)
            close = price + change
            
            # 确保不会归零，最低保留10分
            close = max(10, close)
            
            # 记录 K线
            data.append({
                "Age": age, "Year": year,
                "Open": price, "Close": close,
                "High": max(price, close) + abs(change), # 震荡
                "Low": min(price, close) - abs(change),
                "Status": "📈 牛市" if change > 0 else "📉 熊市",
                "Reason": reason,
                "Dayun": dayun,
                "Liunian": liunian
            })
            
            price = close
            
        return pd.DataFrame(data)

    def get_prompt_context(self):
        """生成给 AI 读的提示词上下文"""
        df = self.generate_realistic_kline()
        # 提取关键转折点 (最低点和最高点)
        min_row = df.loc[df['Close'].idxmin()]
        max_row = df.loc[df['Close'].idxmax()]
        
        return f"""
        用户八字：{self.bazi.getYearGan()}{self.bazi.getYearZhi()}...
        喜用神：{self.favored}
        五行分布：{self.wuxing_strength}
        
        K线数据摘要：
        - 最低谷：{min_row['Age']}岁，原因：{min_row['Reason']}
        - 最高峰：{max_row['Age']}岁，原因：{max_row['Reason']}
        - 当前趋势（{datetime.now().year - self.birth_date.year}岁）：{df.iloc[datetime.now().year - self.birth_date.year]['Status']}
        
        请根据以上数据，用算命师结合金融分析师的口吻，点评该用户的一生财运趋势，并给出3条具体建议。
        """

# ==========================================
# 5. 主程序
# ==========================================
def main():
    # --- 侧边栏配置 ---
    with st.sidebar:
        st.header("⚙️ 终端设置")
        
        with st.expander("🤖 AI 接口设置 (连接朋友AI)", expanded=True):
            st.caption("留空则使用本地模拟分析")
            api_base = st.text_input("Base URL", "https://api.openai.com/v1")
            api_key = st.text_input("API Key", type="password")
        
        st.markdown("---")
        st.header("📂 档案录入")
        name = st.text_input("姓名", "某君")
        gender = st.selectbox("性别", ["男", "女"])
        
        # 日期选择
        c1, c2, c3 = st.columns([1.2, 1, 1])
        y = c1.selectbox("年", range(1950, 2026), index=40)
        m = c2.selectbox("月", range(1, 13), format_func=lambda x:f"{x}月")
        d = c3.selectbox("日", range(1, 32))
        
        # 时间选择
        t1, t2 = st.columns(2)
        hh = t1.selectbox("时", range(24), index=12)
        mm = t2.selectbox("分", range(60))
        
        # 定位
        prov = st.selectbox("省份", ["北京市","上海市","广东省","浙江省","江苏省","四川省","其他"])
        detail = st.text_input("详细地址", "市辖区")
        
        if st.button("🛰️ 重新定位"):
            res = get_precise_location(f"{prov}{detail}")
            st.session_state.loc = res

    # 引擎初始化
    loc = st.session_state.get('loc', {'lat':39.9, 'lng':116.4})
    b_date = date(y, m, d)
    engine = DestinyEngine(b_date, hh, mm, loc['lat'], loc['lng'], gender)
    
    # 标题区
    st.title(f"🔮 命运量化终端: {name}")
    st.caption("Life Destiny Quantitative Terminal (Powered by AI)")
    
    # --- 模块 1: 真实的 K 线 (Real K-Line) ---
    st.subheader("📉 人生大势 K 线 (真实起伏版)")
    
    df_life = engine.generate_realistic_kline()
    curr_age = datetime.now().year - y
    
    fig = go.Figure()
    
    # K线绘制
    fig.add_trace(go.Candlestick(
        x=df_life['Age'], open=df_life['Open'], high=df_life['High'], low=df_life['Low'], close=df_life['Close'],
        increasing_line_color='#ef5350', decreasing_line_color='#26a69a', # 经典红涨绿跌
        name='运势',
        text=df_life['Reason'],
        hovertemplate=(
            "<b>%{x}岁</b><br>"
            "收盘指数: %{close:.1f}<br>"
            "因素: %{text}<br>"
            "<extra></extra>"
        )
    ))
    
    fig.update_layout(
        height=500, template="plotly_white", xaxis_rangeslider_visible=False,
        title=dict(text="大运流年双重演算图", x=0.5),
        hovermode="x unified"
    )
    # 标记当前
    fig.add_vline(x=curr_age, line_dash="dash", line_color="blue", annotation_text="You")
    st.plotly_chart(fig, use_container_width=True)

    # --- 模块 2: AI 深度分析 (AI Analysis) ---
    st.markdown("---")
    st.subheader("🤖 AI 命理分析师")
    
    col_ai_btn, col_ai_status = st.columns([1, 4])
    with col_ai_btn:
        analyze_btn = st.button("⚡ 呼叫 AI 解读 K 线", type="primary")
    
    if analyze_btn:
        with st.spinner("正在连接 AI 大脑分析您的 K 线形态..."):
            # 1. 准备数据上下文
            context = engine.get_prompt_context()
            
            # 2. 调用外部接口 (或本地模拟)
            ai_reply = call_friend_ai(api_key, api_base, context)
            
            # 3. 显示结果
            st.markdown(f"""
            <div class="ai-box">
                <h4>📊 深度分析报告</h4>
                {ai_reply}
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("👆 点击上方按钮，让 AI 根据您的 K 线数据生成详细的运势研报。")

if __name__ == "__main__":
    main()