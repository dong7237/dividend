import streamlit as st
import pandas as pd
from typing import Dict, Any

# --- Constants ---
# Using constants for dictionary keys/column names prevents typos
YEAR = "연차"
PRINCIPAL_USD = "총 투자 원금(USD)"
ASSET_USD = "최종 평가 금액(USD)"
CAPITAL_GAINS_USD = "자본 이득(USD)"
ANNUAL_DIVIDEND_USD = "연간 배당금(USD)"
CUMULATIVE_DIVIDEND_USD = "총 누적 배당금(USD)"
PRINCIPAL_KRW = "총 투자 원금(원)"
ASSET_KRW = "최종 평가 금액(원)"
PROFIT_KRW = "총 손익(원)"
CAPITAL_GAINS_KRW = "자본 이득(원)"
ANNUAL_DIVIDEND_KRW = "연간 배당금(원)"
CUMULATIVE_DIVIDEND_KRW = "총 누적 배당금(원)"
ASSET_PV_KRW = "최종 평가 금액(현재 가치)"
ANNUAL_DIVIDEND_PV_KRW = "연간 배당금(현재 가치)"


def run_simulation(
    monthly_investment_krw: int,
    investment_years: int,
    annual_price_growth_rate: float,
    annual_dividend_yield: float,
    reinvest_dividends: bool,
    exchange_rate: int,
    dividend_tax_rate: float,
    annual_expense_ratio: float
) -> pd.DataFrame:
    """
    적립식 투자 월 복리 시뮬레이션을 실행하고 결과를 DataFrame으로 반환합니다.

    Args:
        monthly_investment_krw (int): 월 투자 원금 (원)
        investment_years (int): 투자 기간 (년)
        annual_price_growth_rate (float): 연평균 주가 성장률 (%)
        annual_dividend_yield (float): 연평균 배당 수익률 (%)
        reinvest_dividends (bool): 배당 수익 재투자 여부
        exchange_rate (int): 원/달러 환율
        dividend_tax_rate (float): 배당소득세율 (%)
        annual_expense_ratio (float): 연간 운용보수 (%)

    Returns:
        pd.DataFrame: 연도별 시뮬레이션 결과가 담긴 데이터프레임
    """
    # 초기 변수 설정
    monthly_investment_usd = monthly_investment_krw / exchange_rate
    total_months = investment_years * 12
    monthly_price_growth_rate = (1 + annual_price_growth_rate / 100) ** (1/12) - 1
    monthly_dividend_yield = (1 + annual_dividend_yield / 100) ** (1/12) - 1

    # 누적 변수 초기화
    total_asset_usd = 0.0
    total_principal_usd = 0.0
    total_dividends_usd = 0.0
    total_capital_gains_usd = 0.0

    results_data = []
    current_year_dividends_usd = 0.0

    if total_months == 0:
        return pd.DataFrame()

    # 월 단위 반복 계산
    for month in range(1, total_months + 1):
        # 1. 주가 성장 적용 (Capital Gain 발생)
        monthly_capital_gain = total_asset_usd * monthly_price_growth_rate
        total_capital_gains_usd += monthly_capital_gain
        asset_after_growth = total_asset_usd + monthly_capital_gain

        # 2. 배당금 발생 및 세금 처리
        monthly_dividend = asset_after_growth * monthly_dividend_yield
        monthly_dividend_after_tax = monthly_dividend * (1 - dividend_tax_rate / 100)
        total_dividends_usd += monthly_dividend_after_tax
        current_year_dividends_usd += monthly_dividend_after_tax

        # 3. 자산 및 원금 업데이트
        total_asset_usd = asset_after_growth + monthly_investment_usd
        if reinvest_dividends:
            total_asset_usd += monthly_dividend_after_tax
        total_principal_usd += monthly_investment_usd

        # 4. 연말 데이터 저장
        if month % 12 == 0:
            # 연간 운용보수 적용 (자본 이득에서 차감)
            expense_amount = total_asset_usd * (annual_expense_ratio / 100)
            total_asset_usd -= expense_amount
            total_capital_gains_usd -= expense_amount

            results_data.append({
                YEAR: month // 12,
                PRINCIPAL_USD: total_principal_usd,
                ASSET_USD: total_asset_usd,
                CAPITAL_GAINS_USD: total_capital_gains_usd,
                ANNUAL_DIVIDEND_USD: current_year_dividends_usd,
                CUMULATIVE_DIVIDEND_USD: total_dividends_usd,
            })
            current_year_dividends_usd = 0.0  # 연간 배당금 초기화

    return pd.DataFrame(results_data)

