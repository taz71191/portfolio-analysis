"""
Utilizing financialmodelingprep.com for their free-endpoint API
to gather company financials.
NOTE: Some code taken directly from their documentation. See: https://financialmodelingprep.com/developer/docs/. 
"""

import json
from urllib.request import urlopen

import pandas as pd
import requests


def get_api_url(requested_data, ticker, period, apikey):
    if period == "annual":
        url = "https://financialmodelingprep.com/api/v3/{requested_data}/{ticker}?limit=400&apikey={apikey}".format(
            requested_data=requested_data, ticker=ticker, apikey=apikey
        )
    elif period == "quarter":
        url = "https://financialmodelingprep.com/api/v3/{requested_data}/{ticker}?period=quarter&apikey={apikey}".format(
            requested_data=requested_data, ticker=ticker, apikey=apikey
        )
    else:
        raise ValueError("invalid period " + str(period))
    return url


def get_jsonparsed_data(url):
    """
    Fetch url, return parsed json.
    args:
        url: the url to fetch.

    returns:
        parsed json
    """
    df = pd.json_normalize(requests.get(url).json())
    return df


def get_EV_statement(ticker, period="annual", apikey=""):
    """
    Fetch EV statement, with details like total shares outstanding, from FMP.com
    args:
        ticker: company tickerr
    returns:
        parsed EV statement
    """
    url = get_api_url("enterprise-value", ticker=ticker, period=period, apikey=apikey)
    return get_jsonparsed_data(url)


#! TODO: maybe combine these with argument flag for which statement, seems pretty redundant tbh
def get_income_statement(ticker, period="annual", apikey=""):
    """
    Fetch income statement.
    args:
        ticker: company ticker.
        period: annual default, can fetch quarterly if specified.
    returns:
        parsed company's income statement
    """
    url = get_api_url("/income-statement", ticker=ticker, period=period, apikey=apikey)
    return get_jsonparsed_data(url)


def get_company_profile(ticker, period="annual", apikey=""):
    """
    Fetch company profile.
    args:
        ticker: company ticker.
        period: annual default, can fetch quarterly if specified.
    returns:
        parsed company's income statement
    """
    url = get_api_url("profile", ticker=ticker, period=period, apikey=apikey)
    return get_jsonparsed_data(url)


def get_cashflow_statement(ticker, period="annual", apikey=""):
    """
    Fetch cashflow statement.
    args:
        ticker: company ticker.
        period: annual default, can fetch quarterly if specified.
    returns:
        parsed company's cashflow statement
    """
    url = get_api_url(
        "financials/cash-flow-statement", ticker=ticker, period=period, apikey=apikey
    )
    return get_jsonparsed_data(url)


def get_balance_statement(ticker, period="annual", apikey=""):
    """
    Fetch balance sheet statement.
    args:
        ticker: company ticker.
        period: annual default, can fetch quarterly if specified.
    returns:
        parsed company's balance sheet statement
    """
    url = get_api_url(
        "balance-sheet-statement", ticker=ticker, period=period, apikey=apikey
    )
    return get_jsonparsed_data(url)


def get_stock_price(ticker, apikey=""):
    """
    Fetches the stock price for a ticker
    args:
        ticker

    returns:
        {'symbol': ticker, 'price': price}
    """
    url = "https://financialmodelingprep.com/api/v3/stock/real-time-price/{ticker}?apikey={apikey}".format(
        ticker=ticker, apikey=apikey
    )
    return get_jsonparsed_data(url)


def get_batch_stock_prices(tickers, apikey=""):
    """
    Fetch the stock prices for a list of tickers.
    args:
        tickers: a list of  tickers........

    returns:
        dict of {'ticker':  price}
    """
    prices = {}
    for ticker in tickers:
        prices[ticker] = get_stock_price(ticker=ticker, apikey=apikey)["price"]

    return prices


