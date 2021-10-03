import numpy as np
import pandas as pd
from requests import api
import streamlit as st
import plotly.express as px

# https://www.youtube.com/watch?v=0ESc1bh3eIg&ab_channel=PartTimeLarry

from portfolio_analysis.api import apikey
from portfolio_analysis.data import (
    get_all_company_tickers,
    get_balance_statement,
    get_company_profile,
    get_financial_ratios,
    get_income_statement,
    get_insider_trading,
    get_market_cap,
    get_company_outlook,
    get_stock_news,
    get_social_sentiment,
    get_stock_peers
)
from portfolio_analysis.dcf import get_irr




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


def run_analysis(company_names, exchange, apikey):
    month = pd.Timestamp.now().month_name()
    try:
        irr_df = pd.read_csv(f"./excels/{exchange}_{month}.csv")
    except FileNotFoundError:
        failed_companies = pd.DataFrame()
        irr_df = pd.DataFrame()
        for index, company in company_names[
            company_names.exchange == exchange
            ].iterrows():
            symbol = company.loc["symbol"]
            company_data = get_single_company_data(symbol, apikey)
            try:
                irr = get_irr(company, company_data["IS"], company_data["Profile"], company_data["BS"], company_data["MC"], company_data["CFR"])
            except KeyError:
                failed_companies = failed_companies.append(company, ignore_index=True)
                continue
            irr_df = irr_df.append(irr, ignore_index=True)
        failed_companies.to_csv(f"./excels/{exchange}_{month}_failed.csv", index=False,)
        irr_df.to_csv(f"./excels/{exchange}_{month}.csv", index=False,)
    
    return irr_df

# https://www.datapine.com/blog/financial-graphs-and-charts-examples/

def analysis_single_company_data(company_data):
    IS = company_data["IS"]
    profile = company_data["Profile"]
    BS = company_data["BS"]
    MC = company_data["MC"]
    CFR = company_data["CFR"]
    # EPS is the net income divided by the weighted average number of common shares issued
    EPS = IS.loc[: ,["date", "eps"]]
    # ROE = Net Income / Shareholder Equity
    # Shareholder Equity = Total Assets - Liabilities

    # Margin of Profits: Operating Income / Sales
    IS["MOP"] = IS.loc[:, "operatingIncome"] / IS.loc[:, "revenue"]
    # Quick assets: Current assets - Inventory / Current Liabilities
    BS["QA"] = (BS.loc[:, "totalCurrentAssets"] - BS.loc[:, "inventory"]) / BS.loc[
        :, "totalCurrentLiabilities"
    ]
    IS['year'] = IS['date'].apply(lambda x: pd.Timestamp(x).year)
    BS['year'] = BS['date'].apply(lambda x: pd.Timestamp(x).year)
     
    combined_data = IS.merge(BS, on='year')
    combined_data["ROE"] = combined_data['netIncome'] / (combined_data["totalAssets"] - combined_data["totalLiabilities"])
    return combined_data

