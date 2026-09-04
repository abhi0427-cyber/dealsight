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

        prompt = f"""Extract structured billing data from this special_terms note.

Text: "{text}"

Return ONLY valid JSON with this schema:
{{
  "type": "coterm" | "ramp" | "none",
  "sub_id": "SUB-XXXXX" or null,
  "coterm_end": "YYYY-MM-DD" or null,
  "prorate": true | false | null,
  "ramp": [{{"year": 1, "amount": 12345.00}}, ...] or []
}}

CRITICAL — extraction rules:
- Populate a field ONLY when the text explicitly states it. Return null for any field the text does not address. Never infer a value from convention, common practice, or what would be typical.
- "type": "coterm" if the text mentions co-terminating, co-term, or aligning end dates with another subscription. "ramp" if the text describes escalating or staged payments across years. "none" otherwise.
- "sub_id": set only if the text contains a subscription ID matching SUB-XXXXX.
- "coterm_end": set only if the text contains an explicit date.
- "prorate": set to true ONLY if the text explicitly says to prorate, pro-rate, bill partially, or bill through a specific date. Set to false ONLY if the text explicitly says not to prorate or to bill in full. If the text does not mention prorating at all, return null.
- "ramp": extract year/amount pairs only when the text states them."""

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
