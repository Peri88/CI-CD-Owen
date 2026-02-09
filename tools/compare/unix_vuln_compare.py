#!/usr/bin/env python3
import argparse
from datetime import datetime
from pathlib import Path
import shutil

import pandas as pd


def _find_existing_header(df: pd.DataFrame) -> int:
    for i, row in df.iterrows():
        vals = row.astype(str).tolist()
        if "영역" in vals and "진단 항목" in vals:
            return i
    raise SystemExit("HEADER_NOT_FOUND: Unix_기존.xlsx")


def load_existing(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, header=None)
    header_idx = _find_existing_header(raw)
    header = raw.iloc[header_idx].tolist()
    existing = raw.iloc[header_idx + 1 :].copy()
    existing.columns = header
    cols_keep = ["영역", "Code", "진단 항목", "중요도"]
    for c in cols_keep:
        if c not in existing.columns:
            existing[c] = None
    existing = existing[cols_keep]
    existing = existing[existing["Code"].notna() | existing["진단 항목"].notna()].copy()
    existing["Code"] = existing["Code"].astype(str).str.strip()
    return existing


def collect_new(mobile_files: list[Path], existing_codes: set[str]) -> pd.DataFrame:
    new_rows = []
    for f in mobile_files:
        xls = pd.ExcelFile(f)
        for sheet in xls.sheet_names:
            if sheet == "요약":
                continue
            df = pd.read_excel(f, sheet_name=sheet, header=None)
            hdr_idx = None
            for i, row in df.iterrows():
                if row.astype(str).str.contains("코드").any() and row.astype(str).str.contains("결과").any():
                    hdr_idx = i
                    break
            if hdr_idx is None:
                continue
            headers = [c if isinstance(c, str) else "" for c in df.iloc[hdr_idx].tolist()]
            data = df.iloc[hdr_idx + 1 :].copy()
            data.columns = headers
            if "결과" not in data.columns:
                continue
            # treat any value containing "취약" as vulnerable (after trim)
            result = data["결과"].astype(str).str.strip()
            data = data[result.str.contains("취약", na=False)]
            for col in ["코드", "그룹", "점검 항목", "중요도"]:
                if col not in data.columns:
                    data[col] = None
            for _, r in data.iterrows():
                code = str(r["코드"]).strip() if pd.notna(r["코드"]) else ""
                if not code or code == "nan":
                    continue
                if code in existing_codes:
                    continue
                new_rows.append(
                    {
                        "영역": r["그룹"],
                        "Code": code,
                        "진단 항목": r["점검 항목"],
                        "중요도": r["중요도"],
                        "출처": f"{f.name}:{sheet}",
                    }
                )

    new_df = pd.DataFrame(new_rows)
    if new_df.empty:
        return new_df

    agg_cols = ["영역", "Code", "진단 항목", "중요도"]
    new_df["출처"] = new_df["출처"].astype(str)
    new_df = (
        new_df.groupby(agg_cols, dropna=False)["출처"]
        .apply(lambda s: ", ".join(sorted(set(s))))
        .reset_index()
    )
    return new_df


def write_output(existing: pd.DataFrame, new_df: pd.DataFrame, out_path: Path) -> None:
    existing_out = existing.copy()
    existing_out["구분"] = "기존"
    existing_out["출처"] = ""

    new_out = new_df.copy()
    if not new_out.empty:
        new_out["구분"] = "추가"

    combined = pd.concat([existing_out, new_out], ignore_index=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        combined.to_excel(writer, sheet_name="통합", index=False)
        new_out.to_excel(writer, sheet_name="추가", index=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai-dir", required=True, help="Folder containing Mobile_* and Unix_기존.xlsx")
    ap.add_argument("--out-dir", required=True, help="Output folder for Unix_결과.xlsx")
    args = ap.parse_args()

    ai_dir = Path(args.ai_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    existing_path = ai_dir / "Unix_기존.xlsx"
    mobile_files = sorted(ai_dir.glob("Mobile_*_UNIX.xlsx"))
    if not mobile_files:
        raise SystemExit("NO_MOBILE_FILES: Mobile_*_UNIX.xlsx not found")

    existing = load_existing(existing_path)
    existing_codes = set(existing["Code"].dropna())
    new_df = collect_new(mobile_files, existing_codes)

    local_out = Path("/tmp/Unix_결과.xlsx")
    write_output(existing, new_df, local_out)

    out_path = out_dir / "Unix_결과.xlsx"
    try:
        shutil.copy2(local_out, out_path)
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback = out_dir / f"Unix_결과_{ts}.xlsx"
        shutil.copy2(local_out, fallback)
        print(f"[WARN] Overwrite failed; wrote {fallback}")

    print(f"[OK] output: {out_path}")
    print(f"[INFO] existing: {len(existing)}, new: {len(new_df)}")


if __name__ == "__main__":
    main()
