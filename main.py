import json
import re
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# =========================================================
# 1. 페이지 설정 및 제목
# =========================================================
st.set_page_config(
    page_title="전국 시군구 인구 구조 단계구분도",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ 전국 시군구 인구 구조 단계구분도")
st.markdown(
    "연도별 전국 읍·면·동 인구 데이터를 바탕으로 시군구별 **고령화율(65세 이상)** 및 **유소년 비율(0~14세)** 변화를 비교·분석합니다."
)

DATA_URL = "https://raw.githubusercontent.com/xeohdk/Population/main/population_ts_yearly_gender.zip"
GEOJSON_URL = "https://raw.githubusercontent.com/xeohdk/Population/main/sigungu_kr.geojson.txt"


# =========================================================
# 2. 행정구역 코드 재매핑 함수
# =========================================================
def remap_sigungu_code(raw_code):
    """옛 행정구역 코드를 최신 GeoJSON 경계 파일 코드에 맞게 변환합니다."""
    if pd.isna(raw_code):
        return ""
    code_str = str(raw_code).split(".")[0].strip().zfill(8)[:5]

    # 군위군: 경북(47720) -> 대구(27720)
    if code_str == "47720":
        return "27720"
    # 강원 특별자치도: 42 -> 51
    elif code_str.startswith("42"):
        return "51" + code_str[2:]
    # 전북 특별자치도: 45 -> 52
    elif code_str.startswith("45"):
        return "52" + code_str[2:]

    return code_str


# =========================================================
# 3. 데이터 로딩 및 캐싱
# =========================================================
@st.cache_data
def load_raw_data():
    # GeoJSON 경계 데이터 내려받기
    geo_res = requests.get(GEOJSON_URL)
    geojson_data = geo_res.json()

    # GeoJSON 내부 시도/시군구 메타 정보 생성
    geojson_info = {}
    for feature in geojson_data.get("features", []):
        props = feature.get("properties", {})
        code = str(props.get("코드", "")).strip()
        sido = str(props.get("시도", "")).strip()
        sigungu = str(props.get("시군구", "")).strip()
        geojson_info[code] = {
            "시도": sido,
            "시군구": sigungu,
            "전체명": f"{sido} {sigungu}".strip(),
        }

    # 인구 데이터 읽기
    df = pd.read_csv(DATA_URL, compression="zip")
    df.columns = df.columns.astype(str).str.strip()
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"]).copy()
    df["연도"] = df["연도"].astype(int)

    return geojson_data, geojson_info, df


try:
    with st.spinner("데이터 및 경계 지도를 불러오는 중입니다..."):
        geojson_data, geojson_info, df_raw = load_raw_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# =========================================================
# 4. 상단 UI 컨트롤러 (지표 선택, 시도 선택, 연도 슬라이더)
# =========================================================
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.2, 1, 1.8])

with ctrl_col1:
    selected_metric = st.selectbox(
        "📊 지표 선택",
        options=["65세 이상 비율 (고령화율)", "0~14세 비율 (유소년 비율)"],
    )

with ctrl_col2:
    sido_list = sorted(
        list(
            set(
                info["시도"]
                for info in geojson_info.values()
                if info["시도"]
            )
        )
    )
    selected_sido = st.selectbox("📍 지역 선택", options=["전국"] + sido_list)

with ctrl_col3:
    available_years = sorted(df_raw["연도"].unique())
    selected_year = st.slider(
        "📅 연도 선택",
        min_value=int(min(available_years)),
        max_value=int(max(available_years)),
        value=int(max(available_years)),
        step=1,
    )


# =========================================================
# 5. 연도별 데이터 가공 및 인구 비율 집계
# =========================================================
@st.cache_data
def get_processed_df(year):
    df_year = df_raw[df_raw["연도"] == year].copy()

    total_cols = [col for col in df_year.columns if col.startswith("계_")]

    elderly_cols = []
    youth_cols = []
    for col in total_cols:
        nums = re.findall(r"\d+", col)
        if nums:
            age = int(nums[0])
            if age >= 65:
                elderly_cols.append(col)
            if age <= 14:
                youth_cols.append(col)

    for col in total_cols:
        df_year[col] = pd.to_numeric(df_year[col], errors="coerce").fillna(0)

    # 행정구역 코드 변환 (42->51, 45->52, 47720->27720)
    df_year["시군구코드"] = df_year["코드"].apply(remap_sigungu_code)

    df_year["전체인구"] = df_year[total_cols].sum(axis=1)
    df_year["고령인구"] = df_year[elderly_cols].sum(axis=1)
    df_year["유소년인구"] = df_year[youth_cols].sum(axis=1)

    grouped = (
        df_year.groupby("시군구코드")[["전체인구", "고령인구", "유소년인구"]]
        .sum()
        .reset_index()
    )

    grouped["고령화율"] = (
        grouped["고령인구"] / grouped["전체인구"] * 100
    ).round(2)
    grouped["유소년비율"] = (
        grouped["유소년인구"] / grouped["전체인구"] * 100
    ).round(2)

    grouped["시도명"] = grouped["시군구코드"].map(
        lambda x: geojson_info.get(x, {}).get("시도", "")
    )
    grouped["시군구명"] = grouped["시군구코드"].map(
        lambda x: geojson_info.get(x, {}).get("전체명", f"미확인 지역 ({x})")
    )

    return grouped


df_year_processed = get_processed_df(selected_year)


