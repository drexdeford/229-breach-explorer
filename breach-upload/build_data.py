#!/usr/bin/env python3
"""Normalize the two scraped CSVs into one compact JSON the dashboard loads."""
import csv, json, io, datetime, os

# Column order in the portal CSV (headers 0 and 7 come out as JSF junk):
# 0 name, 1 state, 2 entityType, 3 affected, 4 date, 5 breachType, 6 location, 7 baPresent, 8 webDesc
COLS = ["name", "state", "entityType", "affected", "date", "breachType", "location", "ba", "desc"]

def load(path, status):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # drop header row
        for r in reader:
            if len(r) < 7:
                continue
            rec = dict(zip(COLS, r + [""] * (len(COLS) - len(r))))
            # affected -> int
            try:
                aff = int(re.sub(r"[^0-9]", "", rec["affected"]) or 0)
            except Exception:
                aff = 0
            # date MM/DD/YYYY -> ISO
            iso = ""
            d = rec["date"].strip()
            for fmt in ("%m/%d/%Y", "%m/%d/%y"):
                try:
                    iso = datetime.datetime.strptime(d, fmt).strftime("%Y-%m-%d")
                    break
                except Exception:
                    pass
            rows.append({
                "n": rec["name"].strip(),
                "s": rec["state"].strip(),
                "e": rec["entityType"].strip(),
                "a": aff,
                "d": iso,
                "t": rec["breachType"].strip(),
                "l": rec["location"].strip(),
                "ba": rec["ba"].strip(),
                "st": status,  # "ui" or "ar"
            })
    return rows

import re
ui = load("data/under_investigation.csv", "ui")
ar = load("data/archive.csv", "ar")
all_rows = ui + ar
dates = [r["d"] for r in all_rows if r["d"]]
meta = {
    "generated": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    "counts": {"ui": len(ui), "ar": len(ar), "total": len(all_rows)},
    "dateRange": {"min": min(dates) if dates else "", "max": max(dates) if dates else ""},
}
os.makedirs("app", exist_ok=True)
with open("app/data.json", "w", encoding="utf-8") as f:
    json.dump({"meta": meta, "rows": all_rows}, f, separators=(",", ":"))

print("rows:", meta["counts"], "| dates", meta["dateRange"])
print("app/data.json bytes:", os.path.getsize("app/data.json"))
