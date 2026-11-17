import logging
import re
from pathlib import Path
from typing import Optional, List

from ..core.config import settings

logger = logging.getLogger(__name__)

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

        if settings.GROQ_API_KEY:
            try:
                return self._call_groq_summary(circular_text, recipients)
            except Exception as e:
                logger.error(f"Error calling Groq for summary: {e}. Falling back to extractive summary.")

        return self._fallback_extractive_summary(circular_text)

    def _call_groq_summary(self, circular_text: str, recipients: Optional[List[str]] = None) -> str:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        recipient_context = ""
        if recipients:
            recipient_context = f"\nAddressed Recipients: {', '.join(recipients)}"

        prompt = f"""You are an institutional circular summarizer. 
Write a concise 2-3 line summary of the following circular.{recipient_context}

REQUIREMENTS:
1. The summary MUST be exactly 2 to 3 sentences / lines.
2. Clearly explain what the circular is about, key actions/instructions required from faculty, and any specific deadlines or dates.
3. Base your summary STRICTLY on the extracted text below. DO NOT invent dates, names, or responsibilities.
4. Keep the tone professional, objective, and executive.

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
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        subject_line = ""
        dates = []
        action_lines = []

        date_pattern = re.compile(r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b', re.IGNORECASE)

        for line in lines:
            if re.match(r'^(?:sub|subject)\s*[:\-]', line, re.IGNORECASE):
                subject_line = line
            if date_pattern.search(line):
                dates.append(line)
            if any(k in line.lower() for k in ["requested to", "directed to", "submit", "deadline", "meeting", "attend", "hereby informed"]):
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
