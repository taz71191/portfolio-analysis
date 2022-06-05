import pickle
import pandas as pd
from portfolio_analysis.data import get_single_company_data, get_all_company_tickers, save_company_metrics, get_company_profile
from portfolio_analysis.dcf import get_irr, get_dividend_ratio, analyse_single_company_data
from portfolio_analysis.api import apikey

company_names = get_all_company_tickers(apikey)

exchange_filter = ['New York Stock Exchange Arca', 'Nasdaq Global Select',
       'New York Stock Exchange', 'Nasdaq Global Market',
       'Nasdaq Capital Market', 'BATS Exchange', 'BATS',
       'NASDAQ Global Market', 'OTC', 'Other OTC', 'Paris', 'Amsterdam',
       'Brussels', 'Lisbon', 'Toronto', 'YHD', 'EURONEXT', 'Swiss',
       'AMEX', 'MCX', 'XETRA', 'NSE', 'LSE', 'SIX', 'HKSE', 'OSE',
       'NASDAQ', 'Sao Paolo', 'TSXV', 'Frankfurt', 'HKG', 'NCM', 'MCE',
       'ASE', 'OSL', 'Oslo', 'FGI', 'Irish', 'Canadian Sec', 'NZSE',
       'Nasdaq', 'Hamburg', 'Copenhagen', 'Helsinki', 'Athens', 'Milan', 'Tokyo',
       'KSE', 'KOSDAQ', 'Stockholm', 'Mexico', 'Tel Aviv', 'IOB','Berlin','NasdaqGM', 'NasdaqGS',
       'Iceland', 'NYSE American', 'NASDAQ Capital Market', 'NSE']


filtered_company_list = company_names[company_names.exchange.isin(exchange_filter)]

irr_df = pd.DataFrame()
change_df = pd.DataFrame()
company_metrics_dict = {}
for index, company in filtered_company_list.iterrows():
    symbol = company.loc['symbol']
    print(f"running analysis for symbol :{symbol}")
    cd = get_single_company_data(symbol, apikey)
    try:
        irr = get_irr(cd, discount_rate=0.05)
        irr_df = irr_df.append(irr, ignore_index=True)
#         Add sector; 
        analysis = analyse_single_company_data(cd, money_only=False)
        analysis = analysis.sort_values('year')
        analysis.loc[:, "revenue_change"] = analysis.loc[:, "revenue"].pct_change()
        change_dict = {}
        change_dict["symbol"] = symbol
        for year in [2021, 2020, 2019, 2018, 2017]:
            if len(analysis.query(f'year == {year}')) == 1:
                year_df = analysis.query(f'year == {year}')
                change_dict[f"revenue_{year}"] = year_df.iloc[0].loc["revenue"]
                change_dict[f"revenue_change_{year}"] = year_df.iloc[0].loc["revenue_change"]
                change_dict[f"roc_{year}"] = year_df.iloc[0].loc["ROC"]
                change_dict[f"dividendsPaid_{year}"] = year_df.iloc[0].loc["dividendsPaid"]
                change_dict[f"dividend_ratio_{year}"] = year_df.iloc[0].loc["dividend_payout_ratio"]
                change_dict[f"gross_margin_{year}"] = (year_df.iloc[0].loc["revenue"] - year_df.iloc[0].loc["costOfRevenue"]) /  year_df.iloc[0].loc["revenue"]
        change_df = change_df.append(pd.Series(change_dict), ignore_index=True)
    except Exception:
        continue
    try:
        combined_metrics = save_company_metrics(cd)
        company_metrics_dict[symbol] = combined_metrics
        print("Done", symbol)
    except:
        pass


irr_merged = irr_df.merge(company_names[["symbol","exchange"]], on="symbol")
irr_merged = irr_merged.merge(change_df, on='symbol')

irr_merged.to_csv('AllCompanyAnalysis_June22.csv')