def get_historical_share_prices(ticker, dates, apikey=""):
    """
    Fetch the stock price for a ticker at the dates listed.
    args:
        ticker: a ticker.
        dates: a list of dates from which to fetch close price.
    returns:
        {'date': price, ...}
    """
    prices = {}
    for date in dates:
        date_start, date_end = date[0:8] + str(int(date[8:]) - 2), date
        url = "https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={date_start}&to={date_end}&apikey={apikey}".format(
            ticker=ticker, date_start=date_start, date_end=date_end, apikey=apikey
        )
        try:
            prices[date_end] = get_jsonparsed_data(url)["historical"][0]["close"]
        except IndexError:
            #  RIP nested try catch, so many issues with dates just try a bunch and get within range of earnings release
            try:
                prices[date_start] = get_jsonparsed_data(url)["historical"][0]["close"]
            except IndexError:
                print(date + " ", get_jsonparsed_data(url))

    return prices


def get_all_company_tickers(apikey="", exchange=None):
    """
    Fetch all companys tickers
    """
    url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={apikey}"
    all_company_tickers = pd.json_normalize(requests.get(url).json())
    if exchange is None:
        return all_company_tickers
    else:
        return all_company_tickers[all_company_tickers.exchange == exchange]


def get_sp500_tickers(apikey=""):
    """
    Fetch all companys tickers
    """
    url = f"https://financialmodelingprep.com/api/v3/sp500_constituent?apikey={apikey}"
    sp500_tickers = pd.json_normalize(requests.get(url).json())
    return sp500_tickers


def get_insider_trading(symbol, apikey=""):
    """
    Fetch insiderstrades
    """
    url = f"https://financialmodelingprep.com/api/v4/insider-trading?symbol={symbol}&limit=100&apikey={apikey}"
    insider_trades = pd.json_normalize(requests.get(url).json())
    return insider_trades


def get_cash_flow_statement(symbol, period="annual",apikey=""):
    """
    get cash flow statement
    """
    if period == "annual":
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{symbol}?apikey={apikey}"
    else:
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{symbol}?period=quarter&apikey={apikey}"
    cashflow = pd.json_normalize(requests.get(url).json())
    return cashflow


def get_financial_ratios(symbol, period="annual", apikey=""):
    """
    financial ratios
    """
    if period == "annual":
        url = (
            f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={apikey}"
        )
    else:
        url = (
            f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?period=quarter&apikey={apikey}"
        )
    financial_ratio = pd.json_normalize(requests.get(url).json())
    return financial_ratio


def get_market_cap(symbol, period="annual", apikey=""):
    """
    market_cap
    """
    if period == "annual":
        url = f"https://financialmodelingprep.com/api/v3/market-capitalization/{symbol}?apikey={apikey}"
    else:
        url = f"https://financialmodelingprep.com/api/v3/market-capitalization/{symbol}?period=quarter&apikey={apikey}"
    financial_ratio = pd.json_normalize(requests.get(url).json())
    return financial_ratio


def get_company_outlook(symbol, apikey="", bucket="ratios"):
    url = f"https://financialmodelingprep.com/api/v4/company-outlook?symbol={symbol}&apikey={apikey}"
    company_outlook = requests.get(url).json()
    return pd.json_normalize(company_outlook[bucket])


def get_stock_news(symbol, apikey=""):
    url = f"https://financialmodelingprep.comapi/v3/stock_news?tickers={symbol}&limit=50&apikey={apikey}"
    stock_news = pd.json_normalize(requests.get(url).json())
    return stock_news


def get_social_sentiment(symbol, apikey=""):
    url = f"https://financialmodelingprep.com/api/v4/social-sentiment?symbol={symbol}&apikey={apikey}"
    social_sentiment = pd.json_normalize(requests.get(url).json())
    return social_sentiment


def get_stock_peers(symbol, apikey=""):
    url = f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={symbol}&apikey={apikey}"
    stock_peers = pd.json_normalize(requests.get(url).json())
    return stock_peers

def get_tickers_with_financials(apikey=""):
    url = f"https://financialmodelingprep.com/api/v3/financial-statement-symbol-lists?apikey={apikey}"
    tickers = requests.get(url).json()
    return tickers

def industry_sector_performance(apikey=""):
    url = f"https://financialmodelingprep.com/api/v3/historical-sectors-performance?apikey={apikey}"
    industry_sector_performance = requests.get(url).json()
    return pd.json_normalize(industry_sector_performance)
