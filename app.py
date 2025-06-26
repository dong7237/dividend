import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

# --- 데이터 클래스 정의 ---
@dataclass
class SimulationInputs:
    """시뮬레이션 입력값을 저장하는 데이터 클래스"""
    monthly_investment_krw: int
    investment_years: int
    exchange_rate: int
    annual_inflation_rate: float
    annual_dividend_yield: float
    annual_price_growth_rate: float
    dividend_tax_rate: float
    annual_expense_ratio: float
    reinvest_dividends: bool
    savings_interest_rate: float
    savings_tax_rate: float


# --- 상수 정의 ---
YEAR = "연차"
PRINCIPAL_KRW = "총 투자 원금(원)"
ASSET_KRW = "최종 평가 금액(원)"
SAVINGS_ASSET_KRW = "예/적금 평가 금액(원)"
ASSET_PV_KRW = "최종 평가 금액(현재 가치)"


# --- 유틸리티 함수 ---
def format_krw(amount: float) -> str:
    """숫자를 '조', '억', '만' 단위의 원화 문자열로 변환합니다."""
    if abs(amount) >= 1_0000_0000_0000:
        return f"{amount / 1_0000_0000_0000:.2f}조 원"
    if abs(amount) >= 1_0000_0000:
        return f"{amount / 1_0000_0000:.2f}억 원"
    if abs(amount) >= 1_0000:
        return f"{amount / 1_0000:.0f}만 원"
    return f"{amount:,.0f}원"


# --- 시뮬레이션 함수 ---
def run_investment_simulation(inputs: SimulationInputs) -> pd.DataFrame:
    """적립식 투자 시뮬레이션을 실행합니다."""
    monthly_investment_usd = inputs.monthly_investment_krw / inputs.exchange_rate
    total_months = inputs.investment_years * 12
    monthly_growth_rate = (1 + inputs.annual_price_growth_rate / 100) ** (1/12) - 1
    monthly_dividend_yield = (1 + inputs.annual_dividend_yield / 100) ** (1/12) - 1

    asset_usd = 0.0
    principal_usd = 0.0
    cumulative_dividends_usd = 0.0
    results = []

    for month in range(1, total_months + 1):
        # 자산 성장 및 배당금 발생
        asset_growth = asset_usd * monthly_growth_rate
        asset_after_growth = asset_usd + asset_growth

        monthly_dividend = asset_after_growth * monthly_dividend_yield
        dividend_after_tax = monthly_dividend * (1 - inputs.dividend_tax_rate / 100)
        cumulative_dividends_usd += dividend_after_tax

        # 월 투자금 및 배당금 재투자
        asset_usd = asset_after_growth + monthly_investment_usd
        if inputs.reinvest_dividends:
            asset_usd += dividend_after_tax
        principal_usd += monthly_investment_usd

        # 연말 결산 및 운용보수 차감
        if month % 12 == 0:
            expense = asset_usd * (inputs.annual_expense_ratio / 100)
            asset_usd -= expense

            results.append({
                YEAR: month // 12,
                PRINCIPAL_KRW: principal_usd * inputs.exchange_rate,
                ASSET_KRW: asset_usd * inputs.exchange_rate,
            })

    return pd.DataFrame(results)

def run_savings_simulation(inputs: SimulationInputs) -> pd.DataFrame:
    """예/적금(단리) 시뮬레이션을 실행합니다."""
    total_months = inputs.investment_years * 12
    monthly_rate = inputs.savings_interest_rate / 100 / 12

    principal = 0.0
    asset = 0.0
    results = []

    for month in range(1, total_months + 1):
        principal += inputs.monthly_investment_krw
        
        if month % 12 == 0:
            # 1년치 이자 계산 (단리)
            interest = (asset + (inputs.monthly_investment_krw * 12)) * (inputs.savings_interest_rate/100) 
            interest_after_tax = interest * (1 - inputs.savings_tax_rate / 100)
            asset = principal + interest_after_tax
            
            results.append({
                YEAR: month // 12,
                SAVINGS_ASSET_KRW: asset,
            })
            
    return pd.DataFrame(results)


# --- UI 표시 함수 ---
def display_summary(final_data: pd.Series, inputs: SimulationInputs):
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
        f"**{inputs.investment_years}년** 후, 총 투자 원금 **{format_krw(inv_principal)}**은(는) "
        f"적립식 투자를 통해 **{format_krw(inv_asset)}**(으)로, "
        f"예/적금 투자를 통해 **{format_krw(sav_asset)}**(으)로 증가할 것으로 예상됩니다."
    )

