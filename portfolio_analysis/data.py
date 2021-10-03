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
    Fetch income statement.
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


def get_financial_ratios(symbol, apikey=""):
    """
    financial ratios
    """
    url = (
        f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={apikey}"
    )
    financial_ratio = pd.json_normalize(requests.get(url).json())
    return financial_ratio


def get_market_cap(symbol, apikey=""):
    """
    financial ratios
    """
    url = f"https://financialmodelingprep.com/api/v3/market-capitalization/{symbol}?apikey={apikey}"
    financial_ratio = pd.json_normalize(requests.get(url).json())
    return financial_ratio

def get_company_outlook(symbol, apikey ="", bucket='ratios'):
    url = f"https://financialmodelingprep.com/api/v4/company-outlook?symbol={symbol}&apikey={apikey}"
    company_outlook = requests.get(url).json()
    return pd.json_normalize(company_outlook[bucket])

def get_stock_news(symbol, apikey=""):
    url = f"https://financialmodelingprep.comapi/v3/stock_news?tickers={symbol}&limit=50&apikey={apikey}"
    stock_news = pd.json_normalize(requests.get(url).json())
    return stock_news

def get_social_sentiment(symbol, apikey =""):
    url = f"https://financialmodelingprep.com/api/v4/social-sentiment?symbol={symbol}&apikey={apikey}"
    social_sentiment = pd.json_normalize(requests.get(url).json())
    return social_sentiment

def get_stock_peers(symbol, apikey =""):
    url = f"https://financialmodelingprep.com/api/v4/stock_peers?symbol={symbol}&apikey={apikey}"
    stock_peers = pd.json_normalize(requests.get(url).json())
    return stock_peers

def get_single_company_data(symbol, apikey):
    IS = get_income_statement(symbol, period="annual", apikey=apikey)
    profile = get_company_profile(symbol, apikey=apikey)
    BS = get_balance_statement(symbol, apikey=apikey)
    MC = get_market_cap(symbol=symbol, apikey=apikey)
    CFR = get_financial_ratios(symbol=symbol, apikey=apikey)
    return {
        "IS":IS,
        "Profile": profile,
        "BS":BS,
        "MC": MC,
        "CFR": CFR
    }

if __name__ == "__main__":
    """quick test, to use run data.py directly"""

    ticker = "AAPL"
    apikey = "<DEMO>"
    data = get_cashflow_statement(ticker=ticker, apikey=apikey)
    print(data)
