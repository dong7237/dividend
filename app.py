
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

def run_simulation(
    monthly_investment_krw: int,
    investment_years: int,
    annual_price_growth_rate: float,
    annual_dividend_yield: float,
    reinvest_dividends: bool,
    exchange_rate: int,
    dividend_tax_rate: float,
    annual_expense_ratio: float
) -> List[Dict[str, Any]]:
    """
    적립식 투자 월 복리 시뮬레이션을 실행합니다.

    Args:
        monthly_investment_krw (int): 월 투자 원금 (원)
        investment_years (int): 투자 기간 (년)
        annual_price_growth_rate (float): 연평균 주가 성장률 (%)
        annual_dividend_yield (float): 연평균 배당 수익률 (%)
        reinvest_dividends (bool): 배당 수익 재투자 여부
        exchange_rate (int): 원/달러 환율

    Returns:
        List[Dict[str, Any]]: 연도별 시뮬레이션 결과 리스트
    """
    # 초기 변수 설정
    monthly_investment_usd = monthly_investment_krw / exchange_rate
    total_months = investment_years * 12
    monthly_price_growth_rate = (1 + annual_price_growth_rate / 100) ** (1/12) - 1
    monthly_dividend_yield = (1 + annual_dividend_yield / 100) ** (1/12) - 1

    total_asset_usd = 0.0
    total_principal_usd = 0.0
    total_dividends_usd = 0.0
    
    results = []
    current_year_dividends_usd = 0.0

    # 월 단위 반복 계산
    for month in range(1, total_months + 1):
        # 1. 주가 성장 적용
        growth_applied_asset = total_asset_usd * (1 + monthly_price_growth_rate)
        
        # 2. 배당금 발생
        monthly_dividend = growth_applied_asset * monthly_dividend_yield

        # 세후 배당금 계산 (추가된 부분)
        monthly_dividend_after_tax = monthly_dividend * (1 - dividend_tax_rate / 100)
    
        total_dividends_usd += monthly_dividend_after_tax # 세후 금액으로 누적
        current_year_dividends_usd += monthly_dividend_after_tax # 세후 금액으로 누적
            
        
        # 3. 자산 및 원금 업데이트
        if reinvest_dividends:
            # 세후 배당금을 재투자
            total_asset_usd = growth_applied_asset + monthly_dividend_after_tax + monthly_investment_usd
        else:
            total_asset_usd = growth_applied_asset + monthly_investment_usd
            
        total_principal_usd += monthly_investment_usd

        # 4. 연말 데이터 저장
        if month % 12 == 0:
            total_asset_usd *= (1 - annual_expense_ratio / 100)
            year = month // 12
            results.append({
                "연차": year,
                "총 투자 원금": total_principal_usd,
                "최종 평가 금액": total_asset_usd,
                "자본 이득": capital_gains_usd,
                "연간 배당금": current_year_dividends_usd,
                "총 누적 배당금": total_dividends_usd,
            })
            current_year_dividends_usd = 0.0 # 다음 해를 위해 초기화
            
    return results

# --- 사이드바 UI 구성 ---
st.sidebar.header("⚙️ 투자 조건 설정")

st.sidebar.subheader("세금 및 수수료")
st.sidebar.subheader("거시 경제")
annual_inflation_rate = st.sidebar.number_input(
    '연평균 물가 상승률 (%)', min_value=0.0, max_value=20.0, value=2.5, step=0.1
)
dividend_tax_rate = st.sidebar.number_input(
    '배당소득세율 (%)', min_value=0.0, max_value=100.0, value=15.0, step=0.1
)

annual_expense_ratio = st.sidebar.number_input(
    '연간 운용보수 (%)', min_value=0.0, max_value=5.0, value=0.06, step=0.01,
    help="ETF 운용사에 매년 지불하는 수수료입니다."
)
monthly_investment_krw_만원 = st.sidebar.slider(
    '월 투자 원금 (만원)', 
    min_value=10, max_value=500, step=5, value=45
)
monthly_investment_krw = monthly_investment_krw_만원 * 10000

investment_years = st.sidebar.slider(
    '투자 기간 (년)', 
    min_value=1, max_value=30, step=1, value=15
)

rate_model = st.sidebar.radio(
    '수익률 모델 선택',
    ('SCHD', 'JEPI', '직접 입력'),
    horizontal=True,
    index=0
)

if rate_model == 'SCHD':
    annual_dividend_yield = 3.5
    annual_price_growth_rate = 7.0
    st.sidebar.info(f"SCHD 모델: 배당 {annual_dividend_yield}%, 성장 {annual_price_growth_rate}%")
elif rate_model == 'JEPI':
    annual_dividend_yield = 7.5
    annual_price_growth_rate = 4.0
    st.sidebar.info(f"JEPI 모델: 배당 {annual_dividend_yield}%, 성장 {annual_price_growth_rate}%")
