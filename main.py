import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# 1. 기본 설정 & 무서운 커스텀 스타일링 (Dark Horror Theme)
# =========================================================

st.set_page_config(
    page_title="공포의 동네별 인구 피라미드",
    page_icon="💀",
    layout="wide",
)

# 으스스하고 기괴한 분위기를 연출하는 커스텀 CSS
st.markdown(
    """
    <style>
        /* 전체 배경: 깊은 어둠의 보이드 블랙 */
        .stApp {
            background-color: #0b090a;
            color: #d3d3d3;
        }
        
        /* 헤더 텍스트: 피에 젖은 듯한 붉은 글로우 효과 */
        h1, h2, h3, h4, h5, h6 {
            color: #ff1e27 !important;
            text-shadow: 0 0 10px #8b0000, 0 0 20px #000000;
            font-family: 'Courier New', Courier, monospace;
        }

        /* 지표 카드: 피로 얼룩진 카드 스타일 */
        div[data-testid="stMetric"] {
            background-color: #161214 !important;
            border: 1px solid #8b0000 !important;
            box-shadow: 0 0 12px rgba(139, 0, 0, 0.5);
            padding: 16px;
            border-radius: 8px;
        }
        
        div[data-testid="stMetricLabel"] {
            color: #a09090 !important;
        }

        div[data-testid="stMetricValue"] {
            color: #ff3333 !important;
            text-shadow: 0 0 8px #ff0000;
        }

        /* 경고 및 안내 박스: 피빛 오버레이 */
        .stAlert {
            background-color: #1a0507 !important;
            border: 1px solid #ff0033 !important;
            color: #ffcccc !important;
            box-shadow: 0 0 15px rgba(255, 0, 51, 0.4);
        }

        /* 드롭다운 셀렉트 박스 스타일 */
        div[data-baseweb="select"] > div {
            background-color: #1a1618 !important;
            color: #ff4d4d !important;
            border-color: #8b0000 !important;
        }

        /* Expander 테두리 */
        .streamlit-expanderHeader {
            background-color: #161214 !important;
            color: #ff4d4d !important;
            border: 1px solid #5a0000 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2. 데이터 불러오기
# =========================================================

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "greatsong/modudata/main/data/population_yearly.csv.gz"
)


@st.cache_data
def load_data():
    data = pd.read_csv(DATA_URL, compression="gzip")
    data.columns = data.columns.astype(str).str.strip()

    data["연도"] = pd.to_numeric(data["연도"], errors="coerce")
    data = data.dropna(subset=["연도"]).copy()
    data["연도"] = data["연도"].astype(int)

    latest_year = int(data["연도"].max())
    data = data[data["연도"] == latest_year].copy()

    for column in ["시도", "시군구", "동"]:
        data[column] = data[column].astype("string").str.strip()

    return data, latest_year


st.title("🩸 공포의 동네별 인구 피라미드 : 생존자 보고서 💀")
st.markdown(
    """
    이곳은 살아남은 자들과 늙어가는 영혼들의 기록입니다...  
    시도, 시군구, 동을 선택해 기괴하게 변화하는 인구 구조와 소멸의 징후를 확인하십시오.
    """
)

try:
    with st.spinner("어둠 속에서 인구 기록을 파헤치는 중..."):
        df, latest_year = load_data()
except Exception as error:
    st.error("기록을 불러오는 데 실패했습니다. 누군가 인구 수첩을 훔쳐갔습니다...")
    st.caption(f"오류 원인: {error}")
    st.stop()

if df.empty:
    st.warning("☠️ 해당 연도에 존재하는 생존 기록이 전혀 없습니다.")
    st.stop()


# =========================================================
# 3. 지역 선택: 시도 → 시군구 → 동
# =========================================================

st.subheader("📍 죽음의 지역 선택")

col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(df["시도"].dropna().unique().tolist())
    if not sido_list:
        st.warning("선택할 시도 데이터가 없습니다.")
        st.stop()
    selected_sido = st.selectbox("❶ 피의 시도", options=sido_list)

sido_df = df[df["시도"] == selected_sido].copy()

with col2:
    sigungu_list = sorted(sido_df["시군구"].dropna().unique().tolist())
    if not sigungu_list:
        st.warning("선택한 시도에 시군구 데이터가 없습니다.")
        st.stop()
    selected_sigungu = st.selectbox("❷ 핏빛 시군구", options=sigungu_list)

sigungu_df = sido_df[sido_df["시군구"] == selected_sigungu].copy()

with col3:
    dong_list = sorted(sigungu_df["동"].dropna().unique().tolist())
    if not dong_list:
        st.warning("선택한 시군구에 동 데이터가 없습니다.")
        st.stop()
    selected_dong = st.selectbox("❸ 죽음의 동", options=dong_list)


# =========================================================
# 4. 선택한 동네의 데이터 찾기
# =========================================================

selected_df = df[
    (df["시도"] == selected_sido)
    & (df["시군구"] == selected_sigungu)
    & (df["동"] == selected_dong)
].copy()

if selected_df.empty:
    st.warning("☠️ 선택한 지역에는 아무런 생존 흔적도 남아있지 않습니다.")
    st.stop()

if len(selected_df) > 1:
    st.warning("⚠️ 동일한 지역의 영혼들이 여럿 겹쳐 있어 합산합니다.")

    population_columns = [
        column for column in selected_df.columns
        if column.startswith("남_") or column.startswith("여_")
    ]
    row = selected_df.iloc[0].copy()
    for column in population_columns:
        row[column] = pd.to_numeric(
            selected_df[column], errors="coerce"
        ).fillna(0).sum()
else:
    row = selected_df.iloc[0]


# =========================================================
# 5. 나이별 남녀 인구 계산
# =========================================================

age_labels = [f"{age}세" for age in range(100)] + ["100세 이상"]
male_columns = [f"남_{age}세" for age in range(100)] + ["남_100세 이상"]
female_columns = [f"여_{age}세" for age in range(100)] + ["여_100세 이상"]


def get_population(data_row, column_name):
    if column_name not in data_row.index:
        return 0

    value = pd.to_numeric(data_row[column_name], errors="coerce")
    if pd.isna(value):
        return 0

    return max(0, int(value))


male_population = [get_population(row, col) for col in male_columns]
female_population = [get_population(row, col) for col in female_columns]

male_left = [-value for value in male_population]
female_right = female_population

age_population = [
    male_population[i] + female_population[i]
    for i in range(101)
]

total_male = sum(male_population)
total_female = sum(female_population)
total_population = total_male + total_female


# =========================================================
# 6. 추가 지표 계산 & 섬뜩한 분석 문구
# =========================================================

if total_population > 0:
    average_age = sum(
        age * age_population[age]
        for age in range(101)
    ) / total_population
else:
    average_age = 0.0

elderly_population = sum(age_population[65:])
aging_rate = (
    elderly_population / total_population * 100
    if total_population > 0
    else 0.0
)

child_population = sum(age_population[0:15])

if child_population > elderly_population:
    population_comment = (
        "이 동네는 어둠 속에서도 0~14세 어린 생명들이 65세 이상 늙은 영혼들보다 "
        "더 많이 꿈틀대고 있습니다..."
    )
elif child_population < elderly_population:
    population_comment = (
        "이 동네는 어린 아이들의 웃음소리가 사라지고 65세 이상 늙은 영혼들만이 "
        "스산하게 자리를 지키고 있습니다..."
    )
else:
    population_comment = (
        "이 동네는 어린 생명과 늙은 영혼의 수가 동일하여 기묘하고 기괴한 균형을 이루고 있습니다..."
    )

is_aging_warning = aging_rate > 20


# =========================================================
# 7. 기괴한 지표 카드 3개
# =========================================================

st.divider()
st.subheader(f"📊 [파멸 분석] {selected_sido} {selected_sigungu} {selected_dong}")
st.caption(f"기록 연도: {latest_year}년 기준 · 참혹한 현주소")

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(
        label="💀 총 생존 인구",
        value=f"{total_population:,} 명",
    )

with metric2:
    st.metric(
        label="⏳ 평균 연령 (영혼의 나이)",
        value=f"{average_age:.1f} 세",
    )

with metric3:
    st.metric(
        label="🩸 고령화율 (65세 이상)",
        value=f"{aging_rate:.1f}%",
        delta="⚠️ 20% 초과 (붉은 재앙)" if is_aging_warning else "20% 이하 (잠식 진행)",
        delta_color="inverse",
    )

if is_aging_warning:
    st.warning(
        f"🚨 **경고**: 고령화율이 20%를 넘었습니다! "
        f"이 지역 생존자의 {aging_rate:.1f}%가 65세 이상 어르신으로, 소멸의 늪에 빠져들고 있습니다..."
    )


# =========================================================
# 8. 잔혹한 인구 피라미드 그리기 (Blood Red & Void Purple)
# =========================================================

fig = go.Figure()

# 남성: 피빛 진홍색
fig.add_trace(
    go.Bar(
        x=male_left,
        y=age_labels,
        orientation="h",
        name="남성 생존자",
        marker_color="#D90429",
        customdata=male_population,
        hovertemplate="연령: %{y}<br>남성 인구: %{customdata:,}명<extra></extra>",
    )
)

# 여성: 음산한 바이올렛 보라색
fig.add_trace(
    go.Bar(
        x=female_right,
        y=age_labels,
        orientation="h",
        name="여성 생존자",
        marker_color="#7B2CBF",
        customdata=female_population,
        hovertemplate="연령: %{y}<br>여성 인구: %{customdata:,}명<extra></extra>",
    )
)

max_population = max(max(male_population), max(female_population), 1)
axis_limit = max_population * 1.1

tick_step = max(1, int(np.ceil(axis_limit / 5)))
positive_ticks = list(range(0, int(axis_limit) + tick_step, tick_step))
positive_ticks = [value for value in positive_ticks if value <= axis_limit]

if not positive_ticks or positive_ticks[0] != 0:
    positive_ticks.insert(0, 0)

tick_values = (
    [-value for value in reversed(positive_ticks) if value != 0]
    + [0]
    + [value for value in positive_ticks if value != 0]
)
tick_text = [f"{abs(value):,}" for value in tick_values]

fig.update_layout(
    title={
        "text": f"👻 {selected_dong} 연령별 생존 영혼 분포",
        "x": 0.5,
        "xanchor": "center",
        "font": {"size": 18, "color": "#FF2E63"},
    },
    barmode="overlay",
    bargap=0.1,
    height=1000,
    plot_bgcolor="#0d090a",
    paper_bgcolor="#0b090a",
    font={"family": "Courier New, monospace", "size": 11, "color": "#E0E0E0"},
    legend={
        "title": "성별",
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "center",
        "x": 0.5,
    },
    xaxis={
        "title": "생존자 수 (명)",
        "range": [-axis_limit, axis_limit],
        "tickmode": "array",
        "tickvals": tick_values,
        "ticktext": tick_text,
        "zeroline": True,
        "zerolinecolor": "#FF0055",
        "zerolinewidth": 2,
        "gridcolor": "#2B0B10",
    },
    yaxis={
        "title": "연령",
        "categoryorder": "array",
        "categoryarray": age_labels,
        "autorange": True,
        "showgrid": False,
        "tickfont": {"size": 10, "color": "#BBBBBB"},
    },
    margin={"l": 100, "r": 40, "t": 100, "b": 70},
)

st.plotly_chart(fig, width="stretch", config={"displayModeBar": True})


# =========================================================
# 9. 피라미드 아래 자동 한 줄 공포 분석
# =========================================================

st.info(
    "🩸 **이 동네는 아이가 많은 편인가요, 어르신이 많은 편인가요?**\n\n"
    + population_comment
)


# =========================================================
# 10. 연령별 인구 표
# =========================================================

with st.expander("📋 [비밀 문서] 연령별 생존자 상세 명단 열람"):
    population_table = pd.DataFrame(
        {
            "나이": age_labels,
            "남성 생존자": male_population,
            "여성 생존자": female_population,
            "영혼 합계": age_population,
        }
    )

    st.dataframe(
        population_table,
        hide_index=True,
        width="stretch",
    )

st.caption(
    "출처: 금기된 읍·면·동 연도별 인구 데이터 | "
    "붉은쪽(왼쪽)은 남성, 보라쪽(오른쪽)은 여성입니다. "
    "100세 이상 불멸자는 100세로 간주하여 처리되었습니다."
)
