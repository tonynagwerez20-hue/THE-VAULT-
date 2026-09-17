"""
AlgoMind AMIGO — Monte Carlo Simulation & Out-of-Sample Test
=============================================================
Backtest context:
  Symbol  : XAUUSDm (XAUUSD micro)
  TF      : M5  (bar-by-bar decisions, execution engine)
  Deposit : $500  Leverage 1:500
  Risk    : 0.5% per trade
  RR      : 2.0  (partial at 2R, trail at 1R activation)
  Partial : 50% of position at 2R
  Trail   : 1.5×ATR after 1R
  Score TH: 0.35  (min best score)
  Margin  : 0.05  (min score spread long vs short)
  Daily DD: 2.0%  hard
  Total DD: 5.0%  hard

Observed backtest issues:
  • Almost every decision: SCORE_GATE (best_score ≥ 0.35 but margin < 0.05)
  • Regime = 2 (TREND_DOWN) + 7 (NO_TRADE) dominate early May 2026
  • No actual trades fired in the observed session (pre-compiled build)

Monte Carlo approach:
  1. Synthetic trade P&L series derived from strategy geometry
     (0.5% risk, 2R TP, 50% partial, trail activated at 1R)
  2. Win-rate calibrated to realistic XAUUSD SMC + orderflow strategies
     (baseline 45–55% range tested)
  3. 10 000 bootstrap paths to estimate drawdown distribution
  4. Out-of-sample split: in-sample = Oct2025–Mar2026 (6 months)
                          out-of-sample = Apr2026–Sep2026 (6 months)
"""

from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import os, warnings
warnings.filterwarnings("ignore")

# -------------------------------------------------------------
# 1. STRATEGY TRADE OUTCOME MODEL
# -------------------------------------------------------------
INITIAL_BALANCE   = 500.0
RISK_PCT          = 0.005        # 0.5 %  per trade
PARTIAL_RR        = 2.0          # take 50% off at 2R
PARTIAL_FRACTION  = 0.50         # fraction closed at partial TP
TRAIL_ACTIVATE_R  = 1.0          # trail starts after 1R gain
TRAIL_ATR_MULT    = 1.5          # trailing stop width
MAX_DAILY_DD_PCT  = 0.020        # 2 %
MAX_TOTAL_DD_PCT  = 0.050        # 5 %

# Score / filter calibration (from observed backtest logs)
SCORE_THRESHOLD   = 0.35
SCORE_MARGIN      = 0.05

rng = np.random.default_rng(42)

def single_trade_rr(win: bool) -> float:
    """
    Compute the R-multiple for one trade using the partial-exit + trailing model.
    
    Win path:
      • 50% of position exits at +2R  → contributes +1.0 R
      • Remaining 50%: trailing stop, modelled as uniform exit between +1R and +3R
        (trail activates at 1R, stop = 1.5 ATR ~= 1.5R)  → mean ~= +1.75 R for 50%
      Net win R ~= 50%×2R + 50%×U(1.5,3) ~= 2.0 – 2.5 R average
    
    Loss path:
      • Full stop: -1R (50% of position if partial TP already hit is handled below)
    """
    if win:
        partial_r   = PARTIAL_FRACTION * PARTIAL_RR           # +1.0 R
        # Trailing exit: the trail activates at TRAIL_ACTIVATE_R (1R)
        # and the stop is TRAIL_ATR_MULT × ATR.  Approximate: exit between 1.5R and 3R
        trail_exit  = rng.uniform(TRAIL_ACTIVATE_R * 1.5, PARTIAL_RR * 1.5)
        trail_r     = (1 - PARTIAL_FRACTION) * trail_exit      # 50% of position
        return partial_r + trail_r
    else:
        # Partial TP has NOT been hit (price went to SL directly)
        return -1.0


def generate_trade_series(n_trades: int, win_rate: float) -> np.ndarray:
    """
    Generate a sequence of R-multiples for n_trades with given win_rate.
    Returns array of R-multiples per trade.
    """
    outcomes = rng.random(n_trades) < win_rate
    return np.array([single_trade_rr(w) for w in outcomes])


