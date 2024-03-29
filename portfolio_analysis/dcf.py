import argparse
from decimal import Decimal

import numpy as np
import numpy_financial as npf
import pandas as pd
from sklearn.linear_model import LinearRegression

from portfolio_analysis.data import *

columns = ['cashAndCashEquivalents',
        'shortTermInvestments',
        'cashAndShortTermInvestments',
        'netReceivables',
        'inventory',
        'otherCurrentAssets',
        'totalCurrentAssets',
        'propertyPlantEquipmentNet',
        'goodwill',
        'intangibleAssets',
        'goodwillAndIntangibleAssets',
        'longTermInvestments',
        'taxAssets',
        'otherNonCurrentAssets',
        'totalNonCurrentAssets',
        'otherAssets',
        'totalAssets',
        'accountPayables',
        'shortTermDebt',
        'taxPayables',
        'deferredRevenue',
        'otherCurrentLiabilities',
        'totalCurrentLiabilities',
        'longTermDebt',
        'deferredRevenueNonCurrent',
        'deferredTaxLiabilitiesNonCurrent',
        'otherNonCurrentLiabilities',
        'totalNonCurrentLiabilities',
        'otherLiabilities',
        'capitalLeaseObligations',
        'totalLiabilities',
        'preferredStock',
        'commonStock',
        'retainedEarnings',
        'accumulatedOtherComprehensiveIncomeLoss',
        'othertotalStockholdersEquity',
        'totalStockholdersEquity',
        'totalLiabilitiesAndStockholdersEquity',
        'minorityInterest',
        'totalEquity',
        'totalLiabilitiesAndTotalEquity',
        'totalInvestments',
        'totalDebt',
        'netDebt']

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
    outliers = (df[f"{metric}_roc"] < (3 * stddev - median)) & (
        df[f"{metric}_roc"] > (3 * stddev + median)
    )
    df.loc[outliers, f"{metric}_roc"] = median
    return df


def regression_analyze(df, years=10):

    df.loc[:, "ln_eps"] = np.log(df["eps"])
    if len(df) > years:
        df = df.iloc[-years:, :]
    df.loc[:, "t1"] = [x for x in range(1, len(df) + 1)]
    reg = LinearRegression()
    try:
        reg.fit(np.array(df["t1"]).reshape(-1, 1), df["ln_eps"].array)
        return {"model": "log-linear", "percent_change": reg.coef_[0]}
    except ValueError as e:
        reg.fit(np.array(df["t1"]).reshape(-1, 1), df["eps"].array)
        return {"model": "linear", "percent_change": reg.coef_[0] / df["eps"].mean()}


def median_method(df, metric):
    df.loc[:, f"{metric}_roc_rolling"] = df[f"{metric}_roc"].rolling(3).median()
    eps_roc = df[f"{metric}_roc"].iloc[-3:].median()
    eps_roc_rolling = df[f"{metric}_roc_rolling"].iloc[-3:].median()
    if eps_roc > eps_roc_rolling:
        eps_roc = eps_roc_rolling
    # Doing this becuase the reson to take the rolling median is to resuce the effect of outliers
    # However there can be a case where the rolling median is an outlier
    # in the spirit of taking the more conservative value use the lesser number
    if eps_roc < 0.01:
        eps_roc = 0.01
    return eps_roc


def predict_future_sales(new_df, eps_base, eps_roc, method):
    future_eps = []
    #     DO this for a optimistic and pessimistic scenario
    for i in range(len(new_df["year"])):
        if i == 0:
            future_eps.append(eps_base * (1 + eps_roc))
        else:
            future_eps.append(future_eps[i - 1] * (1 + eps_roc))

    new_df.loc[:, f"eps_{method}"] = future_eps
    return new_df


