import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -------------------------------------------------------------------
# 1. 페이지 기본 설정 (제목, 아이콘, 레이아웃)
# -------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide"
)

# -------------------------------------------------------------------
# 2. 데이터 불러오기 함수 (캐싱 적용으로 속도 향상)
# -------------------------------------------------------------------
@st.cache_data
def load_population_data():
    # GitHub에서 파일 직접 다운로드를 위해 raw 주소를 사용합니다.
    # 판다스는 .zip으로 압축된 CSV 파일도 바로 읽어올 수 있습니다.
    url = "https://raw.githubusercontent.com/xeohdk/Population/main/population_ts_yearly_gender.zip"
    df = pd.read_csv(url, compression='zip')
    return df

# 데이터 로딩 안내
with st.spinner("따뜻한 마음으로 동네 인구 데이터를 불러오는 중입니다... ☕"):
    raw_df = load_population_data()

# 가장 최신 연도 데이터만 추출
latest_year = raw_df['연도'].max()
df = raw_df[raw_df['연도'] == latest_year].copy()

# -------------------------------------------------------------------
# 3. 화면 상단 타이틀 및 주소 선택 드롭다운 (시도 -> 시군구 -> 동)
# -------------------------------------------------------------------
st.title("🏘️ 우리 동네 인구 피라미드")
st.write(f"가장 최근 데이터인 **{latest_year}년** 기준, 전국 읍·면·동의 연령별 인구 구조를 살펴봅니다.")

# 3개의 컬럼으로 드롭다운 나란히 배치
col1, col2, col3 = st.columns(3)

# 1) 시·도 선택
sido_list = df['시도'].dropna().unique()
selected_sido = col1.selectbox("시·도 선택", sido_list)

# 선택한 시·도로 데이터 필터링
df_sido = df[df['시도'] == selected_sido]

# 2) 시·군·구 선택
sigungu_list = df_sido['시군구'].dropna().unique()
selected_sigungu = col2.selectbox("시·군·구 선택", sigungu_list)

# 선택한 시·군·구로 데이터 필터링
df_sigungu = df_sido[df_sido['시군구'] == selected_sigungu]

# 3) 읍·면·동 선택
dong_list = df_sigungu['동'].dropna().unique()
selected_dong = col3.selectbox("읍·면·동 선택", dong_list)

# 최종 선택된 동네의 1개 행 데이터
target_data = df_sigungu[df_sigungu['동'] == selected_dong].iloc[0]

# -------------------------------------------------------------------
# 4. 피라미드 그래프용 나이 라벨 및 데이터 정제
# -------------------------------------------------------------------
# '남_'으로 시작하는 열 이름에서 나이 라벨만 추출 (예: '0세', '1세', ..., '100세 이상')
# 순서는 원본 CSV 데이터열의 0세 -> 100세 이상 순서를 그대로 유지합니다.
age_labels = [col.replace('남_', '') for col in df.columns if col.startswith('남_')]

# 남성/여성 인구수 리스트 생성
male_pop = [target_data[f"남_{age}"] for age in age_labels]
female_pop = [target_data[f"여_{age}"] for age in age_labels]

# 인구 피라미드 표현을 위해 남성 인구수는 음수로 전환 (왼쪽 배치)
male_pop_neg = [-val for val in male_pop]

# -------------------------------------------------------------------
# 5. Plotly 인구 피라미드 시각화 생성
# -------------------------------------------------------------------
fig = go.Figure()

# [남자] 막대 그래프 (왼쪽, 음수 값)
fig.add_trace(go.Bar(
    y=age_labels,
    x=male_pop_neg,
    name='남자',
    orientation='h',
    marker=dict(color='#6366F1'), # 따뜻하고 부드러운 인디고 블루
    customdata=male_pop,          # 마우스 호버 시 보여줄 실제 양수 값
    hovertemplate='<b>%{y}</b><br>남자 인구: %{customdata:,}명<extra></extra>'
))

# [여자] 막대 그래프 (오른쪽, 양수 값)
fig.add_trace(go.Bar(
    y=age_labels,
    x=female_pop,
    name='여자',
    orientation='h',
    marker=dict(color='#EC4899'), # 따뜻하고 부드러운 핑크
    hovertemplate='<b>%{y}</b><br>여자 인구: %{x:,}명<extra></extra>'
))

# 가로축(X축) 눈금 단위를 양수로 깔끔하게 정돈하기 위한 설정
max_pop = max(max(male_pop), max(female_pop)) if max(male_pop + female_pop) > 0 else 100
step = max(1, int(max_pop / 4))
tick_vals = list(range(-step * 4, step * 5, step))
tick_texts = [f"{abs(v):,}명" for v in tick_vals]

# 레이아웃 상세 설정
fig.update_layout(
    title=dict(
        text=f"<b>[{selected_sido} {selected_sigungu} {selected_dong}] 인구 피라미드</b>",
        font=dict(size=18),
        x=0.5,
        xanchor='center'
    ),
    barmode='relative',
    bargap=0.1,
    xaxis=dict(
        title="인구수",
        tickmode='array',
        tickvals=tick_vals,
        ticktext=tick_texts
    ),
    yaxis=dict(
        title="연령",
        type='category',
        categoryorder='array',
        categoryarray=age_labels  # 0세가 맨 아래, 100세 이상이 맨 위로 배치되는 순서 고정
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    height=750,
    margin=dict(l=40, r=40, t=80, b=40)
)

# -------------------------------------------------------------------
# 6. Streamlit 화면에 그래프 출력 및 요약 정보
# -------------------------------------------------------------------
st.plotly_chart(fig, use_container_width=True)

# 주요 통계 요약
total_male = sum(male_pop)
total_female = sum(female_pop)
total_pop = total_male + total_female

st.info(f"💡 **{selected_dong}**의 총인구는 **{total_pop:,}명** (남성: {total_male:,}명, 여성: {total_female:,}명) 입니다.")
