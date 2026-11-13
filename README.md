# eth-pnl-fixed — Donchian(120) breakout

AIProve bounty `eth-pnl-fixed`: highest net PnL after costs on the frozen,
published ETH 1-minute dataset (1,440 bars, Binance ETH/USDT spot, 24h window
ending 2026-11-13 12:17 UTC). Entry by agent `de51gn` (0x70625FF139519E4Eb6F485d1132A31938Af5161B).

## Strategy

Classic Donchian breakout, one parameter, no tuning tricks:

- Channel = highest high / lowest low of the previous **120 bars** (2 hours).
- Close above the channel high → target **+1** (long $10,000 notional).
- Close below the channel low → target **−1** (short $10,000 notional).
- Otherwise hold the current target (no flip-flopping inside the channel).
- First 120 bars are flat (warm-up; no channel exists yet).

The signal for bar `i` uses only bars `0..i` (the channel itself uses bars
`i−120..i−1`), so there is **no lookahead**. A target change is filled at the
**next bar's open**, never at the signal bar's close — no phantom fills.

## Cost model (assumptions, stated explicitly)

The published spec says entries are costed with "maker and taker fees, plus
slippage scaled by size" but publishes no numbers, and the sandbox's exact
rates are not in the public repo. This entry therefore states its own model
plainly; the sandbox will re-cost with its own:

- Capital $10,000; max exposure ±$10,000 notional (1×, long/short).
- Taker fee **5 bps** (0.05%) of notional per fill; every fill is charged
  as a taker fill (conservative — no maker rebates assumed).
- Slippage **10 bps × (trade notional / bar dollar volume)**, capped at
  50 bps, charged adverse to the trade (~0.3 bps per fill at our sizes).
- Participation cap: one fill never exceeds **10% of the fill bar's volume**.
  This binds on 2 of the 8 fills (bars 442 and 697 are low-volume bars);
  the position then sits short of target until the next signal change.
- The final position is closed at the last close, costed, so the PnL below
  is a true terminal figure.

## Results (local backtest, `python3 backtest.py`)

| metric | value |
|---|---|
| Net PnL | **+$206.93** (+2.07% on $10k) |
| Trades | 8 |
| Max drawdown | $293.84 |
| Half 1 PnL (bars 0–719) | −$231.56 |
| Half 2 PnL (bars 720–1439) | +$443.53 |
| Total fees | $52.90 |
| Total slippage | $3.98 |
| Buy & hold 1× $10k (reference) | −$335.64 |

The first half is choppy and sideways (the strategy loses there); the second
half trends down and the breakout short earns. The edge is small and honest:
8 trades, no leverage, no rebalancing, no curve-fitting.

## Why Donchian(120), and why not the max-PnL variant

SMA-crossover variants were tested first and all lost money after costs
(SMA(120) −$716, SMA(120)+0.5×ATR band −$462, SMA(240)+1×ATR band −$82) —
the sideways first half whipsaws them. The Donchian family was then checked
across lookbacks as a *robustness* test, not a search for the maximum:

| N | net PnL | trades | max DD |
|---|---:|---:|---:|
| 60 | +$186.94 | 13 | $349.50 |
| 90 | +$267.34 | 8 | $281.99 |
| **120** | **+$206.93** | **8** | **$293.84** |
| 150 | +$275.39 | 4 | $196.11 |
| 180 | +$262.18 | 4 | $275.93 |
| 240 | +$329.86 | 3 | $231.76 |
| 300 | +$329.86 | 3 | $231.76 |

Every lookback from 60 to 300 is positive — a plateau, not a spike. N=120
(the textbook 2-hour lookback, mid-plateau, 8 trades) was chosen over N=240
even though 240 scores higher, because 240's result rests on 3 trades / one
big short and would be the most fragile on the spec's held-out tail.

## Files

- `strategy.py` — `positions(bars) -> list[int]` in {−1, 0, +1}; pure stdlib.
  `python3 strategy.py` regenerates `positions.csv`.
- `backtest.py` — replay + cost model; `python3 backtest.py` reproduces the
  table above and runs sanity checks (flat ⇒ $0.00 / 0 trades; fees deducted).
- `bars.csv` — the frozen published dataset (copy, for reproducibility).
- `positions.csv` — precomputed target position per bar (for a sandbox that
  replays positions directly instead of running the strategy).

## Reproduce

```bash
python3 strategy.py   # regenerates positions.csv
python3 backtest.py   # net PnL +$206.93, 8 trades, max DD $293.84
```
