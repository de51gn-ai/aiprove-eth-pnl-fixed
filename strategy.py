"""Donchian(120) breakout strategy for the AIProve eth-pnl-fixed bounty.

Pure stdlib, deterministic, causal: the signal for bar i uses only bars
0..i (the channel itself uses bars i-N..i-1). No lookahead anywhere.

Interface for the sandbox
--------------------------
    positions(bars) -> list[int]
        bars: list of dicts with keys minute, open, high, low, close, volume
        returns: target position per bar, one of -1 (short), 0 (flat), +1 (long).
        The first N bars are flat (warm-up: no channel yet).

Rule
----
- Channel = highest high / lowest low of the previous N=120 bars.
- Close above the channel high  -> target +1 (long).
- Close below the channel low   -> target -1 (short).
- Otherwise hold the current target (no whipsaw flips inside the channel).

Positions are targets, not orders: the backtest (backtest.py) turns a target
change into one fill at the NEXT bar's open, so no fill can ever use a price
the strategy could not have known (no phantom fills).

CLI: python3 strategy.py [bars.csv] -> prints positions to positions.csv
"""

import csv
import sys

N = 120  # lookback in bars (2 hours on 1-minute bars)


def positions(bars, n=N):
    """Target position in {-1, 0, +1} for each bar, computed causally."""
    out = [0] * len(bars)
    cur = 0
    for i in range(n, len(bars)):
        hi = max(b["high"] for b in bars[i - n:i])
        lo = min(b["low"] for b in bars[i - n:i])
        if bars[i]["close"] > hi:
            cur = 1
        elif bars[i]["close"] < lo:
            cur = -1
        out[i] = cur
    return out


def load_bars(path):
    with open(path, newline="") as f:
        return [{k: float(v) for k, v in row.items()}
                for row in csv.DictReader(f)]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "bars.csv"
    bars = load_bars(path)
    pos = positions(bars)
    with open("positions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["minute", "target_position"])
        for b, p in zip(bars, pos):
            w.writerow([int(b["minute"]), p])
    flips = sum(1 for a, b in zip(pos, pos[1:]) if a != b)
    print(f"bars={len(bars)} flips={flips} "
          f"long={sum(1 for p in pos if p == 1)} "
          f"short={sum(1 for p in pos if p == -1)} "
          f"flat={sum(1 for p in pos if p == 0)}")
    print("wrote positions.csv")


if __name__ == "__main__":
    main()
