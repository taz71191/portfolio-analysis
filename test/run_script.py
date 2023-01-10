import pickle
import pandas as pd
from portfolio_analysis.data import get_single_company_data, get_all_company_tickers, save_company_metrics, get_company_profile
from portfolio_analysis.dcf import get_irr, get_dividend_ratio, analyse_single_company_data
from portfolio_analysis.api import apikey
import json

company_names = get_all_company_tickers(apikey)

# exchange_filter = [['New York Stock Exchange Arca', 'NASDAQ Global Select',
#        'New York Stock Exchange', 'NASDAQ Global Market',
#        'NASDAQ Capital Market', 'BATS', 'American Stock Exchange',
#        'Nasdaq Global Select', 'Nasdaq Global Market', 'Other OTC',
#        'Nasdaq Capital Market', 'YHD', 'BATS Exchange', 'Paris',
#        'Amsterdam', 'Brussels', 'Lisbon', 'Toronto Stock Exchange',
#        'Toronto', 'Nasdaq', 'Swiss Exchange', 'AMEX', 'MCX', 'XETRA',
#        'National Stock Exchange of India', 'NSE', 'London Stock Exchange',
#        'LSE', 'SIX', 'HKSE', 'Oslo Stock Exchange', 'OSE', 'São Paulo',
#        'SES', 'TSXV', 'Frankfurt', 'Madrid Stock Exchange', 'NCM',
#        'FTSE Index', 'Irish', 'Canadian Sec', 'Oslo', 'NZSE',
#        'Jakarta Stock Exchange', 'Vienna', 'Santiago', 'Shenzhen',
#        'Shanghai', 'Hamburg', 'Copenhagen', 'Helsinki', 'Athens', 'Milan',
#        'Tokyo', 'KSE', 'KOSDAQ', 'Stockholm Stock Exchange',
#        'Istanbul Stock Exchange', 'Taiwan', 'Mexico', 'Johannesburg',
#        'SAT', 'NASDAQ', 'Tel Aviv', 'Warsaw Stock Exchange', 'Thailand',
#        'IOB', 'Qatar', 'MCE', 'Kuala Lumpur', 'Stockholm', 'Prague',
#        'Warsaw', 'Berlin', 'Taipei Exchange', 'Saudi', 'Iceland',
#        'NYSE American', 'NasdaqGS', 'BSE', 'Dusseldorf', 'Tallinn',
#        'Munich', 'Fukuoka', 'Stuttgart', 'Dubai', 'Buenos Aires',
#        'Budapest', 'NEO', 'CCC']

# exchange_filter = ['New York Stock Exchange Arca', 'Nasdaq Global Select',
#        'New York Stock Exchange', 'Nasdaq Global Market', 'Toronto',
#        'Nasdaq Capital Market', 'NASDAQ', 'Nasdaq',  'NYSE American', 'NASDAQ Capital Market', 'NSE']

exchange_filter = ['New York Stock Exchange Arca', 'Nasdaq Global Select',
       'New York Stock Exchange', 'Nasdaq Global Market', 'Toronto', 
       'TSXV','ASE','London Stock Exchange',
       'Nasdaq Capital Market', 'NASDAQ', 'Nasdaq',  'NYSE American', 'NASDAQ Capital Market', 'NSE','Canadian Sec','National Stock Exchange of India','BSE']

exchange_filter = ['Other OTC']
filename = 'jkt_asx_companies.csv'
exception_file = 'test/exceptions.json'

df = pd.read_csv(filename).iloc[:,1:]
# df = pd.DataFrame()
filtered_company_list = company_names[company_names.exchange.isin(exchange_filter)]
# filtered_company_list.query("symbol == 'KEL.DE'")
# 
irr_df = df
change_df = pd.DataFrame()
company_metrics_dict = {}
with open(exception_file, 'r') as openfile:
 
    # Reading from json file
    exceptions = json.load(openfile)
# cutoff= int(input("number of companies:"))
cutoff = 10000000000
breakpoint()
for index, company in filtered_company_list.iterrows():
    symbol = company.loc['symbol']
    if symbol in irr_df.symbol.unique():
        continue
    print(f"running analysis for symbol :{symbol}")
    cd = get_single_company_data(symbol, apikey)
    # if len(irr_df) > cutoff:
    #     break
    try:
        irr = get_irr(cd, symbol, discount_rate=0.05)
        irr_df = irr_df.append(irr, ignore_index=True)
        analysis = analyse_single_company_data(cd, money_only=False)
        analysis = analysis.sort_values('year')
        analysis.loc[:, "revenue_change"] = analysis.loc[:, "revenue"].pct_change()
        change_dict = {}
        change_dict["symbol"] = symbol
        for year in [2022, 2021, 2020, 2019, 2018, 2017]:
            if len(analysis.query(f'year == {year}')) == 1:
                year_df = analysis.query(f'year == {year}')
                change_dict[f"revenue_{year}"] = year_df.iloc[0].loc["revenue"]
                change_dict[f"revenue_change_{year}"] = year_df.iloc[0].loc["revenue_change"]
                change_dict[f"roc_{year}"] = year_df.iloc[0].loc["ROC"]
                change_dict[f"dividendsPaid_{year}"] = year_df.iloc[0].loc["dividendsPaid"]
                change_dict[f"dividend_ratio_{year}"] = year_df.iloc[0].loc["dividend_payout_ratio"]
                change_dict[f"gross_margin_{year}"] = (year_df.iloc[0].loc["revenue"] - year_df.iloc[0].loc["costOfRevenue"]) /  year_df.iloc[0].loc["revenue"]
        change_df = change_df.append(pd.Series(change_dict), ignore_index=True)
        print("% Complete", round((len(irr_df)/len(filtered_company_list))*100,4), "%")
    except Exception:
        print("Exception", {symbol})
        exceptions["exceptions"] += [symbol]
    try:
        combined_metrics = save_company_metrics(cd)
        company_metrics_dict[symbol] = combined_metrics
        print("Done", symbol)
    except:
        pass
breakpoint()

irr_merged = irr_df.merge(company_names[["symbol","exchange"]], on="symbol")
# irr_merged = irr_merged.merge(change_df, on='symbol')

irr_merged.to_csv(filename)

with open(exception_file, "w") as outfile:
    json.dump(exceptions, outfile)