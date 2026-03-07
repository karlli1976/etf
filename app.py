import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data_manager import get_price_data
from backtest import run_backtest, SIGNAL_TICKER, _futu_fee, LEVERAGE_MAP

st.set_page_config(page_title="ETF 策略回测", layout="wide")
st.title("ETF 组合策略回测")
st.caption(
    f"策略：{SIGNAL_TICKER} 始终持有（固定仓位）；其他 ETF 在 {SIGNAL_TICKER} 价格 ≥ SMAx 时持有，否则清仓持现金。"
    f"早期无实际数据的杠杆 ETF 以 QQQ 日收益 × 杠杆倍数模拟。"
)

# ── Portfolio input (shared) ──────────────────────────────────────────────────
st.header("ETF 组合配置")

DEFAULT_PORTFOLIO = [
    {"ticker": "QQQ", "weight": 60},
    {"ticker": "QLD", "weight": 30},
    {"ticker": "TQQQ", "weight": 10},
]

if "portfolio_rows" not in st.session_state:
    st.session_state.portfolio_rows = DEFAULT_PORTFOLIO.copy()


def render_portfolio_editor():
    rows = st.session_state.portfolio_rows
    updated = []
    cols_header = st.columns([3, 2, 1])
    cols_header[0].markdown("**ETF 代码**")
    cols_header[1].markdown("**仓位 (%)**")
    cols_header[2].markdown("**删除**")

    for i, row in enumerate(rows):
        c1, c2, c3 = st.columns([3, 2, 1])
        ticker = c1.text_input(
            f"ticker_{i}", value=row["ticker"], label_visibility="collapsed", key=f"t_{i}"
        ).upper().strip()
        weight = c2.number_input(
            f"weight_{i}", min_value=0, max_value=100, value=row["weight"],
            label_visibility="collapsed", key=f"w_{i}"
        )
        delete = c3.button("✕", key=f"del_{i}")
        if not delete:
            updated.append({"ticker": ticker, "weight": weight})

    st.session_state.portfolio_rows = updated


render_portfolio_editor()

col_add, col_reset, _ = st.columns([1, 1, 4])
if col_add.button("＋ 添加 ETF"):
    st.session_state.portfolio_rows.append({"ticker": "", "weight": 0})
    st.rerun()
if col_reset.button("重置默认"):
    st.session_state.portfolio_rows = DEFAULT_PORTFOLIO.copy()
    st.rerun()

total_weight = sum(r["weight"] for r in st.session_state.portfolio_rows)
weight_color = "green" if total_weight == 100 else "red"
st.markdown(
    f"仓位合计：<span style='color:{weight_color};font-weight:bold'>{total_weight}%</span>（需等于 100%）",
    unsafe_allow_html=True,
)

st.divider()

# ── Bias correction parameters (shared) ───────────────────────────────────────
st.header("回测修正参数")
st.caption(
    "这三个参数直接影响回测的真实性。默认值已修正常见偏差，可调整后对比差异。"
)

bc1, bc2, bc3 = st.columns(3)

signal_lag = bc1.number_input(
    "信号延迟（交易日）",
    min_value=0, max_value=5, value=1, step=1,
    help=(
        "**0 = 存在前瞻偏差**：用当天收盘价决定当天持仓，"
        "相当于提前知道了收盘价。SMA 窗口越短，偏差越大。\n\n"
        "**1（推荐）= 无偏差**：用昨天的收盘信号决定今天的持仓，"
        "模拟真实操作。"
    ),
)

