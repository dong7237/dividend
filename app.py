import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any

# --- Constants ---
YEAR = "연차"
PRINCIPAL_USD = "총 투자 원금(USD)"
ASSET_USD = "최종 평가 금액(USD)"
CAPITAL_GAINS_USD = "자본 이득(USD)"
ANNUAL_DIVIDEND_USD = "연간 배당금(USD)"
CUMULATIVE_DIVIDEND_USD = "총 누적 배당금(USD)"
PRINCIPAL_KRW = "총 투자 원금(원)"
ASSET_KRW = "최종 평가 금액(원)"
CAPITAL_GAINS_KRW = "자본 이득(원)"
CUMULATIVE_DIVIDEND_KRW = "총 누적 배당금(원)"
SAVINGS_ASSET_KRW = "예/적금 평가 금액(원)"
ASSET_PV_KRW = "최종 평가 금액(현재 가치)"


# --- Utility Functions ---
def format_krw(amount: float) -> str:
    """숫자를 '조', '억', '만' 단위의 원화 문자열로 변환합니다."""
    if abs(amount) >= 1_0000_0000_0000:
        return f"{amount / 1_0000_0000_0000:.2f}조 원"
    if abs(amount) >= 1_0000_0000:
        return f"{amount / 1_0000_0000:.2f}억 원"
    if abs(amount) >= 1_0000:
        return f"{amount / 1_0000:.0f}만 원"
    return f"{amount:,.0f}원"


# --- Simulation Functions ---
def run_investment_simulation(inputs: Dict[str, Any]) -> pd.DataFrame:
    """적립식 투자 시뮬레이션을 실행합니다."""
    monthly_investment_usd = inputs['monthly_investment_krw'] / inputs['exchange_rate']
    total_months = inputs['investment_years'] * 12
    monthly_growth_rate = (1 + inputs['annual_price_growth_rate'] / 100) ** (1/12) - 1
    monthly_dividend_yield = (1 + inputs['annual_dividend_yield'] / 100) ** (1/12) - 1

    asset_usd, principal_usd, gains_usd, dividends_usd = 0.0, 0.0, 0.0, 0.0
    results = []
    year_dividends = 0.0

    if total_months == 0:
        return pd.DataFrame()

    for month in range(1, total_months + 1):
        monthly_gain = asset_usd * monthly_growth_rate
        gains_usd += monthly_gain
        asset_after_growth = asset_usd + monthly_gain

        monthly_dividend = asset_after_growth * monthly_dividend_yield
        dividend_after_tax = monthly_dividend * (1 - inputs['dividend_tax_rate'] / 100)
        dividends_usd += dividend_after_tax
        year_dividends += dividend_after_tax

        asset_usd = asset_after_growth + monthly_investment_usd
        if inputs['reinvest_dividends']:
            asset_usd += dividend_after_tax
        principal_usd += monthly_investment_usd

        if month % 12 == 0:
            expense = asset_usd * (inputs['annual_expense_ratio'] / 100)
            asset_usd -= expense
            gains_usd -= expense

            results.append({
                YEAR: month // 12,
                PRINCIPAL_USD: principal_usd,
                ASSET_USD: asset_usd,
                CAPITAL_GAINS_USD: gains_usd,
                CUMULATIVE_DIVIDEND_USD: dividends_usd,
            })
            year_dividends = 0.0

    return pd.DataFrame(results)

def run_savings_simulation(inputs: Dict[str, Any]) -> pd.DataFrame:
    """예/적금(무위험) 시뮬레이션을 실행합니다."""
    monthly_investment = inputs['monthly_investment_krw']
    total_months = inputs['investment_years'] * 12
    monthly_rate = (1 + inputs['savings_interest_rate'] / 100) ** (1/12) - 1
    tax_rate = inputs['savings_tax_rate'] / 100

    principal, asset = 0.0, 0.0
    results = []

    if total_months == 0:
        return pd.DataFrame()

    for month in range(1, total_months + 1):
        interest = asset * monthly_rate
        asset += interest
        asset += monthly_investment
        principal += monthly_investment

        if month % 12 == 0:
            year_interest = asset - principal - sum(res[SAVINGS_ASSET_KRW] - res[PRINCIPAL_KRW] for res in results)
            taxable_interest = max(0, year_interest - (asset - principal) * (1-tax_rate)) # 이전 이자 제외
            asset -= taxable_interest * tax_rate

            results.append({
                YEAR: month // 12,
                PRINCIPAL_KRW: principal,
                SAVINGS_ASSET_KRW: asset,
            })

    return pd.DataFrame(results)


# --- UI Display Functions ---
def display_summary(final_data: pd.Series, inputs: Dict[str, Any]):
    """최종 결과 요약 정보를 비교하여 표시합니다."""
    st.subheader("📊 최종 결과 요약")

    inv_principal = final_data[PRINCIPAL_KRW]
    inv_asset = final_data[ASSET_KRW]
    sav_asset = final_data[SAVINGS_ASSET_KRW]

    col1, col2, col3 = st.columns(3)
    col1.metric("단순 저축 (미투자)", format_krw(inv_principal), "원금")
    col2.metric("예/적금 투자", format_krw(sav_asset), f"수익: {format_krw(sav_asset - inv_principal)}")
    col3.metric("적립식 투자", format_krw(inv_asset), f"수익: {format_krw(inv_asset - inv_principal)}")

    st.info(
        f"**{inputs['investment_years']}년** 후, 총 투자 원금 **{format_krw(inv_principal)}**은(는) "
        f"적립식 투자를 통해 **{format_krw(inv_asset)}**(으)로, "
        f"예/적금 투자를 통해 **{format_krw(sav_asset)}**(으)로 증가할 것으로 예상됩니다."
    )


