import base64
import io

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account
from requests import api

from portfolio_analysis.api import apikey
from portfolio_analysis.data import (
    get_all_company_tickers,
    get_balance_statement,
    get_company_outlook,
    get_company_profile,
    get_financial_ratios,
    get_income_statement,
    get_insider_trading,
    get_market_cap,
    get_social_sentiment,
    get_stock_news,
    get_stock_peers,
)
from portfolio_analysis.dcf import get_irr

# https://www.youtube.com/watch?v=0ESc1bh3eIg&ab_channel=PartTimeLarry


def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(
        csv.encode()
    ).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="myfilename.csv">Download csv file</a>'
    return href


def get_single_company_data(symbol, apikey):
    IS = get_income_statement(symbol, period="annual", apikey=apikey)
    profile = get_company_profile(symbol, apikey=apikey)
    BS = get_balance_statement(symbol, apikey=apikey)
    MC = get_market_cap(symbol=symbol, apikey=apikey)
    CFR = get_financial_ratios(symbol=symbol, apikey=apikey)
    return {"IS": IS, "Profile": profile, "BS": BS, "MC": MC, "CFR": CFR}


def run_analysis(company_names, exchange, apikey):
    month = pd.Timestamp.now().month_name()
    try:
        if exchange == "New York Stock Exchange":
            exchange = "NYSE"
        source_blob_name = f"{exchange}_{month}.csv"
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        data = blob.download_as_string()
        irr_df = pd.read_csv(io.BytesIO(data))
    except FileNotFoundError:
        failed_companies = pd.DataFrame()
        irr_df = pd.DataFrame()
        for index, company in company_names[
            company_names.exchange == exchange
        ].iterrows():
            symbol = company.loc["symbol"]
            company_data = get_single_company_data(symbol, apikey)
            try:
                irr = get_irr(
                    company,
                    company_data["IS"],
                    company_data["Profile"],
                    company_data["BS"],
                    company_data["MC"],
                    company_data["CFR"],
                )
            except KeyError as e:
                failed_companies = failed_companies.append(company, ignore_index=True)
                print(e)
                continue
            irr_df = irr_df.append(irr, ignore_index=True)
        failed_companies.to_csv(
            f"./excels/{exchange}_{month}_failed.csv",
            index=False,
        )
        irr_df.to_csv(
            f"./excels/{exchange}_{month}.csv",
            index=False,
        )

    return irr_df


def get_data_from_cloud(filename):
    bucket_name = "robostock"
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    storage_client = storage.Client(credentials=credentials)

    source_blob_name = filename
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    data = blob.download_as_string()
    irr_df = pd.read_csv(io.BytesIO(data))
    return irr_df


# https://www.datapine.com/blog/financial-graphs-and-charts-examples/


def analysis_single_company_data(company_data):
    IS = company_data["IS"]
    profile = company_data["Profile"]
    BS = company_data["BS"]
    MC = company_data["MC"]
    CFR = company_data["CFR"]
    # EPS is the net income divided by the weighted average number of common shares issued
    EPS = IS.loc[:, ["date", "eps"]]
    # ROE = Net Income / Shareholder Equity
    # Shareholder Equity = Total Assets - Liabilities

    # Margin of Profits: Operating Income / Sales
    IS["MOP"] = IS.loc[:, "operatingIncome"] / IS.loc[:, "revenue"]
    # Quick assets: Current assets - Inventory / Current Liabilities
    BS["QA"] = (BS.loc[:, "totalCurrentAssets"] - BS.loc[:, "inventory"]) / BS.loc[
        :, "totalCurrentLiabilities"
    ]
    IS["year"] = IS["date"].apply(lambda x: pd.Timestamp(x).year)
    BS["year"] = BS["date"].apply(lambda x: pd.Timestamp(x).year)

    combined_data = IS.merge(BS, on="year")
    combined_data["ROE"] = combined_data["netIncome"] / (
        combined_data["totalAssets"] - combined_data["totalLiabilities"]
    )
    EBIT = (
        combined_data["revenue"]
        - combined_data["costOfRevenue"]
        - combined_data["operatingExpenses"]
    )
    # IS.loc[0, "netIncome"] + IS.loc[0, "incomeTaxExpense"] + IS.loc[0,"interestExpense"]

    NetWorkingCapital = (
        combined_data["totalCurrentAssets"] - combined_data["totalCurrentLiabilities"]
    )
    NetFixedAssets = combined_data["propertyPlantEquipmentNet"]

    combined_data["ROC"] = EBIT / (NetWorkingCapital + NetFixedAssets)

    return combined_data


