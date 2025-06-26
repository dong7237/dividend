import streamlit as st
import pandas as pd
from dataclasses import dataclass

# --- 상수 정의 ---
YEAR = "연차"
PRINCIPAL_KRW = "총 투자 원금(원)"
ASSET_KRW = "최종 평가 금액(원)"
CAPITAL_GAINS_KRW = "자본 이득(원)"
CUMULATIVE_DIVIDEND_KRW = "누적 배당금(원)"
SAVINGS_ASSET_KRW = "예/적금 평가 금액(원)"
ASSET_PV_KRW = "적립식 투자 평가 금액(현재 가치)"
SAVINGS_ASSET_PV_KRW = "예/적금 평가 금액(현재 가치)"

SCHD_DEFAULTS = {'apgr': 7.0, 'ady': 3.5}
JEPI_DEFAULTS = {'apgr': 4.0, 'ady': 7.5}


# --- 데이터 클래스 정의 ---
@dataclass
class SimulationInputs:
    """시뮬레이션 입력값을 저장하는 데이터 클래스"""
    monthly_investment_krw: int
    investment_years: int
    exchange_rate: int
    annual_inflation_rate: float
    annual_price_growth_rate: float
    capital_gains_tax_rate: float
    seed_money_krw: int
    annual_dividend_yield: float
    dividend_tax_rate: float
    annual_expense_ratio: float
    reinvest_dividends: bool
    savings_interest_rate: float
    savings_tax_rate: float


# --- 유틸리티 함수 ---
def format_krw(amount: float) -> str:
    """숫자를 '조', '억', '만' 단위의 원화 문자열로 변환합니다."""
    if abs(amount) >= 1_0000_0000_0000:
        return f"{amount / 1_0000_0000_0000:,.2f}조 원"
    if abs(amount) >= 1_0000_0000:
        return f"{amount / 1_0000_0000:,.2f}억 원"
    if abs(amount) >= 1_0000:
        return f"{amount / 1_0000:,.0f}만 원"
    return f"{amount:,.0f}원"


# --- 시뮬레이션 함수 ---
def run_investment_simulation(inputs: SimulationInputs) -> pd.DataFrame:
    """적립식 투자 시뮬레이션을 실행합니다."""
    # 입력값을 월 단위로 변환 및 초기화
    monthly_investment_usd = inputs.monthly_investment_krw / inputs.exchange_rate
    total_months = inputs.investment_years * 12
    monthly_growth_rate = (1 + inputs.annual_price_growth_rate / 100) ** (1/12) - 1
    monthly_dividend_yield = (1 + inputs.annual_dividend_yield / 100) ** (1/12) - 1
    seed_money_usd = inputs.seed_money_krw / inputs.exchange_rate
    
    asset_usd = seed_money_usd
    principal_usd = seed_money_usd
    cumulative_dividends_usd = 0.0
    results = []

    for month in range(1, total_months + 1):
        asset_usd += asset_usd * monthly_growth_rate # 주가 성장
        
        monthly_dividend = asset_usd * monthly_dividend_yield
        dividend_after_tax = monthly_dividend * (1 - inputs.dividend_tax_rate / 100)
        cumulative_dividends_usd += dividend_after_tax
        
        asset_usd += monthly_investment_usd # 월 추가 납입
        principal_usd += monthly_investment_usd
        
        if inputs.reinvest_dividends:
            asset_usd += dividend_after_tax # 배당금 재투자
            # [수정] 재투자된 배당은 투자 원금(취득가액)에 포함시켜 이중과세 방지
            principal_usd += dividend_after_tax

        # 매년 말일 경우
        if month % 12 == 0:
            asset_usd -= asset_usd * (inputs.annual_expense_ratio / 100) # 운용보수 차감
            
            capital_gains_usd = asset_usd - principal_usd
            final_asset_usd = asset_usd
            
            # [수정] 마지막 해에만 양도소득세 계산 및 차감
            if month // 12 == inputs.investment_years:
                taxable_gains = max(0, capital_gains_usd)
                capital_gains_tax = taxable_gains * (inputs.capital_gains_tax_rate / 100)
                final_asset_usd -= capital_gains_tax
                capital_gains_usd -= capital_gains_tax # 자본이득도 세후 금액으로 조정

            results.append({
                YEAR: month // 12,
                PRINCIPAL_KRW: principal_usd * inputs.exchange_rate,
                ASSET_KRW: final_asset_usd * inputs.exchange_rate,
                CAPITAL_GAINS_KRW: capital_gains_usd * inputs.exchange_rate,
                CUMULATIVE_DIVIDEND_KRW: cumulative_dividends_usd * inputs.exchange_rate,
            })

    return pd.DataFrame(results) if results else pd.DataFrame()


