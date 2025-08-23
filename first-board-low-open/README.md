# First Board Low Open (首板低开) — JoinQuant Strategy

This repository contains a JoinQuant strategy that buys stocks which **hit the limit-up yesterday** and **open within a configurable range today**.  
It uses two candidate pools with different opening windows, and includes simple **AM take-profit**, **PM exit**, and **risk control** (sell if yesterday limit-down or loss > 4% vs cost).

## Adjustable Parameters

Edit the function `set_params(context)` inside `strategy_fb_low_open.py`:

```python
def set_params(context):
    # Pool 1: today's opening change (%) relative to yesterday's close
    g.open_min_1 = 0.25   # lower bound
    g.open_max_1 = 1.0    # upper bound

    # Pool 2: today's opening change (%) relative to yesterday's close
    g.open_min_2 = -4.0   # lower bound
    g.open_max_2 = -3.0   # upper bound
```

## Files

```
first-board-low-open/
├── strategy_fb_low_open.py   # The JoinQuant strategy
├── README.md                 # This file
├── README_zh.md              # Chinese README
├── requirements.txt          # Optional python deps (for local linting or docs)
├── .gitignore
└── examples/
    └── output_sample.png     # Placeholder for backtest chart
```

## How to Use on JoinQuant

1. Copy the content of `strategy_fb_low_open.py` into a new strategy on JoinQuant (research/strategy editor).  
2. Adjust `set_params(context)` opening windows.  
3. Backtest with your preferred time range and commission settings.  
4. (Optional) Export your backtest chart and replace `examples/output_sample.png`.

---

Copyright © 2025
