"""이론가를 DB에서 가져온 정보를 이용하여 산출  
  작성일 : 2023-05-02
  Author:
    구자민
  Todo:
    * 통화, 채권, 일반상품 이론가 추가 필요
"""

import orcl
import pandas as pd
import calcTheoPrice

STRT_DD = "20231204"
END_DD = "20231205"
THEO_PRC_USE_TP_CD = "01"           # 01 : 정산가/증거금기준가 산출용, 02 : 기준가/호가한도계산 산출용
PRC_TP_CD = 'S'

# 환경명
env = "PD_CS_CCP"
conn_oracle = orcl.RDB_client(env)

def makeCustomBd(holidays : pd.DataFrame):
    """ 휴장일 정보를 이용하여 영업일 달력을 생성
    """
    holidays['HOLDY_DD']=pd.to_datetime(holidays['HOLDY_DD'], format='%Y%m%d')
    custom_bd = pd.tseries.offsets.CustomBusinessDay(holidays=holidays['HOLDY_DD'].tolist())
    return custom_bd

def next_n_business_day(bas_dd, n, custom_bd):
    """ 기준일자의 n일 후의 영업일
    """
    bas_dd = pd.to_datetime(bas_dd, format='%Y%m%d')
    return(bas_dd + custom_bd * n).strftime('%Y%m%d')    

def previous_n_business_day(bas_dd, n, custom_bd):
    """ 기준일자의 n일 전 영업일
    """
    bas_dd = pd.to_datetime(bas_dd, format='%Y%m%d')
    return(bas_dd - custom_bd * n).strftime('%Y%m%d')

def make_biz_days(strt_dd, end_dd, custom_bd):
    """ 주어진 기간 내의 영업일자를 생성
    """
    strt_dd = pd.to_datetime(strt_dd, format='%Y%m%d')
    end_dd = pd.to_datetime(end_dd, format='%Y%m%d')
    return pd.date_range(start=strt_dd, end=end_dd, freq=custom_bd)    
    

def howCalcTheo(rawData):
    """ 어떤 공식으로 이론가격을 산출할지 결정    
    
    ** 참고 : 이론가격이 산출되지 않는 예외 규정
    * 나. 코스피고배당50선물거래, 코스피배당성장50선물거래, 코스피200변동성지수선물거래 및 돈육선물거래의 경우: 전일의 기초자산기준가격
    * 다. 해외지수선물거래의 경우: 최종거래일이 동일한 유렉스 유로스톡스50선물의 정산가격(유렉스가 정하는 기준과 방법에 따라 산출하는 최종거래일이 동일한 결제월종목의 직전 거래일 전일의 정산가격을 말한다)
    
    Args:
        rawData : 이론가격 산출 기초정보

    Return:
        이론가를 산출하는 파생상품시장 업무규정 시행세칙의 별표번호를 return      
    """
    uly_id = rawData['FORPRC_ULY_ID'] 
    mkt_dtl_id = rawData['MKT_DTL_ID'] 
    uly_tp_cd = rawData['ULY_TP_CD'] 
    RGHT_TP_CD = rawData['RGHT_TP_CD'] 
    SPD_COMPST_CD = rawData['SPD_COMPST_CD']
    if SPD_COMPST_CD != ' ':
        how_calc_cd = "스프레드"
    elif uly_id in ["VKI", "XA4", "XA5", "XA4", "EST"]:
        how_calc_cd = "이론가 산출대상 상품 아님"
    elif mkt_dtl_id in ["SPI"] and uly_tp_cd in ["IDX"] and RGHT_TP_CD=="F":
        how_calc_cd = "별표7"
    elif mkt_dtl_id in ["EQU"] and uly_tp_cd in ["EQU"] and RGHT_TP_CD=="F":
        how_calc_cd = "별표8"
    elif uly_tp_cd in ["BON"] and RGHT_TP_CD=="F":
        how_calc_cd = "별표9"
    elif uly_tp_cd in ["IRT"] and RGHT_TP_CD=="F":
        how_calc_cd = "별표9의2"
    elif uly_tp_cd in ["CUR"] and RGHT_TP_CD=="F":
        how_calc_cd = "별표12"
    elif uly_tp_cd in ["COM"] and uly_id in ["KGD"] and RGHT_TP_CD=="F":
        how_calc_cd = "별표13"
    elif mkt_dtl_id in ["SPI"] and uly_tp_cd in ["IDX"] and RGHT_TP_CD in ["C", "P"]:
        how_calc_cd = "별표15"
    elif mkt_dtl_id in ["EQU"] and uly_tp_cd in ["EQU"] and RGHT_TP_CD in ["C", "P"]:
        how_calc_cd = "별표16"
    elif uly_tp_cd in ["CUR"] and uly_id in ["USD"] and RGHT_TP_CD in ["C", "P"]:
        how_calc_cd = "별표17"
    else: how_calc_cd = ""
    rawData['HOW_CALC_CD'] = how_calc_cd
    return rawData


