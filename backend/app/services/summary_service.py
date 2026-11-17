import logging
import re
from pathlib import Path
from typing import Optional, List

from ..core.config import settings
from ..utils.text_normalizer import compute_name_token_similarity

logger = logging.getLogger(__name__)

COPY_SECTION_HEADER = re.compile(
    r'^\s*(?:copy\s*to|c\.?\s*c\.?|cc|circulate\s*to|distribution\s+list)\b',
    re.IGNORECASE
)

class SummaryService:
    def generate_summary(self, circular_text: str, recipients: Optional[List[str]] = None) -> str:
        """
        Generates a concise 2-3 line institutional circular summary.
        Explains:
        1. What the circular is about
        2. Relevant action/information for faculty
        3. Key dates, deadlines or instructions
        """
        if not circular_text or not circular_text.strip():
            return "No content available in circular for summary generation."

        summary_text = self._prepare_summary_text(circular_text, recipients or [])
        if not summary_text.strip():
            return "No non-recipient circular content was available to summarize."

        if settings.GROQ_API_KEY:
            try:
                return self._call_groq_summary(summary_text)
            except Exception as e:
                logger.error(f"Error calling Groq for summary: {e}. Falling back to extractive summary.")

        return self._fallback_extractive_summary(summary_text)

    def _prepare_summary_text(self, circular_text: str, recipients: List[str]) -> str:
        """Remove the trailing distribution block and recipient-only OCR lines."""
        lines = []
        for line in circular_text.splitlines():
            if COPY_SECTION_HEADER.match(line):
                break
            if recipients and self._is_recipient_list_line(line, recipients):
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def _is_recipient_list_line(self, line: str, recipients: List[str]) -> bool:
        parts = [part.strip(" \t.:;,-") for part in re.split(r"[,;|&]|\band\b", line, flags=re.IGNORECASE)]
        parts = [re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", part).strip() for part in parts]
        parts = [part for part in parts if part]
        if not parts:
            return False

        return all(
            max((compute_name_token_similarity(part, name) for name in recipients), default=0.0) >= 0.80
            for part in parts
        )

    def _call_groq_summary(self, circular_text: str) -> str:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        prompt = f"""You are an institutional circular summarizer.
Write a concise, specific summary of the circular content below.

REQUIREMENTS:
1. The summary MUST be exactly 2 to 3 sentences / lines.
2. State the actual purpose or event, required action, and dates, times, or venue when present.
3. Do not mention, list, or summarize the To, Copy To, CC, or distribution-list sections or any recipient names.
4. Base the summary STRICTLY on the supplied text. Do not infer missing details or describe OCR uncertainty as circular content.
5. If a detail is unclear in the text, omit it rather than guessing.
6. Keep the tone professional and objective.

CIRCULAR TEXT:
{circular_text[:3500]}

Concise Summary:"""

        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You provide exact, factual 2-3 line circular summaries without preamble or pleasantries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=250
        )

        summary = response.choices[0].message.content.strip()
        # Clean up any potential markdown headers or quotes
        summary = re.sub(r'^(?:Summary:\s*|\*\*Summary:\*\*\s*)', '', summary, flags=re.IGNORECASE)
        return summary

    def _fallback_extractive_summary(self, text: str) -> str:
        """
        Extractive heuristic summary if LLM is unavailable:
        Extracts subject, dates, and action lines.
        """
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("--- PAGE")]
        subject_line = ""
        dates = []
        action_lines = []

        date_pattern = re.compile(r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b', re.IGNORECASE)

        for line in lines:
            if re.match(r'^(?:sub|subject)\s*[:\-]', line, re.IGNORECASE):
                subject_line = line
            if date_pattern.search(line):
                dates.append(line)
            if any(k in line.lower() for k in ["requested to", "directed to", "instructed", "required to", "submit", "deadline", "meeting", "attend", "hereby informed"]):
                action_lines.append(line)
            if re.match(r'^(?:venue|location)\s*[:\-]', line, re.IGNORECASE):
                action_lines.append(line)

        summary_parts = []
        if subject_line:
            clean_sub = re.sub(r'^(?:sub|subject)\s*[:\-]\s*', '', subject_line, flags=re.IGNORECASE)
            summary_parts.append(f"Circular regarding {clean_sub}.")
        else:
            # First meaningful sentence
            first_line = lines[0] if lines else "Institutional Circular"
            summary_parts.append(f"Circular issued: {first_line[:120]}.")

        if action_lines:
            summary_parts.append(f"{action_lines[0][:140]}.")
        elif len(lines) > 2:
            summary_parts.append(f"{lines[2][:140]}.")

        if dates and len(summary_parts) < 3:
            summary_parts.append(f"Important timeline mentioned: {dates[0][:120]}.")

        return " ".join(summary_parts)

summary_service = SummaryService()
