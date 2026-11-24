import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ..core.config import settings
from ..models.schemas import FacultyMember, FacultyMatch
from ..utils.text_normalizer import (
    normalize_name,
    extract_recipient_sections,
)
from .vector_store import vector_store

logger = logging.getLogger(__name__)

EXCLUDED_ROLES = {
    "principal", "vice principal", "director", "dean", "dean academic", "dean academics",
    "registrar", "office of the registrar", "controller of examinations", "coe",
    "head of department", "hod", "head of the department", "accounts section",
    "library", "librarian", "sports department", "administrative officer", "ao",
    "notice board", "all faculty", "all staff", "examination section", "establishment section",
    "chief warden", "placement officer", "estate officer", "file", "file copy", "office copy",
    "all deputy chief superintendents", "exam control room", "cse", "ise", "ece", "eee"
}

class FacultyService:
    def __init__(self, faculty_file: Path = settings.FACULTY_FILE):
        self.faculty_file = faculty_file
        self.faculties: List[FacultyMember] = []
        self.faculty_by_id: Dict[str, FacultyMember] = {}
        self._load_faculty_directory()

    def _load_faculty_directory(self) -> None:
        if not self.faculty_file.exists():
            logger.warning(f"Faculty file {self.faculty_file} does not exist.")
            return
            
        try:
            with open(self.faculty_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                members = data.get("faculties", [])
                self.faculties = [FacultyMember(**m) for m in members]
                self.faculty_by_id = {m.id: m for m in self.faculties}
                logger.info(f"Loaded {len(self.faculties)} faculty members from directory.")
        except Exception as e:
            logger.error(f"Error loading faculty directory: {e}")

    def get_all_faculties(self) -> List[FacultyMember]:
        if not self.faculties:
            self._load_faculty_directory()
        return self.faculties

    def get_faculty_by_id(self, faculty_id: str) -> Optional[FacultyMember]:
        if not self.faculty_by_id:
            self._load_faculty_directory()
        return self.faculty_by_id.get(faculty_id)

    def is_institutional_role_only(self, text: str) -> bool:
        cleaned = normalize_name(text)
        if cleaned in EXCLUDED_ROLES:
            return True
        if cleaned.endswith((" engineering", " science", " department", " dept")):
            return True
        for role in EXCLUDED_ROLES:
            if cleaned == role or cleaned.startswith(f"{role} ") or cleaned.endswith(f" {role}"):
                words = cleaned.split()
                role_words = role.split()
                if len(words) <= len(role_words) + 1:
                    return True
        return False

    def extract_candidates_from_text(self, document_text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        sections = extract_recipient_sections(document_text)
        candidates = []
        
        for line in sections["raw_to_lines"]:
            items = self._split_line_items(line)
            for item in items:
                if item and not self.is_institutional_role_only(item):
                    candidates.append({
                        "raw_reference": item,
                        "section": "To",
                        "context": line
                    })
                    
        for line in sections["raw_copy_to_lines"]:
            items = self._split_line_items(line)
            for item in items:
                if item and not self.is_institutional_role_only(item):
                    candidates.append({
                        "raw_reference": item,
                        "section": "Copy To",
                        "context": line
                    })

        return candidates, sections

    def _split_line_items(self, line: str) -> List[str]:
        # Ignore lines that are pure dates or deadlines
        if re.search(r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b', line, re.IGNORECASE):
            # Check if this line is a deadline sentence
            if any(w in line.lower() for w in ["submit", "before", "deadline", "by", "feedback", "dated", "date:"]):
                return []

        # Remove numbering like '1.', '1)', 'i.', '(a)', bullets
        cleaned = re.sub(r'^\s*(?:\d+[\.\)]|[a-zA-Z][\.\)]|\-|\*|\•)\s*', '', line)
        cleaned = re.sub(r'\s*\[(?:handwritten|ocr)\]\s*$', '', cleaned, flags=re.IGNORECASE)

        # Remove the affiliation after a recipient name (e.g. ", Computer Science & Engineering").
        cleaned = re.sub(
            r',\s*(?:[A-Za-z&]+(?:[\s&]+[A-Za-z&]+){0,5}\s+(?:Engineering|Science)|CSE|ISE|ECE|EEE|'
            r'Department\s+of\s+[A-Za-z\s&]+|[A-Za-z\s&]+\s+Dept\.?|'
            r'Assistant\s+Professor|Associate\s+Professor|Professor|Dean[a-z\s]*|HOD[a-z\s]*)\s*$',
            '',
            cleaned,
            flags=re.IGNORECASE,
        )

        # Split remaining by semicolon, 'and', '&'
        parts = re.split(r'[;]|\band\b|&', cleaned)
        results = []
        for p in parts:
            p_strip = p.strip()
            # If comma still separates different names (e.g. "Dr. Seema, Prof. Rajesh")
            subparts = p_strip.split(',')
            for sp in subparts:
                sp_clean = sp.strip()
                sp_clean = re.sub(r'^[\s\-\.\:]+|[\s\-\.\:]+$', '', sp_clean)
                # Filter out pure department names or single letters
                if len(sp_clean) > 2 and not self.is_institutional_role_only(sp_clean):
                    if not re.match(r'^(?:dept|department|office|cell|division)\b', sp_clean, re.IGNORECASE):
                        results.append(sp_clean)
        return results

    def resolve_faculty(self, document_text: str) -> Tuple[List[FacultyMatch], bool, Optional[str]]:
        """
        Two-stage LLM processing pipeline:
        Stage 1 (LLM Call 1):
            Input: Full circular text from OCR.
            Output: Extracted 'To' and 'Copy To' sections and raw candidate names.
        Embedding Retrieval:
            Input: Extracted recipient names from Stage 1.
            Retrieval: Qdrant vector search using all-MiniLM-L6-v2.
            Output: Focused faculty context (top directory matches with IDs, emails, departments, aliases).
        Stage 2 (LLM Call 2):
            Input: Extracted recipient names + retrieved embedding context.
            Output: Standard faculty names, faculty IDs, emails, departments, confidence scores.
        """
        if not document_text or not document_text.strip():
            logger.warning("Empty document text provided for faculty resolution.")
            return [], True, "No document text available."

        llm_available = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key")
        
        extracted_candidates: List[Dict[str, Any]] = []
        sections_info: Dict[str, Any] = {}
        llm_summary: Optional[str] = None

        # ---------------------------------------------------------
        # STAGE 1: Extract recipient sections and candidate names
        # ---------------------------------------------------------
        extracted_candidates, sections_info = self.extract_candidates_from_text(document_text)

        # If the document has explicit recipient sections, trust their structured
        # rows over whole-document LLM guesses. Use the LLM only for nonstandard
        # layouts where local parsing found no recipient section at all.
        if not extracted_candidates and not sections_info.get("has_recipient_section") and llm_available:
            try:
                logger.info("Executing LLM Call 1 fallback: Extracting nonstandard recipient sections...")
                extracted_candidates, sections_info, llm_summary = self._call_groq_stage1_extract_recipients(document_text)
            except Exception as e:
                logger.error(f"Error in LLM Call 1 ({e}). Falling back to local regex extraction.")
                extracted_candidates = []

        if not extracted_candidates:
            # Keep the local parser as the final fallback when the LLM is unavailable.
            extracted_candidates, sections_info = self.extract_candidates_from_text(document_text)

        if not extracted_candidates:
            logger.warning("No explicit To / Copy To faculty candidates found in circular text.")
            return [], True, llm_summary

        # ---------------------------------------------------------
        # INTERMEDIATE STAGE: Retrieve Context from Qdrant
        # ---------------------------------------------------------
        logger.info(f"Retrieving embedding context for {len(extracted_candidates)} recipient candidates...")
        candidates_with_embedding_context = []
        for cand in extracted_candidates:
            raw_ref = cand.get("raw_reference") or cand.get("extracted_name", "")
            section = cand.get("section", "To")
            
            hits = vector_store.search(raw_ref)
            top_candidates = []
            for hit in hits:
                payload = hit["payload"]
                try:
                    faculty = FacultyMember(
                        id=str(payload.get("id", hit["id"])),
                        standard_name=payload.get("standard_name") or payload.get("name") or "",
                        department=payload.get("department") or "",
                        designation=payload.get("designation") or "",
                        aliases=payload.get("aliases") or [],
                        email=payload.get("email") or "",
                    )
                except Exception:
                    logger.warning("Skipping invalid faculty payload from Qdrant point %s", hit["id"])
                    continue
                top_candidates.append((faculty, float(hit["score"])))
            context_entries = [
                {
                    "faculty_id": f.id,
                    "standard_name": f.standard_name,
                    "department": f.department,
                    "email": f.email,
                    "aliases": f.aliases,
                    "embedding_similarity_score": round(sc, 4)
                }
                for f, sc in top_candidates
            ]
            
            candidates_with_embedding_context.append({
                "extracted_name": raw_ref,
                "section": section,
                "retrieved_faculty_context": context_entries,
                "top_candidates": top_candidates,
                "retrieved_faculty_by_id": {faculty.id: faculty for faculty, _ in top_candidates},
            })

        # ---------------------------------------------------------
        # STAGE 2: Resolve standard names and emails using LLM Call 2
        # ---------------------------------------------------------
        matches: List[FacultyMatch] = []
        stage2_success = False

        if llm_available:
            try:
                logger.info("Executing LLM Call 2: Resolving standard faculty names and emails using embedding context...")
                matches = self._call_groq_stage2_resolve_faculty(candidates_with_embedding_context)
                stage2_success = True
            except Exception as e:
                logger.error(f"Error in LLM Call 2 ({e}). Falling back to local resolution.")

        if stage2_success:
            matches = self._apply_top_candidate_fallback(matches, candidates_with_embedding_context)
        else:
            # Local fallback for Stage 2
            pre_matches = [
                {
                    "raw_reference": item["extracted_name"],
                    "section": item["section"],
                    "top_candidates": item["top_candidates"],
                    "context": f"Section: {item['section']}"
                }
                for item in candidates_with_embedding_context
            ]
            matches = self._local_resolution(pre_matches)

        # Deduplicate matches by faculty_id
        deduped: List[FacultyMatch] = []
        seen_ids = set()
        for m in matches:
            if m.faculty_id == "UNKNOWN":
                deduped.append(m)
            elif m.faculty_id not in seen_ids:
                seen_ids.add(m.faculty_id)
                deduped.append(m)

        has_recipient_sec = sections_info.get("has_recipient_section", True) if sections_info else True
        requires_review = (
            not has_recipient_sec
            or any(m.verification_status == "AMBIGUOUS" for m in deduped)
            or len(deduped) == 0
        )

        return deduped, requires_review, llm_summary

    def _apply_top_candidate_fallback(
        self,
        matches: List[FacultyMatch],
        candidates_with_context: List[Dict[str, Any]]
    ) -> List[FacultyMatch]:
        """Use the highest-scoring directory candidate when it reaches 50%."""
        match_by_reference = {normalize_name(m.original_reference): i for i, m in enumerate(matches)}

        for item in candidates_with_context:
            raw_reference = item["extracted_name"]
            key = normalize_name(raw_reference)
            match_index = match_by_reference.get(key)
            current_match = matches[match_index] if match_index is not None else None
            if current_match and current_match.faculty_id != "UNKNOWN":
                continue

            top_candidates = item.get("top_candidates", [])
            if not top_candidates:
                continue

            best_faculty, best_score = top_candidates[0]
            if best_score < 0.50:
                below_cutoff_explanation = (
                    f"Similarity {best_score:.1%} is below the 50% automatic-match cutoff. "
                    "Select and confirm a faculty member manually."
                )
                if current_match:
                    current_match.standard_name = best_faculty.standard_name
                    current_match.similarity_score = round(best_score, 4)
                    current_match.matching_explanation = below_cutoff_explanation
                else:
                    matches.append(FacultyMatch(
                        original_reference=raw_reference,
                        standard_name=best_faculty.standard_name,
                        faculty_id="UNKNOWN",
                        department="",
                        email="",
                        similarity_score=round(best_score, 4),
                        matching_explanation=below_cutoff_explanation,
                        supporting_evidence=f"Extracted from {item['section']} section.",
                        relevance_explanation="Requires manual faculty selection.",
                        section_found=item["section"],
                        verification_status="AMBIGUOUS",
                        is_verified=False
                    ))
                    match_by_reference[key] = len(matches) - 1
                continue

            fallback_match = FacultyMatch(
                original_reference=raw_reference,
                standard_name=best_faculty.standard_name,
                faculty_id=best_faculty.id,
                department=best_faculty.department,
                email=best_faculty.email,
                similarity_score=round(best_score, 4),
                matching_explanation=(
                    f"Selected the highest-scoring directory candidate, {best_faculty.standard_name}, "
                    f"with similarity {best_score:.1%} (50% minimum)."
                ),
                supporting_evidence=f"Extracted from {item['section']} section.",
                relevance_explanation=f"Recipient candidate found in {item['section']} section.",
                section_found=item["section"],
                verification_status="AUTO_VERIFIED",
                is_verified=True
            )

            if match_index is None:
                matches.append(fallback_match)
                match_by_reference[key] = len(matches) - 1
            else:
                matches[match_index] = fallback_match

        return matches

    def _call_groq_stage1_extract_recipients(
        self,
        document_text: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Optional[str]]:
        """
        LLM CALL 1:
        Receives the full circular in string format from PaddleOCR & TrOCR.
        Responds back with:
        - The 'To:' and/or 'Copy To:' sections
        - Extracted individual recipient candidate names
        """
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        prompt = f"""You are Stage 1 of an institutional circular processing system.
Read the full circular text and extract the recipient sections and their names.

INSTRUCTIONS:
1. Identify the 'To:' and 'Copy To:' / 'Circulate To:' recipient sections located in the circular.
2. Extract all individual person/faculty recipient names verbatim from these sections.
   - Separate multiple names in a single line (e.g. if comma-separated or numbered).
   - Ignore purely administrative generic offices (like 'Principal', 'Registrar', 'Notice Board', 'Accounts Section', 'Office Copy') unless an individual person's name is attached.
   - Do NOT extract people mentioned only in the body text as guest speakers or event coordinators unless they are designated in 'To' or 'Copy To'.
3. Preserve each name as written and do not add people from the circular body.

FULL CIRCULAR TEXT:
{document_text[:3500]}

Respond ONLY in valid JSON matching this schema:
{{
  "to_section": "<verbatim text of To section, or empty string>",
  "copy_to_section": "<verbatim text of Copy To section, or empty string>",
  "recipient_candidates": [
    {{
      "extracted_name": "<exact name as appeared in document>",
      "section": "<To or Copy To>"
    }}
  ]
}}"""

        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise institutional document parser. You output valid JSON strictly."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        raw_candidates = data.get("recipient_candidates", [])
        candidates = []
        for rc in raw_candidates:
            name = rc.get("extracted_name", "").strip()
            # Clean leading/trailing punctuation or numbers
            name = re.sub(r'^\s*(?:\d+[\.\)]|[a-zA-Z][\.\)]|\-|\*|\•)\s*', '', name)
            if name and not self.is_institutional_role_only(name):
                candidates.append({
                    "raw_reference": name,
                    "extracted_name": name,
                    "section": rc.get("section", "To")
                })

        sections = {
            "to_section": data.get("to_section", ""),
            "copy_to_section": data.get("copy_to_section", ""),
            "has_recipient_section": bool(candidates or data.get("to_section") or data.get("copy_to_section"))
        }
        return candidates, sections, None

    def _call_groq_stage2_resolve_faculty(
        self,
        candidates_with_context: List[Dict[str, Any]]
    ) -> List[FacultyMatch]:
        """
        LLM CALL 2:
        Takes the recipient candidates from LLM Call 1 along with the retrieved context
        from the embeddings (top directory matches with standard names, IDs, departments, emails).
        Resolves each name against the embedding context and returns standard names and emails.
        """
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        # Build clean context payload for LLM 2
        payload_for_llm = []
        for item in candidates_with_context:
            payload_for_llm.append({
                "extracted_recipient": item["extracted_name"],
                "section": item["section"],
                "retrieved_candidates_from_embeddings": item["retrieved_faculty_context"]
            })

        prompt = f"""You are Stage 2 of the CircularRoute faculty resolution engine.
Your task is to resolve extracted recipient names from an institutional circular against candidate faculty profiles retrieved via embedding similarity.

INSTRUCTIONS:
1. For each extracted recipient, evaluate the candidates retrieved from the faculty directory.
2. Handle OCR typos, noise, and OCR misspellings (e.g. 'Susesh Kumax P' -> 'Suresh Kumar P', 'Kisan S' -> 'Kiran S', 'Dr. Seema S' -> 'Dr. Seema S.').
3. Handle initials, titles (Dr., Prof.), and abbreviations.
4. If a strong match exists in the retrieved directory, assign:
   - standard_name: exact standard name from directory
   - faculty_id: exact faculty ID (e.g., 'FAC001')
   - department: exact department
   - email: official email from directory
   - confidence: confidence between 0.0 and 1.0 (>= 0.85 for clear matches)
   - is_ambiguous: false
5. If NO clear match exists in the retrieved candidates, or the name is unknown:
   - standard_name: 'Unresolved / Unknown Candidate'
   - faculty_id: 'UNKNOWN'
   - department: ''
   - email: ''
   - confidence: 0.0
   - is_ambiguous: true

RECIPIENT CANDIDATES AND RETRIEVED EMBEDDING CONTEXT:
{json.dumps(payload_for_llm, indent=2)}

Respond ONLY in valid JSON matching this schema:
{{
  "resolved_faculty": [
    {{
      "original_reference": "<exact extracted name>",
      "section_found": "<To or Copy To>",
      "standard_name": "<matching standard_name from directory or 'Unresolved / Unknown Candidate'>",
      "faculty_id": "<matching faculty ID or 'UNKNOWN'>",
      "department": "<department from directory or empty>",
      "email": "<email from directory or empty>",
      "confidence": <float between 0.0 and 1.0>,
      "matching_explanation": "<concise explanation of match or typo resolution>",
      "is_ambiguous": <boolean>
    }}
  ]
}}"""

        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise institutional entity resolution specialist. You output valid JSON strictly."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        resolved_list = data.get("resolved_faculty", [])

        matches: List[FacultyMatch] = []
        for rf in resolved_list:
            raw_ref = rf.get("original_reference", "")
            f_id = rf.get("faculty_id", "UNKNOWN")
            section = rf.get("section_found", "To")
            is_ambiguous = rf.get("is_ambiguous", False)
            conf = float(rf.get("confidence", 0.0))

            faculty = next((item.get("retrieved_faculty_by_id", {}).get(f_id)
                            for item in candidates_with_context
                            if f_id in item.get("retrieved_faculty_by_id", {})), None)
            if not faculty or f_id == "UNKNOWN":
                matches.append(FacultyMatch(
                    original_reference=raw_ref,
                    standard_name=rf.get("standard_name", "Unresolved / Unknown Candidate"),
                    faculty_id="UNKNOWN",
                    department="",
                    email="",
                    similarity_score=conf,
                    matching_explanation=rf.get("matching_explanation", "Could not verify identity in retrieved Qdrant results."),
                    supporting_evidence=f"Extracted from {section} section.",
                    relevance_explanation="Requires manual confirmation or is an external recipient.",
                    section_found=section,
                    verification_status="AMBIGUOUS",
                    is_verified=False
                ))
            else:
                retrieved = next((entry for item in candidates_with_context
                                  if normalize_name(item["extracted_name"]) == normalize_name(raw_ref)
                                  for entry in item.get("top_candidates", []) if entry[0].id == f_id), None)
                final_score = retrieved[1] if retrieved else conf
                is_ambiguous = final_score < 0.50

                status = "AMBIGUOUS" if is_ambiguous else "AUTO_VERIFIED"
                matches.append(FacultyMatch(
                    original_reference=raw_ref,
                    standard_name=faculty.standard_name,
                    faculty_id=faculty.id,
                    department=faculty.department,
                    email=faculty.email,
                    similarity_score=round(final_score, 4),
                    matching_explanation=rf.get("matching_explanation", f"Matched '{raw_ref}' to '{faculty.standard_name}'"),
                    supporting_evidence=f"Found in {section} section.",
                    relevance_explanation=f"Designated recipient in {section} section.",
                    section_found=section,
                    verification_status=status,
                    is_verified=(status == "AUTO_VERIFIED")
                ))

        return matches

    def _local_resolution(self, pre_matches: List[Dict[str, Any]]) -> List[FacultyMatch]:
        matches = []
        for pm in pre_matches:
            raw_ref = pm["raw_reference"]
            top = pm["top_candidates"]
            section = pm["section"]
            
            if not top:
                matches.append(FacultyMatch(
                    original_reference=raw_ref,
                    standard_name="Unresolved / Unknown Candidate",
                    faculty_id="UNKNOWN",
                    email="",
                    department="",
                    similarity_score=0.0,
                    matching_explanation=f"No matching faculty found in institutional directory for '{raw_ref}'.",
                    supporting_evidence=f"Appeared in '{section}' section.",
                    relevance_explanation="Candidate requires manual identification or is an external recipient.",
                    section_found=section,
                    verification_status="AMBIGUOUS",
                    is_verified=False
                ))
                continue

            best_faculty, best_score = top[0]
            
            is_ambiguous = best_score < 0.50

            verification_status = "AMBIGUOUS" if is_ambiguous else "AUTO_VERIFIED"
            
            matches.append(FacultyMatch(
                original_reference=raw_ref,
                standard_name=best_faculty.standard_name,
                faculty_id=best_faculty.id,
                department=best_faculty.department,
                email=best_faculty.email,
                similarity_score=round(best_score, 4),
                matching_explanation=f"Matched '{raw_ref}' to '{best_faculty.standard_name}' with local confidence {best_score:.2f}.",
                supporting_evidence=f"Found in {section} section context: '{pm.get('context', '')}'",
                relevance_explanation=f"Direct recipient designated in {section} section.",
                section_found=section,
                verification_status=verification_status,
                is_verified=(verification_status == "AUTO_VERIFIED")
            ))
            
        return matches

faculty_service = FacultyService()
