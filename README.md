# Daily EUR price automation at 00:00 MEZ (Europe/Berlin)

- **Timezone:** Europe/Berlin (MEZ/MESZ). The script stamps rows with the **Berlin local date**.
- **Schedule:** Two UTC crons (22:00 & 23:00). Due to DST changes, one of them will align with 00:00 Berlin.
  The Python script prevents duplicate rows by skipping the date if it already exists.
- **Outputs:** CSVs in `data/`:
  - `data/bitcoin_eur.csv`
  - `data/gominingtoken_eur.csv`

**Run locally**
```bash
python fetch_prices.py
```

**Deploy on GitHub Actions**
1. Create a repo, copy these files to root.
2. Enable Actions. The workflow will handle 00:00 MEZ via idempotent date logic.
