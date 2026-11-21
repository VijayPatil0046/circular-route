"""Plot measured OCR latency against page count from latency_benchmark.csv."""

import csv
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "latency_benchmark.csv"
OUTPUT = ROOT / "pages_vs_latency.svg"
COLORS = {"printed": "#2563eb", "handwritten": "#9333ea"}


def read_rows():
    with DATA.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def make_chart(rows):
    width, height = 1120, 690
    left, right, top, bottom = 90, 55, 86, 105
    pw, ph = width - left - right, height - top - bottom
    max_pages = max(int(row["page_count"]) for row in rows)
    max_latency = max(float(row["latency_seconds"]) for row in rows)
    y_max = max(10, int((max_latency + 9) // 10) * 10)
    x = lambda page: left + ((page - 0.5) / max_pages) * pw
    y = lambda sec: top + ph - sec / y_max * ph
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fff"/>',
             '<style>text{font:14px Arial,sans-serif;fill:#334155}.title{font-size:23px;font-weight:700;fill:#0f172a}.subtitle{font-size:13px;fill:#64748b}.axis{stroke:#64748b}.grid{stroke:#e2e8f0}</style>',
             f'<text class="title" x="{width/2}" y="35" text-anchor="middle">OCR Latency by Document Page Count</text>',
             f'<text class="subtitle" x="{width/2}" y="58" text-anchor="middle">Measured project circulars · each dot is one OCR run</text>',
             f'<text x="{width/2}" y="{height-30}" text-anchor="middle">Number of pages</text>',
             f'<text x="24" y="{height/2}" text-anchor="middle" transform="rotate(-90 24 {height/2})">OCR latency (seconds)</text>']
    for i in range(6):
        val = y_max * i / 5
        yy = y(val)
        parts.extend([f'<line class="grid" x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}"/>',
                      f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end">{val:.0f}</text>'])
    for page in range(1, max_pages + 1):
        xx = x(page)
        parts.append(f'<text x="{xx:.1f}" y="{height-bottom+27}" text-anchor="middle">{page}</text>')
    parts.extend([f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
                  f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>'])
    grouped = {}
    for row in rows:
        grouped.setdefault(int(row["page_count"]), []).append(row)
    for page, group in grouped.items():
        for i, row in enumerate(group):
            jitter = (i - (len(group)-1)/2) * min(13, 100/max(1, len(group)))
            cx, cy = x(page) + jitter, y(float(row["latency_seconds"]))
            color = COLORS[row["document_type"]]
            marker = '*' if row.get('cold_start', '').lower() == 'true' else ''
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{color}" fill-opacity=".84" stroke="#fff" stroke-width="1.5"><title>{row["circular_id"]}: {row["page_count"]} page(s), {float(row["latency_seconds"]):.2f}s {marker}</title></circle>')
    for label, color, xx in [("Printed", COLORS["printed"], left+25), ("Handwritten marker", COLORS["handwritten"], left+150)]:
        parts.extend([f'<circle cx="{xx}" cy="{height-70}" r="6" fill="{color}"/>',
                      f'<text x="{xx+12}" y="{height-65}">{label}</text>'])
    parts.append(f'<text class="subtitle" x="{width-right}" y="{height-65}" text-anchor="end">* First run includes model initialization</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


if __name__ == "__main__":
    OUTPUT.write_text(make_chart(read_rows()), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
