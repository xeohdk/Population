import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Streamlit 페이지 설정
st.set_page_config(page_title="동네 인구 피라미드 & 지표 분석", layout="wide")

st.title("📊 동네별 인구 구조 분석")

# ---------------------------------------------------------
# 1. 샘플 데이터 생성 (실제 데이터 적용 시 CSV 읽기 로직으로 교체)
# ---------------------------------------------------------
@st.cache_data
def load_sample_data():
    np.random.seed(42)
    ages = list(range(0, 101))
    
    # 동네 A: 신도시 (아이가 많은 동네)
    male_a = np.exp(-np.array(ages)/35) * np.random.uniform(800, 1200, size=101)
    female_a = np.exp(-np.array(ages)/35) * np.random.uniform(800, 1200, size=101)
    
    # 동네 B: 초고령 지역 (어르신이 많은 동네)
    male_b = (1 + np.array(ages)/25) * np.exp(-np.array(ages)/75) * np.random.uniform(200, 500, size=101)
    female_b = (1 + np.array(ages)/25) * np.exp(-np.array(ages)/75) * np.random.uniform(200, 500, size=101)
    
    df_a = pd.DataFrame({'연령': ages, '남성': np.round(male_a), '여성': np.round(female_a), '동네': '행복1동 (젊은 동네)'})
    df_b = pd.DataFrame({'연령': ages, '남성': np.round(male_b), '여성': np.round(female_b), '동네': '희망2동 (고령화 동네)'})
    
    return pd.concat([df_a, df_b], ignore_index=True)

df = load_sample_data()

# 동네 선택 사이드바
selected_region = st.sidebar.selectbox("동네를 선택하세요", df['동네'].unique())
filtered_df = df[df['동네'] == selected_region].copy()

# ---------------------------------------------------------
# 2. 주요 지표 계산
# ---------------------------------------------------------
filtered_df['총인구'] = filtered_df['남성'] + filtered_df['여성']
total_pop = filtered_df['총인구'].sum()

# 평균 연령 계산
avg_age = (filtered_df['연령'] * filtered_df['총인구']).sum() / total_pop if total_pop > 0 else 0

# 유소년인구 (0~14세) & 고령인구 (65세 이상)
child_pop = filtered_df[filtered_df['연령'] <= 14]['총인구'].sum()
elderly_pop = filtered_df[filtered_df['연령'] >= 65]['총인구'].sum()

child_ratio = (child_pop / total_pop * 100) if total_pop > 0 else 0
elderly_ratio = (elderly_pop / total_pop * 100) if total_pop > 0 else 0

# ---------------------------------------------------------
# 3. 그래프 상단 지표 카드 3개 나란히 배치
# ---------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="총인구", value=f"{int(total_pop):,} 명")

with col2:
    st.metric(label="평균연령", value=f"{avg_age:.1f} 세")

with col3:
    # 고령화율 20% 초과 시 주의 표시(⚠️) 붙이기
    if elderly_ratio >= 20.0:
        st.metric(
            label="고령화율 (65세 이상) ⚠️",
            value=f"{elderly_ratio:.1f}%",
            delta="⚠️ 초고령사회 (20% 초과)",
            delta_color="inverse"
        )
    else:
        st.metric(
            label="고령화율 (65세 이상)",
            value=f"{elderly_ratio:.1f}%",
            delta="일반"
        )

st.markdown("---")

# ---------------------------------------------------------
# 4. 연령별 인구 피라미드 그래프
# ---------------------------------------------------------
st.subheader("👥 연령별 인구 피라미드")

fig = go.Figure()

# 남성 (음수 값으로 왼쪽 배치)
fig.add_trace(go.Bar(
    y=filtered_df['연령'],
    x=-filtered_df['남성'],
    name='남성',
    orientation='h',
    marker_color='#3182ce'
))

# 여성 (양수 값으로 오른쪽 배치)
fig.add_trace(go.Bar(
    y=filtered_df['연령'],
    x=filtered_df['여성'],
    name='여성',
    orientation='h',
    marker_color='#e53e3e'
))

# X축 절대값 표시 레이아웃 설정
max_val = max(filtered_df['남성'].max(), filtered_df['여성'].max()) * 1.1
ticks = np.linspace(-max_val, max_val, 7)

fig.update_layout(
    barmode='relative',
    bargap=0.1,
    xaxis=dict(
        tickvals=ticks,
        ticktext=[f"{abs(int(x)):,}" for x in ticks],
        title="인구 수 (명)"
    ),
    yaxis=dict(title="연령 (세)"),
    height=480,
    margin=dict(l=20, r=20, t=30, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 5. 피라미드 아래 자동 한 줄 설명
# ---------------------------------------------------------
st.subheader("💡 이 동네는 아이가 많은 편인가요, 어르신이 많은 편인가요?")

diff = child_ratio - elderly_ratio

if child_ratio > elderly_ratio:
    summary = f"이 동네는 아이(0~14세, **{child_ratio:.1f}%**) 비율이 어르신(65세 이상, **{elderly_ratio:.1f}%**)보다 **{diff:.1f}%p** 높아서 **아이들이 상대적으로 많은 젊은 동네**입니다."
elif elderly_ratio > child_ratio:
    summary = f"이 동네는 어르신(65세 이상, **{elderly_ratio:.1f}%**) 비율이 아이(0~14세, **{child_ratio:.1f}%**)보다 **{abs(diff):.1f}%p** 높아서 **어르신 비중이 높은 동네**입니다."
else:
    summary = f"이 동네는 아이(**{child_ratio:.1f}%**)와 어르신(**{elderly_ratio:.1f}%**)의 비율이 비슷하여 세대 간 균형을 이루고 있는 동네입니다."

st.info(summary)