with bc2:
    st.markdown("**交易成本模式**")
    fee_mode = st.radio(
        "fee_mode",
        ["富途牛牛（逐笔精算）", "固定费率（%）", "不计成本"],
        index=0,
        label_visibility="collapsed",
        help=(
            "**富途牛牛**：按实际费率逐笔计算（佣金 $0.0049/股 + 平台费 $0.005/股 "
            "+ 交收费 $0.003/股 上限$7 + 卖出时 SEC 费 0.00278% + FINRA $0.000166/股），"
            "约 0.015%–0.03%/笔。\n\n"
            "**固定费率**：手动指定每次换仓的成本比例。\n\n"
            "**不计成本**：忽略所有交易摩擦（乐观上界）。"
        ),
    )
    if fee_mode == "固定费率（%）":
        custom_cost_pct = st.number_input(
            "费率（%）", min_value=0.0, max_value=1.0,
            value=0.05, step=0.01, format="%.3f",
            label_visibility="collapsed",
        )
        futu_fees = False
        transaction_cost = custom_cost_pct / 100.0
    elif fee_mode == "富途牛牛（逐笔精算）":
        futu_fees = True
        transaction_cost = 0.0
        # Preview: estimated fee for a sample trade
        sample_pv = 1_000_000
        rows_preview = st.session_state.portfolio_rows
        cond_tickers = [r["ticker"] for r in rows_preview
                        if r["ticker"] and r["ticker"] != SIGNAL_TICKER]
        if cond_tickers:
            sample_lines = []
            for r in rows_preview:
                t = r["ticker"]
                if t and t != SIGNAL_TICKER:
                    tv = sample_pv * r["weight"] / 100
                    lev = LEVERAGE_MAP.get(t, 1)
                    proxy_px = 200 * lev  # rough proxy
                    fee_sell = _futu_fee(tv, proxy_px, is_sell=True)
                    fee_buy  = _futu_fee(tv, proxy_px, is_sell=False)
                    sample_lines.append(
                        f"{t}（${tv:,.0f}）卖出 ≈ ${fee_sell:.1f}，"
                        f"买入 ≈ ${fee_buy:.1f}"
                    )
            st.caption("每笔估算（$1M 组合，ETF 价格按 QQQ 均价估算）：\n" +
                       "\n".join(sample_lines))
    else:
        futu_fees = False
        transaction_cost = 0.0

bc3.markdown("**⚠️ 杠杆 ETF 模拟说明**")
bc3.warning(
    "早期无实际数据时用 QQQ×N 模拟，**忽略了波动率拖累**：\n"
    "- QLD (2×)：约 **−4%/年**\n"
    "- TQQQ (3×)：约 **−12%/年**\n\n"
    "实际早期收益会低于模拟值。"
)

lag_label = "✅ 无偏差" if signal_lag >= 1 else "⚠️ 含前瞻偏差"
if fee_mode == "富途牛牛（逐笔精算）":
    cost_label = "富途牛牛实际费率"
elif fee_mode == "固定费率（%）":
    cost_label = f"固定费率 {transaction_cost*100:.3f}%"
else:
    cost_label = "不计成本"
st.caption(f"当前设置：信号延迟 {signal_lag} 日（{lag_label}）· {cost_label}")

st.divider()


