"""
Bilingual string table for the ETF backtester UI.
Usage:
    from i18n import t, LANGS
    label = t("btn_run", lang)          # plain string
    label = t("sweep_caption", lang, n=45, start=30, end=250, step=5)  # with placeholders
"""

LANGS = ["zh", "en"]

_S: dict[str, dict[str, str]] = {
    # ── App-level ─────────────────────────────────────────────────────────────
    "page_title":       {"zh": "ETF 策略回测",                    "en": "ETF Strategy Backtester"},
    "app_title":        {"zh": "ETF 组合策略回测",                 "en": "ETF Portfolio Strategy Backtester"},
    "app_caption":      {
        "zh": "策略：QQQ 始终持有（固定仓位）；其他 ETF 在 QQQ 价格 ≥ SMAx 时持有，否则清仓持现金。早期无实际数据的杠杆 ETF 以 QQQ 日收益 × 杠杆倍数模拟。",
        "en": "Strategy: QQQ is always held at its configured weight; other ETFs are held when QQQ ≥ SMAx and liquidated to cash otherwise. Leveraged ETFs without historical data are simulated as QQQ daily return × leverage multiple.",
    },

    # ── Portfolio section ─────────────────────────────────────────────────────
    "portfolio_header": {"zh": "ETF 组合配置",         "en": "Portfolio Configuration"},
    "col_ticker":       {"zh": "ETF 代码",             "en": "Ticker"},
    "col_weight":       {"zh": "仓位 (%)",             "en": "Weight (%)"},
    "col_delete":       {"zh": "删除",                 "en": "Remove"},
    "btn_add_etf":      {"zh": "＋ 添加 ETF",          "en": "+ Add ETF"},
    "btn_reset":        {"zh": "重置默认",              "en": "Reset to Default"},
    "weight_total":     {"zh": "仓位合计：{total}%（需等于 100%）",
                         "en": "Total weight: {total}% (must equal 100%)"},

    # ── Correction parameters ─────────────────────────────────────────────────
    "correction_header":  {"zh": "回测修正参数",    "en": "Backtest Correction Parameters"},
    "correction_caption": {
        "zh": "这三个参数直接影响回测的真实性。默认值已修正常见偏差，可调整后对比差异。",
        "en": "These parameters control backtest realism. Defaults correct common biases; adjust to compare results.",
    },
    "signal_lag_label": {"zh": "信号延迟（交易日）", "en": "Signal Lag (trading days)"},
    "signal_lag_help":  {
        "zh": "**0 = 存在前瞻偏差**：用当天收盘价决定当天持仓，相当于提前知道了收盘价。SMA 窗口越短，偏差越大。\n\n**1（推荐）= 无偏差**：用昨天的收盘信号决定今天的持仓，模拟真实操作。",
        "en": "**0 = look-ahead bias**: today's close determines today's position — equivalent to knowing the close in advance. Bias is larger with shorter SMA windows.\n\n**1 (recommended) = no bias**: yesterday's signal determines today's position, matching real execution.",
    },
    "fee_mode_title":   {"zh": "交易成本模式",      "en": "Transaction Cost Mode"},
    "fee_mode_futu":    {"zh": "富途牛牛（逐笔精算）",  "en": "Futu牛牛 (per-trade exact)"},
    "fee_mode_fixed":   {"zh": "固定费率（%）",      "en": "Fixed rate (%)"},
    "fee_mode_none":    {"zh": "不计成本",           "en": "No cost"},
    "fee_mode_help":    {
        "zh": "**富途牛牛**：按实际费率逐笔计算（佣金 $0.0049/股 + 平台费 $0.005/股 + 交收费 $0.003/股上限$7 + 卖出时 SEC 费 0.00278% + FINRA $0.000166/股），约 0.015%–0.03%/笔。\n\n**固定费率**：手动指定每次换仓的成本比例。\n\n**不计成本**：忽略所有交易摩擦（乐观上界）。",
        "en": "**Futu牛牛**: exact per-order fees (commission $0.0049/share + platform $0.005/share + settlement $0.003/share max $7 + SEC fee 0.00278% on sells + FINRA $0.000166/share on sells), ~0.015–0.03% per trade.\n\n**Fixed rate**: specify a flat cost percentage per flip.\n\n**No cost**: ignore all friction (theoretical upper bound).",
    },
    "fee_rate_label":   {"zh": "费率（%）",          "en": "Rate (%)"},
    "fee_preview_caption": {
        "zh": "每笔估算（$1M 组合，ETF 价格按 QQQ 均价估算）：\n{lines}",
        "en": "Per-trade estimate ($1M portfolio, ETF price proxied from QQQ):\n{lines}",
    },
    "fee_preview_line_sell": {"zh": "{ticker}（${value:,.0f}）卖出 ≈ ${sell:.1f}，买入 ≈ ${buy:.1f}",
                              "en": "{ticker} (${value:,.0f}) sell ≈ ${sell:.1f}, buy ≈ ${buy:.1f}"},
    "leverage_warning_title": {"zh": "⚠️ 杠杆 ETF 模拟说明", "en": "⚠️ Leveraged ETF Simulation"},
    "leverage_warning_body":  {
        "zh": "早期无实际数据时用 QQQ×N 模拟，**忽略了波动率拖累**：\n- QLD (2×)：约 **−4%/年**\n- TQQQ (3×)：约 **−12%/年**\n\n实际早期收益会低于模拟值。",
        "en": "Early-period simulation (QQQ × leverage) **ignores volatility decay**:\n- QLD (2×): ~**−4%/yr**\n- TQQQ (3×): ~**−12%/yr**\n\nActual early-period returns will be lower than simulated.",
    },
    "status_caption":   {
        "zh": "当前设置：信号延迟 {lag} 日（{lag_label}）· {cost_label}",
        "en": "Current settings: signal lag {lag} day(s) ({lag_label}) · {cost_label}",
    },
    "lag_ok":           {"zh": "✅ 无偏差",          "en": "✅ no bias"},
    "lag_bias":         {"zh": "⚠️ 含前瞻偏差",      "en": "⚠️ look-ahead bias"},
    "cost_futu":        {"zh": "富途牛牛实际费率",    "en": "Futu牛牛 actual fees"},
    "cost_fixed":       {"zh": "固定费率 {pct:.3f}%", "en": "fixed rate {pct:.3f}%"},
    "cost_none":        {"zh": "不计成本",            "en": "no transaction cost"},

    # ── Tabs ──────────────────────────────────────────────────────────────────
    "tab1_label":       {"zh": "手动对比（最多 10 个 SMA）",  "en": "Manual Comparison (up to 10 SMAs)"},
    "tab2_label":       {"zh": "SMA 范围扫描 · Top 10",       "en": "SMA Range Sweep · Top 10"},

    # ── Tab 1 ─────────────────────────────────────────────────────────────────
    "tab1_sma_header":  {"zh": "SMA 参考值",          "en": "SMA Reference Values"},
    "btn_add_sma":      {"zh": "＋ 添加",             "en": "+ Add"},
    "btn_run":          {"zh": "确认并运行回测",       "en": "Run Backtest"},
    "error_no_qqq":     {"zh": "组合中必须包含 QQQ。", "en": "Portfolio must include QQQ."},
    "spinner_download": {"zh": "正在下载/更新历史数据…", "en": "Downloading / updating historical data…"},
    "spinner_backtest": {"zh": "正在运行回测…",         "en": "Running backtest…"},
    "error_download":   {"zh": "数据获取失败：{e}",     "en": "Data fetch failed: {e}"},
    "error_backtest":   {"zh": "{label} 回测失败：{e}", "en": "{label} backtest failed: {e}"},
    "tab1_table_header":{"zh": "回测结果（逐年）",      "en": "Backtest Results (Yearly)"},
    "col_year":         {"zh": "年份",                 "en": "Year"},
    "col_portfolio_value": {"zh": "资产总值({label})", "en": "Portfolio Value ({label})"},
    "tab1_chart_header":{"zh": "策略组合资产总值走势",  "en": "Portfolio Equity Curve"},
    "qqq_bh_label":     {"zh": "QQQ 买入持有（参考）", "en": "QQQ Buy & Hold (reference)"},
    "chart_y_portfolio":{"zh": "资产总值 (USD)",       "en": "Portfolio Value (USD)"},
    "chart_x_date":     {"zh": "日期",                 "en": "Date"},
    "tab1_stats_header":{"zh": "策略统计摘要",          "en": "Strategy Summary"},
    "metric_final":     {"zh": "最终资产总值",          "en": "Final Portfolio Value"},
    "metric_cagr":      {"zh": "年化收益率 (CAGR)",    "en": "Annualized Return (CAGR)"},
    "metric_max_dd":    {"zh": "最大回撤",              "en": "Max Drawdown"},

    # ── Tab 2 ─────────────────────────────────────────────────────────────────
    "tab2_sweep_header": {"zh": "SMA 扫描范围",     "en": "SMA Sweep Range"},
    "sweep_start":       {"zh": "起始 SMA",         "en": "Start SMA"},
    "sweep_end":         {"zh": "结束 SMA",         "en": "End SMA"},
    "sweep_step":        {"zh": "步长",             "en": "Step"},
    "sort_by_label":     {"zh": "Top 10 排序依据",  "en": "Sort Top 10 By"},
    "sort_cagr":         {"zh": "CAGR（年化收益率）","en": "CAGR"},
    "sort_value":        {"zh": "最终资产总值",      "en": "Final Portfolio Value"},
    "sort_drawdown":     {"zh": "最大回撤（最小）",  "en": "Max Drawdown (smallest)"},
    "oos_toggle":        {"zh": "启用样本外测试（验证过拟合）", "en": "Enable Out-of-Sample Validation"},
    "split_date_label":  {"zh": "训练期 / 测试期 分割日期",    "en": "Train / Test Split Date"},
    "split_date_help":   {
        "zh": "分割点之前为训练期（用于找最优 SMA），之后为测试期（验证结论是否成立）。",
        "en": "Data before this date is the training period (to find the best SMA); data after is the test period (to validate the conclusion).",
    },
    "oos_info":          {
        "zh": "训练期：数据起始 → {split_date}　|　测试期：{split_date} → 今天\n\n**判读方法**：若训练期 Top SMA 在测试期排名大幅下滑，说明结论可能是过拟合。",
        "en": "Training period: data start → {split_date}　|　Test period: {split_date} → today\n\n**How to read**: if top-ranked SMAs in training drop significantly in the test period, the result is likely overfitted.",
    },
    "sweep_warning":     {"zh": "结束 SMA 必须大于起始 SMA。", "en": "End SMA must be greater than Start SMA."},
    "sweep_caption":     {
        "zh": "共 {n} 个 SMA 值：{start} → {end}，步长 {step}",
        "en": "{n} SMA values: {start} → {end}, step {step}",
    },
    "btn_sweep":         {"zh": "运行 SMA 扫描（{n} 个策略）", "en": "Run SMA Sweep ({n} strategies)"},
    "sweep_progress":    {"zh": "SMA{sma} ({i}/{n})",           "en": "SMA{sma} ({i}/{n})"},
    "sweep_empty_error": {"zh": "扫描未产生任何结果。",          "en": "Sweep produced no results."},
    "top10_header":      {"zh": "Top 10 · 全段（按 {sort_by}）","en": "Top 10 · Full Period (by {sort_by})"},
    "col_final_value":   {"zh": "最终资产总值",   "en": "Final Value"},
    "col_cagr":          {"zh": "CAGR",           "en": "CAGR"},
    "col_max_dd":        {"zh": "最大回撤",        "en": "Max Drawdown"},
    "col_sma_window":    {"zh": "SMA 窗口",        "en": "SMA Window"},
    "cagr_chart_header": {"zh": "全局 CAGR 分布（所有 SMA · 全段）", "en": "CAGR Distribution Across All SMAs (Full Period)"},
    "top10_annotation":  {"zh": "深色 = Top 10",  "en": "Dark = Top 10"},
    "chart_y_cagr":      {"zh": "CAGR (%)",        "en": "CAGR (%)"},
    "oos_section_header":{"zh": "样本外测试结果",  "en": "Out-of-Sample Validation Results"},
    "oos_comparison_title": {
        "zh": "训练期 Top 10（SMA {start}–{end}）在测试期的表现",
        "en": "Training-period Top 10 (SMA {start}–{end}) performance in test period",
    },
    "col_train_cagr":    {"zh": "训练期 CAGR",    "en": "Train CAGR"},
    "col_train_dd":      {"zh": "训练期回撤",      "en": "Train Max DD"},
    "col_train_rank":    {"zh": "训练期排名",      "en": "Train Rank"},
    "col_test_cagr":     {"zh": "测试期 CAGR",    "en": "Test CAGR"},
    "col_test_dd":       {"zh": "测试期回撤",      "en": "Test Max DD"},
    "col_test_rank":     {"zh": "测试期排名",      "en": "Test Rank"},
    "col_rank_change":   {"zh": "排名变化 ↑好↓差", "en": "Rank Change ↑better ↓worse"},
    "oos_rank_caption":  {
        "zh": "排名变化：↑ 表示测试期排名比训练期更靠前（结论稳健）；↓ 表示排名下滑（可能过拟合）。",
        "en": "Rank change: ↑ means test-period rank improved vs. training (robust); ↓ means it dropped (possible overfitting).",
    },
    "scatter_title":     {"zh": "训练期排名 vs 测试期排名（散点图）",  "en": "Training Rank vs. Test Rank (Scatter Plot)"},
    "scatter_x":         {"zh": "训练期排名（1 = 最优）",             "en": "Training Rank (1 = best)"},
    "scatter_y":         {"zh": "测试期排名（1 = 最优）",             "en": "Test Rank (1 = best)"},
    "scatter_diagonal":  {"zh": "完美相关（对角线）",                 "en": "Perfect correlation (diagonal)"},
    "scatter_caption":   {
        "zh": "点越靠近对角线，说明训练期排名与测试期排名一致（策略稳健）。深色点 = 训练期 Top 10。若深色点大量偏离对角线右上角，说明过拟合严重。",
        "en": "Points near the diagonal indicate training and test ranks agree (robust strategy). Dark points = training Top 10. Points far above/right of the diagonal suggest overfitting.",
    },
    "spinner_sweep":     {"zh": "正在扫描 SMA…",  "en": "Scanning SMAs…"},
}


def t(key: str, lang: str, **kwargs) -> str:
    """Return the translated string for key in lang, with optional format args."""
    entry = _S.get(key, {})
    s = entry.get(lang) or entry.get("zh", f"[{key}]")
    return s.format(**kwargs) if kwargs else s
