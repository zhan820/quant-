# 首板低开策略（JoinQuant）

本仓库提供一个 **首板低开** 的聚宽策略：
- 选股：昨日涨停、过滤次新/“非ST”后，再按 **今日开盘涨幅区间** 过滤；
- 两套股票池（不同开盘区间）；
- 风控：昨日一字跌停强制卖出；昨日相对成本亏损超过 4% 卖出；
- 卖出：**上午 11:25 止盈**，**下午 14:30 清仓**。

## 可调参数

统一在 `strategy_fb_low_open.py` 的 `set_params(context)` 中调整：

```python
def set_params(context):
    # 股票池1：今日开盘涨幅（%）相对昨收
    g.open_min_1 = 0.25
    g.open_max_1 = 1.0

    # 股票池2：今日开盘涨幅（%）相对昨收
    g.open_min_2 = -4.0
    g.open_max_2 = -3.0
```

## 文件结构

```
first-board-low-open/
├── strategy_fb_low_open.py   # 策略代码
├── README.md                 # 英文说明
├── README_zh.md              # 中文说明
├── requirements.txt          # 可选依赖（本地整理/预览用）
├── .gitignore
└── examples/
    └── output_sample.png     # 放回测图的占位文件
```

## 使用方法

1. 将 `strategy_fb_low_open.py` 内容粘贴到聚宽新建策略中；  
2. 在 `set_params(context)` 调整开盘区间；  
3. 回测/模拟盘。

—  
版权 © 2025