def display_charts_and_data(df: pd.DataFrame, inputs: Dict[str, Any]):
    """상세 데이터 테이블과 시각화 차트를 표시합니다."""
    # 데이터 가공
    exchange_rate = inputs['exchange_rate']
    inflation_rate = inputs['annual_inflation_rate']

    df_display = df.copy()
    for col in [PRINCIPAL_USD, ASSET_USD, CAPITAL_GAINS_USD, CUMULATIVE_DIVIDEND_USD]:
        krw_col_name = col.replace("USD", "KRW")
        if krw_col_name.endswith("(원)"): # 기존 KRW 컬럼 이름 형식 유지
             krw_col_name = krw_col_name.replace("(원)", " KRW")
        df_display[krw_col_name] = df_display[col] * exchange_rate


    inflation_divisor = (1 + inflation_rate / 100) ** df_display[YEAR]
    df_display[ASSET_PV_KRW] = df_display[ASSET_KRW] / inflation_divisor

    # 테이블 표시
    st.subheader("📋 연차별 상세 결과")
    display_cols = {
        YEAR: "연차",
        PRINCIPAL_KRW: "총투자원금",
        ASSET_KRW: "투종평가금액",
        SAVINGS_ASSET_KRW: "예적금평가액",
        ASSET_PV_KRW: "투자현재가치",
    }
    df_table = df_display[list(display_cols.keys())].rename(columns=display_cols)
    st.dataframe(
        df_table.style.format(formatter={
            "총투자원금": "{:,.0f}원", "투종평가금액": "{:,.0f}원",
            "예적금평가액": "{:,.0f}원", "투자현재가치": "{:,.0f}원",
        }),
        hide_index=True, use_container_width=True
    )

    # 차트 표시
    st.subheader("💹 자산 성장 비교 시각화")
    chart_df = df_display.set_index(YEAR)[[PRINCIPAL_KRW, SAVINGS_ASSET_KRW, ASSET_KRW]]
    chart_df.columns = ["단순 저축 (원금)", "예/적금", "적립식 투자"]
    st.line_chart(chart_df)

    st.session_state['final_data'] = df_display.iloc[-1]


# --- Streamlit App Main ---
st.set_page_config(layout="wide")
st.title('📈 적립식 투자 vs 예/적금 비교 시뮬레이터')

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("⚙️ 공통 조건 설정")
    monthly_investment_krw = st.slider('월 투자 원금 (만원)', 10, 500, 50, 5) * 10000
    investment_years = st.slider('투자 기간 (년)', 1, 40, 20, 1)
    exchange_rate = st.number_input('원/달러 환율 (원)', 1000, 2000, 1380)
    annual_inflation_rate = st.slider('연평균 물가 상승률 (%)', 0.0, 10.0, 2.5, 0.1)

    with st.expander("📈 적립식 투자 조건"):
        rate_model = st.radio('수익률 모델', ('SCHD', 'JEPI', '직접 입력'), index=0, horizontal=True)
        if rate_model == 'SCHD':
            annual_dividend_yield, annual_price_growth_rate = 3.5, 7.0
        elif rate_model == 'JEPI':
            annual_dividend_yield, annual_price_growth_rate = 7.5, 4.0
        else:
            annual_dividend_yield = st.number_input('연평균 배당수익률 (%)', 0.0, 20.0, 3.5, 0.1)
            annual_price_growth_rate = st.number_input('연평균 주가 성장률 (%)', -10.0, 30.0, 7.0, 0.1)
        dividend_tax_rate = st.slider('배당소득세율 (%)', 0.0, 50.0, 15.4, 0.1)
        annual_expense_ratio = st.slider('연간 운용보수 (%)', 0.0, 5.0, 0.06, 0.01)
        reinvest_dividends = st.toggle('배당 수익 자동 재투자', value=True)

    with st.expander("💰 예/적금 투자 조건"):
        savings_interest_rate = st.slider('연평균 예/적금 금리 (%)', 0.0, 10.0, 3.5, 0.1)
        savings_tax_rate = st.slider('이자소득세율 (%)', 0.0, 50.0, 15.4, 0.1)


    run_button = st.button('🚀 시뮬레이션 실행', use_container_width=True)

# --- Main Panel Logic ---
if run_button:
    inputs = locals()
    inv_df = run_investment_simulation(inputs)

    if not inv_df.empty:
        sav_df = run_savings_simulation(inputs)
        # 투자 & 예적금 데이터 병합
        results_df = pd.merge(inv_df, sav_df, on=[YEAR, PRINCIPAL_KRW], how="left")
        st.session_state['results_df'] = results_df
        st.session_state['inputs'] = inputs
        st.session_state['simulation_run'] = True
    else:
        st.warning("투자 기간을 1년 이상으로 설정해주세요.")
        st.session_state['simulation_run'] = False

if st.session_state.get('simulation_run', False):
    results_df = st.session_state['results_df']
    inputs = st.session_state['inputs']
    display_charts_and_data(results_df, inputs)
    display_summary(st.session_state['final_data'], inputs)
else:
    st.info("좌측 사이드바에서 투자 조건을 설정하고 '시뮬레이션 실행' 버튼을 눌러주세요.")