def display_summary(final_year_data: pd.Series, investment_years: int):
    """최종 결과 요약 정보를 표시합니다."""
    st.subheader("📊 최종 결과 요약")

    total_principal_krw = final_year_data[PRINCIPAL_KRW]
    final_asset_krw = final_year_data[ASSET_KRW]
    total_profit_krw = final_asset_krw - total_principal_krw
    last_year_dividend_krw = final_year_data[ANNUAL_DIVIDEND_KRW]
    last_month_dividend_krw = last_year_dividend_krw / 12

    summary_text = (
        f"**{investment_years}년** 후, 총 투자 원금 **{total_principal_krw:,.0f}원**은 "
        f"최종 평가 금액 **{final_asset_krw:,.0f}원**(총수익: **{total_profit_krw:,.0f}원**)이 됩니다."
    )
    dividend_text = (
        f"마지막 해의 연간 예상 배당금은 **{last_year_dividend_krw:,.0f}원** 입니다. "
        f"(월 **{last_month_dividend_krw:,.0f}원**)"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="총 투자 원금", value=f"{total_principal_krw:,.0f} 원")
    with col2:
        st.metric(label="최종 평가 금액", value=f"{final_asset_krw:,.0f} 원", delta=f"{total_profit_krw:,.0f} 원")

    st.markdown(summary_text)
    st.markdown(dividend_text)


def display_data_and_charts(df_usd: pd.DataFrame, inputs: Dict[str, Any]):
    """상세 데이터 테이블과 시각화 차트를 표시합니다."""
    if df_usd.empty:
        st.warning("계산 결과가 없습니다. 투자 기간이 1년 이상인지 확인해주세요.")
        return

    exchange_rate = inputs['exchange_rate']
    annual_inflation_rate = inputs['annual_inflation_rate']

    # KRW 및 현재 가치 계산 (벡터화 연산)
    df_display = df_usd.copy()
    usd_cols = [PRINCIPAL_USD, ASSET_USD, CAPITAL_GAINS_USD, ANNUAL_DIVIDEND_USD, CUMULATIVE_DIVIDEND_USD]
    krw_cols = [PRINCIPAL_KRW, ASSET_KRW, CAPITAL_GAINS_KRW, ANNUAL_DIVIDEND_KRW, CUMULATIVE_DIVIDEND_KRW]

    for usd_col, krw_col in zip(usd_cols, krw_cols):
        df_display[krw_col] = df_display[usd_col] * exchange_rate

    # 현재 가치 계산
    inflation_divisor = (1 + annual_inflation_rate / 100) ** df_display[YEAR]
    df_display[ASSET_PV_KRW] = df_display[ASSET_KRW] / inflation_divisor
    df_display[ANNUAL_DIVIDEND_PV_KRW] = df_display[ANNUAL_DIVIDEND_KRW] / inflation_divisor

    # B. 연차별 상세 결과표
    st.subheader("📋 연차별 상세 결과")
    display_cols = {
        YEAR: "연차",
        PRINCIPAL_KRW: "총 투자 원금",
        ASSET_KRW: "최종 평가 금액",
        ASSET_PV_KRW: "최종 평가 금액(현재 가치)",
        ANNUAL_DIVIDEND_KRW: "연간 배당금",
        ANNUAL_DIVIDEND_PV_KRW: "연간 배당금(현재 가치)",
    }
    formatters = {key: "{:,.0f}원" for key in display_cols if key != YEAR}
    st.dataframe(
        df_display[list(display_cols.keys())].rename(columns=display_cols).style.format(formatters),
        hide_index=True,
        use_container_width=True
    )

    # C. 자산 성장 시각화
    st.subheader("💹 자산 성장 시각화")
    chart_df_growth = df_display.set_index(YEAR)[[PRINCIPAL_KRW, ASSET_KRW, ASSET_PV_KRW]]
    chart_df_growth.columns = ["총 투자 원금", "최종 평가 금액", "최종 평가 금액(현재 가치)"]
    st.line_chart(chart_df_growth)

    # D. 자산 구성 시각화
    st.subheader("📈 자산 구성 시각화")
    composition_df = df_display.set_index(YEAR)[[PRINCIPAL_KRW, CAPITAL_GAINS_KRW, CUMULATIVE_DIVIDEND_KRW]]
    composition_df.columns = ["총 투자 원금", "자본 이득", "총 누적 배당금"]
    st.bar_chart(composition_df)

    st.session_state['final_year_data'] = df_display.iloc[-1]


