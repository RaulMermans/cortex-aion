"""Validate CORTEX AION v0.1 downloaded Azure outputs.

Dependencies: pandas, pyarrow. Intended for the original 5,000-row run.
This portable implementation has not been executed in the original audit environment.
"""
import argparse
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

RAW = ["unique_key", "created_date", "closed_date", "agency",
       "complaint_type", "descriptor", "status", "borough", "due_date"]
TYPED = {"created_date": "created_ts", "closed_date": "closed_ts",
         "due_date": "due_ts"}

def load(path):
    path = Path(path)
    files = sorted(path.rglob("*.parquet")) if path.is_dir() else [path]
    if not files:
        raise ValueError(f"No parquet files: {path}")
    tables = [pq.read_table(p) for p in files]
    for table in tables:
        assert set(table.column_names) == set(RAW + list(TYPED.values()) + ["quality_reason"])
        for name in TYPED.values():
            assert str(table.schema.field(name).type).startswith("timestamp"), name
    return pd.concat([t.to_pandas() for t in tables], ignore_index=True), sum(p.stat().st_size for p in files)

def utc(series):
    return pd.to_datetime(series, format="%Y-%m-%dT%H:%M:%S.%f", errors="coerce").dt.tz_localize(
        "America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")

def clean(series):
    return series.astype("string").fillna("")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bronze", "silver", "quarantine"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    bronze = pd.read_csv(args.bronze, dtype=str, keep_default_na=False, escapechar="\\")
    silver, sb = load(args.silver)
    quarantine, qb = load(args.quarantine)
    assert list(bronze.columns) == RAW
    assert (len(bronze), len(silver), len(quarantine)) == (5000, 4987, 13)
    combined = pd.concat([silver, quarantine], ignore_index=True)
    for frame in (bronze, combined):
        assert clean(frame.unique_key).str.strip().ne("").all()
        assert frame.unique_key.is_unique
    assert set(bronze.unique_key) == set(combined.unique_key)
    assert set(silver.unique_key).isdisjoint(quarantine.unique_key)
    left = bronze.set_index("unique_key").sort_index()
    right = combined.set_index("unique_key").sort_index()
    for col in RAW[1:]:
        assert clean(left[col]).eq(clean(right[col])).all(), col
    converted = {}
    for raw, typed in TYPED.items():
        expected = utc(combined[raw])
        actual = pd.to_datetime(combined[typed], utc=True)
        assert (expected.eq(actual) | (expected.isna() & actual.isna())).all(), typed
        converted[typed] = expected
    c, cl = converted["created_ts"], converted["closed_ts"]
    reasons = pd.Series("VALID", index=combined.index)
    rules = [
        (clean(combined.unique_key).str.strip().eq(""), "MISSING_ID"),
        (c.isna(), "INVALID_CREATED_DATE"),
        (clean(combined.closed_date).str.strip().ne("") & cl.isna(), "INVALID_CLOSED_DATE"),
        (cl.lt(c), "NEGATIVE_RESOLUTION_TIME"),
        (clean(combined.status).str.strip().str.lower().eq("closed") & cl.isna(), "CLOSED_WITHOUT_DATE"),
    ]
    for mask, label in rules:
        reasons.loc[mask & reasons.eq("VALID")] = label
    assert reasons.eq(combined.quality_reason).all()
    assert silver.quality_reason.eq("VALID").all()
    assert quarantine.quality_reason.ne("VALID").all()
    size = Path(args.bronze).stat().st_size
    print(f"PASS: {len(bronze)} = {len(silver)} + {len(quarantine)}")
    print(quarantine.quality_reason.value_counts().to_string())
    print(f"Bytes: {size} -> {sb+qb}; reduction: {1-(sb+qb)/size:.2%}")

if __name__ == "__main__":
    main()
