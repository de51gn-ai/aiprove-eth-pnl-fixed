build log — eth-pnl-fixed (agent session, 2026-11-13/14)
$ read challenges/eth-backtest/README.md + bars.csv (1440 bars, ETH/USDT 1m, 24h to 2026-11-13 12:17 UTC)
spec: net PnL after costs (maker+taker fees, size-scaled slippage); sandbox replays, no phantom fills; held-out tail punishes overfit
note: spec publishes NO fee/slippage numbers and the public grader repo only implements FORECAST — cost model assumptions stated explicitly in backtest.py/README.md
$ data check: first close 2028.68, last 1960.59, buy&hold -3.36%; sideways ~2000-2020 first 14h, selloff to ~1907, partial recovery
$ tried SMA crossovers first — all lost after costs: sma120 -$716.19 (79 trades), sma120+0.5xATR band -$462.17, sma60band -$587.07, sma240+1xATR -$82.49
$ tried Donchian breakout family — plateau, not a spike: N=60 +$186.94, 90 +$267.34, 120 +$206.93, 150 +$275.39, 180 +$262.18, 240/300 +$329.86
$ chose Donchian(120): textbook 2h lookback, mid-plateau, 8 trades; did NOT pick N=240 (higher PnL but 3 trades / one short = fragile on held-out tail)
$ wrote strategy.py (positions(bars)->{-1,0,+1}, causal, fill at next bar open) + backtest.py (taker 5bps, slippage 10bps*notional/bar$-vol cap 50bps, 10% participation cap, final position closed costed)
$ python3 backtest.py -> net PnL +$206.93, 8 trades, maxDD $293.84, half1 -$231.56, half2 +$443.53, fees $52.90, slip $3.98; sanity: flat=$0.00/0 trades, fees deducted
$ git init; git add -A; git commit -m "aiprove eth-pnl-fixed entry"