def project_eps(df, metric):
    df.loc[:, "year"] = df["date"].apply(lambda x: x[:4])
    #     Find rate of change of eps yoy
    df = df.sort_values(by="year")
    # Arithemitic Mean
    df.loc[:, f"{metric}_roc"] = df[f"{metric}"].pct_change()

    # Geometric mean growth rate n=-3
    # geometric_mean = (
    #     (df[f"{metric}_roc"].iloc[-1] / df[f"{metric}_roc"].iloc[-5]) ** (1 / 4)
    # ) - 1

    # Regression
    # # https://pages.stern.nyu.edu/~adamodar/pdfiles/valn2ed/ch11.pdf
    regression_results = regression_analyze(df)

    eps_roc_flag = "Positive"
    for i in range(3):
        if df[f"{metric}_roc"].iloc[-i - 1] < 0:
            eps_roc_flag = "Negative"
            break

    #     3 year mean of dilued earnings per share as startpoint
    # remove outliers from metric roc

    eps_roc = median_method(df, metric)
    eps_base = df[f"{metric}"].iloc[-1]

    new_df = pd.DataFrame()
    new_df.loc[:, "year"] = [
        i for i in range(int(df.loc[0, "year"]) + 1, int(df.loc[0, "year"]) + 11)
    ]

    methods = {
        f"{regression_results['model']}": regression_results["percent_change"],
        "mean": eps_roc,
    }

    for method in methods.keys():
        new_df = predict_future_sales(new_df, eps_base, methods[f"{method}"], method)

    return (
        new_df,
        eps_roc,
        eps_base,
        eps_roc_flag,
        df["eps"].iloc[-3:].to_list(),
        regression_results,
    )


def get_dividend_ratio(IS, CFS):
    df = IS.merge(CFS[["date", "dividendsPaid"]], on=["date"])
    df["dividend_payout_ratio"] = abs(df["dividendsPaid"]) / df["netIncome"]
    return df[["date", "dividend_payout_ratio"]]

def check_cd(cd):
    check_dict = {}
    for key in cd.keys():
        if len(cd[key]) == 0:
            check_dict[key] = False
        else:
            check_dict[key] = True

    return check_dict

