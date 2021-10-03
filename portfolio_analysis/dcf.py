import argparse
from decimal import Decimal

import numpy as np
import numpy_financial as npf
import pandas as pd

from portfolio_analysis.data import *


def DCF(
    ticker,
    ev_statement,
    income_statement,
    balance_statement,
    cashflow_statement,
    discount_rate,
    forecast,
    earnings_growth_rate,
    cap_ex_growth_rate,
    perpetual_growth_rate,
):
    """
    a very basic 2-stage DCF implemented for learning purposes.
    see enterprise_value() for details on arguments.
    args:
        see enterprise value for more info...
    returns:
        dict: {'share price': __, 'enterprise_value': __, 'equity_value': __, 'date': __}
        CURRENT DCF VALUATION. See historical_dcf to fetch a history.
    """
    enterprise_val = enterprise_value(
        income_statement,
        cashflow_statement,
        balance_statement,
        forecast,
        discount_rate,
        earnings_growth_rate,
        cap_ex_growth_rate,
        perpetual_growth_rate,
    )

    equity_val, share_price = equity_value(enterprise_val, ev_statement)

    print(
        "\nEnterprise Value for {}: ${}.".format(
            ticker, "%.2E" % Decimal(str(enterprise_val))
        ),
        "\nEquity Value for {}: ${}.".format(ticker, "%.2E" % Decimal(str(equity_val))),
        "\nPer share value for {}: ${}.\n".format(
            ticker, "%.2E" % Decimal(str(share_price))
        ),
        "-" * 60,
    )

    return {
        "date": income_statement[0]["date"],  # statement date used
        "enterprise_value": enterprise_val,
        "equity_value": equity_val,
        "share_price": share_price,
    }


def historical_DCF(
    ticker,
    years,
    forecast,
    discount_rate,
    earnings_growth_rate,
    cap_ex_growth_rate,
    perpetual_growth_rate,
    interval="annual",
    apikey="",
):
    """
    Wrap DCF to fetch DCF values over a historical timeframe, denoted period.
    args:
        same as DCF, except for
        period: number of years to fetch DCF for
    returns:
        {'date': dcf, ..., 'date', dcf}
    """
    dcfs = {}

    income_statement = get_income_statement(
        ticker=ticker, period=interval, apikey=apikey
    )["financials"]
    balance_statement = get_balance_statement(
        ticker=ticker, period=interval, apikey=apikey
    )["financials"]
    cashflow_statement = get_cashflow_statement(
        ticker=ticker, period=interval, apikey=apikey
    )["financials"]
    enterprise_value_statement = get_EV_statement(
        ticker=ticker, period=interval, apikey=apikey
    )["enterpriseValues"]

    if interval == "quarter":
        intervals = years * 4
    else:
        intervals = years

    for interval in range(0, intervals):
        try:
            dcf = DCF(
                ticker,
                enterprise_value_statement[interval],
                income_statement[
                    interval : interval + 2
                ],  # pass year + 1 bc we need change in working capital
                balance_statement[interval : interval + 2],
                cashflow_statement[interval : interval + 2],
                discount_rate,
                forecast,
                earnings_growth_rate,
                cap_ex_growth_rate,
                perpetual_growth_rate,
            )
        except IndexError:
            print(
                "Interval {} unavailable, no historical statement.".format(interval)
            )  # catch
        dcfs[dcf["date"]] = dcf

    return dcfs


def ulFCF(ebit, tax_rate, non_cash_charges, cwc, cap_ex):
    """
    Formula to derive unlevered free cash flow to firm. Used in forecasting.
    args:
        ebit: Earnings before interest payments and taxes.
        tax_rate: The tax rate a firm is expected to pay. Usually a company's historical effective rate.
        non_cash_charges: Depreciation and amortization costs.
        cwc: Annual change in net working capital.
        cap_ex: capital expenditures, or what is spent to maintain zgrowth rate.
    returns:
        unlevered free cash flow
    """
    return ebit * (1 - tax_rate) + non_cash_charges + cwc + cap_ex


def get_discount_rate():
    """
    Calculate the Weighted Average Cost of Capital (WACC) for our company.
    Used for consideration of existing capital structure.
    args:

    returns:
        W.A.C.C.
    """
    return 0.1  # TODO: implement


def equity_value(enterprise_value, enterprise_value_statement):
    """
    Given an enterprise value, return the equity value by adjusting for cash/cash equivs. and total debt.
    args:
        enterprise_value: (EV = market cap + total debt - cash), or total value
        enterprise_value_statement: information on debt & cash

    returns:
        equity_value: (enterprise value - debt + cash)
        share_price: equity value/shares outstanding
    """
    equity_val = enterprise_value - enterprise_value_statement["+ Total Debt"]
    equity_val += enterprise_value_statement["- Cash & Cash Equivalents"]
    share_price = equity_val / float(enterprise_value_statement["Number of Shares"])

    return equity_val, share_price


