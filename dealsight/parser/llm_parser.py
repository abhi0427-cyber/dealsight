"""LLM-based special-terms parser — only used if ANTHROPIC_API_KEY is set."""

import json
import os
import urllib.request
import urllib.error
from .base import BaseParser, ParseResult


class LLMParser(BaseParser):
    API_URL = "https://api.anthropic.com/v1/messages"

    def parse(self, text: str, deal) -> ParseResult:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"type": "none"}

        model = self.config.get("parser", {}).get("llm_model", "claude-sonnet-4-6")
        temperature = self.config.get("parser", {}).get("llm_temperature", 0)

        prompt = f"""Parse this deal special_terms field into structured JSON.

Text: "{text}"

Deal context:
- deal_id: {deal.get('deal_id', '')}
- contract_value_usd: {deal.get('contract_value_usd', '')}
- term_months: {deal.get('term_months', '')}
- term_start: {deal.get('term_start', '')}

Return ONLY valid JSON with this schema:
{{
  "type": "coterm" | "ramp" | "none",
  "sub_id": "SUB-XXXXX" or null,
  "coterm_end": "YYYY-MM-DD" or null,
  "prorate": true/false or null,
  "ramp": [{{"year": 1, "amount": 12345.00}}, ...] or []
}}

Rules:
- "coterm" if text mentions co-terminating with another subscription
- "ramp" if text describes escalating payments across years
- "none" if the text has no billing-relevant structure
- Extract sub_id if a subscription ID (SUB-XXXXX) is mentioned
- Extract coterm_end date if present
- prorate is true if prorating is mentioned
- For ramps, extract each year and its amount"""

        body = json.dumps({
            "model": model,
            "max_tokens": 512,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        req = urllib.request.Request(
            self.API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        content = data["content"][0]["text"]
        # Extract JSON from response
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"type": "none"}
