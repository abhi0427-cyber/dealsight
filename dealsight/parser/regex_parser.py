"""Regex-based special-terms parser."""

import re
from .base import BaseParser, ParseResult


class RegexParser(BaseParser):
    # Co-term patterns — strict (SUB right after co-term keyword)
    _COTERM_RE = re.compile(
        r"[Cc]o[\-\s]?term(?:inat(?:e|ion))?\s+(?:with\s+)?(SUB-\w+)\s+(?:ending\s+)?(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    )
    _COTERM_SIMPLE_RE = re.compile(
        r"[Cc]o[\-\s]?term(?:inat(?:e|ion))?\s+(?:with\s+)?(SUB-\w+)",
        re.IGNORECASE,
    )
    # Co-term keyword anywhere + SUB-ID anywhere + date anywhere
    _COTERM_KEYWORD_RE = re.compile(
        r"co[\-\s]?term(?:inat(?:e|ion))?|align\s+end\s+date|match\s+(?:the\s+)?end\s+date|terminat(?:e|es|ing)",
        re.IGNORECASE,
    )
    _DATE_ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
    # Natural-language date: "December 31st, 2025" etc.
    _MONTHS = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    _DATE_NATURAL_RE = re.compile(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})",
        re.IGNORECASE,
    )
    _PRORATE_RE = re.compile(r"pro[\-\s]?rat[ei]", re.IGNORECASE)

    # Ramp patterns
    _RAMP_RE = re.compile(r"\bramp\b|escalat", re.IGNORECASE)
    _RAMP_YEAR_RE = re.compile(
        r"[Yy](?:ear|r)?\s*(\d+)\s*[:\-\u2014]?\s*(?:(?:is|billed\s+at|at)\s+)?\$?([\d,]+(?:\.\d{2})?)",
    )

    # Sub-ID anywhere in text
    _SUB_RE = re.compile(r"(SUB-\w+)", re.IGNORECASE)

    def parse(self, text: str, deal) -> ParseResult:
        text = str(text).strip()
        if not text:
            return {"type": "none"}

        # Try co-term — strict pattern first
        coterm_match = self._COTERM_RE.search(text)
        if coterm_match:
            return {
                "type": "coterm",
                "sub_id": coterm_match.group(1),
                "coterm_end": coterm_match.group(2),
                "prorate": bool(self._PRORATE_RE.search(text)),
            }

        # Co-term keyword + SUB-ID nearby
        simple_match = self._COTERM_SIMPLE_RE.search(text)
        if simple_match:
            date_match = self._DATE_ISO_RE.search(text)
            return {
                "type": "coterm",
                "sub_id": simple_match.group(1),
                "coterm_end": date_match.group(1) if date_match else None,
                "prorate": bool(self._PRORATE_RE.search(text)),
            }

        # Loose co-term: keyword anywhere + SUB-ID anywhere + date anywhere
        if self._COTERM_KEYWORD_RE.search(text):
            sub_match = self._SUB_RE.search(text)
            date_str = self._extract_date(text)
            if sub_match:
                return {
                    "type": "coterm",
                    "sub_id": sub_match.group(1),
                    "coterm_end": date_str,
                    "prorate": bool(self._PRORATE_RE.search(text)),
                }

        # Try ramp
        if self._RAMP_RE.search(text):
            years = self._extract_ramp_years(text)
            if years:
                sub_match = self._SUB_RE.search(text)
                return {
                    "type": "ramp",
                    "sub_id": sub_match.group(1) if sub_match else None,
                    "ramp": years,
                }

        # Fallback: multiple "Year N ... $amount" without explicit "ramp" keyword
        years = self._extract_ramp_years(text)
        if len(years) >= 2:
            sub_match = self._SUB_RE.search(text)
            return {
                "type": "ramp",
                "sub_id": sub_match.group(1) if sub_match else None,
                "ramp": years,
            }

        return {"type": "none"}

    def _extract_date(self, text: str) -> str | None:
        """Extract a date from text, trying ISO format first, then natural language."""
        iso = self._DATE_ISO_RE.search(text)
        if iso:
            return iso.group(1)
        nat = self._DATE_NATURAL_RE.search(text)
        if nat:
            month = self._MONTHS[nat.group(1).lower()]
            day = nat.group(2).zfill(2)
            year = nat.group(3)
            return f"{year}-{month}-{day}"
        return None

    def _extract_ramp_years(self, text: str) -> list[dict]:
        years = []
        for m in self._RAMP_YEAR_RE.finditer(text):
            amount_str = m.group(2).replace(",", "")
            years.append({"year": int(m.group(1)), "amount": float(amount_str)})
        years.sort(key=lambda y: y["year"])
        return years
