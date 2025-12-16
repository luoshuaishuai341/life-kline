import streamlit as st
import pandas as pd
import datetime
import random
import plotly.graph_objects as go
import plotly.express as px

# 设置页面配置
st.set_page_config(page_title="高阶八字运势分析系统", layout="wide", page_icon="☯️")

# --- 1. 模拟地理数据与经纬度 (实际开发中建议对接高德/百度地图API) ---
# 这是一个简化的四级联动数据结构
CHINA_LOCATIONS = {
    "北京市": {
        "coords": [116.4074, 39.9042],
        "children": {
            "朝阳区": {
                "coords": [116.4431, 39.9215],
                "hospitals": ["朝阳医院", "中日友好医院", "首都儿科研究所"]
            },
            "海淀区": {
                "coords": [116.2981, 39.9593],
                "hospitals": ["北医三院", "海淀医院", "西苑医院"]
            }
        }
    },
    "上海市": {
        "coords": [121.4737, 31.2304],
        "children": {
            "浦东新区": {
                "coords": [121.5447, 31.2225],
                "hospitals": ["东方医院", "仁济医院东院", "曙光医院"]
            },
            "黄浦区": {
                "coords": [121.4844, 31.2317],
                "hospitals": ["瑞金医院", "长征医院", "第九人民医院"]
            }
        }
    }
}

# --- 2. 核心计算函数 (模拟) ---

def calculate_lat_lon(province, city, district, specific_place):
    """
    根据选择的地点计算经纬度。
    在真实场景中，这里应该调用地图API。
    这里使用基准坐标 + 随机微小偏移来模拟具体地点的精度。
    """
    base_coords = CHINA_LOCATIONS.get(province, {}).get("children", {}).get(district, {}).get("coords", [116.0, 39.0])
    
    # 模拟不同医院/地点的微小经纬度差异
    offset_val = sum(ord(c) for c in specific_place) % 100 * 0.0001 if specific_place else 0
    real_lon = base_coords[0] + offset_val
    real_lat = base_coords[1] + offset_val
    
    return real_lon, real_lat

def generate_daily_fortune(birth_date, target_year):
    """
    生成指定年份每一天的运势数据
    """
    start_date = datetime.date(target_year, 1, 1)
    end_date = datetime.date(target_year, 12, 31)
    delta = end_date - start_date
    
    data = []
    # 使用出生日期作为种子，保证同一个人看到的运势是固定的
    seed_base = int(birth_date.strftime("%Y%m%d"))
    
    for i in range(delta.days + 1):
        curr_date = start_date + datetime.timedelta(days=i)
        day_seed = seed_base + int(curr_date.strftime("%Y%m%d"))
        random.seed(day_seed)
        
        # 模拟 K线数据 (开盘, 最高, 最低, 收盘) - 这里指运势分数的波动
        open_score = random.randint(50, 80)
        close_score = open_score + random.randint(-10, 15)
        high_score = max(open_score, close_score) + random.randint(0, 5)
        low_score = min(open_score, close_score) - random.randint(0, 5)
        
        # 限制在0-100之间
        high_score = min(100, high_score)
        low_score = max(0, low_score)
        
        desc = "大吉" if close_score > 85 else ("平运" if close_score > 60 else "需谨慎")
        
        data.append({
            "日期": curr_date,
            "开盘": open_score,
            "收盘": close_score,
            "最高": high_score,
            "最低": low_score,
            "运势描述": desc
        })
    return pd.DataFrame(data)

# --- 3. 页面 UI 布局 ---

st.title("🌌 全息八字运势分析系统 v2.0")
st.markdown("---")