def run_savings_simulation(inputs: SimulationInputs) -> pd.DataFrame:
    """예/적금(월 복리) 시뮬레이션을 실행합니다."""
    total_months = inputs.investment_years * 12
    monthly_rate = inputs.savings_interest_rate / 100 / 12
    tax_rate = inputs.savings_tax_rate / 100

    asset = float(inputs.seed_money_krw)
    interest_for_year = 0.0
    results = []

    for month in range(1, total_months + 1):
        interest = asset * monthly_rate
        interest_for_year += interest
        asset += interest
        
        asset += inputs.monthly_investment_krw

        if month % 12 == 0:
            taxable_interest = max(0, interest_for_year)
            tax = taxable_interest * tax_rate
            asset -= tax
            
            results.append({
                YEAR: month // 12,
                SAVINGS_ASSET_KRW: asset,
            })
            # 연말 정산 후 초기화
            interest_for_year = 0.0

    return pd.DataFrame(results) if results else pd.DataFrame()


# --- UI 표시 함수 ---
def display_summary(final_data: pd.Series, inputs: SimulationInputs):
    """최종 결과 요약 정보를 비교하여 표시합니다."""
    st.subheader("📊 최종 결과 요약")

    inv_principal = final_data[PRINCIPAL_KRW]
    inv_asset = final_data[ASSET_KRW]
    sav_asset = final_data[SAVINGS_ASSET_KRW]

    col1, col2, col3 = st.columns(3)
    col1.metric("단순 저축 (총 원금)", format_krw(inv_principal))
    col2.metric("예/적금 투자 (세후)", format_krw(sav_asset), f"수익: {format_krw(sav_asset - inv_principal)}")
    col3.metric("적립식 투자 (세후)", format_krw(inv_asset), f"수익: {format_krw(inv_asset - inv_principal)}")

    st.info(
        f"**{inputs.investment_years}년** 후, 총 투자 원금 **{format_krw(inv_principal)}**은(는) "
        f"적립식 투자를 통해 **{format_krw(inv_asset)}**(으)로, "
        f"예/적금 투자를 통해 **{format_krw(sav_asset)}**(으)로 증가할 것으로 예상됩니다."
    )
    

def display_charts_and_data(df: pd.DataFrame, inputs: SimulationInputs):
    """상세 데이터 테이블과 시각화 차트를 표시합니다."""
    df_display = df.copy()

    # [수정] 물가상승률을 적용한 현재가치(PV) 계산
    inflation_divisor = (1 + inputs.annual_inflation_rate / 100) ** df_display[YEAR]
    df_display[ASSET_PV_KRW] = df_display[ASSET_KRW] / inflation_divisor
    df_display[SAVINGS_ASSET_PV_KRW] = df_display[SAVINGS_ASSET_KRW] / inflation_divisor

    st.subheader("📋 연차별 상세 결과")
    display_cols = {
        YEAR: "연차",
        PRINCIPAL_KRW: "총 투자 원금",
        ASSET_KRW: "적립식 투자 평가액",
        SAVINGS_ASSET_KRW: "예/적금 평가액",
        ASSET_PV_KRW: "적립식 투자 현재가치",
        SAVINGS_ASSET_PV_KRW: "예/적금 현재가치",
        CUMULATIVE_DIVIDEND_KRW: "누적 배당금(세후)",
        CAPITAL_GAINS_KRW: "자본 이득(세후)",
    }
    df_table = df_display[list(display_cols.keys())].rename(columns=display_cols)
    format_dict = {col: "{:,.0f}원" for col in display_cols.values() if col != "연차"}
    st.dataframe(df_table.style.format(formatter=format_dict), hide_index=True, use_container_width=True)

    st.subheader("💹 자산 명목가치 성장 비교")
    chart_df_nominal = df_display.set_index(YEAR)[[PRINCIPAL_KRW, SAVINGS_ASSET_KRW, ASSET_KRW]]
    chart_df_nominal.columns = ["총 투자 원금", "예/적금 (세후)", "적립식 투자 (세후)"]
    st.line_chart(chart_df_nominal)
    
    # [수정] 현재가치 비교 차트 추가
    st.subheader("📉 자산 현재가치(PV) 성장 비교 (물가상승률 감안)")
    chart_df_pv = df_display.set_index(YEAR)[[PRINCIPAL_KRW, SAVINGS_ASSET_PV_KRW, ASSET_PV_KRW]]
    chart_df_pv.columns = ["총 투자 원금 (명목)", "예/적금 (현재 가치)", "적립식 투자 (현재 가치)"]
    st.line_chart(chart_df_pv)


