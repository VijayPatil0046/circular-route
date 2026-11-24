import re
import unicodedata
from typing import List, Tuple, Optional

TITLE_PATTERNS = [
    r'\bdr\b\.?',
    r'\bprof\b\.?',
    r'\bprofessor\b',
    r'\bmr\b\.?',
    r'\bmrs\b\.?',
    r'\bms\b\.?',
    r'\bh\.?o\.?d\b\.?',
    r'\bhead\s+of\s+department\b',
    r'\bdean\b',
    r'\bprincipal\b',
    r'\bregistrar\b'
]

def clean_and_normalize_text(text: str) -> str:
    """Standardizes text, removing extra whitespaces, weird unicode, etc."""
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    # Replace tabs/multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace multiple linebreaks with single
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def normalize_name(name: str) -> str:
    """
    Normalizes a faculty name for comparison:
    - Lowercase
    - Strip common titles (Dr., Prof., etc.)
    - Strip trailing/leading punctuation
    - Normalize single-letter initials (e.g. 's.' -> 's')
    """
    if not name:
        return ""
    
    clean = name.lower()
    for pattern in TITLE_PATTERNS:
        clean = re.sub(pattern, ' ', clean, flags=re.IGNORECASE)
    
    # Remove punctuation except letters and spaces
    clean = re.sub(r'[^a-z\s]', ' ', clean)
    tokens = [t.strip() for t in clean.split() if t.strip()]
    return " ".join(tokens)

def compute_name_token_similarity(name1: str, name2: str) -> float:
    """
    Computes a jaccard & token containment similarity score between two normalized names.
    Handles initials like 's' matching 'seema' or 'r' matching 'rajesh'.
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if not norm1 or not norm2:
        return 0.0
    
    if norm1 == norm2:
        return 1.0
        
    tokens1 = norm1.split()
    tokens2 = norm2.split()
    
    # Exact set match
    set1 = set(tokens1)
    set2 = set(tokens2)
    if set1 == set2:
        return 0.98
        
    # Jaccard
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Check initial matches (e.g., ['r', 'kumar'] vs ['rajesh', 'kumar'])
    initial_matches = 0
    for t1 in tokens1:
        for t2 in tokens2:
            if t1 == t2:
                initial_matches += 1
                break
            elif (len(t1) == 1 and t2.startswith(t1)) or (len(t2) == 1 and t1.startswith(t2)):
                initial_matches += 0.8
                break
                
    max_tokens = max(len(tokens1), len(tokens2))
    initial_score = (initial_matches / max_tokens) if max_tokens > 0 else 0.0
    
    # Character edit distance / SequenceMatcher ratio for handling OCR typos (e.g. Susesh Kumax -> Suresh Kumar)
    import difflib
    seq_ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    
    return max(jaccard, initial_score, seq_ratio)

def extract_recipient_sections(text: str) -> dict:
    """
    Extracts 'To:' and 'Copy To:' (or 'C.C.:') sections specifically.
    Returns:
    {
        "to_section": str,
        "copy_to_section": str,
        "raw_to_lines": list[str],
        "raw_copy_to_lines": list[str],
        "has_recipient_section": bool
    }
    """
    lines = text.splitlines()
    to_lines = []
    copy_to_lines = []
    
    current_section = None
    
    # Regex markers
    to_pattern = re.compile(r'^\s*(?:to\s*[:\-]|addressed\s+to\s*[:\-])', re.IGNORECASE)
    copy_to_pattern = re.compile(
        r'^\s*(?:copy\s+to|c\.?c\.?)\s*(?:[:\-.,]\s*|$)',
        re.IGNORECASE
    )
    end_pattern = re.compile(r'^\s*(?:subject|sub\s*[:\-]|ref\s*[:\-]|dated|date\s*[:\-]|from\s*[:\-])', re.IGNORECASE)
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_section:
                # Blank lines might signal section end if followed by paragraphs
                pass
            continue

        if re.match(r"^---\s*PAGE\s+\d+\s+OF\s+\d+\s*---$", stripped, re.IGNORECASE):
            continue
        if stripped.lower().startswith("[handwritten copy to additions]"):
            current_section = "copy_to"
            continue
        if stripped.lower().startswith("[handwritten to additions]"):
            current_section = "to"
            continue
        if stripped.startswith("[Extracted Annotations"):
            current_section = None
            continue

        if current_section == "copy_to" and re.match(
            r"^(?:rit\s+circulars\b|circular\s+\d+\s+of\s+\d+\b|page\s+\d+\b)",
            stripped,
            re.IGNORECASE,
        ):
            current_section = None
            continue
            
        if to_pattern.match(stripped):
            current_section = "to"
            # Get rest of line after 'To:'
            rest = to_pattern.sub('', stripped).strip()
            if rest:
                to_lines.append(rest)
            continue
            
        if copy_to_pattern.match(stripped):
            current_section = "copy_to"
            rest = copy_to_pattern.sub('', stripped).strip()
            if rest:
                copy_to_lines.append(rest)
            continue
            
        if end_pattern.match(stripped) and current_section == "to":
            # Switched to subject or body
            current_section = None
            continue
            
        if current_section == "to":
            # Stop if looks like body text or copy to
            if copy_to_pattern.match(stripped):
                current_section = "copy_to"
                continue
            to_lines.append(stripped)
            
        elif current_section == "copy_to":
            # Stop if signature or end
            if stripped.lower().startswith(("s/d", "signature", "sd/-", "registrar", "principal", "thanking you")):
                current_section = None
                continue
            copy_to_lines.append(stripped)
            
    # If standard line parser didn't catch, use block regex search
    if not to_lines and not copy_to_lines:
        to_match = re.search(r'(?:^|\n)\s*To\s*[:\-]\s*(.*?)(?=\n\s*(?:Copy\s+To|C\.?C\.?|Subject|Sub|Ref|Dated|From|\n\n\n)|$)', text, re.IGNORECASE | re.DOTALL)
        if to_match:
            to_block = to_match.group(1).strip()
            to_lines = [l.strip() for l in to_block.splitlines() if l.strip()]
            
        copy_match = re.search(r'(?:^|\n)\s*(?:Copy\s+To|C\.?C\.?)\s*[:\-.,]\s*(.*?)(?=\n\s*(?:Subject|Sub|Ref|Dated|From|Sign|\n\n\n)|$)', text, re.IGNORECASE | re.DOTALL)
        if copy_match:
            copy_block = copy_match.group(1).strip()
            copy_lines = [l.strip() for l in copy_block.splitlines() if l.strip()]

    to_section = "\n".join(to_lines)
    copy_to_section = "\n".join(copy_to_lines)
    has_recipient_section = bool(to_lines or copy_to_lines)
    
    return {
        "to_section": to_section,
        "copy_to_section": copy_to_section,
        "raw_to_lines": to_lines,
        "raw_copy_to_lines": copy_to_lines,
        "has_recipient_section": has_recipient_section
    }