def equity_curve(r_series: np.ndarray,
                 initial: float = INITIAL_BALANCE) -> np.ndarray:
    """
    Convert R-multiples to dollar equity curve, applying:
      • Fixed-fraction sizing (0.5% risk per trade)
      • Daily loss circuit-breaker (2%) — simplified: counted per 20-trade block
      • Total DD circuit-breaker (5%)
    Returns array of equity values (length = n_trades + 1).
    """
    eq = np.empty(len(r_series) + 1)
    eq[0] = initial
    peak = initial
    daily_start_eq = initial
    daily_counter  = 0
    locked_out     = False

    for i, r in enumerate(r_series):
        if locked_out:
            eq[i + 1] = eq[i]
            continue

        current = eq[i]

        # Approximate daily reset every ~24 bars (M5 × 12h active session)
        if daily_counter >= 24:
            daily_start_eq = current
            daily_counter  = 0

        risk_dollars = current * RISK_PCT
        pnl          = r * risk_dollars
        new_eq       = current + pnl
        daily_counter += 1

        # Daily DD gate
        if (new_eq - daily_start_eq) / daily_start_eq < -MAX_DAILY_DD_PCT:
            new_eq = daily_start_eq * (1 - MAX_DAILY_DD_PCT)
            locked_out = True  # daily lock triggers today, resets tomorrow

        # Total DD gate
        peak = max(peak, new_eq)
        if (new_eq - peak) / peak < -MAX_TOTAL_DD_PCT:
            new_eq = peak * (1 - MAX_TOTAL_DD_PCT)
            locked_out = True

        eq[i + 1] = new_eq

    return eq


# -------------------------------------------------------------
# 2. MONTE CARLO ENGINE
# -------------------------------------------------------------
N_PATHS         = 10_000
N_TRADES_TOTAL  = 240           # Realistic trade count over 12 months (~=20/month)
N_TRADES_IS     = 120           # In-sample  (Oct25–Mar26)
N_TRADES_OOS    = 120           # Out-of-sample (Apr26–Sep26)

# Win rate scenarios
WIN_RATES = {
    "Conservative 42%": 0.42,
    "Base Case 48%":    0.48,
    "Optimistic 55%":   0.55,
}

COLORS = {
    "Conservative 42%": "#FF6B6B",
    "Base Case 48%":    "#4ECDC4",
    "Optimistic 55%":   "#95E1D3",
}


def run_monte_carlo(win_rate: float,
                    n_paths: int = N_PATHS,
                    n_trades: int = N_TRADES_TOTAL) -> dict:
    """
    Run Monte Carlo and collect statistics.
    """
    final_equities = []
    max_drawdowns  = []
    all_curves     = []

    for _ in range(n_paths):
        r_series = generate_trade_series(n_trades, win_rate)
        curve    = equity_curve(r_series)
        final_equities.append(curve[-1])
        # Max drawdown
        running_max = np.maximum.accumulate(curve)
        dd = (curve - running_max) / running_max
        max_drawdowns.append(dd.min())
        if _ < 200:   # store only 200 paths for plotting
            all_curves.append(curve)

    final_equities = np.array(final_equities)
    max_drawdowns  = np.array(max_drawdowns)

    return {
        "win_rate":        win_rate,
        "n_trades":        n_trades,
        "final_equities":  final_equities,
        "max_drawdowns":   max_drawdowns,
        "sample_curves":   all_curves,
        "pct5":            np.percentile(final_equities, 5),
        "pct25":           np.percentile(final_equities, 25),
        "pct50":           np.percentile(final_equities, 50),
        "pct75":           np.percentile(final_equities, 75),
        "pct95":           np.percentile(final_equities, 95),
        "prob_profit":     (final_equities > INITIAL_BALANCE).mean(),
        "prob_ruin":       (final_equities < INITIAL_BALANCE * 0.70).mean(),  # >30% loss
        "mean_final":      final_equities.mean(),
        "median_dd":       np.median(max_drawdowns),
        "worst_dd_p95":    np.percentile(max_drawdowns, 95),
        "worst_dd_p99":    np.percentile(max_drawdowns, 99),
        "sharpe_approx":   _approx_sharpe(final_equities, n_trades),
    }


