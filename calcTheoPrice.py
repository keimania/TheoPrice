"""이론가를 산출  
  Date:
    2023-04-19
  Author:
    구자민
  Todo:
    * 통화, 채권, 일반상품 이론가 추가 필요
"""

import math
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.interpolate import interp1d

YEAR_DAYS = 365     # 1년
TIME_STEP = 49      # 옵션 이항모델로 산출시, 단계의 수

def remainDysAnnual(remain_dys):    
    """연 환산 잔존만기 산출
    """
    return remain_dys/YEAR_DAYS


def calc_days(strt_Dd, end_dd, inclusive):    
    """일자간 차이 산출"""
    strt_Dd = pd.to_datetime(strt_Dd, format='%Y%m%d')
    end_dd = pd.to_datetime(end_dd, format='%Y%m%d')
    dates=pd.date_range(start=strt_Dd, end=end_dd, inclusive=inclusive)
    return len(dates)

def calcKRWintBySwapPoint(swapPoint, uly_prc, remain_dys, rf):
    remain_dys_annual = remainDysAnnual(remain_dys)           # 잔존만기(연 환산)
    r = swapPoint * (1 + rf * remain_dys_annual) / uly_prc * (1/remain_dys_annual) + rf
    return r

def inpoDormInt(x, y, input):
    x = np.array(x)
    y = np.array(y)

    result = interp1d(x, y, kind='linear', fill_value='extrapolate')    
    return result(input)

def calcTheoPrice_future(uly_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, how_calc_cd, stdgood_bnd_exp, bnd_yd, storg_cost):    
    """선물 이론가 산출

        Args:
            uly_prc : 기초자산 가격
            remain_dys : 잔존일수
            r : 무위험금리
            div_val : 배당액지수(상품에 따라, 현재가치 또는 미래가치)
            how_calc_cd : 파샏상품시행세칙의 별표 중 어떤 이론가공식을 사용할 것인가를 설정

        Return:
            theo_prc : 이론가
    """
    remain_dys_annual = remainDysAnnual(remain_dys)           # 잔존만기(연 환산)
    if how_calc_cd == "별표7":
        theo_prc = uly_prc * (1 + dom_riskfre_int*remain_dys_annual)-div_val
        return theo_prc

    elif how_calc_cd == "별표8":
        theo_prc = uly_prc * (1 + dom_riskfre_int*remain_dys_annual)-div_val
        return theo_prc

    elif how_calc_cd == "별표8의2":
        theo_prc = uly_prc * (1 + dom_riskfre_int*remain_dys_annual)-div_val
        return theo_prc

    elif how_calc_cd == "별표9":
        theo_prc = 0
        stdgood_bnd_exp = int(stdgood_bnd_exp)
        for i in range(1,2*stdgood_bnd_exp+1):
            theo_prc += (5/2) / pow(1+bnd_yd/2,i)
        theo_prc += 100/pow(1+bnd_yd/2, 2*stdgood_bnd_exp)
        return theo_prc

    elif how_calc_cd == "별표12":
        theo_prc = uly_prc * (1 + dom_riskfre_int*remain_dys_annual)/(1 + forn_riskfre_int*remain_dys_annual)
        return theo_prc

    elif how_calc_cd == "별표13":        
        theo_prc = uly_prc * (1 + dom_riskfre_int*remain_dys_annual)+storg_cost
        return theo_prc

    else:
        return 0

def calcTheoPrice_option(uly_prc, exer_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, volt_annual, FUTOPT_TP_CD, how_calc_cd):
    """옵션 이론가 산출

        Args:
            uly_prc : 기초자산 가격
            exer_prc : 행사가격(옵션)
            remain_dys : 잔존일수
            r : 무위험금리
            div_val : 배당액지수(상품에 따라, 현재가치 또는 미래가치)
            volt_annual : 연 변동성(옵션)
            FUTOPT_TP_CD : 선물옵션구분코드 (F:선물, C:콜업션, P:풋옵션)
            how_calc_cd : 파샏상품시행세칙의 별표 중 어떤 이론가공식을 사용할 것인가를 설정

        Return:
            theo_prc : 이론가
    """
    remain_dys_annual = remainDysAnnual(remain_dys)           # 잔존만기(연 환산)
    
    if how_calc_cd == "별표15":
        u = math.exp(volt_annual*math.sqrt(remain_dys_annual/TIME_STEP))
        d = math.exp(-1 * volt_annual*math.sqrt(remain_dys_annual/TIME_STEP))
        p = (math.exp(dom_riskfre_int*remain_dys_annual/TIME_STEP)-d)/(u-d)
        q = 1-p

        ST = []
        payoff=[]
        if FUTOPT_TP_CD == 'C':
            for k in range(TIME_STEP+1):
                ST.append((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k)))                                      # Binomial Tree의 매 state
                payoff.append(max(((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k)) - exer_prc),0))              # 매 state의 Payoff
        else:
            for k in range(TIME_STEP+1):
                ST.append((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k)))                                      # Binomial Tree의 매 state
                payoff.append(max(exer_prc - ((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k))),0))              # 매 state의 Payoff

        # 이론가 산출
        theo_prc_future = 0
        for k in range(TIME_STEP+1):
            theo_prc_future += math.factorial(TIME_STEP)/(math.factorial(TIME_STEP-k)*math.factorial(k)) * (p ** k) * (q ** (TIME_STEP-k)) *payoff[k]       # 이론가의 미래가치
        theo_prc = math.exp(-1*dom_riskfre_int*remain_dys_annual)*theo_prc_future       # 이론가격, 현재가치

        return theo_prc

    elif how_calc_cd == "별표16":
        u = math.exp(volt_annual*math.sqrt(remain_dys_annual/TIME_STEP))        
        d = math.exp(-1 * volt_annual*math.sqrt(remain_dys_annual/TIME_STEP))
        p = (math.exp(dom_riskfre_int*remain_dys_annual/TIME_STEP)-d)/(u-d)
        q = 1-p

        ST = []
        payoff=[]
        if FUTOPT_TP_CD == 'C':
            for k in range(TIME_STEP+1):
                ST.append((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k)))                                      # Binomial Tree의 매 state
                payoff.append(max(((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k)) - exer_prc),0))              # 매 state의 Payoff
        else:
            for k in range(TIME_STEP+1):
                ST.append((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k)))                                      # Binomial Tree의 매 state
                payoff.append(max(exer_prc - ((uly_prc-div_val) * (u**k) * (d ** (TIME_STEP-k))),0))              # 매 state의 Payoff

        # 이론가 산출
        theo_prc_future = 0
        for k in range(TIME_STEP+1):
            theo_prc_future += math.factorial(TIME_STEP)/(math.factorial(TIME_STEP-k)*math.factorial(k)) * (p ** k) * (q ** (TIME_STEP-k)) *payoff[k]       # 이론가의 미래가치
        theo_prc = math.exp(-1*dom_riskfre_int*remain_dys_annual)*theo_prc_future       # 이론가격, 현재가치

        return theo_prc

    elif how_calc_cd == "별표17":
        theo_prc = 0
        d1= (math.log(uly_prc / exer_prc) + (dom_riskfre_int - forn_riskfre_int + (volt_annual ** 2)/2) * remain_dys_annual) / volt_annual * math.sqrt(remain_dys_annual)
        d2 = d1 - volt_annual * math.sqrt(remain_dys_annual)
        if FUTOPT_TP_CD == 'C':
            theo_prc = uly_prc * math.exp(-1*forn_riskfre_int*remain_dys_annual) * norm.cdf(d1) - exer_prc * math.exp(-1*dom_riskfre_int*remain_dys_annual) * norm.cdf(d2)
        else:
            theo_prc = exer_prc * math.exp(-1*dom_riskfre_int*remain_dys_annual) * norm.cdf(-1*d2) - uly_prc * math.exp(-1*forn_riskfre_int*remain_dys_annual) * norm.cdf(-1*d1)

        return theo_prc

    else:
        return 0

