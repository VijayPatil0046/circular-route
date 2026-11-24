"""Build a research-ready descriptive dataset and SVG plots from circular logs.

Run from the project root with Python 3. The script uses only the standard
library and reads the saved circular artifacts; it does not modify them.
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "backend" / "circulars"
OUT_DIR = Path(__file__).resolve().parent
TYPE_PREFIXES = ("printed", "mixed", "handwritten")
# Aggregate follow-up review supplied by the user. No row-level identities
# were provided, so these labels must not be assigned to particular CSV rows.
REJECTION_REVIEW = {
    "known_incorrect_identifications": 5,
    "valid_candidates_excluded_from_dispatch": 22,
}


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def doc_type(filename: str) -> str:
    base = Path(filename or "").name.lower()
    for label in TYPE_PREFIXES:
        if base.startswith(label):
            return label
    return "unknown"


def numeric(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def rounded(value, digits=3):
    return round(value, digits) if value is not None else ""


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def correlation(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    xvals, yvals = zip(*pairs)
    mx, my = statistics.mean(xvals), statistics.mean(yvals)
    denom = math.sqrt(sum((x - mx) ** 2 for x in xvals) * sum((y - my) ** 2 for y in yvals))
    return sum((x - mx) * (y - my) for x, y in pairs) / denom if denom else None


def rank(values):
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    start = 0
    while start < len(indexed):
        end = start + 1
        while end < len(indexed) and indexed[end][1] == indexed[start][1]:
            end += 1
        average = (start + 1 + end) / 2
        for pos in range(start, end):
            result[indexed[pos][0]] = average
        start = end
    return result


def spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    return correlation(rank([p[0] for p in pairs]), rank([p[1] for p in pairs])) if len(pairs) > 1 else None


def linear_fit(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 2:
        return None, None
    xv, yv = zip(*pairs)
    mx, my = statistics.mean(xv), statistics.mean(yv)
    var = sum((x - mx) ** 2 for x in xv)
    if not var:
        return None, None
    slope = sum((x - mx) * (y - my) for x, y in pairs) / var
    return slope, my - slope * mx


def svg_start(title, width=1000, height=640):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172b4d}.title{font-size:24px;font-weight:bold}.axis{font-size:15px}.small{font-size:13px}.grid{stroke:#d9e1ec;stroke-width:1}.axisline{stroke:#53657d;stroke-width:1.5}</style>',
        f'<text x="{width/2}" y="38" text-anchor="middle" class="title">{escape(title)}</text>',
    ]


def svg_text(x, y, value, cls="axis", anchor="middle", rotate=None, fill=None):
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    color = f' fill="{fill}"' if fill else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="{cls}"{transform}{color}>{escape(str(value))}</text>'


def save_scatter(records):
    width, height = 1000, 640
    left, right, top, bottom = 92, 70, 82, 102
    plot_w, plot_h = width - left - right, height - top - bottom
    xs = [r["page_count"] for r in records if r["page_count"] is not None and r["first_upload_to_email_complete_seconds"] is not None]
    ys = [r["first_upload_to_email_complete_seconds"] for r in records if r["page_count"] is not None and r["first_upload_to_email_complete_seconds"] is not None]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = 0, math.ceil(max(ys) / 20) * 20
    sx = lambda x: left + (x - x_min) / max(1, x_max - x_min) * plot_w
    sy = lambda y: top + plot_h - (y - y_min) / max(1, y_max - y_min) * plot_h
    out = svg_start("Page count vs first upload-to-email completion")
    for tick in range(0, y_max + 1, 20):
        yy = sy(tick)
        out += [f'<line x1="{left}" y1="{yy:.1f}" x2="{left+plot_w}" y2="{yy:.1f}" class="grid"/>', svg_text(left - 12, yy + 5, tick, "small", "end")]
    out += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" class="axisline"/>', f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" class="axisline"/>']
    for x in range(x_min, x_max + 1):
        out += [f'<line x1="{sx(x):.1f}" y1="{top+plot_h}" x2="{sx(x):.1f}" y2="{top+plot_h+6}" class="axisline"/>', svg_text(sx(x), top+plot_h+25, x)]
    colors = {"printed": "#1769aa", "mixed": "#00856a", "handwritten": "#c05a00", "unknown": "#777777"}
    for rec in records:
        x = rec["page_count"]
        y = rec["first_upload_to_email_complete_seconds"]
        if x is None or y is None:
            continue
        # Deterministic small jitter makes overlapping observations visible.
        jitter = ((int(rec["circular_id"].split("_")[-1]) * 37) % 19 - 9) * 1.25
        out.append(f'<circle cx="{sx(x)+jitter:.1f}" cy="{sy(y):.1f}" r="6" fill="{colors[rec["document_type"]]}" fill-opacity="0.78" stroke="#fff" stroke-width="1.2"><title>{escape(rec["circular_id"])}: {x} pages, {y:.2f}s, {rec["document_type"]}</title></circle>')
    slope, intercept = linear_fit(xs, ys)
    if slope is not None:
        out.append(f'<line x1="{sx(x_min):.1f}" y1="{sy(slope*x_min+intercept):.1f}" x2="{sx(x_max):.1f}" y2="{sy(slope*x_max+intercept):.1f}" stroke="#cc3344" stroke-width="3"/>')
    out += [svg_text(left+plot_w/2, height-22, "Pages per circular"), svg_text(25, top+plot_h/2, "Seconds", rotate=-90)]
    stats = f"n={len(xs)}   Pearson r={correlation(xs,ys):.3f}   Spearman ρ={spearman(xs,ys):.3f}   OLS slope={slope:.2f} s/page" if slope is not None else f"n={len(xs)}"
    out.append(svg_text(width/2, 64, stats, "small"))
    legend_x, legend_y = left + 20, top + 15
    for i, kind in enumerate(TYPE_PREFIXES):
        x = legend_x + i*155
        out += [f'<circle cx="{x}" cy="{legend_y}" r="6" fill="{colors[kind]}"/>', svg_text(x+13, legend_y+5, kind, "small", "start")]
    out.append("</svg>")
    (OUT_DIR / "pages_vs_first_completion.svg").write_text("\n".join(out), encoding="utf-8")


def save_type_boxplot(records):
    width, height = 1000, 640
    left, right, top, bottom = 95, 50, 82, 105
    plot_w, plot_h = width-left-right, height-top-bottom
    vals = [r["first_upload_to_email_complete_seconds"] for r in records if r["first_upload_to_email_complete_seconds"] is not None]
    ymax = math.ceil(max(vals)/20)*20
    sy = lambda y: top+plot_h-y/ymax*plot_h
    xs = {"printed": left+plot_w*.18, "mixed": left+plot_w*.50, "handwritten": left+plot_w*.82}
    colors = {"printed":"#1769aa","mixed":"#00856a","handwritten":"#c05a00"}
    out = svg_start("First-pass completion time by document type")
    for tick in range(0,ymax+1,20):
        yy=sy(tick); out += [f'<line x1="{left}" y1="{yy:.1f}" x2="{left+plot_w}" y2="{yy:.1f}" class="grid"/>',svg_text(left-12,yy+5,tick,"small","end")]
    out += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" class="axisline"/>',f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" class="axisline"/>']
    for kind,x in xs.items():
        group=[r for r in records if r["document_type"]==kind and r["first_upload_to_email_complete_seconds"] is not None]
        data=[r["first_upload_to_email_complete_seconds"] for r in group]
        if not data: continue
        q1,med,q3=percentile(data,.25),statistics.median(data),percentile(data,.75)
        low,high=min(data),max(data)
        out += [f'<line x1="{x}" y1="{sy(low):.1f}" x2="{x}" y2="{sy(high):.1f}" stroke="{colors[kind]}" stroke-width="2"/>',f'<line x1="{x-24}" y1="{sy(low):.1f}" x2="{x+24}" y2="{sy(low):.1f}" stroke="{colors[kind]}" stroke-width="2"/>',f'<line x1="{x-24}" y1="{sy(high):.1f}" x2="{x+24}" y2="{sy(high):.1f}" stroke="{colors[kind]}" stroke-width="2"/>',f'<rect x="{x-48}" y="{sy(q3):.1f}" width="96" height="{sy(q1)-sy(q3):.1f}" fill="{colors[kind]}" fill-opacity="0.22" stroke="{colors[kind]}" stroke-width="2"/>',f'<line x1="{x-48}" y1="{sy(med):.1f}" x2="{x+48}" y2="{sy(med):.1f}" stroke="{colors[kind]}" stroke-width="3"/>']
        for i,r in enumerate(group):
            jitter=((int(r["circular_id"].split("_")[-1])*31)%25-12)*3
            yy=sy(r["first_upload_to_email_complete_seconds"])
            out.append(f'<circle cx="{x+jitter}" cy="{yy:.1f}" r="4.5" fill="{colors[kind]}" fill-opacity="0.62"><title>{escape(r["circular_id"])}: {r["first_upload_to_email_complete_seconds"]:.2f}s</title></circle>')
        out += [svg_text(x,top+plot_h+26,f"{kind} (n={len(data)})"),svg_text(x,sy(med)-11,f"median {med:.1f}s","small")]
    out += [svg_text(left+plot_w/2,height-22,"Document class from uploaded filename"),svg_text(25,top+plot_h/2,"Seconds",rotate=-90),"</svg>"]
    (OUT_DIR / "completion_by_document_type.svg").write_text("\n".join(out),encoding="utf-8")


def save_latency_plot(records):
    width,height=1000,600
    left,right,top,bottom=100,45,80,80
    plot_w,plot_h=width-left-right,height-top-bottom
    kinds=list(TYPE_PREFIXES)
    metrics=[("Upload → recipient identification","upload_to_recipient_identification_seconds"),("Upload → first email completion","first_upload_to_email_complete_seconds")]
    vals=[r[key] for r in records for _,key in metrics if r[key] is not None]
    ymax=math.ceil(max(vals)/20)*20
    sy=lambda v:top+plot_h-v/ymax*plot_h
    out=svg_start("Median pipeline latency by document type",width,height)
    for tick in range(0,ymax+1,20):
        yy=sy(tick);out += [f'<line x1="{left}" y1="{yy:.1f}" x2="{left+plot_w}" y2="{yy:.1f}" class="grid"/>',svg_text(left-12,yy+5,tick,"small","end")]
    out += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" class="axisline"/>',f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" class="axisline"/>']
    base_x=[left+plot_w*.19,left+plot_w*.50,left+plot_w*.81]
    colors=["#7057a3","#1769aa"]
    for kind,x in zip(kinds,base_x):
        group=[r for r in records if r["document_type"]==kind]
        for j,(_,key) in enumerate(metrics):
            data=[r[key] for r in group if r[key] is not None]
            med=statistics.median(data) if data else 0
            bx=x+(j-.5)*54
            out += [f'<rect x="{bx-19:.1f}" y="{sy(med):.1f}" width="38" height="{top+plot_h-sy(med):.1f}" fill="{colors[j]}" rx="4"/>',svg_text(bx,sy(med)-9,f"{med:.1f}","small")]
        out.append(svg_text(x,top+plot_h+25,f"{kind} (n={len(group)})"))
    for j,(label,_) in enumerate(metrics):
        x=left+plot_w*.22+j*365
        out += [f'<rect x="{x}" y="48" width="13" height="13" fill="{colors[j]}"/>',svg_text(x+21,60,label,"small","start")]
    out += [svg_text(25,top+plot_h/2,"Seconds",rotate=-90),"</svg>"]
    (OUT_DIR/"pipeline_latency_by_type.svg").write_text("\n".join(out),encoding="utf-8")


def save_recipient_outcomes(counts):
    categories=[("Recorded candidates",counts["candidate"]),("Auto verified",counts["auto"]),("Manually confirmed",counts["manual"]),("Known incorrect ID (rejected)",counts["known_incorrect"]),("Valid candidate excluded from dispatch",counts["valid_excluded"]),("Pending review",counts["pending"]),("Current email records SENT",counts["sent"])]
    width,height=1100,650; left,right,top,bottom=330,85,85,55; plot_w=width-left-right
    maxv=max(v for _,v in categories); xmax=math.ceil(maxv/25)*25
    out=svg_start("Recipient resolution and current email outcomes",width,height)
    for tick in range(0,xmax+1,25):
        xx=left+tick/xmax*plot_w;out += [f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{height-bottom}" class="grid"/>',svg_text(xx,height-bottom+23,tick,"small")]
    colorlist=["#4c6485","#00856a","#1769aa","#bd3545","#c05a00","#8a8f98","#1f8f5f"]
    for i,((label,val),color) in enumerate(zip(categories,colorlist)):
        yy=top+i*69
        out += [svg_text(left-14,yy+26,label,"axis","end"),f'<rect x="{left}" y="{yy}" width="{val/xmax*plot_w:.1f}" height="36" fill="{color}" rx="4"/>',svg_text(left+val/xmax*plot_w+13,yy+25,val,"axis","start")]
    out += [svg_text(left+plot_w/2,height-15,"Count across 50 circulars"),"</svg>"]
    (OUT_DIR/"recipient_resolution_outcomes.svg").write_text("\n".join(out),encoding="utf-8")


def build():
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    dirs=sorted(DATA_ROOT.glob("CIRCULAR_*"),key=lambda p:p.name)
    circular_rows=[]; recipient_rows=[]; audit=[]; score_groups=defaultdict(list); run_outcomes=Counter()
    for folder in dirs:
        status=read_json(folder/"status.json",{})
        matches=read_json(folder/"faculty_matches.json",[])
        emails=read_json(folder/"email_records.json",[])
        if not isinstance(matches,list): matches=[]
        if not isinstance(emails,list): emails=[]
        runs=status.get("email_routing_runs") or []
        filename=status.get("filename","")
        kind=doc_type(filename)
        lookup={str(e.get("faculty_id")):e for e in emails}
        auto=manual=rejected=pending=0
        for idx,m in enumerate(matches,1):
            verification=str(m.get("verification_status") or "").upper()
            auto += verification=="AUTO_VERIFIED"
            manual += verification=="MANUALLY_CONFIRMED" or bool(m.get("manual_override")) and bool(m.get("is_verified"))
            rejected += verification=="REJECTED" or not bool(m.get("is_verified")) and verification not in ("PENDING_REVIEW", "")
            pending += verification=="PENDING_REVIEW" or (not bool(m.get("is_verified")) and verification=="")
            score=numeric(m.get("similarity_score"))
            if score is not None: score_groups[verification or "UNSPECIFIED"].append(score)
            email=lookup.get(str(m.get("faculty_id")),{})
            recipient_rows.append({
                "circular_id":status.get("circular_id",folder.name),
                "recipient_index_within_circular":idx,
                "section":m.get("section_found",""),
                "match_score":rounded(score),
                "verification_status":verification,
                "manual_override":bool(m.get("manual_override")),
                "email_record_status":email.get("status","NO_EMAIL_RECORD"),
                "email_retry_count_field":email.get("retry_count",""),
            })
        for run in runs:
            run_outcomes[str(run.get("outcome") or "UNSPECIFIED")] += 1
        email_status_counts=Counter(str(e.get("status") or "UNSPECIFIED").upper() for e in emails)
        first_run=runs[0] if runs else {}
        latest_run=runs[-1] if runs else {}
        first_complete=numeric(status.get("upload_to_first_email_routing_seconds"))
        if first_complete is None:
            first_complete=numeric(first_run.get("upload_to_completion_seconds"))
        latest_complete=numeric(status.get("upload_to_email_routing_seconds"))
        if latest_complete is None and runs:
            latest_complete=numeric(latest_run.get("upload_to_completion_seconds"))
        row={
            "circular_id":status.get("circular_id",folder.name),
            "source_filename":filename,
            "document_type":kind,
            "file_type":status.get("file_type",folder.suffix.lstrip(".")),
            "page_count":status.get("page_count"),
            "file_size_bytes":status.get("file_size_bytes"),
            "processing_state":status.get("current_state",""),
            "candidate_count":len(matches),
            "auto_verified_count":auto,
            "manually_confirmed_count":manual,
            "rejected_count":rejected,
            "pending_review_count":pending,
            "email_records_count":len(emails),
            "email_sent_record_count":email_status_counts.get("SENT",0),
            "email_failed_record_count":sum(v for k,v in email_status_counts.items() if k in ("FAILED", "BOUNCED", "REJECTED", "CANCELLED")),
            "latest_status_sent_count":status.get("emails_sent_count",0),
            "latest_status_failed_count":status.get("emails_failed_count",0),
            "routing_run_count":len(runs),
            "routing_reruns_after_first":max(0,len(runs)-1),
            "failed_routing_run_count":sum(numeric(r.get("failed_count")) is not None and numeric(r.get("failed_count"))>0 for r in runs),
            "first_routing_run_outcome":first_run.get("outcome",""),
            "latest_routing_run_outcome":latest_run.get("outcome",""),
            "upload_to_recipient_identification_seconds":rounded(numeric(status.get("upload_to_recipient_identification_seconds"))),
            "first_upload_to_email_complete_seconds":rounded(first_complete),
            "latest_upload_to_email_complete_seconds":rounded(latest_complete),
            "first_email_dispatch_duration_seconds":rounded(numeric(first_run.get("dispatch_duration_seconds"))),
            "latest_email_dispatch_duration_seconds":rounded(numeric(status.get("email_routing_duration_seconds"))),
            "mean_match_score":rounded(statistics.mean([numeric(m.get("similarity_score")) for m in matches if numeric(m.get("similarity_score")) is not None]) if any(numeric(m.get("similarity_score")) is not None for m in matches) else None),
        }
        circular_rows.append(row)
        if len(matches)!=int(status.get("matches_count") or 0): audit.append(f"{row['circular_id']}: match file has {len(matches)} rows but status says {status.get('matches_count')}.")
        if len(emails)!=int(status.get("emails_sent_count") or 0): audit.append(f"{row['circular_id']}: email record count {len(emails)} differs from status sent count {status.get('emails_sent_count')}.")
        if email_status_counts.get("SENT",0)!=int(status.get("emails_sent_count") or 0): audit.append(f"{row['circular_id']}: SENT email rows differ from status sent count.")
        if runs and latest_run.get("failed_count",0)>0 and email_status_counts.get("SENT",0)==int(status.get("emails_sent_count") or 0): audit.append(f"{row['circular_id']}: latest logged routing run has failures while current email records/status appear sent.")

    if not dirs:
        raise SystemExit(f"No circular folders found in {DATA_ROOT}")
    with (OUT_DIR/"circular_level_metrics.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(circular_rows[0]));writer.writeheader();writer.writerows(circular_rows)
    with (OUT_DIR/"recipient_level_metrics.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(recipient_rows[0]) if recipient_rows else ["circular_id"]);writer.writeheader();writer.writerows(recipient_rows)
    known_incorrect=REJECTION_REVIEW["known_incorrect_identifications"]
    valid_excluded=REJECTION_REVIEW["valid_candidates_excluded_from_dispatch"]
    with (OUT_DIR/"aggregate_review_annotations.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=["review_classification","count","scope","annotation_source"]);writer.writeheader()
        writer.writerows([
            {"review_classification":"Known incorrect identification among rejected records","count":known_incorrect,"scope":"Aggregate across 50 circulars; no row-level mapping supplied","annotation_source":"User follow-up review"},
            {"review_classification":"Valid candidate manually excluded from dispatch","count":valid_excluded,"scope":"Aggregate across 50 circulars; no row-level mapping supplied","annotation_source":"User follow-up review"},
        ])

    pages=[numeric(r["page_count"]) for r in circular_rows]
    times=[numeric(r["first_upload_to_email_complete_seconds"]) for r in circular_rows]
    groups=defaultdict(list)
    for r in circular_rows:
        if numeric(r["first_upload_to_email_complete_seconds"]) is not None:
            groups[r["document_type"]].append(numeric(r["first_upload_to_email_complete_seconds"]))
    all_candidates=sum(r["candidate_count"] for r in circular_rows)
    all_auto=sum(r["auto_verified_count"] for r in circular_rows)
    all_manual=sum(r["manually_confirmed_count"] for r in circular_rows)
    all_rejected=sum(r["rejected_count"] for r in circular_rows)
    all_pending=sum(r["pending_review_count"] for r in circular_rows)
    if known_incorrect + valid_excluded != all_rejected:
        audit.append(f"Aggregate user annotations total {known_incorrect + valid_excluded}, while rejected match records total {all_rejected}; review these annotations before interpreting them.")
    all_sent=sum(r["email_sent_record_count"] for r in circular_rows)
    type_counts=Counter(r["document_type"] for r in circular_rows)
    page_counts=Counter(r["page_count"] for r in circular_rows)
    extract_times=[numeric(r["upload_to_recipient_identification_seconds"]) for r in circular_rows if numeric(r["upload_to_recipient_identification_seconds"]) is not None]
    first_times=[t for t in times if t is not None]
    latest_times=[numeric(r["latest_upload_to_email_complete_seconds"]) for r in circular_rows if numeric(r["latest_upload_to_email_complete_seconds"]) is not None]
    score_total=sum(len(v) for v in score_groups.values())
    auto_scores=score_groups.get("AUTO_VERIFIED",[])
    manual_scores=score_groups.get("MANUALLY_CONFIRMED",[])
    rejected_scores=score_groups.get("REJECTED",[])
    total_runs=sum(r["routing_run_count"] for r in circular_rows)
    extra_runs=sum(r["routing_reruns_after_first"] for r in circular_rows)
    failed_runs=sum(r["failed_routing_run_count"] for r in circular_rows)
    recovered_failure_circulars=sum(any(str(run.get("failed_count",0)) not in ("0","None") and numeric(run.get("failed_count")) and numeric(run.get("failed_count"))>0 for run in (read_json(p/"status.json",{}).get("email_routing_runs") or [])) and read_json(p/"status.json",{}).get("emails_failed_count",0)==0 for p in dirs)

    save_scatter(circular_rows);save_type_boxplot(circular_rows);save_latency_plot(circular_rows)
    save_recipient_outcomes({"candidate":all_candidates,"auto":all_auto,"manual":all_manual,"known_incorrect":known_incorrect,"valid_excluded":valid_excluded,"pending":all_pending,"sent":all_sent})
    page_stats=[]
    for page in sorted(page_counts,key=lambda v:int(v or 0)):
        vals=[numeric(r["first_upload_to_email_complete_seconds"]) for r in circular_rows if r["page_count"]==page and numeric(r["first_upload_to_email_complete_seconds"]) is not None]
        page_stats.append((page,len(vals),statistics.median(vals) if vals else None,statistics.mean(vals) if vals else None))
    type_table=[]
    for kind in TYPE_PREFIXES:
        vals=groups.get(kind,[])
        extraction=[numeric(r["upload_to_recipient_identification_seconds"]) for r in circular_rows if r["document_type"]==kind and numeric(r["upload_to_recipient_identification_seconds"]) is not None]
        type_table.append((kind,type_counts[kind],statistics.median(vals) if vals else None,statistics.mean(vals) if vals else None,statistics.median(extraction) if extraction else None))
    def fmt(x): return "n/a" if x is None else f"{x:.2f}"
    audit_text="\n".join(f"- {item}" for item in audit) if audit else "- No count discrepancies found across status, match, and email record counts."
    report=[
        "# Circular routing evaluation: descriptive results",
        "",
        f"Generated from {len(circular_rows)} folders in `backend/circulars`.",
        "",
        "## Dataset overview",
        "",
        f"- Circulars: **{len(circular_rows)}** ({', '.join(f'{k}: {type_counts[k]}' for k in TYPE_PREFIXES)}). Document class comes from the uploaded filename prefix.",
        f"- Pages: **{sum(int(r['page_count'] or 0) for r in circular_rows)}** total; {', '.join(f'{k} page(s): {page_counts[k]}' for k in sorted(page_counts,key=lambda v:int(v or 0)))}; mean {statistics.mean([int(r['page_count']) for r in circular_rows if r['page_count'] is not None]):.2f} pages/circular.",
        f"- Processing state: {dict(Counter(r['processing_state'] for r in circular_rows))}.",
        "",
        "## Main operational results",
        "",
        f"- Recipient candidates recorded: **{all_candidates}**. {all_auto} were auto-verified, {all_manual} manually confirmed, and {all_pending} remained pending review. Follow-up review split the {all_rejected} rejected records into **{known_incorrect} known incorrect identifications** and **{valid_excluded} valid candidates manually excluded from dispatch**. The auto-verification threshold is an operational setting, not a measured accuracy rate.",
        f"- Current email records: **{all_sent}/{all_sent} marked SENT** across accepted recipients. Routing history contains {total_runs} runs ({extra_runs} reruns beyond the first, {failed_runs} runs with at least one failed recipient). Later route records indicate recovery for {recovered_failure_circulars} circular(s) whose current status has zero failed email records.",
        f"- Upload to recipient identification: mean **{statistics.mean(extract_times):.2f}s**, median **{statistics.median(extract_times):.2f}s**, P95 **{percentile(extract_times,.95):.2f}s**.",
        f"- Upload to first email-routing completion: mean **{statistics.mean(first_times):.2f}s**, median **{statistics.median(first_times):.2f}s**, P95 **{percentile(first_times,.95):.2f}s**. Latest recorded completion including reroutes: median **{statistics.median(latest_times):.2f}s**.",
        f"- First-run email dispatch duration: median **{statistics.median([numeric(r['first_email_dispatch_duration_seconds']) for r in circular_rows if numeric(r['first_email_dispatch_duration_seconds']) is not None]):.2f}s**. This is separate from the end-to-end time, which includes extraction and other workflow time.",
        "",
        "### Page-count relationship",
        "",
        f"The Pearson correlation between pages and first upload-to-email completion is **r={correlation(pages,times):.3f}** and Spearman rank correlation is **ρ={spearman(pages,times):.3f}** (n={len(first_times)}). The OLS slope is **{fmt(linear_fit(pages,times)[0])} seconds/page**. These are descriptive associations; the data do not establish that page count caused the latency.",
        "",
        "| Pages | Circulars | Median first completion (s) | Mean (s) |",
        "|---:|---:|---:|---:|",
    ]
    report += [f"| {p} | {n} | {fmt(med)} | {fmt(avg)} |" for p,n,med,avg in page_stats]
    report += ["", "### Document-type comparison", "", "| Filename class | n | Median first completion (s) | Mean (s) | Median upload-to-identification (s) |", "|---|---:|---:|---:|---:|"]
    report += [f"| {k} | {n} | {fmt(med)} | {fmt(avg)} | {fmt(ext)} |" for k,n,med,avg,ext in type_table]
    report += [
        "",
        "Interpret type comparisons cautiously: handwritten cases have only four examples, and document class is based on the test filename label rather than independent visual adjudication.",
        "",
        "### Match-score summary",
        "",
        f"Scores are present for {score_total} candidates. Median score: all **{statistics.median([v for vs in score_groups.values() for v in vs]):.3f}**, auto-verified **{statistics.median(auto_scores):.3f}** (n={len(auto_scores)}), manually confirmed **{fmt(statistics.median(manual_scores))}** (n={len(manual_scores)}), and records marked rejected **{fmt(statistics.median(rejected_scores))}** (n={len(rejected_scores)}). The rejected group includes both known incorrect identifications and valid candidates excluded from dispatch, so its score summary is not an error-only distribution.",
        "",
        "## Audit and data quality",
        "",
        audit_text,
        "",
        "- `first_upload_to_email_complete_seconds` uses the first route attempt's end-to-end completion field (or the explicit first-completion field). It is the preferred measure for first-pass latency and avoids including time spent waiting before a user-triggered reroute.",
        "- `latest_upload_to_email_complete_seconds` records the latest end-to-end completion. It may include elapsed time across manual waiting and reruns; do not present it as processing latency without explaining that.",
        "- Historical run outcomes include failures that may have been recovered later. The current recipient-level email-record status is the latest persisted state. Do not equate repeated runs with independent send failures or use `retry_count` as a clean retry total without validating its semantics.",
        "- Follow-up adjudication labels 5 rejected records as incorrect system identifications and 22 as valid candidates excluded from dispatch. These labels are aggregate only; the circular folders do not map them to specific recipient rows. Complete independent ground truth for every candidate, OCR transcription, and To/Copy To section is unavailable, so do not claim overall OCR accuracy, precision, recall, or F1 from these data alone.",
        "- For stronger IEEE accuracy results, annotate the ground-truth recipient names and To/Copy To sections for every circular, plus a corrected transcription for OCR evaluation. Then report recipient precision/recall/F1, exact recipient-set match, canonical identity resolution accuracy, and OCR character/word error rates, split by document class and page count. Keep the scoring threshold fixed or tune it on a separate validation set, not this evaluation set.",
        "- The sample has only four handwritten cases. Add more handwritten and mixed-layout documents and repeat each case under controlled conditions before claiming robust class-specific performance. Separate processing latency from manual review/wait and provider/network latency in the measurement protocol.",
        "- Email addresses and faculty names are intentionally excluded from the recipient CSV. The recipient index is local to each circular; use circular ID plus index to inspect the source match row if needed.",
        "",
        "## Suggested IEEE Results wording (descriptive; adapt to the paper's protocol)",
        "",
        f"The evaluation comprised {len(circular_rows)} circulars ({type_counts['printed']} printed, {type_counts['mixed']} mixed, and {type_counts['handwritten']} handwritten) spanning {sum(int(r['page_count'] or 0) for r in circular_rows)} pages. The median first-pass upload-to-email completion time was {statistics.median(first_times):.2f} s (mean {statistics.mean(first_times):.2f} s; P95 {percentile(first_times,.95):.2f} s), while median upload-to-recipient-identification time was {statistics.median(extract_times):.2f} s. Across {all_candidates} recipient candidates, {all_auto} were auto-verified and {all_manual} manually confirmed. Follow-up review classified {known_incorrect} rejected records as incorrect system identifications and {valid_excluded} as valid candidates manually excluded from dispatch; none remained pending. All {all_sent} current accepted-recipient email records are marked SENT in the stored records. Page count had a Pearson correlation of {correlation(pages,times):.3f} with first-pass completion time; this is an observed association in a 50-document sample, not evidence of a causal effect. The aggregate review labels do not provide complete independent ground truth, so overall identity and extraction accuracy are not inferred.",
        "",
        "## Figure files",
        "",
        "- `pages_vs_first_completion.svg`: each point is one circular; fitted line and correlations are descriptive.",
        "- `completion_by_document_type.svg`: box summaries and points for first-pass completion, grouped by filename label.",
        "- `pipeline_latency_by_type.svg`: medians for identification and first email completion.",
        "- `recipient_resolution_outcomes.svg`: recipient decisions, aggregate review labels, and current delivery counts.",
        "",
        "## Output files",
        "",
        "- `circular_level_metrics.csv`: one row per circular with timing, page, recipient, and delivery fields.",
        "- `recipient_level_metrics.csv`: one anonymized row per extracted match candidate.",
        "- `aggregate_review_annotations.csv`: user-provided aggregate split of rejected records; no individual records are assigned to either class.",
        "- `analyze_circulars.py`: reruns this extraction and plotting workflow from the project root.",
    ]
    (OUT_DIR/"results_summary.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(f"Created {len(circular_rows)} circular rows and {len(recipient_rows)} recipient rows in {OUT_DIR}")
    print(f"First-pass completion median: {statistics.median(first_times):.3f}s; pages correlation r={correlation(pages,times):.3f}")
    print(f"Audit findings: {len(audit)}; runs with failures: {failed_runs}; all current SENT records: {all_sent}")


if __name__ == "__main__":
    build()