def calucTheoPriceFromDF(rawData):
    """Pandas의 DataFrame에서 이론가 산출 기본정보를 가져와 이론가를 산출
    """
    if rawData['SPD_COMPST_CD'] != ' ':
        rawData['THEO_PRC'] = 0
        return rawData
    rght_tp_cd = rawData['RGHT_TP_CD']
    uly_prc = rawData['ULY_PRC']
    exer_prc = rawData['EXER_PRC']
    remain_dys = rawData['REMAIN_DYS']
    volt_annual = rawData['FINAL_VOLT']
    how_calc_cd = rawData['HOW_CALC_CD']
        
    dom_riskfre_int = rawData['DOM_RISKFRE_INT']
    forn_riskfre_int = rawData['FORN_RISKFRE_INT']
    
    stdgood_bnd_exp = rawData['STDGOOD_BND_EXP']    
    bnd_yd = rawData['BND_YD']    
    div_val = rawData['DIV_VAL']
    storg_cost = rawData['STORG_COST']
    if how_calc_cd == "별표9의2":
        rawData['THEO_PRC'] = calcTheoPrice.calcTheoPriceRFR(rawData['LSTTRD_DD'], rawData['APPL_STRT_DD'], rawData['APPL_END_DD'], rawData['FINAL_YN'], rawData['FINAL_INT'], rawData['MM3_GOVBND_STRIP_INT'], rawData['FWD_INT'], rawData['INT_SPD'], rawData['DD'])
    else:
        rawData['THEO_PRC'] = calcTheoPrice.calcTheoPrice(uly_prc, exer_prc, remain_dys, dom_riskfre_int, forn_riskfre_int, div_val, volt_annual, rght_tp_cd, how_calc_cd, stdgood_bnd_exp, bnd_yd, storg_cost)
    rawData['THEO_PRC_DIFF_DB_AND_PYTHON'] = rawData['THEO_PRC'] - rawData['THEO_PRC_DB']
    
    return rawData


def calc_remain_dys_next_day(df, df_old, custom_bd):
    isu_cd = df['ISU_CD']
    dd = df['DD']
    next_day = next_n_business_day(dd, 1, custom_bd)
    if df_old.loc[(df_old['ISU_CD'] == isu_cd) & (df_old['DD'] == next_day), 'REMAIN_DYS'].empty:
        next_remain_dys = 0
    else:
        next_remain_dys = df_old.loc[(df_old['ISU_CD'] == isu_cd) & (df_old['DD'] == next_day), 'REMAIN_DYS'].values[0]    
    return next_remain_dys

# 잔존일수 계산
def calc_remaindys(dd, exp_dd, inclusive):    
    dd = pd.to_datetime(dd, format='%Y%m%d')
    exp_dd = pd.to_datetime(exp_dd, format='%Y%m%d')
    dates=pd.date_range(start=dd, end=exp_dd, inclusive=inclusive)
    return len(dates)

def read_div_val(rawData):
    how_calc_cd = rawData['HOW_CALC_CD']
    if how_calc_cd in ["별표7", "별표8", "별표8의2"]:
        rawData['DIV_VAL'] = rawData['FSETLPRC_DIV_FUT_VAL']
    elif how_calc_cd in ["별표15", "별표16"]:
        rawData['DIV_VAL'] = rawData['FSETLPRC_DIV_PRSNT_VAL']
    return rawData

        
