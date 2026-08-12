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
st.title("📊 자산 목표 관리")
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
    chart_row1_col1, chart_row1_col2 = st.columns(2)

    with chart_row1_col1:
        st.subheader("📌 종목별 목표 점유비 (%)")
        if "종목명" in calc_df.columns and "점유비" in calc_df.columns:
            fig_pie1 = px.pie(calc_df, names="종목명", values="점유비", hole=0.4, title="목표 자산 비중")
            st.plotly_chart(fig_pie1, use_container_width=True)

    with chart_row1_col2:
        st.subheader("📌 종목별 현재 점유비 (%)")
        if "종목명" in calc_df.columns and "현재 투자금액" in calc_df.columns:
            fig_pie2 = px.pie(calc_df, names="종목명", values="현재 투자금액", hole=0.4, title="현재 자산 비중")
            st.plotly_chart(fig_pie2, use_container_width=True)

    chart_row2_col1, chart_row2_col2 = st.columns(2)

    with chart_row2_col1:
        st.subheader("🎯 종목별 목표 달성율 (%)")
        if "종목명" in calc_df.columns and "달성율" in calc_df.columns:
            fig_bar = px.bar(calc_df, x="종목명", y="달성율", text_auto=".2f", color="달성율", title="수량 기준 목표 달성 현황")
            fig_bar.update_layout(height=450)
            st.plotly_chart(fig_bar, use_container_width=True)

    with chart_row2_col2:
        st.subheader("📊 52주 변동폭 대비 현재가 위치")
        if "52주 최고가" in calc_df.columns and "52주 최저가" in calc_df.columns and "주당가격" in calc_df.columns:
            bullet_df = calc_df[(calc_df["52주 최고가"] > 0) & (calc_df["52주 최저가"] > 0)]
            
            if not bullet_df.empty:
                fig_bullet = go.Figure()
                N = len(bullet_df)
                
                # [오류 해결된 반복문 반영]
                for i, row in bullet_df.reset_index().iterrows():
                    gap_bottom = 0.3 / N  
                    gap_top = 0.05 / N    
                    
                    y_start = 1 - (i + 1) / N + gap_bottom
                    y_end = 1 - i / N - gap_top
                    
                    label_text = row["종목명"]
                    
                    tick_vals = [row["52주 최저가"], row["주당가격"], row["52주 최고가"]]
                    tick_texts = [f"{row['52주 최저가']:,.0f}(최저)", f"{row['주당가격']:,.0f}(현재)", f"{row['52주 최고가']:,.0f}(고점)"]
                    
                    fig_bullet.add_trace(go.Indicator(
                        mode = "number+gauge",
                        value = row["주당가격"],
                        number = {'valueformat': ',.0f', 'font': {'size': 18}},
                        title = {'text': f"<span style='font-size:13px'>{label_text}</span>"},
                        domain = {'x': [0.25, 1], 'y': [y_start, y_end]},
                        gauge = {
                            'shape': "bullet",
                            'axis': {
                                'range': [row["52주 최저가"] * 0.9, row["52주 최고가"] * 1.1],
                                'tickvals': tick_vals,
                                'ticktext': tick_texts,
                                'tickfont': {'size': 10, 'color': '#333'}
                            },
                            'threshold': {
                                'line': {'color': "red", 'width': 3},
                                'thickness': 0.75,
                                'value': row["52주 최고가"]
                            },
                            'steps': [
                                {'range': [0, row["52주 최저가"]], 'color': "#e6e6e6"},
                                {'range': [row["52주 최저가"], row["52주 최고가"]], 'color': "#b3b3b3"}
                            ],
                            'bar': {'color': "#1f77b4"}
                        }
                    ))
                
                fig_bullet.update_layout(
                    height=max(450, N * 80), 
                    margin=dict(l=120, r=80, t=60, b=40), 
                    title="검은색 막대: 현재가 / 빨간선: 52주 최고가 / 회색 영역: 52주 최저~최고 구간"
                )
                st.plotly_chart(fig_bullet, use_container_width=True)
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