# =========================================================
# 6. 지표별 범주 및 색상 구간 설정 (연도 변경에도 구간 고정)
# =========================================================
if "65세 이상" in selected_metric:
    val_col = "고령화율"
    target_pop_col = "고령인구"
    metric_title = "고령화율"
    target_label = "65세 이상 인구"

    # 지정된 구간: 19%, 23%, 28%, 38%
    bins = [-float("inf"), 19, 23, 28, 38, float("inf")]
    bin_labels = [
        "19% 미만",
        "19% ~ 23% 미만",
        "23% ~ 28% 미만",
        "28% ~ 38% 미만",
        "38% 이상",
    ]
    color_map = {
        "19% 미만": "#fee5d9",
        "19% ~ 23% 미만": "#fcae91",
        "23% ~ 28% 미만": "#fb6a4a",
        "28% ~ 38% 미만": "#de2d26",
        "38% 이상": "#a50f15",
    }
else:
    val_col = "유소년비율"
    target_pop_col = "유소년인구"
    metric_title = "유소년 비율"
    target_label = "0~14세 인구"

    # 유소년 전용 구간: 7%, 9%, 11%, 13%
    bins = [-float("inf"), 7, 9, 11, 13, float("inf")]
    bin_labels = [
        "7% 미만",
        "7% ~ 9% 미만",
        "9% ~ 11% 미만",
        "11% ~ 13% 미만",
        "13% 이상",
    ]
    color_map = {
        "7% 미만": "#eff3ff",
        "7% ~ 9% 미만": "#bdd7e7",
        "9% ~ 11% 미만": "#6baed6",
        "11% ~ 13% 미만": "#3182bd",
        "13% 이상": "#08519c",
    }

df_year_processed["구간"] = pd.cut(
    df_year_processed[val_col], bins=bins, labels=bin_labels, right=False
)


# =========================================================
# 7. 선택 지역(시도) 필터링 및 지표 카드 3개
# =========================================================
if selected_sido != "전국":
    df_display = df_year_processed[
        df_year_processed["시도명"] == selected_sido
    ].copy()
    geojson_display = {
        "type": "FeatureCollection",
        "features": [
            f
            for f in geojson_data.get("features", [])
            if str(f.get("properties", {}).get("시도", "")).strip()
            == selected_sido
        ],
    }
    region_label = selected_sido
else:
    df_display = df_year_processed.copy()
    geojson_display = geojson_data
    region_label = "전국"

st.divider()

# 지표 카드 3개 계산 및 출력
if not df_display.empty and df_display["전체인구"].sum() > 0:
    total_pop_sum = df_display["전체인구"].sum()
    target_pop_sum = df_display[target_pop_col].sum()
    overall_rate = target_pop_sum / total_pop_sum * 100

    max_row = df_display.loc[df_display[val_col].idxmax()]
    min_row = df_display.loc[df_display[val_col].idxmin()]

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    with metric_col1:
        st.metric(
            label=f"👥 {region_label} 평균 {metric_title} ({selected_year}년)",
            value=f"{overall_rate:.2f}%",
            delta=f"대상 인구: {int(target_pop_sum):,}명",
        )

    with metric_col2:
        st.metric(
            label=f"📈 가장 높은 시군구 ({metric_title})",
            value=f"{max_row['시군구명']}",
            delta=f"{max_row[val_col]:.1f}%",
        )

    with metric_col3:
        st.metric(
            label=f"📉 가장 낮은 시군구 ({metric_title})",
            value=f"{min_row['시군구명']}",
            delta=f"{min_row[val_col]:.1f}%",
        )


# =========================================================
# 8. Plotly 단계구분도 시각화
# =========================================================
fig = px.choropleth(
    df_display,
    geojson=geojson_display,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="구간",
    color_discrete_map=color_map,
    category_orders={"구간": bin_labels},
    hover_name="시군구명",
    hover_data={
        "시군구코드": False,
        "구간": True,
        val_col: ":.2f%",
        "전체인구": ":,명",
        target_pop_col: ":,명",
    },
    labels={
        val_col: metric_title,
        "구간": "구간",
        "전체인구": "전체 인구",
        target_pop_col: target_label,
    },
)

# 배경 타일 제거 및 자동 영역 지정
fig.update_geos(
    fitbounds="locations",
    visible=False,
)

fig.update_layout(
    height=720,
    margin={"r": 0, "t": 20, "l": 0, "b": 0},
    legend_title_text=f"{metric_title} 구간",
    legend={"yanchor": "top", "y": 0.98, "xanchor": "left", "x": 0.01},
)

st.plotly_chart(fig, use_container_width=True)


# =========================================================
# 9. 행정구역 미매칭 안내 (회색 표시 지역)
# =========================================================
geo_codes = set(
    str(f.get("properties", {}).get("코드", "")).strip()
    for f in geojson_display.get("features", [])
)
data_codes = set(df_display["시군구코드"])
unmapped_codes = geo_codes - data_codes

if unmapped_codes:
    unmapped_names = [
        geojson_info.get(c, {}).get("전체명", f"코드 {c}")
        for c in sorted(unmapped_codes)
    ]
    st.caption(
        f"ℹ️ **행정구역 미매칭 안내 (회색 표시 지역):** "
        f"{selected_year}년 데이터 수집 기준 또는 코드 차이로 인해 인구 데이터가 매칭되지 않아 회색으로 표시된 지역이 {len(unmapped_codes)}곳 있습니다: "
        f"**{', '.join(unmapped_names)}**"
    )