def display_charts_and_data(df: pd.DataFrame, inputs: SimulationInputs):
    """상세 데이터 테이블과 시각화 차트를 표시합니다."""
    df_display = df.copy()

    # 현재가치 계산
    inflation_divisor = (1 + inputs.annual_inflation_rate / 100) ** df_display[YEAR]
    df_display[ASSET_PV_KRW] = df_display[ASSET_KRW] / inflation_divisor

    # 테이블 표시
    st.subheader("📋 연차별 상세 결과")
    display_cols = {
        YEAR: "연차",
        PRINCIPAL_KRW: "총 투자 원금",
        ASSET_KRW: "적립식 투자 평가액",
        SAVINGS_ASSET_KRW: "예/적금 평가액",
        ASSET_PV_KRW: "적립식 투자 현재가치",
    }
    df_table = df_display[list(display_cols.keys())].rename(columns=display_cols)
    
    format_dict = {col: "{:,.0f}원" for col in display_cols.values() if col != "연차"}

    st.dataframe(
        df_table.style.format(formatter=format_dict),
        hide_index=True, use_container_width=True
    )

    # 차트 표시
    st.subheader("💹 자산 성장 비교 시각화")
    chart_df = df_display.set_index(YEAR)[[PRINCIPAL_KRW, SAVINGS_ASSET_KRW, ASSET_KRW]]
    chart_df.columns = ["단순 저축 (원금)", "예/적금", "적립식 투자"]
    st.line_chart(chart_df)

    st.session_state['final_data'] = df_display.iloc[-1]


# --- Streamlit 앱 메인 로직 ---
def main():
    st.set_page_config(layout="wide")
    st.title('📈 적립식 투자 vs 예/적금 비교 시뮬레이터')

    # --- 사이드바 입력 ---
    with st.sidebar:
        st.header("⚙️ 공통 조건 설정")
        monthly_investment_krw = st.slider('월 투자 원금 (만원)', 10, 500, 50, 5) * 10000
        investment_years = st.slider('투자 기간 (년)', 1, 40, 20, 1)
        exchange_rate = st.number_input('원/달러 환율 (원)', 1000, 2000, 1380)
        annual_inflation_rate = st.slider('연평균 물가 상승률 (%)', 0.0, 10.0, 2.5, 0.1, format="%.1f")

        with st.expander("📈 적립식 투자 조건", expanded=True):
            rate_model = st.radio('수익률 모델', ('SCHD', 'JEPI', '직접 입력'), index=0, horizontal=True)
            if rate_model == 'SCHD':
                annual_dividend_yield, annual_price_growth_rate = 3.5, 7.0
            elif rate_model == 'JEPI':
                annual_dividend_yield, annual_price_growth_rate = 7.5, 4.0
            else:
                annual_dividend_yield = st.number_input('연평균 배당수익률 (%)', 0.0, 20.0, 3.5, 0.1)
                annual_price_growth_rate = st.number_input('연평균 주가 성장률 (%)', -10.0, 30.0, 7.0, 0.1)
            
            dividend_tax_rate = st.slider('배당소득세율 (%)', 0.0, 50.0, 15.4, 0.1, format="%.1f")
            annual_expense_ratio = st.slider('연간 운용보수 (%)', 0.0, 2.0, 0.06, 0.01, format="%.2f")
            reinvest_dividends = st.toggle('배당 수익 자동 재투자', value=True)

        with st.expander("💰 예/적금 투자 조건", expanded=True):
            savings_interest_rate = st.slider('연평균 예/적금 금리 (%)', 0.0, 10.0, 3.5, 0.1, format="%.1f")
            savings_tax_rate = st.slider('이자소득세율 (%)', 0.0, 50.0, 15.4, 0.1, format="%.1f")

        run_button = st.button('🚀 시뮬레이션 실행', use_container_width=True)

    # --- 메인 패널 로직 ---
    if run_button:
        inputs = SimulationInputs(
            monthly_investment_krw=monthly_investment_krw,
            investment_years=investment_years,
            exchange_rate=exchange_rate,
            annual_inflation_rate=annual_inflation_rate,
            annual_dividend_yield=annual_dividend_yield,
            annual_price_growth_rate=annual_price_growth_rate,
            dividend_tax_rate=dividend_tax_rate,
            annual_expense_ratio=annual_expense_ratio,
            reinvest_dividends=reinvest_dividends,
            savings_interest_rate=savings_interest_rate,
            savings_tax_rate=savings_tax_rate,
        )
        
        if inputs.investment_years > 0:
            inv_df = run_investment_simulation(inputs)
            sav_df = run_savings_simulation(inputs)
            
            # YEAR 기준으로 데이터 병합
            results_df = pd.merge(inv_df, sav_df, on=YEAR, how="left")
            
            st.session_state['results_df'] = results_df
            st.session_state['inputs'] = inputs
            st.session_state['simulation_run'] = True
        else:
            st.warning("투자 기간을 1년 이상으로 설정해주세요.")
            st.session_state['simulation_run'] = False

    if st.session_state.get('simulation_run', False):
        results_df = st.session_state['results_df']
        inputs = st.session_state['inputs']
        
        display_summary(results_df.iloc[-1], inputs)
        display_charts_and_data(results_df, inputs)
    else:
        st.info("좌측 사이드바에서 투자 조건을 설정하고 '시뮬레이션 실행' 버튼을 눌러주세요.")

if __name__ == "__main__":
    main()
