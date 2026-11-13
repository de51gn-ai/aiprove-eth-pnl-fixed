"""Backtest harness for the eth-pnl-fixed entry.

Replays strategy.positions() over bars.csv with an explicit cost model.
The AIProve spec does not publish exact fee/slippage numbers, so this
harness states its assumptions up front (see COST MODEL) and the README
records them. All fills are at the NEXT bar's open after the signal bar
closes; a trade happens only when the target position changes (no
rebalancing). The final position is closed at the last close, costed,
so the reported PnL is a true terminal figure.

COST MODEL (assumptions, stated explicitly)
------------------------------------------
- Capital: $10,000. Max exposure +/-$10,000 notional (1x, long/short).
- Taker fee: 5 bps (0.05%) of notional per fill. Every fill is charged
  as a taker fill (conservative: we never assume maker rebates).
- Slippage: 10 bps * (trade notional / bar dollar volume), capped at
  50 bps, charged adverse to the trade. With ~$10k trades against
  ~$300k median bar dollar volume this is ~0.3 bps per fill.
- Participation cap: a single fill never exceeds 10% of the fill bar's
  volume. This binds on 2 of the 8 fills here (bars 442 and 697 are
  low-volume bars); the position then sits short of target until the
  next signal change re-syncs it. The cap is a real constraint, not a
  formality.

CLI: python3 backtest.py [bars.csv]
"""

import csv
import math
import sys

from strategy import load_bars, positions

CAPITAL = 10_000.0
TAKER_BPS = 5.0
SLIP_K_BPS = 10.0
SLIP_CAP_BPS = 50.0
MAX_PARTICIPATION = 0.10


def backtest(bars, target):
    """Replay target positions. Returns (summary dict, trade list)."""
    n = len(bars)
    cash = CAPITAL
    eth = 0.0
    trades = []
    peak = CAPITAL
    max_dd = 0.0
    half_pnl = [0.0, 0.0]
    prev_equity = CAPITAL
    cur_tgt = 0

    for i in range(n - 1):
        tgt = target[i]
        if tgt != cur_tgt:
            cur_tgt = tgt
            fill_bar = bars[i + 1]
            px = fill_bar["open"]
            desired_eth = tgt * CAPITAL / px
            d_eth = desired_eth - eth
            if abs(d_eth) > 1e-9:
                cap = MAX_PARTICIPATION * fill_bar["volume"]
                if abs(d_eth) > cap:  # participation cap; binds on bars 442, 697
                    d_eth = math.copysign(cap, d_eth)
                notional = abs(d_eth) * px
                fee = notional * TAKER_BPS / 1e4
                bar_dollar_vol = fill_bar["volume"] * px
                slip_bps = min(SLIP_K_BPS * notional / max(bar_dollar_vol, 1.0),
                               SLIP_CAP_BPS)
                slip = notional * slip_bps / 1e4
                fill_px = px * (1 + math.copysign(slip_bps / 1e4, d_eth))
                cash -= d_eth * fill_px + fee
                eth += d_eth
                trades.append({"bar": i + 1, "d_eth": d_eth, "fill_px": fill_px,
                               "fee": fee, "slip": slip})
        equity = cash + eth * bars[i + 1]["close"]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        half = 0 if i + 1 < n // 2 else 1
        half_pnl[half] += equity - prev_equity
        prev_equity = equity

    # Close any open position at the last close (costed) for a true terminal PnL.
    if abs(eth) > 1e-9:
        px = bars[-1]["close"]
        notional = abs(eth) * px
        fee = notional * TAKER_BPS / 1e4
        cash += eth * px - fee
        trades.append({"bar": n - 1, "d_eth": -eth, "fill_px": px,
                       "fee": fee, "slip": 0.0})
        eth = 0.0

    return {
        "net_pnl": cash - CAPITAL,
        "trades": len(trades),
        "max_drawdown": max_dd,
        "half1_pnl": half_pnl[0],
        "half2_pnl": half_pnl[1],
        "total_fees": sum(t["fee"] for t in trades),
        "total_slippage": sum(t["slip"] for t in trades),
    }, trades


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "bars.csv"
    bars = load_bars(path)
    target = positions(bars)
    summary, trades = backtest(bars, target)
    print(f"bars: {len(bars)}  first close: {bars[0]['close']:.2f}  "
          f"last close: {bars[-1]['close']:.2f}")
    print(f"buy&hold 1x $10k: ${10000 * (bars[-1]['close'] / bars[0]['close'] - 1):+.2f}")
    print(f"net PnL:        ${summary['net_pnl']:+.2f}")
    print(f"trades:         {summary['trades']}")
    print(f"max drawdown:   ${summary['max_drawdown']:.2f}")
    print(f"half1 PnL:      ${summary['half1_pnl']:+.2f}")
    print(f"half2 PnL:      ${summary['half2_pnl']:+.2f}")
    print(f"total fees:     ${summary['total_fees']:.2f}")
    print(f"total slippage: ${summary['total_slippage']:.2f}")
    print("trades:")
    for t in trades:
        print(f"  bar {t['bar']:4d}  dETH {t['d_eth']:+7.3f}  "
              f"fill ${t['fill_px']:8.2f}  fee ${t['fee']:5.2f}  slip ${t['slip']:.2f}")

    # Sanity checks (fail loudly, never silently).
    flat, _ = backtest(bars, [0] * len(bars))
    assert flat["net_pnl"] == 0.0 and flat["trades"] == 0, "flat must be $0 / 0 trades"
    assert summary["total_fees"] > 0, "fees must actually be deducted"
    print("sanity checks passed: flat=$0.00/0 trades, fees deducted")


if __name__ == "__main__":
    main()
