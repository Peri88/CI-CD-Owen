#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# NetBackup "Jobs" export header columns (fixed-width)
COLUMNS = [
    "Job Id",
    "Type",
    "State",
    "State Details",
    "Status",
    "Job Policy",
    "Job Schedule",
    "Client",
    "Media Server",
    "Start Time",
    "Elapsed Time",
    "End Time",
    "Storage Unit",
    "Attempt",
    "Operation",
    "Kilobytes",
    "Files",
    "Pathname",
    "% Complete (Estimated)",
    "Job PID",
    "Owner",
    "Copy",
    "Parent Job ID",
    "KB/Sec",
    "Active Start",
    "Active Elapsed",
    "Robot",
    "Vault",
    "Profile",
    "Session ID",
    "Media to Eject",
    "Data Movement",
    "Off-Host Type",
    "Master",
    "Priority",
    "Deduplication Rate",
    "Transport",
    "Accelerator Optimization",
    "Instance or Database",
    "Share Host",
]

TEMPLATE_PDF_DEFAULT = "/home/owen/[벽산] Veritas 백업상태 점검보고서_2026_1월_5주차.pdf"
TEMPLATE_IMG_DIR = "/tmp/nbu_template_img"
FONT_PATH = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"

POLICY_ROWS = [
    {"label": "ERP-DB_ORACLE", "policy": "ERP-DB_ORACLE"},
    {"label": "ERP_ORA_DUMP", "policy": "ERP_ORA_DUMP"},
    {"label": "E-HR_ORA_DUMP", "policy": "E-HR_ORA_DUMP"},
    {"label": "SFA_MSSQL", "policy": "SFA_MSSQL", "instance": "SFA"},
    {"label": "PRM_ORACLE_PRMIF", "policy": "PRM_ORACLE_PRMIF"},
    {"label": "PRM_ORACLE_PRMORA", "policy": "PRM_ORACLE_PRMORA"},
    {"label": "ReportServer", "policy": "HZDB_MSSQL", "instance": "ReportServer"},
    {"label": "SMS", "policy": "HZDB_MSSQL", "instance": "SMS"},
    {"label": "NEOE", "policy": "HZDB_MSSQL", "instance": "NEOE"},
    {"label": "ERP-APP2", "policy": "ERP-APP2"},
    {"label": "E-HR_WAS", "policy": "E-HR_WAS"},
    {"label": "E-HR_WEB", "policy": "E-HR_WEB"},
    {"label": "PRM_WAS", "policy": "PRM_WAS"},
    {"label": "PRM_WEB", "policy": "PRM_WEB"},
    {"label": "HZWEB_ERP", "policy": "HZWEB_ERP"},
    {"label": "ERP-APP", "policy": "ERP-APP"},
]


def parse_nb_datetime(s: str) -> Optional[datetime]:
    s = re.sub(r"\s+", " ", s.strip())
    if not s:
        return None
    m = re.match(r"(\d{4})\. (\d{1,2})\. (\d{1,2}) (오전|오후) (\d{1,2}):(\d{2}):(\d{2})", s)
    if m:
        y, mo, d, ap, hh, mm, ss = m.groups()
        hh = int(hh)
        if ap == "오후" and hh != 12:
            hh += 12
        if ap == "오전" and hh == 12:
            hh = 0
        return datetime(int(y), int(mo), int(d), hh, int(mm), int(ss))
    for fmt in ("%Y. %m. %d %H:%M:%S",):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def kb_to_gb(kb_str: str) -> Optional[float]:
    kb_str = kb_str.strip().replace(",", "")
    if not kb_str:
        return None
    try:
        kb = float(kb_str)
        return round(kb / 1024.0 / 1024.0, 2)  # KB -> GB
    except ValueError:
        return None