def calcTheoPrice(uly_prc, exer_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, volt_annual, FUTOPT_TP_CD, how_calc_cd, stdgood_bnd_exp, bnd_yd, storg_cost):
    """ 이론가 산출을 위한 함수
        * 필요시 아래 파라미터를 직접 넣어 호출하면, 상품에 따라 이론가 산출

        Args:
            uly_prc : 기초자산 가격
            exer_prc : 행사가격(옵션)
            remain_dys : 잔존일수
            r : 무위험금리
            div_val : 배당액지수(상품에 따라, 현재가치 또는 미래가치)
            volt_annual : 연 변동성(옵션)
            FUTOPT_TP_CD : 선물옵션구분코드 (F:선물, C:콜업션, P:풋옵션)
            how_calc_cd : 파샏상품시행세칙의 별표 중 어떤 이론가공식을 사용할 것인가를 설정

        Return:
            theo_prc : 이론가
    """
    if FUTOPT_TP_CD in ["F"]:
        theo_prc = calcTheoPrice_future(uly_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, how_calc_cd, stdgood_bnd_exp, bnd_yd, storg_cost)
    elif FUTOPT_TP_CD in ["C", "P"]:
        theo_prc = calcTheoPrice_option(uly_prc, exer_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, volt_annual, FUTOPT_TP_CD, how_calc_cd)
    else:
        theo_prc = 0
    return theo_prc

def calcTheoPriceRFR(lsttrd_dd, appl_strt_dd, appl_end_dd, final_yn, final_int, mm3_govbnd_strip_int, fwd_int, int_spd, calc_dd):
    if final_yn == 'Y':
        x = calc_days(calc_dd, appl_strt_dd, "left")
        N = calc_days(appl_strt_dd, appl_end_dd, "both")
        strip_int = 1 + mm3_govbnd_strip_int/100 * (N-x) / YEAR_DAYS
        theo_int = YEAR_DAYS/N*(final_int*strip_int-1)*100
    else:
        theo_int = fwd_int - int_spd
    theo_prc = 100 - theo_int
    return theo_prc

### 단일 값을 넣어서 테스트할 수 있게 만듬
if __name__ == "__main__":

    result_columns = ["기초자산기준가격", "행사가격", "잔존일수", "국내무위험금리", "국외무위험금리","배당액지수", "연 변동성", "선물옵션구분코드", "이론가격", "산출방법", "채권선물만기", "채권수익률", "금선물 g당 보관료"]
    results = pd.DataFrame(columns=result_columns)

    uly_prc=1337.2
    exer_prc=0
    remain_dys=2
    dom_riskfre_int=0.032367
    forn_riskfre_int=0.050022
    div_val=0
    volt_annual=0.42
    FUTOPT_TP_CD="F"    
    how_calc_cd="별표12"
    stdgood_bnd_exp = 3.0
    bnd_yd = 0.0312
    storg_cost = 4.5
    
    theo_prc = calcTheoPrice(uly_prc, exer_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, volt_annual, FUTOPT_TP_CD, how_calc_cd, stdgood_bnd_exp, bnd_yd, storg_cost)
    
    results.loc[len(results)] = [uly_prc, exer_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, volt_annual, FUTOPT_TP_CD, theo_prc, how_calc_cd, stdgood_bnd_exp, bnd_yd, storg_cost]
    print(results)
    results.to_excel("results_theoPrcSimple.xlsx")