# Circular routing evaluation: descriptive results

Generated from 50 folders in `backend/circulars`.

## Dataset overview

- Circulars: **50** (printed: 28, mixed: 18, handwritten: 4). Document class comes from the uploaded filename prefix.
- Pages: **96** total; 1 page(s): 19, 2 page(s): 16, 3 page(s): 15; mean 1.92 pages/circular.
- Processing state: {'COMPLETED': 49, 'REQUIRES_REVIEW': 1}.

## Main operational results

- Recipient candidates recorded: **200**. 163 were auto-verified, 10 manually confirmed, and 0 remained pending review. Follow-up review split the 27 rejected records into **5 known incorrect identifications** and **22 valid candidates manually excluded from dispatch**. The auto-verification threshold is an operational setting, not a measured accuracy rate.
- Current email records: **173/173 marked SENT** across accepted recipients. Routing history contains 76 runs (26 reruns beyond the first, 3 runs with at least one failed recipient). Later route records indicate recovery for 2 circular(s) whose current status has zero failed email records.
- Upload to recipient identification: mean **53.20s**, median **51.12s**, P95 **84.57s**.
- Upload to first email-routing completion: mean **66.27s**, median **65.22s**, P95 **105.12s**. Latest recorded completion including reroutes: median **68.38s**.
- First-run email dispatch duration: median **1.95s**. This is separate from the end-to-end time, which includes extraction and other workflow time.

### Page-count relationship

The Pearson correlation between pages and first upload-to-email completion is **r=0.763** and Spearman rank correlation is **ρ=0.768** (n=50). The OLS slope is **22.62 seconds/page**. These are descriptive associations; the data do not establish that page count caused the latency.

| Pages | Circulars | Median first completion (s) | Mean (s) |
|---:|---:|---:|---:|
| 1 | 19 | 34.08 | 44.01 |
| 2 | 16 | 67.94 | 71.53 |
| 3 | 15 | 85.25 | 88.86 |

### Document-type comparison

| Filename class | n | Median first completion (s) | Mean (s) | Median upload-to-identification (s) |
|---|---:|---:|---:|---:|
| printed | 28 | 62.44 | 62.54 | 49.84 |
| mixed | 18 | 76.98 | 73.05 | 55.04 |
| handwritten | 4 | 59.42 | 61.87 | 48.01 |

Interpret type comparisons cautiously: handwritten cases have only four examples, and document class is based on the test filename label rather than independent visual adjudication.

### Match-score summary

Scores are present for 200 candidates. Median score: all **0.990**, auto-verified **0.990** (n=163), manually confirmed **0.99** (n=10), and records marked rejected **0.44** (n=27). The rejected group includes both known incorrect identifications and valid candidates excluded from dispatch, so its score summary is not an error-only distribution.

## Audit and data quality

- No count discrepancies found across status, match, and email record counts.

- `first_upload_to_email_complete_seconds` uses the first route attempt's end-to-end completion field (or the explicit first-completion field). It is the preferred measure for first-pass latency and avoids including time spent waiting before a user-triggered reroute.
- `latest_upload_to_email_complete_seconds` records the latest end-to-end completion. It may include elapsed time across manual waiting and reruns; do not present it as processing latency without explaining that.
- Historical run outcomes include failures that may have been recovered later. The current recipient-level email-record status is the latest persisted state. Do not equate repeated runs with independent send failures or use `retry_count` as a clean retry total without validating its semantics.
- Follow-up adjudication labels 5 rejected records as incorrect system identifications and 22 as valid candidates excluded from dispatch. These labels are aggregate only; the circular folders do not map them to specific recipient rows. Complete independent ground truth for every candidate, OCR transcription, and To/Copy To section is unavailable, so do not claim overall OCR accuracy, precision, recall, or F1 from these data alone.
- For stronger IEEE accuracy results, annotate the ground-truth recipient names and To/Copy To sections for every circular, plus a corrected transcription for OCR evaluation. Then report recipient precision/recall/F1, exact recipient-set match, canonical identity resolution accuracy, and OCR character/word error rates, split by document class and page count. Keep the scoring threshold fixed or tune it on a separate validation set, not this evaluation set.
- The sample has only four handwritten cases. Add more handwritten and mixed-layout documents and repeat each case under controlled conditions before claiming robust class-specific performance. Separate processing latency from manual review/wait and provider/network latency in the measurement protocol.
- Email addresses and faculty names are intentionally excluded from the recipient CSV. The recipient index is local to each circular; use circular ID plus index to inspect the source match row if needed.

## Suggested IEEE Results wording (descriptive; adapt to the paper's protocol)

The evaluation comprised 50 circulars (28 printed, 18 mixed, and 4 handwritten) spanning 96 pages. The median first-pass upload-to-email completion time was 65.22 s (mean 66.27 s; P95 105.12 s), while median upload-to-recipient-identification time was 51.12 s. Across 200 recipient candidates, 163 were auto-verified and 10 manually confirmed. Follow-up review classified 5 rejected records as incorrect system identifications and 22 as valid candidates manually excluded from dispatch; none remained pending. All 173 current accepted-recipient email records are marked SENT in the stored records. Page count had a Pearson correlation of 0.763 with first-pass completion time; this is an observed association in a 50-document sample, not evidence of a causal effect. The aggregate review labels do not provide complete independent ground truth, so overall identity and extraction accuracy are not inferred.

## Figure files

- `pages_vs_first_completion.svg`: each point is one circular; fitted line and correlations are descriptive.
- `completion_by_document_type.svg`: box summaries and points for first-pass completion, grouped by filename label.
- `pipeline_latency_by_type.svg`: medians for identification and first email completion.
- `recipient_resolution_outcomes.svg`: recipient decisions, aggregate review labels, and current delivery counts.

## Output files

- `circular_level_metrics.csv`: one row per circular with timing, page, recipient, and delivery fields.
- `recipient_level_metrics.csv`: one anonymized row per extracted match candidate.
- `aggregate_review_annotations.csv`: user-provided aggregate split of rejected records; no individual records are assigned to either class.
- `analyze_circulars.py`: reruns this extraction and plotting workflow from the project root.