def extract_jobs(raw_bytes: bytes) -> List[Dict]:
    lines = raw_bytes.splitlines()

    header_idx = -1
    header_line = b""
    for i, ln in enumerate(lines):
        if ln.startswith(b"Job Id") and b"Job Policy" in ln and b"Start Time" in ln:
            header_idx = i
            header_line = ln
            break
    if header_idx == -1:
        return []

    starts = {}
    pos = 0
    for col in [c.encode() for c in COLUMNS]:
        idx = header_line.find(col, pos)
        if idx == -1:
            return []
        starts[col] = idx
        pos = idx + len(col)

    spans = []
    cols_b = [c.encode() for c in COLUMNS]
    for i, col in enumerate(cols_b):
        start = starts[col]
        end = starts[cols_b[i + 1]] if i < len(cols_b) - 1 else len(header_line)
        spans.append((col, start, end))

    j = header_idx + 1
    while j < len(lines) and lines[j].strip() == b"":
        j += 1
    if j < len(lines) and set(lines[j].strip()) == {ord("-")}:
        data_start = j + 1
    else:
        data_start = header_idx + 1

    jobs = []
    for ln in lines[data_start:]:
        if not ln.strip():
            continue
        if ln.startswith(b"----") or ln.startswith(b"Job Id"):
            continue

        row = {}
        for col, s, e in spans:
            row[col.decode()] = ln[s:e].strip().decode("cp949", "ignore")

        if not row.get("Job Id", "").isdigit():
            continue

        candidates = re.findall(rb"\b\d{1,3}(?:,\d{3})+\b|\b\d+\b", ln)
        if candidates:
            k_val = max(candidates, key=lambda b: int(b.replace(b",", b""))).decode("ascii", "ignore")
        else:
            k_val = row.get("Kilobytes", "")

        jobs.append({
            "job_id": row.get("Job Id", ""),
            "policy": row.get("Job Policy", ""),
            "client": row.get("Client", ""),
            "start_dt": parse_nb_datetime(row.get("Start Time", "")),
            "end_dt": parse_nb_datetime(row.get("End Time", "")),
            "size_gb": kb_to_gb(k_val),
            "pathname": row.get("Pathname", ""),
            "instance": row.get("Instance or Database", ""),
        })

    return jobs


def run_pdftotext_bbox(template_pdf: str) -> str:
    out = subprocess.check_output(["pdftotext", "-bbox", template_pdf, "-"])
    return out.decode("utf-8", "ignore")


def parse_bbox(template_pdf: str) -> Tuple[float, float, List[List[Dict]]]:
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    xml_text = run_pdftotext_bbox(template_pdf)
    root = ET.fromstring(xml_text)
    pages = root.findall(".//x:page", ns)
    if not pages:
        raise SystemExit("TEMPLATE_PARSE_FAIL: no pages in bbox output")

    page_words: List[List[Dict]] = []
    width = float(pages[0].attrib["width"])
    height = float(pages[0].attrib["height"])

    for p in pages:
        words = []
        for w in p.findall(".//x:word", ns):
            text = "".join(w.itertext())
            words.append({
                "text": text,
                "xMin": float(w.attrib["xMin"]),
                "yMin": float(w.attrib["yMin"]),
                "xMax": float(w.attrib["xMax"]),
                "yMax": float(w.attrib["yMax"]),
            })
        page_words.append(words)
    return width, height, page_words


def bbox_union(words: List[Dict]) -> Tuple[float, float, float, float]:
    xMin = min(w["xMin"] for w in words)
    yMin = min(w["yMin"] for w in words)
    xMax = max(w["xMax"] for w in words)
    yMax = max(w["yMax"] for w in words)
    return xMin, yMin, xMax, yMax


def find_word(words: List[Dict], text: str) -> Optional[Dict]:
    for w in words:
        if w["text"] == text:
            return w
    return None


def find_line_words(words: List[Dict], target_y: float, tol: float = 0.7) -> List[Dict]:
    line_words = [w for w in words if abs(w["yMin"] - target_y) <= tol]
    return sorted(line_words, key=lambda w: w["xMin"])


def ensure_template_images(template_pdf: str) -> Tuple[str, str]:
    os.makedirs(TEMPLATE_IMG_DIR, exist_ok=True)
    page1 = os.path.join(TEMPLATE_IMG_DIR, "page-1.png")
    page2 = os.path.join(TEMPLATE_IMG_DIR, "page-2.png")
    if not (os.path.exists(page1) and os.path.exists(page2)):
        subprocess.check_call(["pdftoppm", "-png", "-r", "150", template_pdf, os.path.join(TEMPLATE_IMG_DIR, "page")])
    return page1, page2


