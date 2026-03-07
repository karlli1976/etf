import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backtest import LEVERAGE_MAP, SIGNAL_TICKER, _futu_fee, run_backtest
from data_manager import get_price_data
from i18n import t

st.set_page_config(page_title="ETF Backtester", layout="wide")

# ── Language toggle ───────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "zh"
lang = st.session_state.lang

title_col, lang_col = st.columns([11, 1])
with title_col:
    st.title(t("app_title", lang))
    st.caption(t("app_caption", lang))
with lang_col:
    st.markdown("<br>", unsafe_allow_html=True)
    next_lang, btn_label = ("en", "EN") if lang == "zh" else ("zh", "中文")
    if st.button(btn_label, key="lang_toggle"):
        st.session_state.lang = next_lang
        st.rerun()

# ── Portfolio input (shared) ──────────────────────────────────────────────────
st.header(t("portfolio_header", lang))

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
    h1, h2, h3 = st.columns([3, 2, 1])
    h1.markdown(f"**{t('col_ticker', lang)}**")
    h2.markdown(f"**{t('col_weight', lang)}**")
    h3.markdown(f"**{t('col_delete', lang)}**")

    for i, row in enumerate(rows):
        c1, c2, c3 = st.columns([3, 2, 1])
        ticker = c1.text_input(
            f"ticker_{i}", value=row["ticker"],
            label_visibility="collapsed", key=f"t_{i}",
        ).upper().strip()
        weight = c2.number_input(
            f"weight_{i}", min_value=0, max_value=100, value=row["weight"],
            label_visibility="collapsed", key=f"w_{i}",
        )
        if not c3.button("✕", key=f"del_{i}"):
            updated.append({"ticker": ticker, "weight": weight})

    st.session_state.portfolio_rows = updated


render_portfolio_editor()

col_add, col_reset, _ = st.columns([1, 1, 4])
if col_add.button(t("btn_add_etf", lang)):
    st.session_state.portfolio_rows.append({"ticker": "", "weight": 0})
    st.rerun()
if col_reset.button(t("btn_reset", lang)):
    st.session_state.portfolio_rows = DEFAULT_PORTFOLIO.copy()
    st.rerun()

total_weight = sum(r["weight"] for r in st.session_state.portfolio_rows)
weight_color = "green" if total_weight == 100 else "red"
st.markdown(
    f"<span style='color:{weight_color};font-weight:bold'>"
    + t("weight_total", lang, total=total_weight)
    + "</span>",
    unsafe_allow_html=True,
)

st.divider()

# ── Bias correction parameters (shared) ───────────────────────────────────────
st.header(t("correction_header", lang))
st.caption(t("correction_caption", lang))

bc1, bc2, bc3 = st.columns(3)

signal_lag = bc1.number_input(
    t("signal_lag_label", lang),
    min_value=0, max_value=5, value=1, step=1,
    help=t("signal_lag_help", lang),
)

with bc2:
    st.markdown(f"**{t('fee_mode_title', lang)}**")
    fee_options = [
        t("fee_mode_futu", lang),
        t("fee_mode_fixed", lang),
        t("fee_mode_none", lang),
    ]
    fee_mode_idx = st.radio(
        "fee_mode", fee_options, index=0,
        label_visibility="collapsed",
        help=t("fee_mode_help", lang),
    )
    if fee_mode_idx == t("fee_mode_fixed", lang):
        custom_cost_pct = st.number_input(
            t("fee_rate_label", lang), min_value=0.0, max_value=1.0,
            value=0.05, step=0.01, format="%.3f",
            label_visibility="collapsed",
        )
        futu_fees = False
        transaction_cost = custom_cost_pct / 100.0
        fee_mode = "fixed"
    elif fee_mode_idx == t("fee_mode_futu", lang):
        futu_fees = True
        transaction_cost = 0.0
        fee_mode = "futu"
        sample_pv = 1_000_000
        cond_rows = [r for r in st.session_state.portfolio_rows
                     if r["ticker"] and r["ticker"] != SIGNAL_TICKER]
        if cond_rows:
            lines = []
            for r in cond_rows:
                tv = sample_pv * r["weight"] / 100
                lev = LEVERAGE_MAP.get(r["ticker"], 1)
                px = 200 * lev
                lines.append(t("fee_preview_line_sell", lang,
                               ticker=r["ticker"], value=tv,
                               sell=_futu_fee(tv, px, True),
                               buy=_futu_fee(tv, px, False)))
            st.caption(t("fee_preview_caption", lang, lines="\n".join(lines)))
    else:
        futu_fees = False
        transaction_cost = 0.0
        fee_mode = "none"