else:
    annual_dividend_yield = st.sidebar.number_input(
        '연평균 배당수익률 (%)', min_value=0.0, step=0.1, value=3.5
    )
    annual_price_growth_rate = st.sidebar.number_input(
        '연평균 주가 성장률 (%)', min_value=0.0, step=0.1, value=7.0
    )

reinvest_dividends = st.sidebar.toggle('배당 수익 자동 재투자', value=True)

exchange_rate = st.sidebar.number_input(
    '원/달러 환율 (원)', 
    min_value=0, value=1380
)

run_button = st.sidebar.button('🚀 시뮬레이션 실행')

# --- 메인 화면 구성 ---
st.title('📈 적립식 투자 월 복리 시뮬레이터')

if run_button:
    results_data = run_simulation(
        monthly_investment_krw,
        investment_years,
        annual_price_growth_rate,
        annual_dividend_yield,
        reinvest_dividends,
        exchange_rate,
        dividend_tax_rate,    # 추가
        annual_expense_ratio  # 추가
    )
    st.session_state['results'] = results_data
    st.session_state['simulation_run'] = True

if st.session_state.get('simulation_run', False):
    results = st.session_state['results']
    
    if not results:
        st.warning("계산 결과가 없습니다. 투자 기간이 1년 이상인지 확인해주세요.")
    else:
        # A. 최종 결과 요약
        st.subheader("📊 최종 결과 요약")
        final_year_data = results[-1]
        
        total_principal_krw = final_year_data["총 투자 원금"] * exchange_rate
        final_asset_krw = final_year_data["최종 평가 금액"] * exchange_rate
        total_profit_krw = final_asset_krw - total_principal_krw
        
        last_year_dividend_krw = final_year_data["연간 배당금"] * exchange_rate
        last_month_dividend_krw = last_year_dividend_krw / 12

        summary_text = (
            f"**{investment_years}년** 후, 총 투자 원금 **{total_principal_krw:,.0f}원**은 "
            f"최종 평가 금액 **{final_asset_krw:,.0f}원** (총수익: **{total_profit_krw:,.0f}원**)이 됩니다."
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
        
        # B. 연차별 상세 결과표
        st.subheader("📋 연차별 상세 결과")
        df = pd.DataFrame(results)

        # KRW로 변환된 컬럼 추가
        df_display = df.copy()
        for col in ["총 투자 원금", "최종 평가 금액", "연간 배당금", "총 누적 배당금"]:
            df_display[col] = (df_display[col] * exchange_rate)
        # 현재 가치 컬럼 추가 (추가된 부분)
        df_display["최종 평가 금액 (현재 가치)"] = df_display.apply(
            lambda row: row["최종 평가 금액"] / ((1 + annual_inflation_rate / 100) ** row["연차"]),
            axis=1
        )
        df_display["연간 배당금 (현재 가치)"] = df_display.apply(
            lambda row: row["연간 배당금"] / ((1 + annual_inflation_rate / 100) ** row["연차"]),
            axis=1
        )
        st.dataframe(
            df_display.style.format({
                "총 투자 원금": "{:,.0f}원",
                "최종 평가 금액": "{:,.0f}원",
                "연간 배당금": "{:,.0f}원",
                "총 누적 배당금": "{:,.0f}원",
                "최종 평가 금액 (현재 가치)": "{:,.0f}원",
                "연간 배당금 (현재 가치)": "{:,.0f}원",
            }),
            hide_index=True,
            use_container_width=True
        )

        # C. 자산 성장 시각화
        st.subheader("💹 자산 성장 시각화")
        chart_df = df_display.set_index("연차")[["총 투자 원금", "최종 평가 금액","최종 평가 금액 (현재 가치)"]]
        st.line_chart(chart_df)

        st.subheader("📈 자산 구성 시각화")
        
        # 누적 막대 그래프를 위한 데이터프레임 생성
        composition_df = df_display.set_index("연차")[
            ["총 투자 원금", "자본 이득", "총 누적 배당금"]
        ]
st.bar_chart(composition_df)
else:
    st.info("좌측 사이드바에서 투자 조건을 설정하고 '시뮬레이션 실행' 버튼을 눌러주세요.")
    st.markdown("""
    ### 앱 사용 방법
    1.  **사이드바 설정**: 화면 왼쪽의 사이드바에서 월 투자금, 기간, 수익률 등 원하는 투자 조건을 설정합니다.
    2.  **수익률 모델 선택**:
        - **SCHD/JEPI**: 대표적인 배당성장 ETF의 평균 수익률을 자동으로 적용합니다.
        - **직접 입력**: 원하는 연평균 배당수익률과 주가 성장률을 직접 입력할 수 있습니다.
    3.  **시뮬레이션 실행**: 모든 조건 설정 후 '시뮬레이션 실행' 버튼을 클릭하면 결과가 메인 화면에 표시됩니다.
    """)
