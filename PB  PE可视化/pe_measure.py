# -*- coding: utf-8 -*-
"""
A-Share Valuation Visualization (PE/PB + Price)
JoinQuant Research version, ready to run.

- Batch tickers: each subplot shows PE (blue, left Y), PB (orange, right Y), and Price (grey dotted).
- Optional price indexing (=100) for trend comparison.
- Optional resampling: None/'W'/'M' (last obs per period).
- Optional visual smoothing (rolling median) for nicer curves.
- Auto-exports per-ticker CSV and a combined CSV.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateLocator, DateFormatter
from datetime import date
from jqdata import *

# ------------------ Utilities ------------------
def _ensure_dir(path: str) -> None:
    """Create directory if missing."""
    if path and not os.path.exists(path):
        os.makedirs(path)

def _to_float_clean(s: pd.Series) -> pd.Series:
    """Convert to float, drop NaN/±inf; keep index alignment."""
    s = pd.to_numeric(s, errors='coerce').astype('float64')
    return s.replace([np.inf, -np.inf], np.nan).dropna()

# ------------------ Data fetching: PE/PB ------------------
def _fetch_valuation_block(stocks, end_dt, count) -> pd.DataFrame:
    """
    Fast path: one query for all tickers across a continuous window.
    Returns MultiIndex [date, code] with columns: pe_ratio, pb_ratio.
    """
    q = query(valuation.code, valuation.pe_ratio, valuation.pb_ratio) \
        .filter(valuation.code.in_(stocks))
    df = get_fundamentals_continuously(q, end_date=end_dt, count=count, panel=False)
    if df is None or df.empty:
        raise RuntimeError('empty from get_fundamentals_continuously')
    df = df.rename(columns={'day': 'date'})
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index(['date', 'code']).sort_index()
    return df

def _fetch_valuation_daily_loop(stock: str, trade_days) -> pd.DataFrame:
    """
    Fallback path: loop dates for a single ticker; slower but robust.
    """
    q = query(valuation.code, valuation.pe_ratio, valuation.pb_ratio) \
        .filter(valuation.code == stock)
    rec = []
    for d in trade_days:
        tmp = get_fundamentals(q, date=d)
        if tmp is None or tmp.empty:
            continue
        row = tmp.iloc[0]
        rec.append({
            'date': pd.to_datetime(d),
            'code': stock,
            'pe_ratio': row['pe_ratio'],
            'pb_ratio': row['pb_ratio']
        })
    if not rec:
        return (pd.DataFrame(columns=['date', 'code', 'pe_ratio', 'pb_ratio'])
                  .set_index(['date', 'code']))
    return pd.DataFrame(rec).set_index(['date', 'code']).sort_index()

def _prep_single_stock(df_all: pd.DataFrame, stock: str, trade_days, resample=None):
    """
    Extract single ticker from the big valuation table, align to trading days,
    forward-fill gaps, clean to float, and optionally resample.
    Returns: (pe_series, pb_series)
    """
    try:
        df = df_all.xs(stock, level='code')
    except Exception:
        df = pd.DataFrame(columns=['pe_ratio', 'pb_ratio'])

    # Deduplicate by date, keep last, set date index, align to all trading days
    df = (df.reset_index()
            .drop_duplicates(subset=['date'], keep='last')
            .set_index('date')
            .sort_index())
    df = df.reindex(pd.to_datetime(trade_days)).ffill()

    pe = _to_float_clean(df.get('pe_ratio', pd.Series(index=df.index, dtype='float64')))
    pb = _to_float_clean(df.get('pb_ratio', pd.Series(index=df.index, dtype='float64')))
    idx = pe.index.intersection(pb.index)
    pe, pb = pe.loc[idx], pb.loc[idx]

    # Optional resample to weekly/monthly (take last obs per period)
    if resample in ['W', 'M']:
        pe = pe.resample(resample).last().dropna()
        pb = pb.resample(resample).last().dropna()
        idx = pe.index.intersection(pb.index)
        pe, pb = pe.loc[idx], pb.loc[idx]

    return pe, pb

# ------------------ Price fetching ------------------
def _get_price_series(stock: str, start_ts, end_ts, resample=None) -> pd.Series:
    """
    Get daily close price from JoinQuant. Optionally resample to W/M.
    """
    px = get_price(stock, start_date=start_ts, end_date=end_ts,
                   frequency='daily', fields=['close'])
    if px is None or px.empty:
        return pd.Series(dtype='float64')
    s = _to_float_clean(px['close'])
    if resample in ['W', 'M']:
        s = s.resample(resample).last().dropna()
    return s

# ------------------ Main plotting function ------------------
def plot_pe_pb_with_price_batch(
    stocks,
    start_date='2018-01-01',
    end_date=None,
    resample='M',
    price_indexed=True,
    smooth_window=3,
    out_dir='pepb_out',
    combined_csv='pepb_combined.csv',
    show=True,
    max_cols=2,
    figsize_per_plot=(6.6, 3.9),
):
    """
    Batch plot PE/PB/Price for multiple tickers with a dual-axis layout.

    Args:
        stocks: list of JoinQuant tickers, e.g. ['000001.XSHE', '600519.XSHG']
        start_date, end_date: date strings 'YYYY-MM-DD' (end defaults to today)
        resample: None/'W'/'M' (weekly/monthly last)
        price_indexed: True to index price to 100 at first point
        smooth_window: median window size for display smoothing (1 disables)
        out_dir: CSV output directory
        combined_csv: name of combined CSV file
        show: show the figure
        max_cols: subplots per row
        figsize_per_plot: size per subplot (width, height)
    """
    if end_date is None:
        end_date = date.today().strftime('%Y-%m-%d')
    _ensure_dir(out_dir)

    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    trade_days = get_trade_days(start_date=start_ts, end_date=end_ts)
    if len(trade_days) == 0:
        raise ValueError('No trading days in range.')

    # Fetch valuation: fast path + fallback
    try:
        df_all = _fetch_valuation_block(stocks, end_ts, count=len(trade_days))
        df_all = df_all.loc[
            (df_all.index.get_level_values('date') >= start_ts) &
            (df_all.index.get_level_values('date') <= end_ts)
        ]
    except Exception:
        parts = []
        for s in stocks:
            parts.append(_fetch_valuation_daily_loop(s, trade_days))
        df_all = pd.concat(parts).sort_index() if parts else None
        if df_all is None or df_all.empty:
            raise RuntimeError('Failed to fetch valuation data.')

    # Figure canvas
    n = len(stocks)
    rows = (n + max_cols - 1) // max_cols
    fig, axes = plt.subplots(
        rows, max_cols,
        figsize=(figsize_per_plot[0] * max_cols, figsize_per_plot[1] * rows),
        squeeze=False
    )

    locator = AutoDateLocator()
    formatter = DateFormatter('%Y-%m')

    color_pe, color_pb, color_px = 'tab:blue', 'tab:orange', '#555555'
    combined_rows = []

    for i, stock in enumerate(stocks):
        r, c = divmod(i, max_cols)
        ax1 = axes[r][c]
        ax2 = ax1.twinx()  # right Y for PB

        # Prepare PE/PB/Price
        pe, pb = _prep_single_stock(df_all, stock, trade_days, resample=resample)
        px = _get_price_series(stock, start_ts, end_ts, resample=resample)

        # Align to common dates (intersection)
        idx = pe.index
        if not pb.empty:
            idx = idx.intersection(pb.index)
        if not px.empty:
            idx = idx.intersection(px.index)
        pe, pb, px = pe.loc[idx], pb.loc[idx], px.loc[idx]

        if px.empty or (pe.empty and pb.empty):
            ax1.text(0.5, 0.5, f"{stock}\nNo usable data",
                     ha='center', va='center', transform=ax1.transAxes)
            ax1.axis('off'); ax2.axis('off')
            continue

        # Optional price indexing: normalize to first point = 100
        px_plot = px.copy()
        px_label = 'Price'
        if price_indexed:
            base = px.iloc[0]
            if base and np.isfinite(base):
                px_plot = (px / base) * 100.0
                px_label = 'Price(=100)'

        # Optional visual smoothing (median)
        if smooth_window and smooth_window > 1:
            def _med(s): return s.rolling(smooth_window, center=True).median().dropna()
            pe_p = _med(pe) if not pe.empty else pe
            pb_p = _med(pb) if not pb.empty else pb
            px_p = _med(px_plot)

            idx2 = px_p.index
            if not pe_p.empty:
                idx2 = idx2.intersection(pe_p.index)
            if not pb_p.empty:
                idx2 = idx2.intersection(pb_p.index)
            pe_plot = pe_p.loc[idx2] if not pe_p.empty else pe_p
            pb_plot = pb_p.loc[idx2] if not pb_p.empty else pb_p
            px_plot = px_p.loc[idx2]
        else:
            pe_plot, pb_plot = pe, pb

        # Stats band (mean ± std) computed on raw series
        pe_avg = float(pe.mean()) if not pe.empty else np.nan
        pe_std = float(pe.std(ddof=1)) if not pe.empty else np.nan
        pb_avg = float(pb.mean()) if not pb.empty else np.nan
        pb_std = float(pb.std(ddof=1)) if not pb.empty else np.nan

        # Plot lines
        if not pe_plot.empty:
            ax1.plot(pe_plot.index, pe_plot.values, color=color_pe, lw=1.6, label='PE')
        if not pb_plot.empty:
            ax2.plot(pb_plot.index, pb_plot.values, color=color_pb, lw=1.6, linestyle='--', label='PB')
        if not px_plot.empty:
            ax1.plot(px_plot.index, px_plot.values, color=color_px, lw=1.4, linestyle=':', label=px_label)

        # Shaded mean ± 1σ bands (use constant arrays to avoid dtype issues)
        if not np.isnan(pe_avg) and len(pe_plot) > 2:
            x1 = pe_plot.index
            ax1.fill_between(x1,
                             np.full(len(x1), pe_avg - pe_std),
                             np.full(len(x1), pe_avg + pe_std),
                             color=color_pe, alpha=0.10, label='PE mean ± 1σ')
        if not np.isnan(pb_avg) and len(pb_plot) > 2:
            x2 = pb_plot.index
            ax2.fill_between(x2,
                             np.full(len(x2), pb_avg - pb_std),
                             np.full(len(x2), pb_avg + pb_std),
                             color=color_pb, alpha=0.10, label='PB mean ± 1σ')

        # Cosmetics
        ax1.set_title(stock)
        ax1.set_ylabel('PE / Price Index(=100)' if price_indexed else 'PE', color=color_pe)
        ax2.set_ylabel('PB', color=color_pb)
        ax1.tick_params(axis='y', colors=color_pe)
        ax2.tick_params(axis='y', colors=color_pb)
        ax1.xaxis.set_major_locator(locator)
        ax1.xaxis.set_major_formatter(formatter)
        ax1.grid(True, linestyle='--', alpha=0.25)

        # Only show bottom row x labels
        if r < rows - 1:
            ax1.tick_params(axis='x', labelbottom=False)
        else:
            ax1.set_xlabel('Date')

        # Export per-ticker CSV
        out_df = pd.DataFrame({'PE': pe, 'PB': pb, 'Close': px})
        if price_indexed and not px.empty:
            out_df['Close_indexed_100'] = (px / px.iloc[0]) * 100.0
        out_df.to_csv(os.path.join(out_dir, f"jq_pepb_{stock.replace('.', '')}.csv"),
                      encoding='utf-8-sig')

        # For combined CSV (optional extension)
        tmp = out_df.copy()
        tmp['code'] = stock
        tmp['date'] = tmp.index
        combined_rows.append(tmp.reset_index(drop=True))

    # Hide any empty axes
    for j in range(n, rows * max_cols):
        r, c = divmod(j, max_cols)
        axes[r][c].axis('off')

    fig.suptitle(
        f"PE / PB / Price ({start_date} ~ {end_date})" +
        ('' if resample is None else f' | {resample}'),
        y=0.995, fontsize=13, fontweight='bold'
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])

    if show:
        plt.show()

    # Optional: combined CSV (uncomment if desired)
    # if combined_rows:
    #     combined = pd.concat(combined_rows, ignore_index=True)
    #     combined.to_csv(os.path.join(out_dir, combined_csv),
    #                     encoding='utf-8-sig', index=False)

# ------------------ Example Run ------------------
if __name__ == '__main__':
    # Tip: uncomment these two lines if you see Chinese label issues on local matplotlib
    # plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    # plt.rcParams['axes.unicode_minus'] = False

    stocks = [
        '000001.XSHE',  # Ping An Bank
        '600519.XSHG',  # Kweichow Moutai
        '000651.XSHE',  # Gree Electric
        '300750.XSHE',  # CATL
        '601318.XSHG',  # Ping An Insurance
    ]
    plot_pe_pb_with_price_batch(
        stocks=stocks,
        start_date='2018-01-01',
        end_date='2025-08-22',
        resample='M',
        price_indexed=True,
        smooth_window=3,
        out_dir='pepb_out',
        show=True,
        max_cols=2
    )
