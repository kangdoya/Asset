import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go 

# 1. Streamlit 페이지 설정 (반드시 최상단 위치)
st.set_page_config(
    page_title="Asset Management Goal Dashboard",
    page_icon="📊",
    layout="wide"
)

# 2. 앱 타이틀 및 설명
st.title("📊 자산 관리 & 목표 달성 대시보드 (Goal)")
st.caption("구글 드라이브의 Asset Management 데이터와 실시간으로 연동된 대시보드입니다.")

# =====================================================================
# 3. 구글 시트 데이터 불러오기 (실시간 연동)
# [중요] 아래 " " 안에 구글 시트 CSV 링크를 붙여넣으세요! (큰따옴표 유지)
# =====================================================================
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQU6y2YfBERtFZG0ZzIzFbUpFls96ieDaa_K1dBdPtvg6LQaH3AgiS4LLeP34V5J_OPa7v8fUy1NoDm/pub?gid=200962951&single=true&output=csv"

try:
    # 웹에서 최신 CSV 데이터를 읽어옵니다.
    df = pd.read_csv(sheet_url)
    
    # =====================================================================
    # [정제 1] 글자 'None'이 그대로 출력되는 현상 원천 차단
    # =====================================================================
    for text_col in ["Ticker", "종목명", "비고"]:
        if text_col in df.columns:
            df[text_col] = df[text_col].fillna("")
            df.loc[df[text_col].astype(str).str.strip().str.lower().isin(["none", "nan", "null", ""]), text_col] = ""
    
    # 데이터 내부 계산을 위해 비어있는 맨 마지막 행을 '합계'로 임시 지정
    if "종목명" in df.columns:
        df.loc[df["종목명"] == "", "종목명"] = "합계"

    # =====================================================================
    # 4. 데이터 숫자형 변환 함수
    # =====================================================================
    def clean_numeric(val):
        if pd.isna(val):
            return 0.0
        if isinstance(val, str):
            val = val.replace('%', '').replace(',', '').replace('원', '').replace('주', '').strip()
        try:
            return float(val) if val else 0.0
        except ValueError:
            return 0.0

    numeric_cols = ["점유비", "투자금액", "주당가격", "목표주식수", "보유주식수", "달성율", "목표 세전배당", "목표 세후배당", "52주 최고가", "52주 최저가"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = [clean_numeric(x) for x in df[col]]

    # =====================================================================
    # 5. 상단 KPI 요약 카드
    # =====================================================================
    calc_df = df[df["종목명"] != "합계"].copy()
    total_row = df[df["종목명"] == "합계"] 

    if "주당가격" in calc_df.columns and "보유주식수" in calc_df.columns:
        calc_df["현재 투자금액"] = calc_df["주당가격"] * calc_df["보유주식수"]
    else:
        calc_df["현재 투자금액"] = 0

    if not total_row.empty and "투자금액" in total_row.columns and total_row["투자금액"].values[0] > 0:
        total_investment = total_row["투자금액"].values[0]
    else:
        total_investment = calc_df["투자금액"].sum() if "투자금액" in calc_df.columns else 0

    current_investment = calc_df["현재 투자금액"].sum()

    if not total_row.empty and "목표 세후배당" in total_row.columns and total_row["목표 세후배당"].values[0] > 0:
        total_target_dividend = total_row["목표 세후배당"].values[0]
    else:
        total_target_dividend = calc_df["목표 세후배당"].sum() if "목표 세후배당" in calc_df.columns else 0

    if not total_row.empty and "달성율" in total_row.columns and total_row["달성율"].values[0] > 0:
        avg_achievement = total_row["달성율"].values[0]
    else:
        avg_achievement = calc_df["달성율"].mean() if "달성율" in calc_df.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 목표 투자금액", f"{total_investment:,.0f} 원")
    col2.metric("현재 투자금액", f"{current_investment:,.0f} 원")
    col3.metric("총 목표 세후배당금", f"{total_target_dividend:,.0f} 원")
    col4.metric("평균 목표 달성률", f"{avg_achievement:.2f} %")

    st.markdown("---")

    # =====================================================================
    # 6. 시각화 차트 (2x2 그리드 배치)
    # =====================================================================
    
    # [데이터 가공] 목표 점유비와 현재 점유비(%) 계산 및 병합
    melted_df = pd.DataFrame()
    if "종목명" in calc_df.columns and "점유비" in calc_df.columns:
        chart_df = calc_df[calc_df["종목명"] != "합계"].copy()
        
        total_curr_inv = chart_df["현재 투자금액"].sum() if "현재 투자금액" in chart_df.columns else 1
        if total_curr_inv == 0: total_curr_inv = 1
        
        chart_df["현재 점유비"] = (chart_df["현재 투자금액"] / total_curr_inv) * 100
        
        melted_df = chart_df.melt(
            id_vars=["종목명"], 
            value_vars=["점유비", "현재 점유비"],
            var_name="구분", 
            value_name="비중(%)"
        )
        melted_df["구분"] = melted_df["구분"].replace({"점유비": "목표 점유비", "현재 점유비": "현재 점유비"})

    # [첫 번째 행] 좌측: 종목별 목표 달성율 (%) / 우측: 종목별 현재 자산 비중 (%)
    chart_row1_col1, chart_row1_col2 = st.columns(2)

    with chart_row1_col1:
        st.subheader("🎯 종목별 목표 달성율 (%)")
        if "종목명" in calc_df.columns and "달성율" in calc_df.columns:
            fig_bar = px.bar(calc_df, x="종목명", y="달성율", text_auto=".2f", color="달성율", title="수량 기준 목표 달성 현황")
            fig_bar.update_layout(height=450)
            st.plotly_chart(fig_bar, use_container_width=True)

    with chart_row1_col2:
        st.subheader("📌 종목별 현재 자산 비중 (%)")
        if "종목명" in calc_df.columns and "현재 투자금액" in calc_df.columns:
            fig_pie2 = px.pie(calc_df, names="종목명", values="현재 투자금액", hole=0.4, title="현재 자산 비중")
            fig_pie2.update_layout(height=450)
            st.plotly_chart(fig_pie2, use_container_width=True)

    # [두 번째 행] 좌측: 종목별 목표 vs 현재 점유비 비교 (Gap) / 우측: 가격 범위 바벨 차트
    chart_row2_col1, chart_row2_col2 = st.columns(2)

    with chart_row2_col1:
        st.subheader("📊 종목별 목표 vs 현재 점유비 비교 (Gap)")
        if not melted_df.empty:
            fig_gap = px.bar(
                melted_df, 
                x="종목명", 
                y="비중(%)", 
                color="구분", 
                barmode="group",
                text_auto=".1f",
                title="목표 점유비 vs 현재 점유비 비교"
            )
            fig_gap.update_layout(height=450, xaxis_tickangle=-15)
            st.plotly_chart(fig_gap, use_container_width=True)

    with chart_row2_col2:
        st.subheader("📊 52주 가격 범위 및 현재가 위치")
        if "52주 최고가" in calc_df.columns and "52주 최저가" in calc_df.columns and "주당가격" in calc_df.columns:
            range_df = calc_df[(calc_df["52주 최고가"] > 0) & (calc_df["52주 최저가"] > 0)].copy()
            
            if not range_df.empty:
                fig_range = go.Figure()
                
                # 각 종목별 52주 최저~최고 구간(수평선) 및 현재가(마커) 추가
                for _, row in range_df.iterrows():
                    name = row["종목명"]
                    low = row["52주 최저가"]
                    high = row["52주 최고가"]
                    current = row["주당가격"]
                    
                    # 1. 최저~최고 구간을 잇는 회색 수평 바 (Range Line)
                    fig_range.add_trace(go.Scatter(
                        x=[low, high],
                        y=[name, name],
                        mode="lines",
                        line=dict(color="#b3b3b3", width=8),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    
                    # 2. 52주 최저가 텍스트 마커
                    fig_range.add_trace(go.Scatter(
                        x=[low],
                        y=[name],
                        mode="text+markers",
                        marker=dict(color="#888888", size=10),
                        text=[f"{low:,.0f} (최저)"],
                        textposition="bottom center",
                        showlegend=False
                    ))

                    # 3. 현재가 파란색 포인트 마커
                    fig_range.add_trace(go.Scatter(
                        x=[current],
                        y=[name],
                        mode="text+markers",
                        marker=dict(color="#1f77b4", size=14),
                        text=[f"{current:,.0f} (현재)"],
                        textposition="top center",
                        textfont=dict(color="#1f77b4", size=12, family="sans-serif"),
                        showlegend=False
                    ))
                    
                    # 4. 52주 최고가 빨간색 포인트 마커
                    fig_range.add_trace(go.Scatter(
                        x=[high],
                        y=[name],
                        mode="text+markers",
                        marker=dict(color="red", size=12, symbol="line-ns-open"),
                        text=[f"{high:,.0f} (고점)"],
                        textposition="bottom center",
                        textfont=dict(color="red", size=11),
                        showlegend=False
                    ))

                fig_range.update_layout(
                    height=450,
                    margin=dict(l=20, r=20, t=50, b=40),
                    title="회색선: 52주 최저~고점 구간 / 파란점: 현재가 / 빨간선: 52주 최고가",
                    xaxis=dict(title="가격 (원)", zeroline=False),
                    yaxis=dict(title="", autorange="reversed") # 위에서 아래로 종목 정렬
                )
                st.plotly_chart(fig_range, use_container_width=True)
            else:
                st.info("💡 종목별 52주 최고가 및 최저가 데이터가 아직 유효하게 입력되지 않았습니다.")
        else:
            st.warning("⚠️ 구글 시트에 '52주 최고가', '52주 최저가' 열을 올바르게 추가했는지 확인해 주세요.")

    # =====================================================================
    # 7. 상세 데이터 테이블 
    # =====================================================================
    st.subheader("📋 Goal 시트 실시간 데이터 현황")

    display_df = df.copy()
    
    is_total_row = display_df["종목명"] == "합계"
    if is_total_row.any():
        if "점유비" in display_df.columns: display_df.loc[is_total_row, "점유비"] = calc_df["점유비"].sum()
        if "목표주식수" in display_df.columns: display_df.loc[is_total_row, "목표주식수"] = calc_df["목표주식수"].sum()
        if "보유주식수" in display_df.columns: display_df.loc[is_total_row, "보유주식수"] = calc_df["보유주식수"].sum()
        if "주당가격" in display_df.columns: display_df.loc[is_total_row, "주당가격"] = calc_df["주당가격"].mean()
        
        if "Ticker" in display_df.columns: display_df.loc[is_total_row, "Ticker"] = "합계"
        if "종목명" in display_df.columns: display_df.loc[is_total_row, "종목명"] = ""

    display_df = display_df.rename(columns={"주당가격": "현재가"})

    expected_columns = ["Ticker", "종목명", "점유비", "투자금액", "52주 최저가", "현재가", "52주 최고가", "목표주식수", "보유주식수", "달성율", "비고", "목표 세전배당", "목표 세후배당"]
    available_columns = [col for col in expected_columns if col in display_df.columns]
    
    format_dict = {}
    if "점유비" in available_columns: format_dict["점유비"] = "{:.2f}%"
    if "투자금액" in available_columns: format_dict["투자금액"] = "{:,.0f} 원"
    if "현재가" in available_columns: format_dict["현재가"] = "{:,.0f} 원"
    if "52주 최고가" in available_columns: format_dict["52주 최고가"] = "{:,.0f} 원"
    if "52주 최저가" in available_columns: format_dict["52주 최저가"] = "{:,.0f} 원"
    if "목표주식수" in available_columns: format_dict["목표주식수"] = "{:,.0f} 주"
    if "보유주식수" in available_columns: format_dict["보유주식수"] = "{:,.0f} 주"
    if "달성율" in available_columns: format_dict["달성율"] = "{:.2f}%"
    if "목표 세전배당" in available_columns: format_dict["목표 세전배당"] = "{:,.0f} 원"
    if "목표 세후배당" in available_columns: format_dict["목표 세후배당"] = "{:,.0f} 원"

    styled_df = display_df[available_columns].style.format(formatter=format_dict, na_rep="")

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("🚨 구글 시트 데이터를 불러오는 중 오류가 발생했습니다.")
    st.error(f"상세 오류: {e}")