bc3.markdown(f"**{t('leverage_warning_title', lang)}**")
bc3.warning(t("leverage_warning_body", lang))

lag_label = t("lag_ok", lang) if signal_lag >= 1 else t("lag_bias", lang)
if fee_mode == "futu":
    cost_label = t("cost_futu", lang)
elif fee_mode == "fixed":
    cost_label = t("cost_fixed", lang, pct=transaction_cost * 100)
else:
    cost_label = t("cost_none", lang)
st.caption(t("status_caption", lang, lag=signal_lag, lag_label=lag_label, cost_label=cost_label))

st.divider()


# ── Helpers ───────────────────────────────────────────────────────────────────
def compute_stats(daily_values: pd.Series) -> dict:
    dv = daily_values.dropna()
    final = dv.iloc[-1]
    total_ret = (final / 1_000_000 - 1) * 100
    n_years = (dv.index[-1] - dv.index[0]).days / 365.25
    cagr = ((final / 1_000_000) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    max_dd = ((daily_values - daily_values.cummax()) / daily_values.cummax() * 100).min()
    return {"最终资产总值": final, "总收益率": total_ret, "CAGR": cagr, "最大回撤": max_dd}


def compute_stats_period(daily_values: pd.Series, start=None, end=None) -> dict:
    dv = daily_values.dropna()
    if start is not None:
        dv = dv[dv.index >= pd.Timestamp(start)]
    if end is not None:
        dv = dv[dv.index <= pd.Timestamp(end)]
    if len(dv) < 20:
        return {"CAGR": None, "最大回撤": None}
    n_years = (dv.index[-1] - dv.index[0]).days / 365.25
    cagr = ((dv.iloc[-1] / dv.iloc[0]) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    max_dd = ((dv - dv.cummax()) / dv.cummax() * 100).min()
    return {"CAGR": cagr, "最大回撤": max_dd}


def _run(portfolio, price_data, sma):
    return run_backtest(
        portfolio, price_data,
        sma_window=sma, signal_lag=signal_lag,
        transaction_cost=transaction_cost, futu_fees=futu_fees,
    )


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([t("tab1_label", lang), t("tab2_label", lang)])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Manual comparison
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(t("tab1_sma_header", lang))

    if "sma_windows" not in st.session_state:
        st.session_state.sma_windows = [200]

    sma_cols = st.columns(11)
    sma_windows_updated = []
    to_delete = None

    for i, val in enumerate(st.session_state.sma_windows):
        with sma_cols[i]:
            new_val = st.number_input(
                f"SMA #{i+1}", min_value=5, max_value=500,
                value=val, step=1, key=f"sma_{i}",
            )
            sma_windows_updated.append(new_val)
            if len(st.session_state.sma_windows) > 1 and st.button("✕", key=f"del_sma_{i}"):
                to_delete = i

    if to_delete is not None:
        st.session_state.sma_windows.pop(to_delete)
        st.rerun()
    else:
        st.session_state.sma_windows = sma_windows_updated

    with sma_cols[len(st.session_state.sma_windows)]:
        st.markdown("<br>", unsafe_allow_html=True)
        if len(st.session_state.sma_windows) < 10 and st.button(t("btn_add_sma", lang)):
            st.session_state.sma_windows.append(200)
            st.rerun()

    sma_windows = st.session_state.sma_windows

    if st.button(t("btn_run", lang), type="primary", key="run1", disabled=(total_weight != 100)):
        portfolio = [r for r in st.session_state.portfolio_rows if r["ticker"]]
        if not any(p["ticker"] == SIGNAL_TICKER for p in portfolio):
            st.error(t("error_no_qqq", lang))
            st.stop()

        tickers = list(dict.fromkeys(p["ticker"] for p in portfolio))

        with st.spinner(t("spinner_download", lang)):
            try:
                price_data = get_price_data(tickers)
            except Exception as e:
                st.error(t("error_download", lang, e=e))
                st.stop()

        results = {}
        with st.spinner(t("spinner_backtest", lang)):
            for sma in sma_windows:
                label = f"SMA{sma}"
                try:
                    yearly_df, daily_values = _run(portfolio, price_data, sma)
                    results[label] = (yearly_df, daily_values)
                except Exception as e:
                    st.error(t("error_backtest", lang, label=label, e=e))
                    st.stop()

        etf_tickers = [p["ticker"] for p in portfolio]
        first_yearly = list(results.values())[0][0]

        # Yearly table
        st.subheader(t("tab1_table_header", lang))
        display_df = pd.DataFrame(index=first_yearly.index)
        display_df.index.name = t("col_year", lang)
        for tk in etf_tickers:
            if tk in first_yearly.columns:
                display_df[tk] = first_yearly[tk].apply(
                    lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
                )
        for label, (yearly_df, _) in results.items():
            display_df[t("col_portfolio_value", lang, label=label)] = yearly_df["资产总值"].apply(
                lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
            )
        st.dataframe(display_df, use_container_width=True)

        # Equity curve chart
        st.subheader(t("tab1_chart_header", lang))
        COLORS = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
                  "#e377c2", "#7f7f7f", "#bcbd22", "#17becf", "#aec7e8"]
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
            name=t("qqq_bh_label", lang),
            line=dict(color="#ff7f0e", width=1.5, dash="dot"),
        ))
        fig.update_layout(
            yaxis_title=t("chart_y_portfolio", lang),
            xaxis_title=t("chart_x_date", lang),
            hovermode="x unified", yaxis_tickformat="$,.0f",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Summary stats
        st.subheader(t("tab1_stats_header", lang))
        stat_cols = st.columns(len(results))
        for col, (label, (_, dv)) in zip(stat_cols, results.items()):
            s = compute_stats(dv)
            col.markdown(f"**{label}**")
            col.metric(t("metric_final", lang), f"${s['最终资产总值']:,.0f}", f"{s['总收益率']:+.1f}%")
            col.metric(t("metric_cagr", lang), f"{s['CAGR']:.2f}%")
            col.metric(t("metric_max_dd", lang), f"{s['最大回撤']:.1f}%")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — SMA range sweep + out-of-sample validation
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(t("tab2_sweep_header", lang))

    sc1, sc2, sc3, sc4 = st.columns([1, 1, 1, 2])
    sweep_start = sc1.number_input(t("sweep_start", lang), min_value=5,  max_value=490, value=30,  step=5)
    sweep_end   = sc2.number_input(t("sweep_end",   lang), min_value=10, max_value=500, value=250, step=5)
    sweep_step  = sc3.number_input(t("sweep_step",  lang), min_value=1,  max_value=50,  value=5,   step=1)

    sort_opts = [t("sort_cagr", lang), t("sort_value", lang), t("sort_drawdown", lang)]
    sort_by   = sc4.selectbox(t("sort_by_label", lang), sort_opts)

    st.divider()
    oos_enabled = st.toggle(t("oos_toggle", lang), value=True)
    if oos_enabled:
        oc1, oc2 = st.columns([1, 3])
        split_date = oc1.date_input(
            t("split_date_label", lang),
            value=datetime.date(2015, 1, 1),
            min_value=datetime.date(2000, 1, 1),
            max_value=datetime.date.today() - datetime.timedelta(days=365),
            help=t("split_date_help", lang),
        )
        oc2.info(t("oos_info", lang, split_date=split_date))
    st.divider()

    if sweep_end <= sweep_start:
        st.warning(t("sweep_warning", lang))
    else:
        sweep_list = list(range(int(sweep_start), int(sweep_end) + 1, int(sweep_step)))
        st.caption(t("sweep_caption", lang, n=len(sweep_list),
                     start=sweep_list[0], end=sweep_list[-1], step=int(sweep_step)))

        if st.button(t("btn_sweep", lang, n=len(sweep_list)),
                     type="primary", key="run2", disabled=(total_weight != 100)):
            portfolio = [r for r in st.session_state.portfolio_rows if r["ticker"]]
            if not any(p["ticker"] == SIGNAL_TICKER for p in portfolio):
                st.error(t("error_no_qqq", lang))
                st.stop()

            tickers = list(dict.fromkeys(p["ticker"] for p in portfolio))

            with st.spinner(t("spinner_download", lang)):
                try:
                    price_data = get_price_data(tickers)
                except Exception as e:
                    st.error(t("error_download", lang, e=e))
                    st.stop()

            sweep_rows = []
            progress = st.progress(0, text=t("spinner_sweep", lang))
            for idx, sma in enumerate(sweep_list):
                try:
                    _, dv = _run(portfolio, price_data, sma)
                    row = {"SMA": sma}
                    full = compute_stats(dv)
                    row["CAGR_全段"] = full["CAGR"]
                    row["回撤_全段"] = full["最大回撤"]
                    row["总值_全段"] = full["最终资产总值"]
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
                progress.progress((idx + 1) / len(sweep_list),
                                  text=t("sweep_progress", lang, sma=sma, i=idx+1, n=len(sweep_list)))
            progress.empty()

            if not sweep_rows:
                st.error(t("sweep_empty_error", lang))
                st.stop()

            sweep_df = pd.DataFrame(sweep_rows).set_index("SMA")

            sort_col_map = {
                t("sort_cagr",     lang): ("CAGR_全段", False),
                t("sort_value",    lang): ("总值_全段",  False),
                t("sort_drawdown", lang): ("回撤_全段",  True),
            }
            sort_col, sort_asc = sort_col_map[sort_by]
            ranked_full = sweep_df.sort_values(sort_col, ascending=sort_asc)
            top10_smas  = set(ranked_full.head(10).index.tolist())

            # Top 10 table
            st.subheader(t("top10_header", lang, sort_by=sort_by))
            top10_raw = ranked_full.head(10)[["总值_全段", "CAGR_全段", "回撤_全段"]].copy()
            top10_raw.index.name = t("col_sma_window", lang)
            top10_raw.columns = [t("col_final_value", lang), t("col_cagr", lang), t("col_max_dd", lang)]
            fmt = top10_raw.copy()
            fmt[t("col_final_value", lang)] = fmt[t("col_final_value", lang)].apply(lambda x: f"${x:,.0f}")
            fmt[t("col_cagr",        lang)] = fmt[t("col_cagr",        lang)].apply(lambda x: f"{x:.2f}%")
            fmt[t("col_max_dd",      lang)] = fmt[t("col_max_dd",      lang)].apply(lambda x: f"{x:.1f}%")
            st.dataframe(fmt, use_container_width=True)

            # CAGR bar chart
            st.subheader(t("cagr_chart_header", lang))
            bar_colors = ["#1f77b4" if s in top10_smas else "#aec7e8" for s in sweep_df.index]
            fig2 = go.Figure(go.Bar(
                x=sweep_df.index, y=sweep_df["CAGR_全段"],
                marker_color=bar_colors,
                hovertemplate=f"SMA%{{x}}<br>{t('col_cagr', lang)}: %{{y:.2f}}%<extra></extra>",
            ))
            fig2.add_annotation(text=t("top10_annotation", lang),
                                xref="paper", yref="paper", x=1, y=1.06,
                                showarrow=False, font=dict(size=11, color="#1f77b4"))
            fig2.update_layout(
                xaxis_title=t("col_sma_window", lang),
                yaxis_title=t("chart_y_cagr", lang),
                height=380, showlegend=False, bargap=0.15,
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Out-of-sample section
            if oos_enabled:
                st.divider()
                st.subheader(t("oos_section_header", lang))

                valid = sweep_df.dropna(subset=["CAGR_训练", "CAGR_测试"]).copy()
                valid["训练期排名"] = valid["CAGR_训练"].rank(ascending=False).astype(int)
                valid["测试期排名"] = valid["CAGR_测试"].rank(ascending=False).astype(int)
                valid["排名变化"]   = valid["训练期排名"] - valid["测试期排名"]

                st.markdown(f"**{t('oos_comparison_title', lang, start=sweep_list[0], end=sweep_list[-1])}**")
                top10_train = valid.sort_values("训练期排名").head(10)

                cmp = top10_train[["CAGR_训练", "回撤_训练", "训练期排名",
                                   "CAGR_测试", "回撤_测试", "测试期排名", "排名变化"]].copy()
                cmp.index.name = t("col_sma_window", lang)
                cmp.columns = [
                    t("col_train_cagr", lang), t("col_train_dd", lang), t("col_train_rank", lang),
                    t("col_test_cagr",  lang), t("col_test_dd",  lang), t("col_test_rank",  lang),
                    t("col_rank_change", lang),
                ]

                def fmt_rank_change(v):
                    return f"↑{v}" if v > 0 else (f"↓{abs(v)}" if v < 0 else "—")

                disp = cmp.copy()
                disp[t("col_train_cagr", lang)] = cmp[t("col_train_cagr", lang)].apply(lambda x: f"{x:.2f}%")
                disp[t("col_train_dd",   lang)] = cmp[t("col_train_dd",   lang)].apply(lambda x: f"{x:.1f}%")
                disp[t("col_test_cagr",  lang)] = cmp[t("col_test_cagr",  lang)].apply(lambda x: f"{x:.2f}%")
                disp[t("col_test_dd",    lang)] = cmp[t("col_test_dd",    lang)].apply(lambda x: f"{x:.1f}%")
                disp[t("col_rank_change",lang)] = cmp[t("col_rank_change",lang)].apply(fmt_rank_change)
                st.dataframe(disp, use_container_width=True)
                st.caption(t("oos_rank_caption", lang))

                # Scatter plot
                st.markdown(f"**{t('scatter_title', lang)}**")
                top10_set = set(top10_train.index.tolist())
                pt_colors = ["#1f77b4" if s in top10_set else "#aec7e8" for s in valid.index]
                pt_sizes  = [14 if s in top10_set else 7 for s in valid.index]

                fig_sc = go.Figure()
                fig_sc.add_trace(go.Scatter(
                    x=valid["训练期排名"], y=valid["测试期排名"],
                    mode="markers",
                    marker=dict(color=pt_colors, size=pt_sizes,
                                line=dict(width=0.5, color="white")),
                    text=[f"SMA{s}" for s in valid.index],
                    hovertemplate=f"%{{text}}<br>{t('col_train_rank', lang)}: %{{x}}<br>{t('col_test_rank', lang)}: %{{y}}<extra></extra>",
                    showlegend=False,
                ))
                n = len(valid)
                fig_sc.add_trace(go.Scatter(
                    x=[1, n], y=[1, n], mode="lines",
                    line=dict(color="gray", dash="dash", width=1),
                    name=t("scatter_diagonal", lang),
                ))
                for sma, row in top10_train.iterrows():
                    fig_sc.add_annotation(
                        x=row["训练期排名"], y=row["测试期排名"],
                        text=f"SMA{sma}", showarrow=False,
                        font=dict(size=9, color="#1f77b4"), yshift=8,
                    )
                fig_sc.update_layout(
                    xaxis_title=t("scatter_x", lang),
                    yaxis_title=t("scatter_y", lang),
                    height=420,
                    legend=dict(orientation="h", y=1.08),
                )
                fig_sc.update_xaxes(autorange="reversed")
                fig_sc.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_sc, use_container_width=True)
                st.caption(t("scatter_caption", lang))