# ── Helper: compute summary stats from daily_values ──────────────────────────
def compute_stats(daily_values: pd.Series) -> dict:
    dv = daily_values.dropna()
    final = dv.iloc[-1]
    total_ret = (final / 1_000_000 - 1) * 100
    n_years = (dv.index[-1] - dv.index[0]).days / 365.25
    cagr = ((final / 1_000_000) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    max_dd = ((daily_values - daily_values.cummax()) / daily_values.cummax() * 100).min()
    return {"最终资产总值": final, "总收益率": total_ret, "CAGR": cagr, "最大回撤": max_dd}


def compute_stats_period(daily_values: pd.Series, start=None, end=None) -> dict:
    """Compute stats for a sub-period. CAGR is relative to period start value."""
    dv = daily_values.dropna()
    if start is not None:
        dv = dv[dv.index >= pd.Timestamp(start)]
    if end is not None:
        dv = dv[dv.index <= pd.Timestamp(end)]
    if len(dv) < 20:
        return {"CAGR": None, "最大回撤": None}
    start_val = dv.iloc[0]
    end_val = dv.iloc[-1]
    n_years = (dv.index[-1] - dv.index[0]).days / 365.25
    cagr = ((end_val / start_val) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    max_dd = ((dv - dv.cummax()) / dv.cummax() * 100).min()
    return {"CAGR": cagr, "最大回撤": max_dd}


# ── Two backtest modes ────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["手动对比（最多 5 个 SMA）", "SMA 范围扫描 · Top 10"])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Manual comparison
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("SMA 参考值")

    if "sma_windows" not in st.session_state:
        st.session_state.sma_windows = [200]

    sma_cols = st.columns(6)
    sma_windows_updated = []
    to_delete = None

    for i, val in enumerate(st.session_state.sma_windows):
        with sma_cols[i]:
            new_val = st.number_input(
                f"SMA #{i+1}", min_value=5, max_value=500, value=val, step=1, key=f"sma_{i}"
            )
            sma_windows_updated.append(new_val)
            if len(st.session_state.sma_windows) > 1:
                if st.button("✕", key=f"del_sma_{i}"):
                    to_delete = i

    if to_delete is not None:
        st.session_state.sma_windows.pop(to_delete)
        st.rerun()
    else:
        st.session_state.sma_windows = sma_windows_updated

    with sma_cols[len(st.session_state.sma_windows)]:
        st.markdown("<br>", unsafe_allow_html=True)
        if len(st.session_state.sma_windows) < 5:
            if st.button("＋ 添加"):
                st.session_state.sma_windows.append(200)
                st.rerun()

    sma_windows = st.session_state.sma_windows

    run1 = st.button(
        "确认并运行回测", type="primary", key="run1", disabled=(total_weight != 100)
    )

    if run1:
        portfolio = [r for r in st.session_state.portfolio_rows if r["ticker"]]
        if not any(p["ticker"] == SIGNAL_TICKER for p in portfolio):
            st.error(f"组合中必须包含 {SIGNAL_TICKER}。")
            st.stop()

        tickers = list(dict.fromkeys(p["ticker"] for p in portfolio))

        with st.spinner("正在下载/更新历史数据…"):
            try:
                price_data = get_price_data(tickers)
            except Exception as e:
                st.error(f"数据获取失败：{e}")
                st.stop()

        results = {}
        with st.spinner("正在运行回测…"):
            for sma in sma_windows:
                label = f"SMA{sma}"
                try:
                    yearly_df, daily_values = run_backtest(portfolio, price_data, sma_window=sma, signal_lag=signal_lag, transaction_cost=transaction_cost, futu_fees=futu_fees)
                    results[label] = (yearly_df, daily_values)
                except Exception as e:
                    st.error(f"{label} 回测失败：{e}")
                    st.stop()

        etf_tickers = [p["ticker"] for p in portfolio]
        first_yearly = list(results.values())[0][0]

        # Table
        st.subheader("回测结果（逐年）")
        display_df = pd.DataFrame(index=first_yearly.index)
        display_df.index.name = "年份"
        for t in etf_tickers:
            if t in first_yearly.columns:
                display_df[t] = first_yearly[t].apply(
                    lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
                )
        for label, (yearly_df, _) in results.items():
            display_df[f"资产总值({label})"] = yearly_df["资产总值"].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
            )
        st.dataframe(display_df, use_container_width=True)

        # Chart
        st.subheader("策略组合资产总值走势")
        COLORS = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
        fig = go.Figure()
        for i, (label, (_, dv)) in enumerate(results.items()):
            fig.add_trace(go.Scatter(
                x=dv.index, y=dv.values, mode="lines", name=label,
                line=dict(color=COLORS[i % len(COLORS)], width=2),
            ))
        qqq_px = price_data[SIGNAL_TICKER].dropna()
        qqq_bh = 1_000_000 * qqq_px / qqq_px.iloc[0]
        fig.add_trace(go.Scatter(
            x=qqq_bh.index, y=qqq_bh.values, mode="lines",
            name="QQQ 买入持有（参考）",
            line=dict(color="#ff7f0e", width=1.5, dash="dot"),
        ))
        fig.update_layout(
            yaxis_title="资产总值 (USD)", xaxis_title="日期",
            hovermode="x unified", yaxis_tickformat="$,.0f",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Summary stats
        st.subheader("策略统计摘要")
        stat_cols = st.columns(len(results))
        for col, (label, (_, dv)) in zip(stat_cols, results.items()):
            s = compute_stats(dv)
            col.markdown(f"**{label}**")
            col.metric("最终资产总值", f"${s['最终资产总值']:,.0f}", f"{s['总收益率']:+.1f}%")
            col.metric("年化收益率 (CAGR)", f"{s['CAGR']:.2f}%")
            col.metric("最大回撤", f"{s['最大回撤']:.1f}%")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — SMA range sweep + out-of-sample validation
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("SMA 扫描范围")

    sc1, sc2, sc3, sc4 = st.columns([1, 1, 1, 2])
    sweep_start = sc1.number_input("起始 SMA", min_value=5, max_value=490, value=30, step=5)
    sweep_end   = sc2.number_input("结束 SMA", min_value=10, max_value=500, value=250, step=5)
    sweep_step  = sc3.number_input("步长",     min_value=1, max_value=50,  value=5,   step=1)
    sort_by     = sc4.selectbox(
        "Top 10 排序依据",
        ["CAGR（年化收益率）", "最终资产总值", "最大回撤（最小）"],
    )

    # ── Out-of-sample toggle ──────────────────────────────────────────────────
    st.divider()
    oos_enabled = st.toggle("启用样本外测试（验证过拟合）", value=True)
    if oos_enabled:
        import datetime
        oc1, oc2 = st.columns([1, 3])
        split_date = oc1.date_input(
            "训练期 / 测试期 分割日期",
            value=datetime.date(2015, 1, 1),
            min_value=datetime.date(2000, 1, 1),
            max_value=datetime.date.today() - datetime.timedelta(days=365),
            help="分割点之前为训练期（用于找最优 SMA），之后为测试期（验证结论是否成立）。",
        )
        oc2.info(
            f"训练期：数据起始 → {split_date}　|　"
            f"测试期：{split_date} → 今天\n\n"
            "**判读方法**：若训练期 Top SMA 在测试期排名大幅下滑，说明结论可能是过拟合。"
        )
    st.divider()

    if sweep_end <= sweep_start:
        st.warning("结束 SMA 必须大于起始 SMA。")
    else:
        sweep_list = list(range(int(sweep_start), int(sweep_end) + 1, int(sweep_step)))
        st.caption(f"共 {len(sweep_list)} 个 SMA 值：{sweep_list[0]} → {sweep_list[-1]}，步长 {int(sweep_step)}")

        run2 = st.button(
            f"运行 SMA 扫描（{len(sweep_list)} 个策略）", type="primary", key="run2",
            disabled=(total_weight != 100),
        )

        if run2:
            portfolio = [r for r in st.session_state.portfolio_rows if r["ticker"]]
            if not any(p["ticker"] == SIGNAL_TICKER for p in portfolio):
                st.error(f"组合中必须包含 {SIGNAL_TICKER}。")
                st.stop()

            tickers = list(dict.fromkeys(p["ticker"] for p in portfolio))

            with st.spinner("正在下载/更新历史数据…"):
                try:
                    price_data = get_price_data(tickers)
                except Exception as e:
                    st.error(f"数据获取失败：{e}")
                    st.stop()

            # Sweep: compute full / train / test stats per SMA
            sweep_rows = []
            progress = st.progress(0, text="正在扫描 SMA…")
            for idx, sma in enumerate(sweep_list):
                try:
                    _, dv = run_backtest(portfolio, price_data, sma_window=sma, signal_lag=signal_lag, transaction_cost=transaction_cost, futu_fees=futu_fees)
                    row = {"SMA": sma}
                    full = compute_stats(dv)
                    row["CAGR_全段"]   = full["CAGR"]
                    row["回撤_全段"]   = full["最大回撤"]
                    row["总值_全段"]   = full["最终资产总值"]
                    if oos_enabled:
                        tr = compute_stats_period(dv, end=split_date)
                        te = compute_stats_period(dv, start=split_date)
                        row["CAGR_训练"] = tr["CAGR"]
                        row["回撤_训练"] = tr["最大回撤"]
                        row["CAGR_测试"] = te["CAGR"]
                        row["回撤_测试"] = te["最大回撤"]
                    sweep_rows.append(row)
                except Exception:
                    pass
                progress.progress((idx + 1) / len(sweep_list), text=f"SMA{sma} ({idx+1}/{len(sweep_list)})")
            progress.empty()

            if not sweep_rows:
                st.error("扫描未产生任何结果。")
                st.stop()

            sweep_df = pd.DataFrame(sweep_rows).set_index("SMA")

            # ── Determine sort column (full period) ───────────────────────────
            sort_col_map = {
                "CAGR（年化收益率）": ("CAGR_全段", False),
                "最终资产总值":       ("总值_全段",  False),
                "最大回撤（最小）":   ("回撤_全段",  True),
            }
            sort_col, sort_asc = sort_col_map[sort_by]
            ranked_full = sweep_df.sort_values(sort_col, ascending=sort_asc)
            top10_smas  = set(ranked_full.head(10).index.tolist())

            # ── Top 10 table（全段）─────────────────────────────────────────
            st.subheader(f"Top 10 · 全段（按 {sort_by}）")
            top10_df = ranked_full.head(10)[["总值_全段", "CAGR_全段", "回撤_全段"]].copy()
            top10_df.index.name = "SMA 窗口"
            top10_df.columns     = ["最终资产总值", "CAGR", "最大回撤"]
            fmt = top10_df.copy()
            fmt["最终资产总值"] = fmt["最终资产总值"].apply(lambda x: f"${x:,.0f}")
            fmt["CAGR"]        = fmt["CAGR"].apply(lambda x: f"{x:.2f}%")
            fmt["最大回撤"]    = fmt["最大回撤"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(fmt, use_container_width=True)

            # ── CAGR bar chart（全段）────────────────────────────────────────
            st.subheader("全局 CAGR 分布（所有 SMA · 全段）")
            bar_colors = ["#1f77b4" if s in top10_smas else "#aec7e8" for s in sweep_df.index]
            fig2 = go.Figure(go.Bar(
                x=sweep_df.index, y=sweep_df["CAGR_全段"],
                marker_color=bar_colors,
                hovertemplate="SMA%{x}<br>CAGR: %{y:.2f}%<extra></extra>",
            ))
            fig2.add_annotation(text="深色 = Top 10", xref="paper", yref="paper",
                                x=1, y=1.06, showarrow=False,
                                font=dict(size=11, color="#1f77b4"))
            fig2.update_layout(xaxis_title="SMA 窗口", yaxis_title="CAGR (%)",
                               height=380, showlegend=False, bargap=0.15)
            st.plotly_chart(fig2, use_container_width=True)

            # ══════════════════════════════════════════════════════════════════
            # Out-of-sample section
            # ══════════════════════════════════════════════════════════════════
            if oos_enabled:
                st.divider()
                st.subheader("样本外测试结果")

                # Rank by CAGR in train & test periods
                valid = sweep_df.dropna(subset=["CAGR_训练", "CAGR_测试"])
                valid = valid.copy()
                valid["训练期排名"] = valid["CAGR_训练"].rank(ascending=False).astype(int)
                valid["测试期排名"] = valid["CAGR_测试"].rank(ascending=False).astype(int)
                valid["排名变化"]   = valid["训练期排名"] - valid["测试期排名"]  # positive = improved in test

                # ── Comparison table: Top 10 训练期 → 测试期 ─────────────────
                st.markdown(f"**训练期 Top 10（{sweep_list[0]}–{sweep_list[-1]}）在测试期的表现**")
                top10_train = valid.sort_values("训练期排名").head(10)
                cmp = top10_train[["CAGR_训练", "回撤_训练", "训练期排名",
                                   "CAGR_测试", "回撤_测试", "测试期排名", "排名变化"]].copy()
                cmp.index.name = "SMA 窗口"
                cmp.columns = ["训练期 CAGR", "训练期回撤", "训练期排名",
                               "测试期 CAGR", "测试期回撤", "测试期排名", "排名变化 ↑好↓差"]

                def fmt_rank_change(v):
                    if v > 0:   return f"↑{v}"
                    elif v < 0: return f"↓{abs(v)}"
                    else:       return "—"

                display_cmp = cmp.copy()
                display_cmp["训练期 CAGR"] = cmp["训练期 CAGR"].apply(lambda x: f"{x:.2f}%")
                display_cmp["训练期回撤"]  = cmp["训练期回撤"].apply(lambda x: f"{x:.1f}%")
                display_cmp["测试期 CAGR"] = cmp["测试期 CAGR"].apply(lambda x: f"{x:.2f}%")
                display_cmp["测试期回撤"]  = cmp["测试期回撤"].apply(lambda x: f"{x:.1f}%")
                display_cmp["排名变化 ↑好↓差"] = cmp["排名变化 ↑好↓差"].apply(fmt_rank_change)
                st.dataframe(display_cmp, use_container_width=True)

                st.caption(
                    "排名变化：↑ 表示测试期排名比训练期更靠前（结论稳健）；"
                    "↓ 表示排名下滑（可能过拟合）。"
                )

                # ── Scatter: 训练期排名 vs 测试期排名 ────────────────────────
                st.markdown("**训练期排名 vs 测试期排名（散点图）**")
                top10_set = set(top10_train.index.tolist())
                pt_colors  = ["#1f77b4" if s in top10_set else "#aec7e8" for s in valid.index]
                pt_sizes   = [14 if s in top10_set else 7 for s in valid.index]

                fig_sc = go.Figure()
                # All points
                fig_sc.add_trace(go.Scatter(
                    x=valid["训练期排名"], y=valid["测试期排名"],
                    mode="markers",
                    marker=dict(color=pt_colors, size=pt_sizes, line=dict(width=0.5, color="white")),
                    text=[f"SMA{s}" for s in valid.index],
                    hovertemplate="%{text}<br>训练期排名: %{x}<br>测试期排名: %{y}<extra></extra>",
                    showlegend=False,
                ))
                # Diagonal reference line (perfect correlation)
                n = len(valid)
                fig_sc.add_trace(go.Scatter(
                    x=[1, n], y=[1, n], mode="lines",
                    line=dict(color="gray", dash="dash", width=1),
                    name="完美相关（对角线）",
                ))
                # Label top10 points
                for sma, row in top10_train.iterrows():
                    fig_sc.add_annotation(
                        x=row["训练期排名"], y=row["测试期排名"],
                        text=f"SMA{sma}", showarrow=False,
                        font=dict(size=9, color="#1f77b4"), yshift=8,
                    )
                fig_sc.update_layout(
                    xaxis_title="训练期排名（1 = 最优）",
                    yaxis_title="测试期排名（1 = 最优）",
                    height=420,
                    legend=dict(orientation="h", y=1.08),
                )
                fig_sc.update_xaxes(autorange="reversed")
                fig_sc.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_sc, use_container_width=True)
                st.caption(
                    "点越靠近对角线，说明训练期排名与测试期排名一致（策略稳健）。"
                    "深色点 = 训练期 Top 10。若深色点大量偏离对角线右上角，说明过拟合严重。"
                )