### 실행시, 기본적으로 특정일자(DAY)의 모든 종목에 대해 이론가를 산출
### * 리스트로 특정 종목만 지정시, 특정 종목에 대해서만 산출
if __name__ == "__main__":
    if (END_DD < STRT_DD):
        print("Date error : END_DD should be equal or greater than STRT_DD")
        exit()
    rawData_columns = []
    rawData = pd.DataFrame(columns=rawData_columns)
    
    # Oracle DB 접속
    conn_oracle = orcl.RDB_client(env)    

    conn_oracle.cursor.execute(f"SELECT * FROM TBCS_HOLDY WHERE CALND_ID = 'COMMON'")
    TBCS_HOLDY = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    custom_bd = makeCustomBd(TBCS_HOLDY)

    rawData['DD'] = make_biz_days(STRT_DD, END_DD, custom_bd).strftime('%Y%m%d')

    # 종목정보를 TBCS_DRV_ISU 에서 가져오기
    conn_oracle.cursor.execute(f"SELECT STRT_DD, END_DD, ISU_CD, ISU_KOR_NM, PROD_ID, ULY_ID, FORPRC_ULY_ID, SPD_COMPST_CD, ULY_TP_CD, RGHT_TP_CD, EXER_PRC, EXP_DD, MKT_DTL_ID FROM TBCS_DRV_ISU WHERE END_DD >='{STRT_DD}' AND STRT_DD<='{END_DD}'")
    TBCS_DRV_ISU = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())  

    rawData2 = pd.merge(rawData, TBCS_DRV_ISU, how='cross')
    rawData2 = rawData2[(rawData2['STRT_DD']<=rawData2['DD']) & (rawData2['END_DD']>=rawData2['DD'])]  
    rawData2.drop(columns=['STRT_DD', 'END_DD'], inplace=True)

    # 국채만기 정보를 TBCS_ULY 에서 가져오기
    conn_oracle.cursor.execute(f"SELECT STRT_DD, END_DD, ULY_ID, STDGOOD_BND_EXP FROM TBCS_ULY WHERE END_DD >='{STRT_DD}' AND STRT_DD<='{END_DD}'")    
    TBCS_ULY = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())  
    rawData3 = pd.merge(rawData, TBCS_ULY, how='cross')
    rawData3 = rawData3[(rawData3['STRT_DD']<=rawData3['DD']) & (rawData3['END_DD']>=rawData3['DD'])]  
    rawData3.drop(columns=['STRT_DD', 'END_DD'], inplace=True) 
    rawData = pd.merge(rawData2, rawData3, on=['DD', 'ULY_ID'], how='left')    

    # 금시장 보관료를 TBCS_STORG_COST 에서 가져오기
    conn_oracle.cursor.execute(f"SELECT DD, ULY_ID, STORG_COST FROM TBCS_STORG_COST WHERE DD BETWEEN '{STRT_DD}' AND '{END_DD}'")
    TBCS_STORG_COST = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    rawData = pd.merge(rawData, TBCS_STORG_COST, on=['DD', 'ULY_ID'], how='left')    

    # 기초자산기준가격, 잔존일수, 금리, 국채수익률를 TBCS_THEO_PRC_VAR 에서 가져오기
    conn_oracle.cursor.execute(f"SELECT CALC_DD, ISU_CD, ULY_PRC, REMAIN_DYS, DOM_RISKFRE_INT, FORN_RISKFRE_INT, BND_YD FROM TBCS_THEO_PRC_VAR WHERE CALC_DD BETWEEN '{previous_n_business_day(STRT_DD,1,custom_bd)}' AND '{END_DD}' AND THEO_PRC_USE_TP_CD='{THEO_PRC_USE_TP_CD}' AND SEQ='1'")
    TBCS_THEO_PRC_VAR = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    rawData = pd.merge(rawData, TBCS_THEO_PRC_VAR, left_on=['DD', 'ISU_CD'], right_on=['CALC_DD', 'ISU_CD'], how='left')
    
    conn_oracle.cursor.execute(f"SELECT DD, ISU_CD, FINAL_VOLT, FINAL_VOLT_TP_CD FROM TBCS_VOLT WHERE DD BETWEEN '{STRT_DD}' AND '{END_DD}'")  # 
    TBCS_VOLT = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    rawData = pd.merge(rawData, TBCS_VOLT, on=['DD','ISU_CD'], how='left')

    # 산출된 이론가 값을 DB(TBCS_THEO_PRC)에서 가져오기
    if THEO_PRC_USE_TP_CD == '01':  
        conn_oracle.cursor.execute(f"SELECT DD, ISU_CD, VOLT_TP_CD, SETL_THEO_PRC AS THEO_PRC_DB, '01' AS THEO_PRC_USE_TP_CD FROM TBCS_THEO_PRC WHERE DD BETWEEN '{STRT_DD}' AND '{END_DD}'")  # 
        TBCS_THEO_PRC = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())         
        FILTERED_TBCS_THEO_PRC = TBCS_THEO_PRC[TBCS_THEO_PRC['VOLT_TP_CD'].isin(['00', 'BV'])].sort_values(by=['ISU_CD', 'VOLT_TP_CD'], ascending=[True, False]).drop_duplicates(subset=['DD','ISU_CD'], keep='first')
        rawData = pd.merge(rawData, FILTERED_TBCS_THEO_PRC, on=['DD','ISU_CD'], how='left')    

    # 기초자산기준가격은 TBCS_ULY_BAS_PRC에서 가져오기
    # conn_oracle.cursor.execute((f"SELECT DISTINCT TBCS_BYDD_DRV_ISU.DD, TBCS_ULY_BAS_PRC.FORPRC_ULY_ID, TBCS_ULY_BAS_PRC.TRD_PERSIS_ULY_BAS_PRC from TBCS_BYDD_DRV_ISU, TBCS_ULY_BAS_PRC "
    #     f"where TBCS_BYDD_DRV_ISU.DD BETWEEN '{STRT_DD}' AND '{END_DD}' AND TBCS_BYDD_DRV_ISU.DD = TBCS_ULY_BAS_PRC.DD "
    #     f"AND TBCS_BYDD_DRV_ISU.FORPRC_ULY_ID = TBCS_ULY_BAS_PRC.FORPRC_ULY_ID "))
    # rows = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    # rawData = pd.merge(rawData, rows, on=['DD', 'FORPRC_ULY_ID'], how='left')
    # rawData = rawData.rename(columns={'TRD_PERSIS_ULY_BAS_PRC':'ULY_PRC'})

    # 무위험금리 가져오기
    # conn_oracle.cursor.execute(f"SELECT DD, CURR_ISO_CD, BENCHMK_NM, RISKFRE_INT FROM TBCS_RISKFRE_INT WHERE DD BETWEEN '{STRT_DD}' AND '{END_DD}' ")  # 
    # TBCS_RISKFRE_INT = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    # TBCS_RISKFRE_INT['RISKFRE_INT'] = TBCS_RISKFRE_INT['RISKFRE_INT'] / 100
    
    # DOM_RISKFRE_INT_DF = TBCS_RISKFRE_INT[(TBCS_RISKFRE_INT['CURR_ISO_CD'] == 'KRW') & (TBCS_RISKFRE_INT['BENCHMK_NM'] == '3MCD')]
    # FORN_RISKFRE_INT_DF = TBCS_RISKFRE_INT[(TBCS_RISKFRE_INT['CURR_ISO_CD'] == 'USD') & (TBCS_RISKFRE_INT['BENCHMK_NM'] == '3MLIBOR')]
    # DOM_RISKFRE_INT_DF = DOM_RISKFRE_INT_DF[['DD', 'RISKFRE_INT']].rename(columns={'RISKFRE_INT':'DOM_RISKFRE_INT'})
    # FORN_RISKFRE_INT_DF = FORN_RISKFRE_INT_DF[['DD', 'RISKFRE_INT']].rename(columns={'RISKFRE_INT':'FORN_RISKFRE_INT'})
    # merged_df = pd.merge(DOM_RISKFRE_INT_DF, FORN_RISKFRE_INT_DF, on=['DD'])
    # rawData = pd.merge(rawData, merged_df, on=['DD'], how='left')
    
    # # 통화선물을 위한 내재원화금리 산출(미완성)
    # CURR_ISO_CD = ["KRW", "JPY", "USD", "CNH", "EUR"]
    # conn_oracle.cursor.execute(f"SELECT CURR_ISO_CD, YD_PD_STRUCT_BAS_DYS, EXP_YD, BENCHMK_NM FROM TBCS_YD_PD_STRUCT WHERE DD='{DAY}' ")  # 
    # TBCS_YD_PD_STRUCT = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())     

    # # TBCS_YD_PD_STRUCT['ULY_PRC'] = [0] * len(TBCS_YD_PD_STRUCT)
    # for i in range(len(TBCS_YD_PD_STRUCT)):
    #     if TBCS_YD_PD_STRUCT.loc[i, 'CURR_ISO_CD'] == 'KRW':
    #         TBCS_YD_PD_STRUCT.loc[i, 'ULY_PRC'] = 1
    #     elif TBCS_YD_PD_STRUCT.loc[i, 'CURR_ISO_CD'] in CURR_ISO_CD:
    #         print(rawData(rawData['ULY_ID']==TBCS_YD_PD_STRUCT.loc[i, 'CURR_ISO_CD']))
    #         # == TBCS_YD_PD_STRUCT['CURR_ISO_CD']

    # TBCS_YD_PD_STRUCT['DOM_INT'] = [0] * len(TBCS_YD_PD_STRUCT)
    # for i in range(len(TBCS_YD_PD_STRUCT)):
    #     TBCS_YD_PD_STRUCT.loc[i, 'DOM_INT'] = calcTheoPrice.calcKRWintBySwapPoint()

    # print(rawData.columns)
    #         
    rawData = rawData.apply(howCalcTheo, axis=1)
        
    # 배당 현재가치는 TBCS_DVAL에서 가져오기
    conn_oracle.cursor.execute((f"SELECT TBCS_BYDD_DRV_ISU.DD, TBCS_BYDD_DRV_ISU.ISU_CD, TBCS_DVAL.FSETLPRC_DIV_PRSNT_VAL, TBCS_DVAL.FSETLPRC_DIV_FUT_VAL, TBCS_DVAL.FBASPRC_DIV_PRSNT_VAL, TBCS_DVAL.FBASPRC_DIV_FUT_VAL, TBCS_DVAL.AFADJ_DIV_PRSNT_VAL, TBCS_DVAL.AFADJ_DIV_FUT_VAL, TBCS_DVAL.AFEXDIV_DIV_PRSNT_VAL, TBCS_DVAL.AFEXDIV_DIV_FUT_VAL FROM TBCS_BYDD_DRV_ISU, TBCS_DVAL "
        f"where TBCS_BYDD_DRV_ISU.DD BETWEEN '{STRT_DD}' AND '{END_DD}' AND TBCS_BYDD_DRV_ISU.DD = TBCS_DVAL.DD "
        f"AND TBCS_BYDD_DRV_ISU.PROD_ID = TBCS_DVAL.PROD_ID "
        f"AND TBCS_BYDD_DRV_ISU.EXPMM = TBCS_DVAL.EXPMM"))
    rows = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    rawData = pd.merge(rawData, rows, on=['DD', 'ISU_CD'], how='left')
    rawData = rawData.apply(read_div_val, axis=1)    
        
    # RFR 금리 가져오기
    conn_oracle.cursor.execute((f"SELECT DD, ISU_CD, LSTTRD_DD, APPL_STRT_DD, APPL_END_DD, FINAL_YN, FINAL_INT, MM3_GOVBND_STRIP_INT, FWD_INT, INT_SPD, THEO_INT FROM TBCS_THEO_PRC_RFR_FUT WHERE DD BETWEEN '{STRT_DD}' AND '{END_DD}' AND PRC_TP_CD = '{PRC_TP_CD}'"))
    TBCS_THEO_PRC_RFR_FUT = pd.DataFrame(conn_oracle.cursor.fetchall(), columns=conn_oracle.get_column_names())
    rawData = pd.merge(rawData, TBCS_THEO_PRC_RFR_FUT, on=['DD', 'ISU_CD'], how='left')

    rawData = rawData.apply(calucTheoPriceFromDF, axis=1)
    rawData = rawData.reset_index(drop=True)
    rawData.to_excel(f"rawdata_theoPrcFromCSDB_{env}_{STRT_DD}_{END_DD}.xlsx")
    
    result = rawData[['DD', 'ISU_CD', 'ULY_ID', 'FORPRC_ULY_ID', 'ULY_TP_CD', 'PROD_ID', 'ISU_KOR_NM',
     'THEO_PRC_USE_TP_CD', 'RGHT_TP_CD', 'EXER_PRC', 'ULY_PRC', 'REMAIN_DYS', 'DOM_RISKFRE_INT', 'FORN_RISKFRE_INT', 'FINAL_VOLT', 'FINAL_VOLT_TP_CD', 'DIV_VAL', 'BND_YD', "STORG_COST",
      'THEO_PRC_DB', 'THEO_PRC', 'THEO_PRC_DIFF_DB_AND_PYTHON', 'HOW_CALC_CD']]
    result_columns = ["일자", "종목코드","기초자산ID", "가격용기초자산ID", "기초자산유형코드", "상품ID", "종목한글명",
     "이론가격용용도구분코드(01:정산가/증거금기준가용, 02:기준가/호가한도계산용)", "선물옵션구분코드", "행사가격", "기초자산가격", "잔존일수", "국내무위험금리", "해외무위험금리", "내재변동성", "변동성유형코드", "배당가치", "채권수익률", "금선물 g당 보관료",
      "이론가격(DB)", "이론가격(산출)", "이론가격 차이(산출-DB)", "산출방법"]    
    result.columns = result_columns
    result.to_excel(f"result_theoPrcFromCSDB_{env}_{STRT_DD}_{END_DD}.xlsx")