def enterprise_value(
    income_statement,
    cashflow_statement,
    balance_statement,
    period,
    discount_rate,
    earnings_growth_rate,
    cap_ex_growth_rate,
    perpetual_growth_rate,
):
    """
    Calculate enterprise value by NPV of explicit _period_ free cash flows + NPV of terminal value,
    both discounted by W.A.C.C.
    args:
        ticker: company for forecasting
        period: years into the future
        earnings growth rate: assumed growth rate in earnings, YoY
        cap_ex_growth_rate: assumed growth rate in cap_ex, YoY
        perpetual_growth_rate: assumed growth rate in perpetuity for terminal value, YoY
    returns:
        enterprise value
    """
    # XXX: statements are returned as historical list, 0 most recent
    ebit = float(income_statement[0]["EBIT"])
    tax_rate = float(income_statement[0]["Income Tax Expense"]) / float(
        income_statement[0]["Earnings before Tax"]
    )
    non_cash_charges = float(cashflow_statement[0]["Depreciation & Amortization"])
    cwc = (
        float(balance_statement[0]["Total assets"])
        - float(balance_statement[0]["Total non-current assets"])
    ) - (
        float(balance_statement[1]["Total assets"])
        - float(balance_statement[1]["Total non-current assets"])
    )
    cap_ex = float(cashflow_statement[0]["Capital Expenditure"])
    discount = discount_rate

    flows = []

    # Now let's iterate through years to calculate FCF, starting with most recent year
    print(
        "Forecasting flows for {} years out, starting at {}.".format(
            period, income_statement[0]["date"]
        ),
        ("\n         DFCF   |    EBIT   |    D&A    |    CWC     |   CAP_EX   | "),
    )
    for yr in range(1, period + 1):

        # increment each value by growth rate
        ebit = ebit * (1 + (yr * earnings_growth_rate))
        non_cash_charges = non_cash_charges * (1 + (yr * earnings_growth_rate))
        cwc = cwc * 0.7  # TODO: evaluate this cwc rate? 0.1 annually?
        cap_ex = cap_ex * (1 + (yr * cap_ex_growth_rate))

        # discount by WACC
        flow = ulFCF(ebit, tax_rate, non_cash_charges, cwc, cap_ex)
        PV_flow = flow / ((1 + discount) ** yr)
        flows.append(PV_flow)

        print(
            str(int(income_statement[0]["date"][0:4]) + yr) + "  ",
            "%.2E" % Decimal(PV_flow) + " | ",
            "%.2E" % Decimal(ebit) + " | ",
            "%.2E" % Decimal(non_cash_charges) + " | ",
            "%.2E" % Decimal(cwc) + " | ",
            "%.2E" % Decimal(cap_ex) + " | ",
        )

    NPV_FCF = sum(flows)

    # now calculate terminal value using perpetual growth rate
    final_cashflow = flows[-1] * (1 + perpetual_growth_rate)
    TV = final_cashflow / (discount - perpetual_growth_rate)
    NPV_TV = TV / (1 + discount) ** (1 + period)

    return NPV_TV + NPV_FCF

def remove_outliers(df, metric):
    median = df[f"{metric}_roc"].median()
    stddev = df[f"{metric}_roc"].std()
    outliers = (df[f"{metric}_roc"] < (3*stddev - median)) & (df[f"{metric}_roc"] > (3*stddev + median))
    df.loc[outliers, f"{metric}_roc"] = median
    return df

def project_eps(df, metric):
    df["year"] = df["date"].apply(lambda x: x[:4])
    #     Find rate of change of eps yoy
    df = df.sort_values(by="year")
    df[f"{metric}_roc"] = df[f"{metric}"].pct_change()
    
    eps_roc_flag = 'Positive' 
    for i in range(3):
        if df[f"{metric}_roc"].iloc[-i-1] < 0:
            eps_roc_flag = 'Negative'
            break
    df[f"{metric}_roc_rolling"] = df[f"{metric}_roc"].rolling(3).median()
    #     3 year mean of dilued earnings per share as startpoint
    # remove outliers from metric roc


    eps_base = df[f"{metric}"].iloc[-3:].median()
    eps_roc = df[f"{metric}_roc"].iloc[-3:].median()
    eps_roc_rolling = df[f"{metric}_roc_rolling"].iloc[-3:].median()
    if eps_roc > eps_roc_rolling:
        eps_roc = eps_roc_rolling
    # Doing this becuase the reson to take the rolling median is to resuce the effect of outliers
    # However there can be a case where the rolling median is an outlier
    # in the spirit of taking the more conservative value use the lesser number
    if eps_roc < 0.01:
        eps_roc = 0.01
    new_df = pd.DataFrame()
    new_df["year"] = [i for i in range(int(df.loc[0, 'year']) +1, int(df.loc[0, 'year']) +11)]
    future_eps = []
    #     DO this for a optimistic and pessimistic scenario
    for i in range(len(new_df["year"])):
        if i == 0:
            future_eps.append(eps_base * (1 + eps_roc))
        else:
            future_eps.append(future_eps[i - 1] * (1 + eps_roc))
    new_df[f"{metric}"] = future_eps
    return new_df, eps_roc, eps_base, eps_roc_flag, df["eps"].iloc[-3:].to_list()


