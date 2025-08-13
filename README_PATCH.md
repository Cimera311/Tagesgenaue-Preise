# Patch: robust EUR price for GoMining (CoinPaprika EUR + USD→EUR)

- Fallback 1 now calls CoinPaprika with `?quotes=EUR`.
- Fallback 2 converts Paprika USD price using exchangerate.host if EUR is unavailable.
- `run_test.py` includes extended debug output.