# --- 사이드바 UI 구성 ---
st.sidebar.header("⚙️ 투자 조건 설정")

# 경제/세금 설정
with st.sidebar.expander("경제 및 세금 설정", expanded=True):
    exchange_rate = st.sidebar.number_input('원/달러 환율 (원)', min_value=100, value=1380, step=10)
    annual_inflation_rate = st.sidebar.number_input('연평균 물가 상승률 (%)', min_value=0.0, max_value=20.0, value=2.5, step=0.1)
    dividend_tax_rate = st.sidebar.number_input('배당소득세율 (%)', min_value=0.0, max_value=100.0, value=15.0, step=0.1)
    annual_expense_ratio = st.sidebar.number_input('연간 운용보수 (%)', min_value=0.0, max_value=5.0, value=0.06, step=0.01, help="ETF 운용사에 매년 지불하는 수수료입니다.")

# 투자 계획 설정
with st.sidebar.expander("투자 계획 설정", expanded=True):
    monthly_investment_krw_만원 = st.sidebar.slider('월 투자 원금 (만원)', min_value=10, max_value=500, step=5, value=45)
    monthly_investment_krw = monthly_investment_krw_만원 * 10000
    investment_years = st.sidebar.slider('투자 기간 (년)', min_value=1, max_value=40, step=1, value=15)
    reinvest_dividends = st.sidebar.toggle('배당 수익 자동 재투자', value=True)

# 수익률 모델 설정
with st.sidebar.expander("수익률 모델 설정", expanded=True):
    rate_model = st.radio('수익률 모델 선택', ('SCHD', 'JEPI', '직접 입력'), horizontal=True, index=0)

    if rate_model == 'SCHD':
        annual_dividend_yield, annual_price_growth_rate = 3.5, 7.0
        st.info(f"SCHD 모델: 배당 {annual_dividend_yield}%, 성장 {annual_price_growth_rate}%")
    elif rate_model == 'JEPI':
        annual_dividend_yield, annual_price_growth_rate = 7.5, 4.0
        st.info(f"JEPI 모델: 배당 {annual_dividend_yield}%, 성장 {annual_price_growth_rate}%")
    else:
        annual_dividend_yield = st.number_input('연평균 배당수익률 (%)', min_value=0.0, step=0.1, value=3.5)
        annual_price_growth_rate = st.number_input('연평균 주가 성장률 (%)', min_value=0.0, step=0.1, value=7.0)

run_button = st.sidebar.button('🚀 시뮬레이션 실행', use_container_width=True)


# --- 메인 화면 구성 ---
st.title('📈 적립식 투자 월 복리 시뮬레이터')

# 시뮬레이션 실행 버튼 로직
if run_button:
    results_df = run_simulation(
        monthly_investment_krw, investment_years,
        annual_price_growth_rate, annual_dividend_yield,
        reinvest_dividends, exchange_rate,
        dividend_tax_rate, annual_expense_ratio
    )
    if not results_df.empty:
        st.session_state['simulation_run'] = True
        st.session_state['results_df'] = results_df
        st.session_state['inputs'] = {
            "investment_years": investment_years,
            "exchange_rate": exchange_rate,
            "annual_inflation_rate": annual_inflation_rate
        }
    else:
        st.session_state['simulation_run'] = False
        st.warning("투자 기간이 1년 미만인 경우 결과를 표시할 수 없습니다.")


# 결과 표시 로직
if st.session_state.get('simulation_run', False):
    results_df = st.session_state['results_df']
    inputs = st.session_state['inputs']

    display_data_and_charts(results_df, inputs)
    display_summary(st.session_state['final_year_data'], inputs['investment_years'])
else:
    st.info("좌측 사이드바에서 투자 조건을 설정하고 '시뮬레이션 실행' 버튼을 눌러주세요.")
    st.markdown("""
    ### 앱 사용 방법
    1.  **사이드바 설정**: 화면 왼쪽의 사이드바에서 투자 조건(투자금, 기간, 수익률 등)을 설정합니다.
    2.  **수익률 모델 선택**:
        - **SCHD/JEPI**: 대표적인 배당성장 ETF의 평균 수익률을 자동으로 적용합니다.
        - **직접 입력**: 원하는 연평균 배당수익률과 주가 성장률을 직접 입력할 수 있습니다.
    3.  **시뮬레이션 실행**: 모든 조건 설정 후 '시뮬레이션 실행' 버튼을 클릭하면 결과가 표시됩니다.
    """)