def run_dashboard():
    st.title("RoboStock 0.0.01")
    option = st.sidebar.selectbox("Select dashboard", ['Stock Screener', 'Stock DeepDive'])
    st.header(option)

    if option == 'Stock Screener':

        # Get all the tickers
        company_names = get_all_company_tickers(apikey)
        # Pick an exchange to run analysus on
        # exchanges = company_names.exchange.unique()
        exchanges = ["New York Stock Exchange", "NASDAQ", "AMEX", "EURONEXT", "Toronto"]

        selected_exchange = st.selectbox("Pick an exchange to analyze", exchanges)
        st.write("You selected:", selected_exchange)

        try:
            irr_df = run_analysis(company_names, selected_exchange, apikey)
            irr_df["irr"] = irr_df["irr"].fillna(-100)
            irr_df["eps_roc"] = irr_df["eps_roc"].fillna(-100)
            irr_filter = st.sidebar.slider("Filter for Internal Rate of Return", value=[4, int(irr_df.irr.max())])
            st.sidebar.write("irr filter", irr_filter)
            eps_roc_filter = st.sidebar.slider("Filter for EPS rate of Change", value=[int(irr_df.eps_roc.min()), int(irr_df.eps_roc.max())])
            st.sidebar.write("eps_roc_filter", eps_roc_filter)
            filtered_df = irr_df[(irr_df.irr >= irr_filter[0]) & (irr_df.irr <= irr_filter[1]) & (irr_df.eps_roc >= eps_roc_filter[0]) & (irr_df.eps_roc <= eps_roc_filter[1])]
            filtered_df
            selected_company = st.sidebar.selectbox("Pick a company to analyse", company_names[company_names.symbol.isin(filtered_df['symbol'].to_list())].sort_values(by='name')['name'])
            drop_down = company_names[company_names.name == selected_company].iloc[0]['symbol']
            st.subheader(irr_df[irr_df.symbol == drop_down].iloc[0]["name"])
            text_input = st.sidebar.text_input("Enter a ticker to analyse")
            if text_input:
                drop_down = text_input
            company_data = get_single_company_data(drop_down, apikey)
            company_data = analysis_single_company_data(company_data)
            insider_trading = get_insider_trading(drop_down, apikey)
            ratios = get_company_outlook(drop_down, apikey, bucket='ratios')
            ratios
            fig = px.line(company_data, x='year', y=['MOP','QA','eps', 'ROE'])
            st.plotly_chart(fig)
            st.write('Insider Trades')
            insider_trading[['transactionDate','typeOfOwner','acquistionOrDisposition','securitiesTransacted','securityName']]
        except Exception as e:
            print(e)

        try:
            ss = get_social_sentiment(drop_down, apikey)
            st.write('Social Sentiment')
            ss['date'] = ss['date'].apply(lambda x: pd.Timestamp(x).date())
            ss = ss.groupby('date').agg({'absoluteIndex': np.mean, 'relativeIndex': np.mean, 'generalPerception': np.mean, 'sentiment': np.mean})
            ss
        except KeyError:
            "No social sentiment data"
        #   ss.columns
        
        sp = get_stock_peers(drop_down, apikey)
        compare_to = st.sidebar.selectbox("Pick a company to compare to", company_names[company_names.symbol.isin(sp['peersList'].iloc[0])]['name'])
        st.subheader(compare_to)
        compare_to_company_data = get_single_company_data(compare_to, apikey)
        compare_to_company_data = analysis_single_company_data(compare_to_company_data)
        fig2 = px.line(compare_to_company_data, x='year', y=['MOP','QA','eps', 'ROE'])
        st.plotly_chart(fig2)
        try:
            st.subheader(irr_df[irr_df.symbol == drop_down].iloc[0]["name"])
            company_data = get_single_company_data(drop_down, apikey)
            company_data = analysis_single_company_data(company_data)
            stock_news = get_stock_news(company_data)
            fig = px.line(company_data, x='year', y=['MOP','QA','eps', 'ROE'])
            st.plotly_chart(fig)
            stock_news
        except Exception as e:
            """
            There are no companies that match your current selection
            """

    elif option == 'Stock DeepDive':
        company_names = get_all_company_tickers(apikey)
        ticker = st.sidebar.text_input("Enter a ticker to analyse", value='AAPL')
        

        st.subheader(ticker.upper())
        company = company_names[
            company_names.symbol == ticker
            ]
        
        company_data = get_single_company_data(ticker, apikey)
        for index, comp in company.iterrows():
            irr = get_irr(comp, company_data["IS"], company_data["Profile"], company_data["BS"], company_data["MC"], company_data["CFR"])
        
        st.write(irr.to_dict())
        company_data = analysis_single_company_data(company_data)
        
        
        fig = px.line(company_data, x='year', y=['MOP','QA','eps', 'ROE'])
        st.plotly_chart(fig)

        try:
            ratios = get_company_outlook(ticker, apikey, bucket='ratios')
            ratios
        except:
            'No company ratios'

        try:
            insider_trading = get_insider_trading(ticker, apikey)
            st.write('Insider Trades')
            insider_trading[['transactionDate','typeOfOwner','acquistionOrDisposition','securitiesTransacted','securityName']]

        except:
            print('No Insider data')
        
        
        try:
            ss = get_social_sentiment(ticker, apikey)
            st.write('Social Sentiment')
            ss['date'] = ss['date'].apply(lambda x: pd.Timestamp(x).date())
            ss = ss.groupby('date').agg({'absoluteIndex': np.mean, 'relativeIndex': np.mean, 'generalPerception': np.mean, 'sentiment': np.mean})
            ss
        except KeyError:
            "No social sentiment data"
        #   ss.columns
        
        try:
            sp = get_stock_peers(ticker, apikey)
            compare_to = st.sidebar.selectbox("Pick a company to compare to", company_names[company_names.symbol.isin(sp['peersList'].iloc[0])]['name'])
            st.subheader(compare_to)
            compare_to_company_data = get_single_company_data(compare_to, apikey)
            compare_to_company_data = analysis_single_company_data(compare_to_company_data)
            fig2 = px.line(compare_to_company_data, x='year', y=['MOP','QA','eps', 'ROE'])
            st.plotly_chart(fig2)
        except:
            print('No peers data')

if __name__ == "__main__":
    run_dashboard()