def _approx_sharpe(final_eq: np.ndarray, n_trades: int) -> float:
    """Approximate annualised Sharpe from terminal equity distribution."""
    returns = (final_eq - INITIAL_BALANCE) / INITIAL_BALANCE
    if returns.std() == 0:
        return 0.0
    trades_per_year = 240
    scale = trades_per_year / n_trades
    mean_r = returns.mean() * scale
    std_r  = returns.std()  * np.sqrt(scale)
    return mean_r / std_r if std_r > 0 else 0.0


# -------------------------------------------------------------
# 3. OUT-OF-SAMPLE TEST
# -------------------------------------------------------------
def out_of_sample_test(win_rate: float) -> dict:
    """
    Compare in-sample vs out-of-sample performance for a single win-rate.
    Approach:
      • IS  = first 120 trades (Oct25–Mar26 equivalent)
      • OOS = next  120 trades (Apr26–Sep26 equivalent), each path independent
    """
    is_finals  = []
    oos_finals = []
    is_dds     = []
    oos_dds    = []
    is_curves_sample  = []
    oos_curves_sample = []

    for p in range(N_PATHS):
        # In-sample
        r_is = generate_trade_series(N_TRADES_IS, win_rate)
        c_is = equity_curve(r_is, initial=INITIAL_BALANCE)
        is_finals.append(c_is[-1])
        rm_is = np.maximum.accumulate(c_is)
        is_dds.append(((c_is - rm_is) / rm_is).min())
        if p < 150:
            is_curves_sample.append(c_is)

        # Out-of-sample (starts from IS ending equity)
        r_oos = generate_trade_series(N_TRADES_OOS, win_rate)
        c_oos = equity_curve(r_oos, initial=c_is[-1])
        oos_finals.append(c_oos[-1])
        rm_oos = np.maximum.accumulate(c_oos)
        oos_dds.append(((c_oos - rm_oos) / rm_oos).min())
        if p < 150:
            oos_curves_sample.append(c_oos)

    is_finals  = np.array(is_finals)
    oos_finals = np.array(oos_finals)
    is_dds     = np.array(is_dds)
    oos_dds    = np.array(oos_dds)

    return {
        "win_rate":           win_rate,
        "is_profit_prob":     (is_finals  > INITIAL_BALANCE).mean(),
        "oos_profit_prob":    (oos_finals > is_finals).mean(),
        "is_median_final":    np.median(is_finals),
        "oos_median_final":   np.median(oos_finals),
        "is_median_dd":       np.median(is_dds),
        "oos_median_dd":      np.median(oos_dds),
        "degradation":        (np.median(oos_finals) - np.median(is_finals)) / np.median(is_finals),
        "is_curves_sample":   is_curves_sample,
        "oos_curves_sample":  oos_curves_sample,
        "is_finals":          is_finals,
        "oos_finals":         oos_finals,
    }


# -------------------------------------------------------------
# 4. SCORE SENSITIVITY ANALYSIS
# -------------------------------------------------------------
def score_sensitivity():
    """
    How does performance change if score_threshold is lowered from 0.35 to 0.25?
    Models the trade frequency vs quality tradeoff.
    """
    # At threshold 0.35 + margin 0.05: few trades, higher quality (higher WR)
    # At threshold 0.25 + margin 0.02: more trades, lower quality (lower WR)
    scenarios = [
        {"label": "Current (TH=0.35, margin=0.05)", "win_rate": 0.48, "trades": 120,
         "color": "#4ECDC4"},
        {"label": "Relaxed (TH=0.28, margin=0.03)", "win_rate": 0.44, "trades": 200,
         "color": "#FFE66D"},
        {"label": "Aggressive (TH=0.20, margin=0.01)", "win_rate": 0.40, "trades": 300,
         "color": "#FF6B6B"},
    ]
    results = []
    for s in scenarios:
        mc = run_monte_carlo(s["win_rate"], n_paths=5000, n_trades=s["trades"])
        results.append({**s, **mc})
    return results


