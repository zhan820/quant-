# A-Share Valuation Visualization (PE/PB)

A clean, JoinQuant-Research-ready tool to batch fetch and visualize **P/E (PE)**, **P/B (PB)**, and **price** for A-share stocks.

> 🧰 Data source: JoinQuant `jqdata` APIs (`get_price`, `get_fundamentals_continuously` / `get_fundamentals`)

## ✨ Features
- **Batch plotting**: multiple tickers per run, grid layout
- **Dual-axis chart** per ticker:
  - Left Y: PE (blue, solid), Price (grey, dotted; optionally indexed to 100)
  - Right Y: PB (orange, dashed)
- **Resampling**: daily / weekly / monthly
- **Smoothing**: rolling **median** window for presentation
- **Stats band**: auto **mean ± 1σ** shading for PE & PB
- **CSV export**: per-ticker and combined

## 📦 Project Structure
```
pepb-visualization/
├── README.md
├── requirements.txt
├── pe_measure.py
└── examples/
    └── output_sample.png   # add your screenshot here
```

## 🚀 Quick Start (JoinQuant Research)
1. Upload `pe_measure.py` to JoinQuant Research.
2. Adjust the `stocks` list.
3. Run the script. Figures will show inline; CSVs go to `pepb_out/`.

## 🔧 Key Parameters
- `resample`: `'M'` (monthly), `'W'` (weekly), or `None` (daily)
- `price_indexed`: `True` to index price to `100` at the first point
- `smooth_window`: median smoothing window (e.g. `3`), set `1` to disable
- `out_dir`: CSV output directory
- `combined_csv`: name for combined CSV

## 🧠 Design Notes
- Robust data cleaning (`NaN`, ±∞) to avoid plotting errors
- Fast path (continuous fundamentals) + safe fallback (daily loop)
- Median smoothing for visual clarity without altering stored raw data

## 📝 Example (inside `pe_measure.py`)
```python
if __name__ == '__main__':
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
```

## 📑 License
MIT (feel free to adapt for your internship portfolio).