# https://opendata.gov.je/dataset/average-earnings-index/resource/ae19c45b-91c7-4636-9c4a-10f939e767e5

def historical_daily_price(symbol, apikey=""):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={apikey}"
    historical_daily_price = requests.get(url).json()
    return pd.json_normalize(historical_daily_price["historical"])

def full_financial_statement(symbol, apikey=""):
    url = f"https://financialmodelingprep.com/api/v3/financial-statement-full-as-reported/{symbol}?apikey={apikey}"
    print(url)
    historical_daily_price = requests.get(url).json()
    return pd.json_normalize(historical_daily_price["historical"])

def historical_prices(symbol, days=5, apikey=""):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries={days}&apikey={apikey}"
    print(url)
    historical_prices = requests.get(url).json()
    return pd.json_normalize(historical_prices)

def get_single_company_data(symbol, apikey, period='annual', money_only=False):
    if period == 'annual':
        if money_only:
            IS = get_income_statement(symbol, period="annual", apikey=apikey)
            BS = get_balance_statement(symbol, apikey=apikey)
        else:
            IS = get_income_statement(symbol, period="annual", apikey=apikey)
            profile = get_company_profile(symbol, apikey=apikey)
            BS = get_balance_statement(symbol, apikey=apikey)
            MC = get_market_cap(symbol=symbol, apikey=apikey)
            CFR = get_financial_ratios(symbol=symbol, apikey=apikey)
            CFS = get_cash_flow_statement(symbol=symbol, apikey=apikey)
            # HP = historical_daily_price(symbol=symbol, apikey=apikey)
            # FFS = full_financial_statement(symbol=symbol, apikey=apikey)
    elif period == 'quarter':
        IS = get_income_statement(symbol, period="quarter", apikey=apikey)
        profile = get_company_profile(symbol, period="quarter", apikey=apikey)
        BS = get_balance_statement(symbol, period="quarter", apikey=apikey)
        MC = get_market_cap(symbol=symbol, period="quarter", apikey=apikey)
        CFR = get_financial_ratios(symbol=symbol,period="quarter", apikey=apikey)
        CFS = get_cash_flow_statement(symbol=symbol,period="quarter", apikey=apikey)
        # HP = historical_daily_price(symbol=symbol, apikey=apikey)
    else:
        print("Invalid Period")
        return

    if money_only:
        return {"IS": IS, "BS": BS}
    else:
        return {"IS": IS, "profile": profile, "BS": BS, "MC": MC, "CFR": CFR, "CFS": CFS}

def aggregate_to_quarter(df, agg=True, statistic="mean"):
    df["date"] = pd.to_datetime(df.date)
    df["year"] = df.date.dt.year
    df["quarter"] = df.date.dt.quarter
    if agg:
        df = df.groupby(["year","quarter"]).agg(statistic).reset_index()
    return df

def save_company_metrics(company_data_dict, ):
    IS = company_data_dict["IS"]
    BS = company_data_dict["BS"]
    # HP = company_data_dict["HP"]
    CFS = company_data_dict["CFS"]

    IS_metric = IS.loc[:, ["date","eps","revenue","costOfRevenue","operatingExpenses","netIncome","interestExpense"]].copy()
    IS_metric = aggregate_to_quarter(IS_metric)
    BS_metric = BS.loc[:, ["date","propertyPlantEquipmentNet","totalCurrentAssets","inventory","netReceivables","otherCurrentAssets","propertyPlantEquipmentNet","totalDebt"]]
    BS_metric = aggregate_to_quarter(BS_metric)
    # HP_metric = HP.loc[:, ["date","volume", "close"]]
    # HP_metric = aggregate_to_quarter(HP_metric, agg=True)
    CFS = HP.loc[:, ["date","volume", "close"]]
    combined = IS_metric.merge(BS_metric, on=["year","quarter"], how="outer").merge(HP_metric, on=["year","quarter"], how="outer").merge(HP_metric, on=["year","quarter"], how="outer")
    return combined



if __name__ == "__main__":
    """quick test, to use run data.py directly"""

    ticker = "AAPL"
    apikey = "<DEMO>"
    data = get_cashflow_statement(ticker=ticker, apikey=apikey)
    print(data)