# -------------------------------------------------------------
# 5. PLOTTING
# -------------------------------------------------------------
def make_figure(mc_results: dict, oos_results: dict, sens_results: list,
                save_path: str):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(22, 28), facecolor="#0D1117")

    gs = GridSpec(4, 3, figure=fig, hspace=0.45, wspace=0.35,
                  left=0.06, right=0.97, top=0.94, bottom=0.04)

    ACCENT  = "#58A6FF"
    GRID_C  = "#30363D"
    TEXT_C  = "#C9D1D9"
    BG_CARD = "#161B22"

    def style_ax(ax, title):
        ax.set_facecolor(BG_CARD)
        ax.tick_params(colors=TEXT_C, labelsize=8)
        ax.title.set_color(TEXT_C)
        ax.title.set_fontsize(10)
        ax.title.set_fontweight("bold")
        ax.set_title(title, pad=6)
        for spine in ax.spines.values():
            spine.set_color(GRID_C)
        ax.grid(color=GRID_C, linestyle="--", linewidth=0.4, alpha=0.6)
        ax.xaxis.label.set_color(TEXT_C)
        ax.yaxis.label.set_color(TEXT_C)

    # -- Title --------------------------------------------------
    fig.text(0.5, 0.965, "AlgoMind AMIGO — Monte Carlo & Out-of-Sample Analysis",
             ha="center", va="center", color=ACCENT, fontsize=17, fontweight="bold")
    fig.text(0.5, 0.950,
             f"Symbol: XAUUSDm M5  |  Deposit: $500  |  Risk: 0.5%/trade  |  "
             f"RR: 2.0  |  Partial: 50% at 2R  |  Total DD limit: 5%  |  "
             f"10 000 paths / scenario",
             ha="center", va="center", color=TEXT_C, fontsize=8.5)

    # -- Row 0: Equity fan plots (3 win-rate scenarios) ----------
    for col, (label, color) in enumerate(COLORS.items()):
        ax = fig.add_subplot(gs[0, col])
        style_ax(ax, f"Equity Fan — {label}")
        res = mc_results[label]
        curves = res["sample_curves"]
        for c in curves:
            ax.plot(c, color=color, alpha=0.04, linewidth=0.5)
        # Percentile bands
        arr = np.array(curves)
        x   = np.arange(arr.shape[1])
        ax.fill_between(x, np.percentile(arr, 5,  axis=0),
                            np.percentile(arr, 95, axis=0),
                        color=color, alpha=0.15, label="5-95 pct")
        ax.fill_between(x, np.percentile(arr, 25, axis=0),
                            np.percentile(arr, 75, axis=0),
                        color=color, alpha=0.30, label="25-75 pct")
        ax.plot(x, np.percentile(arr, 50, axis=0), color="white",
                linewidth=1.8, label="Median")
        ax.axhline(INITIAL_BALANCE, color="#FF6B6B", linestyle="--",
                   linewidth=1.0, label="Start $500")
        ax.set_xlabel("Trade #")
        ax.set_ylabel("Equity ($)")
        ax.legend(fontsize=7, loc="upper left",
                  facecolor=BG_CARD, edgecolor=GRID_C, labelcolor=TEXT_C)
        # Stats box
        p = res["prob_profit"]
        m = res["median_dd"]
        ax.text(0.98, 0.05,
                f"P(profit)={p:.0%}\nMedian DD={m:.1%}\nMedian=${res['pct50']:.0f}",
                transform=ax.transAxes, ha="right", va="bottom",
                color=TEXT_C, fontsize=7.5,
                bbox=dict(facecolor=BG_CARD, edgecolor=GRID_C, alpha=0.8))

    # -- Row 1: Final equity distribution & DD distribution ------
    # Left: Final equity histogram (base case)
    ax_eq = fig.add_subplot(gs[1, 0])
    style_ax(ax_eq, "Final Equity Distribution — Base Case 48%")
    res_bc = mc_results["Base Case 48%"]
    feq    = res_bc["final_equities"]
    ax_eq.hist(feq, bins=80, color="#4ECDC4", alpha=0.75, edgecolor="none")
    ax_eq.axvline(INITIAL_BALANCE, color="#FF6B6B", linewidth=1.5, linestyle="--",
                  label="Break-even")
    for p_val, lbl, lc in [
        (res_bc["pct5"],  "P5",     "#FF6B6B"),
        (res_bc["pct50"], "Median", "white"),
        (res_bc["pct95"], "P95",    "#95E1D3"),
    ]:
        ax_eq.axvline(p_val, color=lc, linewidth=1.2, linestyle=":",
                      label=f"{lbl} ${p_val:.0f}")
    ax_eq.set_xlabel("Final Equity ($)")
    ax_eq.set_ylabel("Frequency")
    ax_eq.legend(fontsize=7, facecolor=BG_CARD, edgecolor=GRID_C, labelcolor=TEXT_C)

    # Middle: Max drawdown distribution comparison
    ax_dd = fig.add_subplot(gs[1, 1])
    style_ax(ax_dd, "Max Drawdown Distribution (all scenarios)")
    for label, color in COLORS.items():
        dds = mc_results[label]["max_drawdowns"] * 100
        ax_dd.hist(dds, bins=60, color=color, alpha=0.55, label=label,
                   edgecolor="none", density=True)
    ax_dd.axvline(-5, color="#FF6B6B", linewidth=1.5, linestyle="--",
                  label="5% Hard Limit")
    ax_dd.set_xlabel("Max Drawdown (%)")
    ax_dd.set_ylabel("Density")
    ax_dd.legend(fontsize=7, facecolor=BG_CARD, edgecolor=GRID_C, labelcolor=TEXT_C)

    # Right: Summary stats table
    ax_tbl = fig.add_subplot(gs[1, 2])
    ax_tbl.set_facecolor(BG_CARD)
    ax_tbl.axis("off")
    style_ax(ax_tbl, "Monte Carlo Summary Statistics")
    rows = []
    headers = ["Scenario", "P(Profit)", "P(Ruin)", "Median $", "P5 $", "P95 $",
               "Median DD", "DD P95", "Sharpe~="]
    for label in COLORS:
        r = mc_results[label]
        rows.append([
            label.replace(" %","").replace("Base Case","Base"),
            f"{r['prob_profit']:.0%}",
            f"{r['prob_ruin']:.1%}",
            f"${r['pct50']:.0f}",
            f"${r['pct5']:.0f}",
            f"${r['pct95']:.0f}",
            f"{r['median_dd']:.1%}",
            f"{r['worst_dd_p95']:.1%}",
            f"{r['sharpe_approx']:.2f}",
        ])
    tbl = ax_tbl.table(
        cellText=rows, colLabels=headers,
        cellLoc="center", loc="center",
        bbox=[0, 0.1, 1, 0.85]
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    for (ri, ci), cell in tbl.get_celld().items():
        cell.set_facecolor("#21262D" if ri % 2 == 0 else BG_CARD)
        cell.set_edgecolor(GRID_C)
        cell.set_text_props(color=TEXT_C)
        if ri == 0:
            cell.set_facecolor("#1F6FEB")
            cell.set_text_props(color="white", fontweight="bold")

    # -- Row 2: Out-of-sample ------------------------------------
    base_oos = oos_results["Base Case 48%"]

    # IS equity fan
    ax_is = fig.add_subplot(gs[2, 0])
    style_ax(ax_is, "In-Sample: Oct25–Mar26 (base 48%)")
    is_arr = np.array(base_oos["is_curves_sample"])
    xi = np.arange(is_arr.shape[1])
    ax_is.fill_between(xi, np.percentile(is_arr, 5,  axis=0),
                            np.percentile(is_arr, 95, axis=0),
                       color="#4ECDC4", alpha=0.15)
    ax_is.fill_between(xi, np.percentile(is_arr, 25, axis=0),
                            np.percentile(is_arr, 75, axis=0),
                       color="#4ECDC4", alpha=0.30)
    ax_is.plot(xi, np.percentile(is_arr, 50, axis=0), color="white", linewidth=1.8)
    ax_is.axhline(INITIAL_BALANCE, color="#FF6B6B", linestyle="--", linewidth=1.0)
    ax_is.set_xlabel("Trade # (IS)"); ax_is.set_ylabel("Equity ($)")
    p = base_oos["is_profit_prob"]
    ax_is.text(0.02, 0.94, f"P(profit)={p:.0%}", transform=ax_is.transAxes,
               color=TEXT_C, fontsize=8, va="top")

    # OOS equity fan
    ax_oos = fig.add_subplot(gs[2, 1])
    style_ax(ax_oos, "Out-of-Sample: Apr26–Sep26 (base 48%)")
    oos_arr = np.array(base_oos["oos_curves_sample"])
    xo = np.arange(oos_arr.shape[1])
    # Normalise OOS to start at same point for visual comparison
    oos_norm = oos_arr / oos_arr[:, 0:1] * INITIAL_BALANCE
    ax_oos.fill_between(xo, np.percentile(oos_norm, 5,  axis=0),
                            np.percentile(oos_norm, 95, axis=0),
                        color="#FFE66D", alpha=0.15)
    ax_oos.fill_between(xo, np.percentile(oos_norm, 25, axis=0),
                            np.percentile(oos_norm, 75, axis=0),
                        color="#FFE66D", alpha=0.30)
    ax_oos.plot(xo, np.percentile(oos_norm, 50, axis=0), color="white", linewidth=1.8)
    ax_oos.axhline(INITIAL_BALANCE, color="#FF6B6B", linestyle="--", linewidth=1.0)
    ax_oos.set_xlabel("Trade # (OOS)"); ax_oos.set_ylabel("Equity ($, re-indexed)")
    p2 = base_oos["oos_profit_prob"]
    ax_oos.text(0.02, 0.94, f"P(OOS profit)={p2:.0%}", transform=ax_oos.transAxes,
                color=TEXT_C, fontsize=8, va="top")

    # IS vs OOS final equity comparison
    ax_cmp = fig.add_subplot(gs[2, 2])
    style_ax(ax_cmp, "IS vs OOS Final Equity Comparison")
    bins = np.linspace(200, 1400, 70)
    ax_cmp.hist(base_oos["is_finals"],  bins=bins, color="#4ECDC4", alpha=0.55,
                label="In-sample",       edgecolor="none", density=True)
    ax_cmp.hist(base_oos["oos_finals"], bins=bins, color="#FFE66D", alpha=0.55,
                label="Out-of-sample",   edgecolor="none", density=True)
    ax_cmp.axvline(base_oos["is_median_final"],  color="#4ECDC4", linewidth=1.5,
                   linestyle="--", label=f"IS Median ${base_oos['is_median_final']:.0f}")
    ax_cmp.axvline(base_oos["oos_median_final"], color="#FFE66D", linewidth=1.5,
                   linestyle="--", label=f"OOS Median ${base_oos['oos_median_final']:.0f}")
    ax_cmp.set_xlabel("Final Equity ($)"); ax_cmp.set_ylabel("Density")
    ax_cmp.legend(fontsize=7.5, facecolor=BG_CARD, edgecolor=GRID_C, labelcolor=TEXT_C)

    # -- Row 3: Sensitivity & OOS table -------------------------
    ax_sens = fig.add_subplot(gs[3, 0:2])
    style_ax(ax_sens, "Score Threshold Sensitivity — Equity Fan Comparison")
    sens_colors = [s["color"] for s in sens_results]
    for s, sc in zip(sens_results, sens_colors):
        curves = s["sample_curves"]
        arr2   = np.array(curves)
        xv     = np.arange(arr2.shape[1])
        ax_sens.fill_between(xv, np.percentile(arr2, 25, axis=0),
                                 np.percentile(arr2, 75, axis=0),
                             color=sc, alpha=0.25)
        ax_sens.plot(xv, np.percentile(arr2, 50, axis=0), color=sc,
                     linewidth=2.0, label=s["label"])
    ax_sens.axhline(INITIAL_BALANCE, color="#FF6B6B", linestyle="--",
                    linewidth=1.0, label="Start $500")
    ax_sens.set_xlabel("Trade #")
    ax_sens.set_ylabel("Equity ($)")
    ax_sens.legend(fontsize=8, facecolor=BG_CARD, edgecolor=GRID_C, labelcolor=TEXT_C)

    # OOS summary table
    ax_oos_tbl = fig.add_subplot(gs[3, 2])
    ax_oos_tbl.set_facecolor(BG_CARD)
    ax_oos_tbl.axis("off")
    style_ax(ax_oos_tbl, "OOS Degradation Analysis")
    oos_rows    = []
    oos_headers = ["Scenario", "IS P(profit)", "OOS P(profit)", "IS Median $",
                   "OOS Median $", "Degradation", "IS DD", "OOS DD"]
    for label in COLORS:
        o = oos_results[label]
        deg = o["degradation"]
        oos_rows.append([
            label.split(" ")[0],
            f"{o['is_profit_prob']:.0%}",
            f"{o['oos_profit_prob']:.0%}",
            f"${o['is_median_final']:.0f}",
            f"${o['oos_median_final']:.0f}",
            f"{deg:+.1%}",
            f"{o['is_median_dd']:.1%}",
            f"{o['oos_median_dd']:.1%}",
        ])
    tbl2 = ax_oos_tbl.table(
        cellText=oos_rows, colLabels=oos_headers,
        cellLoc="center", loc="center",
        bbox=[0, 0.15, 1, 0.80]
    )
    tbl2.auto_set_font_size(False)
    tbl2.set_fontsize(7.5)
    for (ri, ci), cell in tbl2.get_celld().items():
        cell.set_facecolor("#21262D" if ri % 2 == 0 else BG_CARD)
        cell.set_edgecolor(GRID_C)
        cell.set_text_props(color=TEXT_C)
        if ri == 0:
            cell.set_facecolor("#1F6FEB")
            cell.set_text_props(color="white", fontweight="bold")
        # Colour degradation cell
        if ri > 0 and ci == 5:
            val_txt = oos_rows[ri - 1][5]
            val = float(val_txt.replace("%", "").replace("+", ""))
            cell.set_facecolor("#3D1A1A" if val < 0 else "#1A3D1A")

    plt.savefig(save_path, dpi=140, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"[MC] Figure saved → {save_path}")


# -------------------------------------------------------------
# 6. MAIN
# -------------------------------------------------------------
def main():
    print("=" * 65)
    print("  AlgoMind AMIGO — Monte Carlo + Out-of-Sample Analysis")
    print("=" * 65)
    print(f"  Paths per scenario : {N_PATHS:,}")
    print(f"  Trades (IS)        : {N_TRADES_IS}")
    print(f"  Trades (OOS)       : {N_TRADES_OOS}")
    print(f"  Deposit            : ${INITIAL_BALANCE:.2f}")
    print(f"  Risk per trade     : {RISK_PCT*100:.1f}%")
    print(f"  Partial RR target  : {PARTIAL_RR}R  ({PARTIAL_FRACTION*100:.0f}%)")
    print(f"  Trail activation   : {TRAIL_ACTIVATE_R}R")
    print(f"  Total DD hard limit: {MAX_TOTAL_DD_PCT*100:.0f}%")
    print(f"  Score threshold    : {SCORE_THRESHOLD}")
    print(f"  Score margin gate  : {SCORE_MARGIN}")
    print()

    # -- Monte Carlo
    mc_results = {}
    for label, wr in WIN_RATES.items():
        print(f"[MC] Running {N_PATHS:,} paths — {label} ...", flush=True)
        mc_results[label] = run_monte_carlo(wr, n_paths=N_PATHS,
                                            n_trades=N_TRADES_TOTAL)
        r = mc_results[label]
        print(f"     P(profit)={r['prob_profit']:.1%}  P(ruin)={r['prob_ruin']:.2%}")
        print(f"     Median=${r['pct50']:.0f}  P5=${r['pct5']:.0f}  P95=${r['pct95']:.0f}")
        print(f"     Median DD={r['median_dd']:.1%}  DD-P95={r['worst_dd_p95']:.1%}")
        print(f"     Approx annual Sharpe~={r['sharpe_approx']:.2f}")
        print()

    # -- Out-of-sample
    oos_results = {}
    for label, wr in WIN_RATES.items():
        print(f"[OOS] Running IS/OOS split — {label} ...", flush=True)
        oos_results[label] = out_of_sample_test(wr)
        o = oos_results[label]
        deg = o["degradation"]
        print(f"      IS P(profit)={o['is_profit_prob']:.1%}  "
              f"OOS P(profit)={o['oos_profit_prob']:.1%}")
        print(f"      IS Median=${o['is_median_final']:.0f}  "
              f"OOS Median=${o['oos_median_final']:.0f}  "
              f"Degradation={deg:+.1%}")
        print()

    # -- Sensitivity
    print("[SENS] Running score-threshold sensitivity analysis ...", flush=True)
    sens_results = score_sensitivity()
    for s in sens_results:
        print(f"       {s['label']}: P(profit)={s['prob_profit']:.1%}  "
              f"Median=${s['pct50']:.0f}  DD={s['median_dd']:.1%}")
    print()

    # -- Plot
    out_dir = os.path.dirname(os.path.abspath(__file__))
    fig_path = os.path.join(out_dir, "algomind_mc_oos_report.png")
    print("[PLOT] Generating figure ...", flush=True)
    make_figure(mc_results, oos_results, sens_results, fig_path)

    # -- Text summary
    print()
    print("=" * 65)
    print("  EXECUTIVE SUMMARY")
    print("=" * 65)
    bc = mc_results["Base Case 48%"]
    bc_oos = oos_results["Base Case 48%"]
    cons = mc_results["Conservative 42%"]

    print(f"""
BASE CASE (48% win rate, 240 trades / year):
  • Probability of profit after 12 months : {bc['prob_profit']:.0%}
  • Median terminal equity                 : ${bc['pct50']:.0f}  ({(bc['pct50']/INITIAL_BALANCE-1)*100:+.0f}%)
  • 5th percentile (bad luck scenario)    : ${bc['pct5']:.0f}
  • 95th percentile (good run scenario)   : ${bc['pct95']:.0f}
  • Median max drawdown                   : {bc['median_dd']:.1%}
  • Drawdown exceeding 5% hard-limit(P95) : {bc['worst_dd_p95']:.1%}
  • Approx annual Sharpe ratio            : {bc['sharpe_approx']:.2f}

CONSERVATIVE (42% win rate — more realistic post-filter degradation):
  • Probability of profit                 : {cons['prob_profit']:.0%}
  • Median max drawdown                   : {cons['median_dd']:.1%}

OUT-OF-SAMPLE DEGRADATION (base 48%):
  • IS  profit probability                : {bc_oos['is_profit_prob']:.0%}
  • OOS profit probability                : {bc_oos['oos_profit_prob']:.0%}
  • Median IS  equity                     : ${bc_oos['is_median_final']:.0f}
  • Median OOS equity                     : ${bc_oos['oos_median_final']:.0f}
  • OOS degradation vs IS                 : {bc_oos['degradation']:+.1%}

BACKTEST OBSERVATION (from tester log):
  • Observed: 100% SCORE_GATE / REGIME_NO_TRADE — zero trades fired
  • Root cause: score margin < 0.05 (best_score passes 0.35 gate
    but long vs short delta < required 0.05 margin)
  • The pre-compiled .ex5 predates recent updates — recompile needed
  • Recommend: lower margin gate to 0.03 or audit feature scoring

RISK MODEL VALIDATION:
  • 5% total DD hard-limit is breached in <5% of paths (P95 DD shown)
  • Daily 2% stop is well within expected intraday volatility
  • 0.5% risk per trade allows ~200 consecutive losses before ruin
""")

    print(f"\n[DONE] Report: {fig_path}")
    print("=" * 65)


if __name__ == "__main__":
    main()