# === 左侧边栏：信息输入 ===
with st.sidebar:
    st.header("1. 个人信息录入")
    
    # --- 出生日期 (中文显示) ---
    birth_date = st.date_input(
        "选择出生日期",
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date.today(),
        value=datetime.date(1990, 1, 1),
        format="YYYY/MM/DD" # 显示格式
    )
    
    birth_time = st.time_input("选择出生时间", datetime.time(12, 00))
    
    # --- 级联地址选择 ---
    st.subheader("出生地点精确选择")
    
    # Level 1: 省/直辖市
    province_list = list(CHINA_LOCATIONS.keys())
    selected_province = st.selectbox("选择省份/直辖市", province_list)
    
    # Level 2: 市 (这里为了简化，直辖市的下一级直接是区，逻辑可根据实际json调整)
    # 假设直辖市逻辑: 省=市
    selected_city = selected_province 
    
    # Level 3: 区/县
    district_data = CHINA_LOCATIONS[selected_province]["children"]
    district_list = list(district_data.keys())
    selected_district = st.selectbox("选择区/县", district_list)
    
    # Level 4: 医院/具体地点
    hospital_list = district_data[selected_district].get("hospitals", []) + ["其他地点"]
    selected_hospital = st.selectbox("选择出生医院/地点", hospital_list)
    
    # 计算经纬度
    lon, lat = calculate_lat_lon(selected_province, selected_city, selected_district, selected_hospital)
    
    st.info(f"📍 自动计算坐标：\n经度 {lon:.4f} E\n纬度 {lat:.4f} N")
    
    if st.button("开始排盘分析", type="primary"):
        st.session_state['analyzed'] = True
    else:
        st.session_state['analyzed'] = False

# === 主界面内容 ===

if st.session_state.get('analyzed'):
    # 基础信息展示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("出生地点", f"{selected_province} {selected_district}")
    with col2:
        st.metric("出生坐标", f"E:{lon:.2f}, N:{lat:.2f}")
    with col3:
        st.metric("生辰", f"{birth_date} {birth_time}")

    st.markdown("---")

    # --- 模块：年度运势 K线图 ---
    st.header("📈 2025年流年运势 K线图")
    st.caption("注：K线代表每日运势能量波动。红色代表运势上升（阳线），绿色代表运势下行（阴线）。")

    # 生成数据
    df_fortune = generate_daily_fortune(birth_date, 2025)
    
    # 绘制 K线图
    fig = go.Figure(data=[go.Candlestick(
        x=df_fortune['日期'],
        open=df_fortune['开盘'],
        high=df_fortune['最高'],
        low=df_fortune['最低'],
        close=df_fortune['收盘'],
        increasing_line_color='red', 
        decreasing_line_color='green',
        name="运势能量"
    )])

    fig.update_layout(
        title='2025年 全年运势波动图',
        yaxis_title='运势能量值 (0-100)',
        xaxis_title='日期',
        template="plotly_white",
        height=500,
        hovermode="x unified" # 鼠标悬停显示详细信息
    )
    
    # 添加中文解释注解
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="大吉区", annotation_position="top left")
    fig.add_hline(y=40, line_dash="dash", line_color="gray", annotation_text="低谷区", annotation_position="bottom left")

    st.plotly_chart(fig, use_container_width=True)

    # --- 模块：具体查看每一天的运势 ---
    st.markdown("---")
    st.header("📅 每日运势详情查询")
    
    c1, c2 = st.columns([1, 3])
    with c1:
        # 选择具体日期
        check_date = st.date_input(
            "选择你想查询的日期", 
            value=datetime.date(2025, 1, 1),
            min_value=datetime.date(2025, 1, 1),
            max_value=datetime.date(2025, 12, 31)
        )
    
    with c2:
        # 获取该日数据
        day_data = df_fortune[df_fortune['日期'] == check_date].iloc[0]
        
        score = day_data['收盘']
        desc = day_data['运势描述']
        
        # 动态展示样式
        if score > 80:
            st.success(f"🌟 **{check_date} 运势：{desc} (分数: {score})**")
            st.markdown("今日能量充沛，适合做重要决策，诸事皆宜。")
        elif score > 60:
            st.info(f"🍃 **{check_date} 运势：{desc} (分数: {score})**")
            st.markdown("今日运势平稳，按部就班即可，无大碍。")
        else:
            st.warning(f"⚠️ **{check_date} 运势：{desc} (分数: {score})**")
            st.markdown("今日能量较低，宜静不宜动，注意言行，避免冲突。")
            
        # 模拟展示宜忌 (这里随机生成，实际需结合老黄历算法)
        st.write("**今日宜：** 读书、纳财、修造")
        st.write("**今日忌：** 远行、诉讼、动土")

else:
    st.info("👈 请在左侧填写完整信息并点击【开始排盘分析】")