# -*- coding: utf-8 -*-
"""
First Board Low Open Strategy (首板低开) for JoinQuant

Only the "today opening range" parameters are intended for frequent tuning.
Modify them in set_params(context). Everything else can stay as-is.
"""

from jqlib.technical_analysis import *
from jqfactor import *
from jqdata import *
import datetime as dt
import pandas as pd


# ===================== Top-level params (only opening range) =====================
def set_params(context):
    # Pool 1: today's opening change (%) relative to yesterday's close
    g.open_min_1 = 0.25   # lower bound, e.g. 0.0
    g.open_max_1 = 1.0    # upper bound, e.g. 1.0

    # Pool 2: today's opening change (%) relative to yesterday's close
    g.open_min_2 = -4.0   # lower bound, e.g. -4.0
    g.open_max_2 = -3.0   # upper bound, e.g. -3.0


# ===================== Initialize =====================
def initialize(context):
    # Benchmark
    set_benchmark('000300.XSHG')
    # Use real price / avoid future data
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)

    set_params(context)  # tune here

    run_daily(sell_if_limit_down_yesterday, '09:30')
    run_daily(buy, '09:30')
    run_daily(sell, '11:25')
    run_daily(sell, '14:30')


# ===================== Buy =====================
def buy(context):
    date = get_previous_trade_day(context, 0)
    stock_list_with_ST = prepare_stock_list(context)
    stock_list_not_ST  = prepare_stock_list2(context)

    # keep order & dedup
    stock_list = list(dict.fromkeys(stock_list_with_ST + stock_list_not_ST))

    if len(stock_list) > 0:
        print("今日待选池为：{}".format(stock_list))
        cash = context.portfolio.cash
        if cash > 0:
            for s in stock_list:
                order_target_value(s, cash / len(stock_list))
                print('买入', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')
        else:
            print("当前账户没有现金,无法买入")


# ===================== Sell =====================
def sell(context):
    date = get_previous_trade_day(context, 0)
    current_data = get_current_data()

    # AM take-profit
    if str(context.current_dt)[-8:] == '11:25:00':
        for s in list(context.portfolio.positions):
            if ((context.portfolio.positions[s].closeable_amount != 0) and
                (current_data[s].last_price < current_data[s].high_limit) and
                (current_data[s].last_price > context.portfolio.positions[s].avg_cost)):
                order_target_value(s, 0)
                print('止盈卖出', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')

    # PM exit
    if str(context.current_dt)[-8:] == '14:30:00':
        for s in list(context.portfolio.positions):
            if ((context.portfolio.positions[s].closeable_amount != 0) and
                (current_data[s].last_price < current_data[s].high_limit)):
                order_target_value(s, 0)
                if current_data[s].last_price > context.portfolio.positions[s].avg_cost:
                    print('止盈卖出', [get_security_info(s, date).display_name, s])
                else:
                    print('止损卖出', [get_security_info(s, date).display_name, s])
                print('———————————————————————————————————')


# ===================== Risk control =====================
def sell_if_limit_down_yesterday(context):
    positions = context.portfolio.positions
    yesterday = get_previous_trade_day(context, 1)

    for stock in positions:
        avg_cost = positions[stock].avg_cost
        df = get_price(stock, end_date=yesterday, count=1, fields=['close', 'low', 'low_limit'])
        if df is None or df.empty:
            log.warning('无法获取 {} 的价格数据'.format(stock))
            continue

        close_price = df['close'].iloc[0]
        low_price   = df['low'].iloc[0]
        low_limit   = df['low_limit'].iloc[0]

        # one-word limit down yesterday
        if close_price == low_limit and low_price == low_limit:
            order_target_value(stock, 0)
            log.info('股票 {} 昨日跌停，触发风控止损卖出'.format(stock))
            continue

        # yesterday loss > 4% vs cost
        loss_ratio = (close_price - avg_cost) / avg_cost * 100
        if loss_ratio <= -4:
            order_target_value(stock, 0)
            log.info('股票 {} 亏损超过阈值，触发风控止损卖出'.format(stock))


# ===================== Pool 1 =====================
def prepare_stock_list(context):
    date      = get_previous_trade_day(context, 0)   # today
    last_date = get_previous_trade_day(context, 1)   # yesterday
    last_last_date = get_previous_trade_day(context, 2)

    stock_list = get_all_securities('stock', last_date).index.tolist()
    stock_list = get_limit_up_stock(stock_list, last_date)          # yesterday limit-up
    stock_list = filter_new_stock(stock_list, last_date)            # exclude very new stocks (60d)
    stock_list = filter_st_stock(stock_list, last_date)             # your prior "non-ST" filter
    stock_list = filter_stocks_by_opening_range(date, stock_list)   # opening window 1
    stock_list = get_no_limit_up_stocks(last_last_date, 1, stock_list) # no limit-up in lookback (excl yesterday)
    stock_list = get_relative_position_stocks(last_date, 15, stock_list) # low relative position
    return stock_list


# ===================== Pool 2 =====================
def prepare_stock_list2(context):
    date      = get_previous_trade_day(context, 0)
    last_date = get_previous_trade_day(context, 1)
    last_last_date = get_previous_trade_day(context, 2)

    stock_list = get_all_securities('stock', last_date).index.tolist()
    stock_list = get_limit_up_stock2(stock_list, last_date)
    stock_list = filter_new_stock2(stock_list, last_date)
    stock_list = filter_st_stock2(stock_list, last_date)
    stock_list = filter_stocks_by_opening_range2(date, stock_list)  # opening window 2
    stock_list = get_no_limit_up_stocks2(last_last_date, 1, stock_list)
    stock_list = get_relative_position_stocks2(last_date, 30, stock_list)
    return stock_list


# ===================== Utilities =====================
def get_limit_up_stock(initial_list, date):
    df = get_price(initial_list, end_date=date, frequency='daily',
                   fields=['close', 'high', 'high_limit'], count=1,
                   panel=False, fill_paused=False, skip_paused=False).dropna()
    df = df[df['close'] == df['high_limit']]
    hl_list = list(df.code)
    return hl_list


def filter_new_stock(initial_list, date, days=60):
    return [stock for stock in initial_list if date - get_security_info(stock).start_date > dt.timedelta(days=days)]


def filter_st_stock(stock_list, date):
    filtered_stocks = []
    for stock in stock_list:
        try:
            price_data = get_price(stock, end_date=date, count=2, frequency='daily', fields=['open', 'close'])
            if len(price_data) == 2:
                close_today = price_data['close'][-1]
                close_yesterday = price_data['close'][-2]
                return_percent_yesterday = (close_today - close_yesterday) / close_yesterday * 100

                open_today = price_data['open'][-1]
                return_percent_today = (close_today - open_today) / open_today * 100

                # original rule: yesterday 4%~6% and close_today > 2.5
                if 4 < return_percent_yesterday < 6 and close_today > 2.5:
                    filtered_stocks.append(stock)
        except Exception as e:
            print("根据涨幅过滤ST出错 {}: {}".format(stock, e))
    return filtered_stocks


def filter_stocks_by_opening_range(date, code_list):
    filtered_codes = []
    for code in code_list:
        stock_data = get_price(code, start_date=date, end_date=date, frequency='daily', fields=['open', 'pre_close'])
        if stock_data.empty:
            continue
        open_price = stock_data['open'].iloc[0]
        pre_close_price = stock_data['pre_close'].iloc[0]
        open_change_ratio = (open_price - pre_close_price) / pre_close_price * 100
        if g.open_min_1 <= open_change_ratio <= g.open_max_1:
            filtered_codes.append(code)
    return filtered_codes


def get_no_limit_up_stocks(date, no_limit_date, code_list):
    start_date = (pd.to_datetime(date) - pd.Timedelta(days=no_limit_date - 1)).strftime('%Y-%m-%d')
    end_date = date
    trading_days = get_trade_days(start_date=start_date, end_date=end_date)

    no_limit_up_stocks = code_list.copy()
    for day in trading_days:
        if not no_limit_up_stocks:
            break
        stock_data = get_price(no_limit_up_stocks, end_date=day, frequency='daily',
                               fields=['close', 'high', 'high_limit'], count=1, panel=False, fill_paused=False,
                               skip_paused=False).dropna()
        limit_up_stocks = stock_data[stock_data['close'] == stock_data['high_limit']]['code'].tolist()
        no_limit_up_stocks = [code for code in no_limit_up_stocks if code not in limit_up_stocks]
    return no_limit_up_stocks


def get_relative_position_stocks(date, watch_days, code_list):
    filtered_codes = []
    for code in code_list:
        data = get_price(code, end_date=date, count=watch_days, fields=['high', 'low'])
        if data is None or data.empty:
            continue
        max_high = data['high'].max()
        min_low = data['low'].min()

        close_price = get_price(code, end_date=date, count=1, fields=['close'])['close'].iloc[0]
        if max_high == min_low:
            continue
        relative_position = (close_price - min_low) / (max_high - min_low)

        if 0.0 <= relative_position <= 0.3:
            filtered_codes.append(code)
    return filtered_codes


# —— Pool 2 variants ——
def get_limit_up_stock2(initial_list, date):
    df = get_price(initial_list, end_date=date, frequency='daily',
                   fields=['close', 'high', 'high_limit'], count=1,
                   panel=False, fill_paused=False, skip_paused=False).dropna()
    df = df[df['close'] == df['high_limit']]
    hl_list = list(df.code)
    return hl_list


def filter_new_stock2(initial_list, date, days=60):
    return [stock for stock in initial_list if date - get_security_info(stock).start_date > dt.timedelta(days=days)]


def filter_st_stock2(stock_list, date):
    filtered_stocks = []
    for stock in stock_list:
        try:
            price_data = get_price(stock, end_date=date, count=2, frequency='daily', fields=['open', 'close'])
            if len(price_data) == 2:
                close_today = price_data['close'][-1]
                close_yesterday = price_data['close'][-2]
                return_percent_yesterday = (close_today - close_yesterday) / close_yesterday * 100

                open_today = price_data['open'][-1]
                return_percent_today = (close_today - open_today) / open_today * 100

                # original rule for pool2: yesterday 9%~22% and today (close - open)/open > 5%
                if 9 < return_percent_yesterday < 22 and return_percent_today > 5:
                    filtered_stocks.append(stock)
        except Exception as e:
            print("根据涨幅过滤ST出错 {}: {}".format(stock, e))
    return filtered_stocks


def filter_stocks_by_opening_range2(date, code_list):
    filtered_codes = []
    for code in code_list:
        stock_data = get_price(code, start_date=date, end_date=date, frequency='daily', fields=['open', 'pre_close'])
        if stock_data.empty:
            continue
        open_price = stock_data['open'].iloc[0]
        pre_close_price = stock_data['pre_close'].iloc[0]
        open_change_ratio = (open_price - pre_close_price) / pre_close_price * 100
        if g.open_min_2 <= open_change_ratio <= g.open_max_2:
            filtered_codes.append(code)
    return filtered_codes


def get_no_limit_up_stocks2(date, no_limit_date, code_list):
    return get_no_limit_up_stocks(date, no_limit_date, code_list)


def get_relative_position_stocks2(date, watch_days, code_list):
    filtered_codes = []
    for code in code_list:
        data = get_price(code, end_date=date, count=watch_days, fields=['high', 'low'])
        if data is None or data.empty:
            continue
        max_high = data['high'].max()
        min_low = data['low'].min()

        close_price = get_price(code, end_date=date, count=1, fields=['close'])['close'].iloc[0]
        if max_high == min_low:
            continue
        relative_position = (close_price - min_low) / (max_high - min_low)

        if 0.0 <= relative_position <= 0.5:
            filtered_codes.append(code)
    return filtered_codes


# ===================== Common helpers =====================
def get_previous_trade_day(context, n):
    current_date = context.current_dt.date()
    trade_days = get_trade_days(end_date=current_date, count=100)
    if n > len(trade_days):
        return None
    return trade_days[-(n + 1)]


def filter_paused_stock(initial_list, date):
    df = get_price(initial_list, end_date=date, frequency='daily', fields=['paused'], count=1,
                   panel=False, fill_paused=True)
    df = df[df['paused'] == 0]
    paused_list = list(df.code)
    return paused_list