def draw_replacement(c: canvas.Canvas, page_height: float, box: Tuple[float, float, float, float], text: str, font_name: str):
    xMin, yMin, xMax, yMax = box
    x = xMin
    y = page_height - yMax
    w = (xMax - xMin)
    h = (yMax - yMin)
    c.setFillGray(1.0)
    c.rect(x, y, w, h, stroke=0, fill=1)

    if text:
        font_size = max(9, (yMax - yMin) * 0.95)
        c.setFillColorRGB(0.0, 0.0, 0.0)
        c.setFont(font_name, font_size)
        # Draw left-aligned in the column to avoid clipping
        c.drawString(xMin + 2, page_height - yMax + 1, text)


def latest_sum_by_policy(jobs: List[Dict], policy: str, instance: Optional[str] = None) -> Optional[float]:
    filtered = []
    for j in jobs:
        if j["policy"] != policy:
            continue
        if instance:
            if instance.lower() not in (j.get("instance") or "").lower():
                continue
        if j["end_dt"] is None or j["size_gb"] is None:
            continue
        filtered.append(j)

    if not filtered:
        return None

    latest_date = max(j["end_dt"].date() for j in filtered)
    total = round(sum(j["size_gb"] for j in filtered if j["end_dt"].date() == latest_date), 2)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_pdf", required=True)
    ap.add_argument("--template-pdf", default=TEMPLATE_PDF_DEFAULT)
    args = ap.parse_args()

    in_path = os.path.abspath(args.in_path)
    out_pdf = os.path.abspath(args.out_pdf)

    raw_bytes = open(in_path, "rb").read()
    jobs = extract_jobs(raw_bytes)
    if not jobs:
        raise SystemExit("PARSE_FAIL: 'Job Id ...' header not found or no job rows parsed. Check Export1.txt format.")

    page_width, page_height, page_words = parse_bbox(args.template_pdf)
    page1_img, page2_img = ensure_template_images(args.template_pdf)

    os.makedirs(os.path.dirname(out_pdf), exist_ok=True)

    pdfmetrics.registerFont(TTFont("KFont", FONT_PATH))
    c = canvas.Canvas(out_pdf, pagesize=landscape(A4))

    # Page 1 background only
    c.drawImage(ImageReader(page1_img), 0, 0, width=page_width, height=page_height)
    c.showPage()

    # Page 2: background + replace only the "백업용량" column
    c.drawImage(ImageReader(page2_img), 0, 0, width=page_width, height=page_height)
    words_p2 = page_words[1]

    # Determine backup volume column bounds
    col_xmin = None
    col_xmax = None

    header_backup = find_word(words_p2, "백업용량")
    if header_backup:
        col_xmin = header_backup["xMin"] - 2
        col_xmax = header_backup["xMax"] + 18

    header_path = [find_word(words_p2, t) for t in ["백업", "대상", "및", "경로"]]
    header_result = find_word(words_p2, "백업결과")
    if all(header_path) and header_result:
        seq = header_path
        col_xmin = max(w["xMax"] for w in seq) + 2
        col_xmax = header_result["xMin"] - 2

    if col_xmin is None or col_xmax is None or col_xmax <= col_xmin:
        raise SystemExit("TEMPLATE_PARSE_FAIL: cannot determine backup volume column bounds")

    # Build row boxes from label positions
    row_boxes: Dict[str, Tuple[float, float, float, float]] = {}
    for row in POLICY_ROWS:
        w = find_word(words_p2, row["label"])
        if not w:
            continue
        line_words = find_line_words(words_p2, w["yMin"], tol=0.7)
        if not line_words:
            continue
        _, yMin, _, yMax = bbox_union(line_words)
        row_boxes[row["label"]] = (col_xmin, yMin, col_xmax, yMax)

    # Apply replacements
    for row in POLICY_ROWS:
        label = row["label"]
        box = row_boxes.get(label)
        if not box:
            continue
        total = latest_sum_by_policy(jobs, row["policy"], row.get("instance"))
        text = f"{total:.2f}" if total is not None else ""
        draw_replacement(c, page_height, box, text, "KFont")

    c.showPage()
    c.save()

    print(f"[OK] parsed_jobs_total={len(jobs)}")
    print(f"[OK] PDF generated: {out_pdf}")


if __name__ == "__main__":
    main()