def get_irr(company, IS, profile, BS, MC, CFR, cash_flow_metric='eps', discount_rate=0.09):
    symbol = company.loc["symbol"]
    try:
        new_df, eps_roc, eps_base, eps_roc_flag, eps_list = project_eps(IS, cash_flow_metric) #eps_roc_flag indicates if any of the years had a negative earning per share rate of change
        eps = new_df[cash_flow_metric].to_list()
        price = profile.loc[0, "price"]
        eps.insert(0, -price)
        irr = npf.irr(eps)
        
        # npv = cash flow / (1 + i)t - intial_investment
        new_df['t'] = pd.Series(range(1, len(new_df)+1))
        new_df['npv'] = new_df[cash_flow_metric] / np.power((1+discount_rate), new_df['t'])
        npv = new_df['npv'].sum()
        # ROE is net income divided by average shareholders' equity 
        ROE = CFR.loc[0, "returnOnEquityTTM"]
        # EPS is the net income divided by the weighted average number of common shares issued
        EPS = IS.loc[0, "epsdiluted"]
        # Margin of Profits: Operating Income / Sales
        MOP = IS.loc[0, "operatingIncome"] / IS.loc[0, "revenue"]
        # Quick assets: Current assets - Inventory / Current Liabilities
        QA = (BS.loc[0, "totalCurrentAssets"] - BS.loc[0, "inventory"]) / BS.loc[
            0, "totalCurrentLiabilities"
        ]
        # Market Cap
        if len(MC) > 0:
            MCap = MC.loc[0, "marketCap"]
        else:
            MCap = np.nan
        PE = CFR.loc[0, "priceEarningsRatioTTM"]

        return pd.Series(
            {
                "symbol": company.loc["symbol"],
                "name": company.loc["name"],
                "price": company.loc["price"],
                "irr": irr,
                "npv": npv,
                "eps_roc": eps_roc,
                "eps_diluted": ROE,
                "MOP": MOP,
                "QA": QA,
                "MCap": MCap,
                "PE": PE,
                "eps_roc_flag": eps_roc_flag,
                "eps_base": eps_base,
                "eps_list": eps_list,
                "error_message": ""
            }
        )
    except Exception as e:
        print(f"Company with symbol: {symbol} failed with error: {e}")
        # https://finance.zacks.com/difference-between-return-equity-earnings-per-share-1632.html
        # ROE is net income divided by average shareholders' equity 
        ROE = CFR.loc[0, "returnOnEquityTTM"]
        # EPS is the net income divided by the weighted average number of common shares issued
        EPS = IS.loc[0, "epsdiluted"]
        # Margin of Profits: Operating Income / Sales
        MOP = IS.loc[0, "operatingIncome"] / IS.loc[0, "revenue"]
        # Quick assets: Current assets - Inventory / Current Liabilities
        QA = (BS.loc[0, "totalCurrentAssets"] - BS.loc[0, "inventory"]) / BS.loc[
            0, "totalCurrentLiabilities"
        ]
        # Market Cap
        MCap = MC.loc[0, "marketCap"]
        PE = CFR.loc[0, "priceEarningsRatioTTM"]
        return pd.Series(
                {
                    "symbol": symbol,
                    "name": company.loc["name"],
                    "price": company.loc["price"],
                    "irr": np.nan,
                    "npv": np.nan,
                    "eps_roc": np.nan,
                    "ROE": ROE,
                    "eps_diluted": EPS,
                    "MOP": MOP,
                    "QA": QA,
                    "MCap": MCap,
                    "PE": PE,
                    "eps_roc_flag": np.nan,
                    "eps_base": eps_base,
                    "eps_list": np.nan,
                    "error_message": e,
                })
                    
def run_analysis(company_names, exchange):
    month = pd.Timestamp.now().month_name()
    try:
        irr_df = pd.read_csv(f"excels/{exchange}_{month}.csv")
    except FileNotFoundError:
        irr_df = pd.DataFrame()
    for index, company in company_names[
        company_names.exchange == exchange
        ].iterrows():
        symbol = company.loc["symbol"]
        IS = get_income_statement(symbol, period="annual", apikey=apikey)
        profile = get_company_profile(symbol, apikey=apikey)
        BS = get_balance_statement(symbol, apikey=apikey)
        MC = get_market_cap(symbol=symbol, apikey=apikey)
        CFR = get_financial_ratios(symbol=symbol, apikey=apikey)
        irr = get_irr(company, IS, profile, BS, MC, CFR)
        irr_df = irr_df.append(irr, ignore_index=True)

    irr_df.to_csv(f"excels/{exchange}_{month}.csv")
    return irr_df