def get_irr(cd, symbol, cash_flow_metric="eps", discount_rate=0.09,
):
    check_dict = check_cd(cd)
    IS = cd["IS"]
    BS = cd["BS"]
    # HP = cd["HP"]
    MC = cd["MC"]
    CFR = cd["CFR"]
    CFS = cd["CFS"]
    profile = cd["profile"]
    breakpoint()
    if check_dict['BS']:
        currency = BS.loc[0, "reportedCurrency"]
    else:
        currency = None
    if check_dict['profile']:
        sector_name = profile.loc[0, "sector"] 
        price = profile.loc[0, "price"]
        industry_name = profile.loc[0, "industry"]
    else:
        sector_name = None
        price = None
        industry_name = None
    try:
        (
            new_df,
            eps_roc,
            eps_base,
            eps_roc_flag,
            eps_list,
            regression_results,
        ) = project_eps(
            IS, cash_flow_metric
        )  # eps_roc_flag indicates if any of the years had a negative earning per share rate of change
        eps = new_df[f"{cash_flow_metric}_{regression_results['model']}"].to_list()
        eps.insert(0, -price)
        irr = npf.irr(eps)

        # npv = cash flow / (1 + i)t - intial_investment
        new_df.loc[:, "t"] = pd.Series(range(1, len(new_df) + 1))
        new_df.loc[:, "npv_mean"] = new_df[f"{cash_flow_metric}_mean"] / np.power(
            (1 + discount_rate), new_df["t"]
        )
        new_df.loc[:, f'npv_{regression_results["model"]}'] = new_df[
            f"{cash_flow_metric}_{regression_results['model']}"
        ] / np.power((1 + discount_rate), new_df["t"])
        npv_mean = new_df["npv_mean"].sum()
        npv_regression = new_df[f'npv_{regression_results["model"]}'].sum()
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
        # Return on Capital - Magic Formula
        EBIT = (
            IS.loc[0, "revenue"]
            - IS.loc[0, "costOfRevenue"]
            - IS.loc[0, "operatingExpenses"]
        )
        # IS.loc[0, "netIncome"] + IS.loc[0, "incomeTaxExpense"] + IS.loc[0,"interestExpense"]

        NetWorkingCapital = (
            BS.loc[0, "totalCurrentAssets"] - BS.loc[0, "totalCurrentLiabilities"]
        )
        NetFixedAssets = BS.loc[0, "propertyPlantEquipmentNet"]

        ROC = EBIT / (NetWorkingCapital + NetFixedAssets)

        # Market Cap
        if len(MC) > 0:
            MCap = MC.loc[0, "marketCap"]
            # Enterprise_Value = Market_value + netInterestBearingdebt
            NetInterestBearingdebt = BS.loc[0, "totalDebt"] - BS.loc[0, "taxPayables"]
            EV = MCap + NetInterestBearingdebt
            EarningsYield = EBIT / EV
        else:
            MCap = np.nan
            EarningsYield = np.nan
        PE = CFR.loc[0, "peRatioTTM"]
        # Get Divivdend
        try:
            dividend_paid_trend = round(
                get_dividend_ratio(IS, CFS).loc[0:3, "dividend_payout_ratio"], 3
            ).to_list()
            dividend_paid = dividend_paid_trend[0]
            commonstock_repurchased_trend = CFS.loc[0:3, "commonStockRepurchased"].to_list()
            commonstock_repurchased = commonstock_repurchased_trend[0]
        except TypeError:
            dividend_paid_trend[0]
            dividend_paid = 0
            commonstock_repurchased_trend = [0]
            commonstock_repurchased = commonstock_repurchased_trend[0]

        if len(IS) >= 5:
            trend_years = 5
        elif len(IS) > 0:
            trend_years = len(IS)
        revenue_change = IS.sort_values("date")["revenue"].iloc[-trend_years:].pct_change().sort_index().to_list()
        return pd.Series(
            {
                "symbol": symbol,
                "name": profile.loc[0, "companyName"],
                "price": profile.loc[0, "price"],
                "industry": industry_name,
                "income_statement_date": IS["date"].iloc[0],
                "ROC": ROC,
                "EarningsYield": EarningsYield,
                "irr": irr,
                "npv_mean": npv_mean,
                "npv_regression": npv_regression,
                "regression_type": regression_results["model"],
                "eps_roc": eps_roc,
                "eps_roc_regression": regression_results["percent_change"],
                "ROE": ROE,
                "eps_diluted": EPS,
                "MOP": MOP,
                "QA": QA,
                "MCap": MCap,
                "PE": PE,
                "eps_roc_flag": eps_roc_flag,
                "eps_base": eps_base,
                "eps_list": eps_list,
                "dividend_ratio": dividend_paid,
                "dividend_trend": dividend_paid_trend,
                "commonstock_repurchased_trend": commonstock_repurchased_trend,
                "commonstock_repurchased": commonstock_repurchased,
                "error_message": "",
                "reportedCurrency": currency,
                "revenue_trend": IS.loc[0:trend_years,"revenue"].to_list(),
                "revenue_change": revenue_change,
                "sector": sector_name
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
        industry_name = profile.loc[0, "industry"]
        sector_name = profile.loc[0, "sector"]
        dividend_paid_trend = round(
            abs(get_dividend_ratio(IS, CFS).loc[0:3, "dividend_payout_ratio"]), 3
        ).to_list()
        dividend_paid = dividend_paid_trend[0]
        commonstock_repurchased_trend = CFS.loc[0:3, "commonStockRepurchased"].to_list()
        commonstock_repurchased = commonstock_repurchased_trend[0]
        return pd.Series(
            {
                "symbol": symbol,
                "name": profile.loc[0, "companyName"],
                "price": profile.loc[0, "price"],
                "industry": industry_name,
                "income_statement_date": IS["date"].iloc[0],
                "ROC": np.nan,
                "EarningsYield": np.nan,
                "irr": np.nan,
                "npv_mean": np.nan,
                "npv_regression": np.nan,
                "regression_type": np.nan,
                "eps_roc": np.nan,
                "eps_roc_regression": np.nan,
                "eps_diluted": EPS,
                "MOP": MOP,
                "QA": QA,
                "MCap": MCap,
                "PE": PE,
                "eps_roc_flag": np.nan,
                "eps_base": np.nan,
                "eps_list": np.nan,
                "dividend_ratio": dividend_paid,
                "dividend_trend": dividend_paid_trend,
                "commonstock_repurchased_trend": commonstock_repurchased_trend,
                "commonstock_repurchased": commonstock_repurchased,
                "error_message": e,
                "reportedCurrency": currency,
                "revenue_trend": np.nan,
                "revenue_change": np.nan,
                "sector": sector_name
            }
        )

def get_irr_new(
    company, IS, profile, BS, MC, CFR, CFS, cash_flow_metric="eps", discount_rate=0.09
):
    symbol = company.loc["symbol"]
    currency = BS.loc[0, "reportedCurrency"]
    price = profile.loc[0, "price"]
    industry_name = profile.loc[0, "industry"]

    (
        new_df,
        eps_roc,
        eps_base,
        eps_roc_flag,
        eps_list,
        regression_results,
    ) = project_eps(
        IS, cash_flow_metric
    )  # eps_roc_flag indicates if any of the years had a negative earning per share rate of change
    eps = new_df[f"{cash_flow_metric}_{regression_results['model']}"].to_list()
    eps.insert(0, -price)
    irr = npf.irr(eps)

    # npv = cash flow / (1 + i)t - intial_investment
    new_df.loc[:, "t"] = pd.Series(range(1, len(new_df) + 1))
    new_df.loc[:, "npv_mean"] = new_df[f"{cash_flow_metric}_mean"] / np.power(
        (1 + discount_rate), new_df["t"]
    )
    new_df.loc[:, f'npv_{regression_results["model"]}'] = new_df[
        f"{cash_flow_metric}_{regression_results['model']}"
    ] / np.power((1 + discount_rate), new_df["t"])
    npv_mean = new_df["npv_mean"].sum()
    npv_regression = new_df[f'npv_{regression_results["model"]}'].sum()
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
    # Return on Capital - Magic Formula
    EBIT = (
        IS.loc[0, "revenue"]
        - IS.loc[0, "costOfRevenue"]
        - IS.loc[0, "operatingExpenses"]
    )
    # IS.loc[0, "netIncome"] + IS.loc[0, "incomeTaxExpense"] + IS.loc[0,"interestExpense"]

    NetWorkingCapital = (
        BS.loc[0, "totalCurrentAssets"] - BS.loc[0, "totalCurrentLiabilities"]
    )
    NetFixedAssets = BS.loc[0, "propertyPlantEquipmentNet"]

    ROC = EBIT / (NetWorkingCapital + NetFixedAssets)

    # Market Cap
    if len(MC) > 0:
        MCap = MC.loc[0, "marketCap"]
        # Enterprise_Value = Market_value + netInterestBearingdebt
        NetInterestBearingdebt = BS.loc[0, "totalDebt"] - BS.loc[0, "taxPayables"]
        EV = MCap + NetInterestBearingdebt
        EarningsYield = EBIT / EV
    else:
        MCap = np.nan
        EarningsYield = np.nan
    PE = CFR.loc[0, "peRatioTTM"]
    # Get Divivdend
    dividend_paid_trend = round(
        abs(get_dividend_ratio(IS, CFS).loc[0:3, "dividend_payout_ratio"]), 3
    ).to_list()
    dividend_paid = dividend_paid_trend[0]
    commonstock_repurchased_trend = CFS.loc[0:3, "commonStockRepurchased"].to_list()
    commonstock_repurchased = commonstock_repurchased_trend[0]

    return pd.Series(
        {
            "symbol": company.loc["symbol"],
            "name": company.loc["name"],
            "price": company.loc["price"],
            "industry": industry_name,
            "income_statement_date": IS["date"].iloc[0],
            "ROC": ROC,
            "EarningsYield": EarningsYield,
            "irr": irr,
            "npv_mean": npv_mean,
            "npv_regression": npv_regression,
            "regression_type": regression_results["model"],
            "eps_roc": eps_roc,
            "eps_roc_regression": regression_results["percent_change"],
            "ROE": ROE,
            "eps_diluted": EPS,
            "MOP": MOP,
            "QA": QA,
            "MCap": MCap,
            "PE": PE,
            "eps_roc_flag": eps_roc_flag,
            "eps_base": eps_base,
            "eps_list": eps_list,
            "dividend_ratio": dividend_paid,
            "dividend_trend": dividend_paid_trend,
            "commonstock_repurchased_trend": commonstock_repurchased_trend,
            "commonstock_repurchased": commonstock_repurchased,
            "error_message": "",
            "reportedCurrency": currency,
        }
    )

def run_analysis(company_names, exchange):
    month = pd.Timestamp.now().month_name()
    try:
        irr_df = pd.read_csv(f"excels/{exchange}_{month}.csv")
    except FileNotFoundError:
        irr_df = pd.DataFrame()
    for index, company in company_names[company_names.exchange == exchange].iterrows():
        symbol = company.loc["symbol"]
        cd = get_single_company_data(symbol)
        irr = get_irr(cd)
        irr_df = irr_df.append(irr, ignore_index=True)

    irr_df.to_csv(f"excels/{exchange}_{month}.csv")
    return irr_df

def get_npv(IS, price, cash_flow_metric, discount_rate):
    (
        new_df,
        eps_roc,
        eps_base,
        eps_roc_flag,
        eps_list,
        regression_results,
    ) = project_eps(
        IS, cash_flow_metric
    )  # eps_roc_flag indicates if any of the years had a negative earning per share rate of change
    eps = new_df[f"{cash_flow_metric}_{regression_results['model']}"].to_list()
    eps.insert(0, -price)
    irr = npf.irr(eps)

    # npv = cash flow / (1 + i)t - intial_investment
    new_df.loc[:, "t"] = pd.Series(range(1, len(new_df) + 1))
    new_df.loc[:, "npv_mean"] = new_df[f"{cash_flow_metric}_mean"] / np.power(
        (1 + discount_rate), new_df["t"]
    )
    new_df.loc[:, f'npv_{regression_results["model"]}'] = new_df[
        f"{cash_flow_metric}_{regression_results['model']}"
    ] / np.power((1 + discount_rate), new_df["t"])
    npv_mean = new_df["npv_mean"].sum()
    npv_regression = new_df[f'npv_{regression_results["model"]}'].sum()
    npv_dict = {"eps_roc":eps_roc, 
        "eps_base":eps_base, 
        "eps_roc_flag":eps_roc_flag, 
        "eps_list": eps_list,
        "npv_mean": npv_mean,
        "npv_regression": npv_regression}
    return npv_dict

def get_roc_earnings(IS, BS, MC):
    if len(IS) >= 5:
        trend_years = 5
    elif len(IS) > 0:
        trend_years = len(IS)
    
    if trend_years > 0:
        MOP = IS.loc[0:trend_years, "operatingIncome"] / IS.loc[0:trend_years, "revenue"]
        # Quick assets: Current assets - Inventory / Current Liabilities
        QA = (BS.loc[0:trend_years, "totalCurrentAssets"] - BS.loc[0:trend_years, "inventory"]) / BS.loc[
            0:trend_years, "totalCurrentLiabilities"
        ]
        # Return on Capital - Magic Formula
        EBIT = (
            IS.loc[0:trend_years, "revenue"]
            - IS.loc[0:trend_years, "costOfRevenue"]
            - IS.loc[0:trend_years, "operatingExpenses"]
        )
        # IS.loc[0, "netIncome"] + IS.loc[0, "incomeTaxExpense"] + IS.loc[0,"interestExpense"]

        NetWorkingCapital = (
            BS.loc[0:trend_years, "totalCurrentAssets"] - BS.loc[0:trend_years, "totalCurrentLiabilities"]
        )
        NetFixedAssets = BS.loc[0:trend_years, "propertyPlantEquipmentNet"]

        ROC = EBIT / (NetWorkingCapital + NetFixedAssets)
    else:
        MOP = [np.nan]
        QA = [np.nan]
        EBIT = [np.nan]
        ROC = [np.nan]

    # Market Cap
    if len(MC) > 0:
        MCap = MC.loc[0, "marketCap"]
        # Enterprise_Value = Market_value + netInterestBearingdebt
        NetInterestBearingdebt = BS.loc[0, "totalDebt"] - BS.loc[0, "taxPayables"]
        EV = MCap + NetInterestBearingdebt
        EarningsYield = EBIT[0] / EV
    else:
        MCap = np.nan
        EarningsYield = np.nan

    roc_dict = {"MOP":MOP.iloc[0],
        "MOP_trend": MOP,
        "QA": QA.iloc[0],
        "QA_trend": QA,
        "EBIT": EBIT.iloc[0]}

def analyse_company_data(cd, cash_flow_metric='eps', discount_rate=0.05):
    IS = cd["IS"].sort_values('date', ascending=False)
    BS = cd["BS"].sort_values('date', ascending=False)
    # HP = cd["HP"].sort_values('date', ascending=False)
    MC = cd["MC"]
    CFR = cd["CFR"]
    CFS = cd["CFS"].sort_values('date', ascending=False)
    profile = cd["profile"]

    symbol = profile.loc[0,"symbol"]
    currency = BS.loc[0, "reportedCurrency"]
    price = profile.loc[0, "price"]
    industry_name = profile.loc[0, "industry"]

    npv_dict = get_npv(IS, price, cash_flow_metric, discount_rate)

    ROE = CFR.loc[0, "returnOnEquityTTM"]
    EPS = IS.loc[0, "epsdiluted"]

def analyse_single_company_data(company_data,  money_only=False):
    if money_only:
        IS = company_data["IS"]
        BS = company_data["BS"]
    else:
        IS = company_data["IS"]
        BS = company_data["BS"]
        profile = company_data["profile"]
        MC = company_data["MC"]
        CFR = company_data["CFR"]
        CFS = company_data["CFS"]
        # EPS is the net income divided by the weighted average number of common shares issued
        EPS = IS.loc[:, ["date", "eps"]]
    # ROE = Net Income / Shareholder Equity
    # Shareholder Equity = Total Assets - Liabilities

    # Margin of Profits: Operating Income / Sales
    IS.loc[:, "MOP"] = IS.loc[:, "operatingIncome"] / IS.loc[:, "revenue"]
    # Quick assets: Current assets - Inventory / Current Liabilities
    BS.loc[:, "QA"] = (BS.loc[:, "totalCurrentAssets"] - BS.loc[:, "inventory"]) / BS.loc[
        :, "totalCurrentLiabilities"
    ]
    IS.loc[:, "year"] = IS["date"].apply(lambda x: pd.Timestamp(x).year)
    BS.loc[:, "year"] = BS["date"].apply(lambda x: pd.Timestamp(x).year)
    CFS.loc[:, "year"] = CFS["date"].apply(lambda x: pd.Timestamp(x).year)

    columns = ['cashAndCashEquivalents',
        'shortTermInvestments',
        'cashAndShortTermInvestments',
        'netReceivables',
        'inventory',
        'otherCurrentAssets',
        'totalCurrentAssets',
        'propertyPlantEquipmentNet',
        'goodwill',
        'intangibleAssets',
        'goodwillAndIntangibleAssets',
        'longTermInvestments',
        'taxAssets',
        'otherNonCurrentAssets',
        'totalNonCurrentAssets',
        'otherAssets',
        'totalAssets',
        'accountPayables',
        'shortTermDebt',
        'taxPayables',
        'deferredRevenue',
        'otherCurrentLiabilities',
        'totalCurrentLiabilities',
        'longTermDebt',
        'deferredRevenueNonCurrent',
        'deferredTaxLiabilitiesNonCurrent',
        'otherNonCurrentLiabilities',
        'totalNonCurrentLiabilities',
        'otherLiabilities',
        'capitalLeaseObligations',
        'totalLiabilities',
        'preferredStock',
        'commonStock',
        'retainedEarnings',
        'accumulatedOtherComprehensiveIncomeLoss',
        'othertotalStockholdersEquity',
        'totalStockholdersEquity',
        'totalLiabilitiesAndStockholdersEquity',
        'minorityInterest',
        'totalEquity',
        'totalLiabilitiesAndTotalEquity',
        'totalInvestments',
        'totalDebt',
        'netDebt']

    columns += ['year', 'QA']

    combined_data = IS.merge(BS[columns], on="year")
    combined_data = combined_data.merge(CFS[["year","dividendsPaid"]], on="year")
    
    combined_data.loc[:, "dividend_payout_ratio"] = abs(combined_data["dividendsPaid"]) / combined_data["netIncome"]
    combined_data.loc[:, "ROE"] = combined_data["netIncome"] / (
        combined_data["totalAssets"] - combined_data["totalLiabilities"]
    )
    combined_data.loc[:, "EBIT"] = (
        combined_data["revenue"]
        - combined_data["costOfRevenue"]
        - combined_data["operatingExpenses"]
    )

    # IS.loc[0, "netIncome"] + IS.loc[0, "incomeTaxExpense"] + IS.loc[0,"interestExpense"]

    combined_data.loc[:, "NetWorkingCapital"] = (
        combined_data["totalCurrentAssets"] - combined_data["totalCurrentLiabilities"]
    )
    # NetFixedAssets = combined_data["propertyPlantEquipmentNet"]

    #  ROC = EBIT / (NetWorkingCapital + Net Fixed Assests)
    combined_data.loc[:, "ROC"] = combined_data["EBIT"] / (combined_data["NetWorkingCapital"] + combined_data["propertyPlantEquipmentNet"])
    combined_data = combined_data.sort_values('year')
    return combined_data

def analyse_reit(cd):
    IS = cd["IS"].sort_values('date', ascending=False)
    BS = cd["BS"].sort_values('date', ascending=False)
    # HP = cd["HP"].sort_values('date', ascending=False)
    MC = cd["MC"]
    CFR = cd["CFR"]
    CFS = cd["CFS"].sort_values('date', ascending=False)
    profile = cd["profile"]
    profile = cd["profile"]
    symbol = profile.loc[0, "symbol"]
    currency = BS.loc[0, "reportedCurrency"]
    price = profile.loc[0, "price"]
    industry_name = profile.loc[0, "industry"]
    company_name = profile.loc[0, "companyName"]

    IS["ffo"] = IS["netIncome"] + IS["depreciationAndAmortization"]
    
    columns = ["calendarYear", "totalDebt"]
    combined_data = IS.merge(BS[columns], on="calendarYear")
    combined_data["debt_to_ffo"] = combined_data["totalDebt"] / combined_data["ffo"]

    ffo_yield = combined_data.loc[0, "ffo"] / MC.loc[0,"marketCap"]

    reit_analysis = {}
    reit_analysis["ffo_yield"] = ffo_yield
    reit_analysis["symbol"] = symbol
    reit_analysis["name"] = company_name
    reit_analysis["industry_name"] = industry_name
    reit_analysis["price"] = price
    for year in ['2021', '2020', '2019', '2018', '2017']:

        year_data = combined_data.query(f"calendarYear == '{year}'")
        if len(year_data) == 0:
            pass
        else:
            reit_analysis[f"{year}_ffo"] = year_data.iloc[0].loc["ffo"]
            reit_analysis[f"{year}_debt_to_ffo"] = year_data.iloc[0].loc["debt_to_ffo"]
    
    return reit_analysis


            





