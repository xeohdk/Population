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
    page_title="전국 시군구 고령화 단계구분도 (2026년)",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ 전국 시군구 고령화 단계구분도 (2026년)")
st.markdown(
    "2026년 6월 기준 전국 읍·면·동 인구 데이터를 바탕으로 시군구별 고령화율(65세 이상 인구 비율)을 시각화합니다."
)

# 데이터 URL (GitHub Raw 링크)
DATA_URL = "https://raw.githubusercontent.com/xeohdk/Population/main/population_ts_yearly_gender.zip"
GEOJSON_URL = "https://raw.githubusercontent.com/xeohdk/Population/main/sigungu_kr.geojson.txt"


# =========================================================
# 2. 데이터 불러오기 및 가공
# =========================================================
@st.cache_data
def load_data():
    # 1) GeoJSON 경계 데이터 내려받기
    geo_res = requests.get(GEOJSON_URL)
    geojson_data = geo_res.json()

    # GeoJSON 내 시군구 코드 및 이름 매핑 생성
    sigungu_info = {}
    for feature in geojson_data.get("features", []):
        props = feature.get("properties", {})
        code = str(props.get("코드", "")).strip()
        sido = props.get("시도", "").strip()
        sigungu = props.get("시군구", "").strip()
        full_name = f"{sido} {sigungu}".strip()
        sigungu_info[code] = full_name

    # 2) 인구 데이터 CSV 읽기 (ZIP 내 CSV 자동 인식)
    df = pd.read_csv(DATA_URL, compression="zip")
    df.columns = df.columns.astype(str).str.strip()

    # 2026년 데이터만 필터링
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df_2026 = df[df["연도"] == 2026].copy()

    if df_2026.empty:
        # 2026년이 없을 경우 최신 연도로 대체 처리
        latest_year = df["연도"].max()
        df_2026 = df[df["연도"] == latest_year].copy()

    # 3) '계_' 열 구분 (전체 인구열 및 65세 이상 인구열)
    total_cols = [col for col in df_2026.columns if col.startswith("계_")]

    elderly_cols = []
    for col in total_cols:
        # 숫자 추출 (예: '계_65세' -> 65, '계_100세 이상' -> 100)
        numbers = re.findall(r"\d+", col)
        if numbers and int(numbers[0]) >= 65:
            elderly_cols.append(col)

    # 숫자로 변환 및 결측치 0 처리
    for col in total_cols:
        df_2026[col] = pd.to_numeric(df_2026[col], errors="coerce").fillna(0)

    # 4) 동 코드를 5자리 시군구 코드로 변환
    df_2026["시군구코드"] = (
        df_2026["코드"].astype(str).str.split(".").str[0].str.zfill(8).str[:5]
    )

    # 5) 시군구 단위 합산
    df_2026["전체인구"] = df_2026[total_cols].sum(axis=1)
    df_2026["고령인구"] = df_2026[elderly_cols].sum(axis=1)

    grouped = (
        df_2026.groupby("시군구코드")[["전체인구", "고령인구"]]
        .sum()
        .reset_index()
    )

    # 고령화율 (%) 계산
    grouped["고령화율"] = (
        grouped["고령인구"] / grouped["전체인구"] * 100
    ).round(2)

    # GeoJSON 정보 기반 시군구 이름 연결
    grouped["시군구명"] = grouped["시군구코드"].map(
        lambda x: sigungu_info.get(x, f"알 수 없음 ({x})")
    )

    return geojson_data, grouped


# 데이터 로드
try:
    with st.spinner("데이터 및 경계 지도를 불러오는 중입니다..."):
        geojson_data, df_sigungu = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# =========================================================
# 3. Plotly 단계구분도 (Choropleth) 시각화
# =========================================================
fig = px.choropleth(
    df_sigungu,
    geojson=geojson_data,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="고령화율",
    color_continuous_scale="Reds",
    hover_name="시군구명",
    hover_data={
        "시군구코드": False,
        "고령화율": ":.1f%",
        "전체인구": ":,명",
        "고령인구": ":,명",
    },
    labels={
        "고령화율": "고령화율(%)",
        "전체인구": "전체 인구",
        "고령인구": "65세 이상 인구",
    },
)

# 배경 타일 없이 경계만 표시
fig.update_geos(
    fitbounds="locations",
    visible=False,
)

fig.update_layout(
    height=750,
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    coloraxis_colorbar={
        "title": "고령화율 (%)",
        "ticksuffix": "%",
    },
)

# 지도 출력
st.plotly_chart(fig, use_container_width=True)

# 데이터 요약 정보
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("전국 평균 고령화율", f"{df_sigungu['고령인구'].sum() / df_sigungu['전체인구'].sum() * 100:.2f}%")
with col2:
    max_row = df_sigungu.loc[df_sigungu["고령화율"].idxmax()]
    st.metric("최고 고령화 지역", f"{max_row['시군구명']}", f"{max_row['고령화율']:.1f}%")
with col3:
    min_row = df_sigungu.loc[df_sigungu["고령화율"].idxmin()]
    st.metric("최저 고령화 지역", f"{min_row['시군구명']}", f"{min_row['고령화율']:.1f}%")
