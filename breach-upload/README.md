# 229Project U.S. Healthcare Data Breach Explorer

Public dashboard of U.S. healthcare data breaches (500+ individuals) reported to
the HHS Office for Civil Rights. Independent visualization of public data — not
affiliated with HHS.

- `app/` — the published site (deployed by Netlify)
- `scraper.py` — pulls the portal's Under Investigation + Archive CSVs
- `build_data.py` — normalizes them into `app/data.json`
- `.github/workflows/refresh.yml` — re-runs the pull weekly and commits fresh data

Live: https://229-breach-explorer.netlify.app