def run_dashboard():
    st.title("RoboStock 0.0.1")
    option = st.sidebar.selectbox(
        "Select dashboard", ["Stock Screener", "Stock DeepDive"]
    )
    st.header(option)

    if option == "Stock Screener":

        # Get all the tickers
        company_names = get_all_company_tickers(apikey)
        # Pick an exchange to run analysus on
        # exchanges = company_names.exchange.unique()
        try:
            irr_df = get_data_from_cloud(filename="AllCompanies_October.csv")
        except Exception as e:
            st.write(e)

        irr_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        irr_df = irr_df.sort_values("ROC", ascending=False)
        irr_df["ROC_rank"] = [x for x in range(1, len(irr_df) + 1)]
        irr_df = irr_df.sort_values("EarningsYield", ascending=False)
        irr_df["EarningsYield_rank"] = [x for x in range(1, len(irr_df) + 1)]
        irr_df["Total_rank"] = irr_df["ROC_rank"] + irr_df["EarningsYield_rank"]
        irr_df = irr_df.sort_values("Total_rank")
        mcap_filter = st.sidebar.number_input(
            "Filter for MarketCap in billion$", min_value=0.0, max_value=100.0
        )
        st.sidebar.write("Min Marcap cap $", mcap_filter, "Billion")
        roc_filter = st.sidebar.number_input(
            "Filter for Return on Capital", min_value=0.0, max_value=1.0
        )
        st.sidebar.write("Min Return On Capital %", roc_filter)
        pe_filter = st.sidebar.number_input(
            "Filter for P/E", min_value=0.0, max_value=100.0
        )
        st.sidebar.write("Min P/E", pe_filter)
        irr_df = irr_df.merge(company_names[["symbol", "exchange"]], on="symbol")
        exchanges = list(irr_df["exchange"].unique())
        exchanges.insert(0, "None")
        exchange_filter = st.sidebar.selectbox(
            "Pick an exchange to filter on", exchanges
        )
        exclude_industries = [
            "Banks—Diversified",
            "Capital Markets",
            "Banks—Regional",
            "Credit Services",
            "Insurance—Specialty",
            "Asset Management",
            "Insurance—Diversified",
            "Insurance—Reinsurance",
            "Insurance—Property & Casualty",
            "Insurance—Life",
            "Mortgage Finance"
        ]

        cols = st.sidebar.multiselect(
            "Exclude Industries", irr_df.industry.unique(), default=exclude_industries
        )
        filtered_df = irr_df[
            (irr_df.MCap >= mcap_filter * (10 ** 9))
            & (irr_df.ROC >= roc_filter)
            & (irr_df.PE >= pe_filter)
        ]
        if exchange_filter == "None":
            filtered_df[~filtered_df.industry.isin(cols)]
        else:
            filtered_df = filtered_df[
                (filtered_df.exchange == exchange_filter)
                & ~(filtered_df.industry.isin(cols))
            ]
            filtered_df
        st.sidebar.markdown(
            get_table_download_link(filtered_df), unsafe_allow_html=True
        )
        filtered_company_names = company_names[
            (company_names.symbol.isin(filtered_df["symbol"].to_list()))
            & (company_names.name != "")
        ].sort_values(by="name")["name"]
        selected_company = st.sidebar.selectbox(
            "Pick a company to analyse", filtered_company_names
        )
        drop_down = company_names[company_names.name == selected_company].iloc[0][
            "symbol"
        ]
        st.subheader(irr_df[irr_df.symbol == drop_down].iloc[0]["name"])
        text_input = st.sidebar.text_input("Enter a ticker to analyse")
        if text_input:
            drop_down = text_input
        company_data = get_single_company_data(drop_down, apikey)
        company_data = analysis_single_company_data(company_data)
        insider_trading = get_insider_trading(drop_down, apikey)
        ratios = get_company_outlook(drop_down, apikey, bucket="ratios")
        ratios
        fig = px.line(company_data, x="year", y=["MOP", "QA", "ROE", "ROC"])
        st.plotly_chart(fig)
        st.write("Insider Trades")
        insider_trading[
            [
                "transactionDate",
                "typeOfOwner",
                "acquistionOrDisposition",
                "securitiesTransacted",
                "securityName",
            ]
        ]
        # except Exception as e:
        #     print(e)

        try:
            ss = get_social_sentiment(drop_down, apikey)
            st.write("Social Sentiment")
            ss["date"] = ss["date"].apply(lambda x: pd.Timestamp(x).date())
            ss = ss.groupby("date").agg(
                {
                    "absoluteIndex": np.mean,
                    "relativeIndex": np.mean,
                    "generalPerception": np.mean,
                    "sentiment": np.mean,
                }
            )
            ss
        except KeyError:
            "No social sentiment data"
        #   ss.columns

        sp = get_stock_peers(drop_down, apikey)
        compare_to = st.sidebar.selectbox(
            "Pick a company to compare to",
            company_names[company_names.symbol.isin(sp["peersList"].iloc[0])]["name"],
        )
        st.subheader(compare_to)
        compare_to_company_data = get_single_company_data(compare_to, apikey)
        compare_to_company_data = analysis_single_company_data(compare_to_company_data)
        fig2 = px.line(compare_to_company_data, x="year", y=["MOP", "QA", "eps", "ROE"])
        st.plotly_chart(fig2)
        try:
            st.subheader(irr_df[irr_df.symbol == drop_down].iloc[0]["name"])
            company_data = get_single_company_data(drop_down, apikey)
            company_data = analysis_single_company_data(company_data)
            stock_news = get_stock_news(company_data)
            fig = px.line(company_data, x="year", y=["MOP", "QA", "eps", "ROE"])
            st.plotly_chart(fig)
            stock_news
        except Exception as e:
            """
            There are no companies that match your current selection
            """

    elif option == "Stock DeepDive":
        company_names = get_all_company_tickers(apikey)
        ticker = st.sidebar.text_input("Enter a ticker to analyse", value="AAPL")

        st.subheader(ticker.upper())
        company = company_names[company_names.symbol == ticker]

        company_data = get_single_company_data(ticker, apikey)
        for index, comp in company.iterrows():
            irr = get_irr(
                comp,
                company_data["IS"],
                company_data["Profile"],
                company_data["BS"],
                company_data["MC"],
                company_data["CFR"],
            )

        st.write(irr.to_dict())
        company_data = analysis_single_company_data(company_data)

        fig = px.line(company_data, x="year", y=["MOP", "QA", "eps", "ROE"])
        st.plotly_chart(fig)

        try:
            ratios = get_company_outlook(ticker, apikey, bucket="ratios")
            ratios
        except:
            "No company ratios"

        try:
            insider_trading = get_insider_trading(ticker, apikey)
            st.write("Insider Trades")
            insider_trading[
                [
                    "transactionDate",
                    "typeOfOwner",
                    "acquistionOrDisposition",
                    "securitiesTransacted",
                    "securityName",
                ]
            ]

        except:
            print("No Insider data")

        try:
            ss = get_social_sentiment(ticker, apikey)
            st.write("Social Sentiment")
            ss["date"] = ss["date"].apply(lambda x: pd.Timestamp(x).date())
            ss = ss.groupby("date").agg(
                {
                    "absoluteIndex": np.mean,
                    "relativeIndex": np.mean,
                    "generalPerception": np.mean,
                    "sentiment": np.mean,
                }
            )
            ss
        except KeyError:
            "No social sentiment data"
        #   ss.columns

        try:
            sp = get_stock_peers(ticker, apikey)
            compare_to = st.sidebar.selectbox(
                "Pick a company to compare to",
                company_names[company_names.symbol.isin(sp["peersList"].iloc[0])][
                    "name"
                ],
            )
            st.subheader(compare_to)
            compare_to_company_data = get_single_company_data(compare_to, apikey)
            compare_to_company_data = analysis_single_company_data(
                compare_to_company_data
            )
            fig2 = px.line(
                compare_to_company_data, x="year", y=["MOP", "QA", "eps", "ROE"]
            )
            st.plotly_chart(fig2)
        except:
            print("No peers data")


if __name__ == "__main__":
    run_dashboard()
