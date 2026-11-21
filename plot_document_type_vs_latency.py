"""Plot measured OCR latency by recognition type from latency_benchmark.csv."""

import csv
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "latency_benchmark.csv"
OUTPUT = ROOT / "document_type_vs_latency.svg"
COLORS = {"printed": "#2563eb", "handwritten": "#9333ea"}


def read_rows():
    with DATA.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def make_chart(rows):
    width, height = 1000, 690
    left, right, top, bottom = 92, 55, 86, 105
    pw, ph = width - left - right, height - top - bottom
    max_latency = max(float(row["latency_seconds"]) for row in rows)
    y_max = max(10, int((max_latency + 9) // 10) * 10)
    y = lambda sec: top + ph - sec / y_max * ph
    centers = {"printed": left + pw * .31, "handwritten": left + pw * .73}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fff"/>',
             '<style>text{font:14px Arial,sans-serif;fill:#334155}.title{font-size:23px;font-weight:700;fill:#0f172a}.subtitle{font-size:13px;fill:#64748b}.axis{stroke:#64748b}.grid{stroke:#e2e8f0}</style>',
             f'<text class="title" x="{width/2}" y="35" text-anchor="middle">OCR Latency by Document Type</text>',
             f'<text class="subtitle" x="{width/2}" y="58" text-anchor="middle">Per-document timings with category mean</text>',
             f'<text x="{width/2}" y="{height-30}" text-anchor="middle">Recognition type</text>',
             f'<text x="24" y="{height/2}" text-anchor="middle" transform="rotate(-90 24 {height/2})">OCR latency (seconds)</text>']
    for i in range(6):
        val = y_max * i / 5
        yy = y(val)
        parts.extend([f'<line class="grid" x1="{left}" y1="{yy:.1f}" x2="{width-right}" y2="{yy:.1f}"/>',
                      f'<text x="{left-12}" y="{yy+5:.1f}" text-anchor="end">{val:.0f}</text>'])
    parts.extend([f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
                  f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>'])
    for kind in ("printed", "handwritten"):
        group = [row for row in rows if row["document_type"] == kind]
        if not group:
            continue
        center = centers[kind]
        values = [float(row["latency_seconds"]) for row in group]
        mean = sum(values) / len(values)
        bar_w = 140
        parts.append(f'<rect x="{center-bar_w/2:.1f}" y="{y(mean):.1f}" width="{bar_w}" height="{height-bottom-y(mean):.1f}" rx="7" fill="{COLORS[kind]}" fill-opacity=".18"/>')
        parts.append(f'<line x1="{center-bar_w/2:.1f}" y1="{y(mean):.1f}" x2="{center+bar_w/2:.1f}" y2="{y(mean):.1f}" stroke="{COLORS[kind]}" stroke-width="3"/>')
        for i, row in enumerate(group):
            jitter = (i - (len(group)-1)/2) * min(15, 100/max(1, len(group)))
            cx, cy = center + jitter, y(float(row["latency_seconds"]))
            marker = ' · cold start' if row.get('cold_start', '').lower() == 'true' else ''
            parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{COLORS[kind]}" stroke="#fff" stroke-width="1.5"><title>{row["circular_id"]}: {float(row["latency_seconds"]):.2f}s{marker}</title></circle>')
        label = "Printed" if kind == "printed" else "Handwritten marker"
        parts.append(f'<text x="{center:.1f}" y="{height-bottom+28}" text-anchor="middle">{label} (n={len(group)})</text>')
        parts.append(f'<text x="{center:.1f}" y="{y(mean)-12:.1f}" text-anchor="middle" font-weight="bold">mean {mean:.1f}s</text>')
    parts.append(f'<text class="subtitle" x="{width/2}" y="{height-65}" text-anchor="middle">Handwritten class uses the saved OCR [Handwritten] marker; first run includes model initialization</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


if __name__ == "__main__":
    OUTPUT.write_text(make_chart(read_rows()), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