# --- Streamlit 앱 메인 로직 ---
def main():
    st.set_page_config(layout="wide")
    st.title('📈 적립식 투자 시뮬레이터')

    # 세션 상태 초기화
    if 'simulation_run' not in st.session_state:
        st.session_state['simulation_run'] = False
        
    with st.sidebar:
        st.header("⚙️ 공통 조건 설정")
        monthly_investment_krw = st.slider('월 투자 원금 (만원)', 10, 500, 50, 5) * 10000
        investment_years = st.slider('투자 기간 (년)', 1, 60, 20, 1)
        exchange_rate = st.number_input('원/달러 환율 (원)', 800, 2500, 1380)
        annual_inflation_rate = st.slider('연평균 물가 상승률 (%)', 0.0, 10.0, 2.5, 0.1, format="%.1f")
        seed_money_krw = st.number_input('초기 시드머니 (만원)', 0, 10000, 0, 100) * 10000

        with st.expander("📈 적립식 투자 조건", expanded=True):
            rate_model = st.radio('수익률 모델', ('SCHD', 'JEPI', '직접 입력'), index=0, horizontal=True)
            if rate_model == 'SCHD':
                apgr, ady = SCHD_DEFAULTS['apgr'], SCHD_DEFAULTS['ady']
            elif rate_model == 'JEPI':
                apgr, ady = JEPI_DEFAULTS['apgr'], JEPI_DEFAULTS['ady']
            else:
                # 입력값 범위 일부 조정
                apgr = st.number_input('연평균 주가 성장률 (%)', -20.0, 50.0, 7.0, 0.1)
                ady = st.number_input('연평균 배당수익률 (%)', 0.0, 20.0, 3.5, 0.1)

            reinvest_dividends = st.toggle('배당 수익 자동 재투자', value=True)
            annual_expense_ratio = st.slider('연간 운용보수 (%)', 0.0, 2.0, 0.06, 0.01, format="%.2f")
            dividend_tax_rate = st.slider('배당소득세율 (%)', 0.0, 50.0, 15.4, 0.1, format="%.1f")
            capital_gains_tax_rate = st.slider('자본이득세율(양도소득세) (%)', 0.0, 50.0, 22.0, 0.1, format="%.1f")

        with st.expander("💰 예/적금 투자 조건", expanded=True):
            savings_interest_rate = st.slider('연평균 예/적금 금리 (%)', 0.0, 10.0, 3.5, 0.1, format="%.1f")
            savings_tax_rate = st.slider('이자소득세율 (%)', 0.0, 50.0, 15.4, 0.1, format="%.1f")

        run_button = st.button('🚀 시뮬레이션 실행', use_container_width=True)

        inputs = SimulationInputs(
            seed_money_krw=seed_money_krw,
            monthly_investment_krw=monthly_investment_krw, investment_years=investment_years,
            exchange_rate=exchange_rate, annual_inflation_rate=annual_inflation_rate,
            annual_price_growth_rate=apgr, capital_gains_tax_rate=capital_gains_tax_rate,
            annual_dividend_yield=ady, dividend_tax_rate=dividend_tax_rate,
            annual_expense_ratio=annual_expense_ratio, reinvest_dividends=reinvest_dividends,
            savings_interest_rate=savings_interest_rate, savings_tax_rate=savings_tax_rate,
        )
    
    if run_button:
        if inputs.investment_years > 0:
            inv_df = run_investment_simulation(inputs)
            sav_df = run_savings_simulation(inputs)
            
            if not inv_df.empty and not sav_df.empty:
                results_df = pd.merge(inv_df, sav_df, on=YEAR, how="left")
                st.session_state['results_df'] = results_df
                st.session_state['inputs'] = inputs
                st.session_state['simulation_run'] = True
            else:
                st.error("시뮬레이션 결과가 없습니다. 입력값을 확인해주세요.")
                st.session_state['simulation_run'] = False
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
        
    # [수정] 모델의 주요 가정과 한계점 명시
    with st.expander("ℹ️ 시뮬레이션 모델의 주요 가정 및 한계"):
        st.warning("본 시뮬레이션의 모든 결과는 사용자가 입력한 가정에 기반한 추정치이며, 미래의 실제 수익률을 보장하지 않습니다.")
        st.markdown("""
        - **고정 수익률**: 시뮬레이션은 사용자가 입력한 '연평균' 수익률이 매년 일정하게 발생한다고 가정합니다. 실제 시장의 변동성은 반영되지 않으므로, 손실이 발생하는 해가 있을 수 있습니다.
        - **고정 환율**: 전체 투자 기간 동안 환율이 변동하지 않는다고 가정합니다. 장기 투자 시 환율 변동은 수익률에 큰 영향을 줄 수 있습니다.
        - **단순화된 세금**: 배당소득세와 양도소득세는 현재의 단일 세율을 적용하며, 실제로는 금융소득종합과세, 세법 개정 등 더 복잡한 세금 체계가 적용될 수 있습니다.
        - **기타 비용 미반영**: 증권사 매매 수수료, 환전 수수료 등의 거래 비용은 계산에 포함되지 않아 실제 수익률은 더 낮을 수 있습니다.
        - **배당과 가격 성장**: 배당수익률과 주가 성장률을 독립적인 변수로 가정합니다. 현실에서는 두 지표가 서로 영향을 미칠 수 있습니다.
        
        **결론적으로 본 도구는 교육 및 시나리오 분석 목적으로만 활용해야 하며, 실제 투자 결정의 직접적인 근거로 사용될 수 없습니다.**
        """)

if __name__ == "__main__":
    main()

