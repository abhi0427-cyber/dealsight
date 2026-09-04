"""Append-only ledger — out/ledger.jsonl.

Every decision: {deal_id, bucket, codes, evidence, actor, ts}.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


LEDGER_PATH = Path("out/ledger.jsonl")


def append(deal_id: str, bucket: str, findings: list, actor: str = "engine",
           extra: dict | None = None) -> None:
    """Append a decision to the ledger."""
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "deal_id": deal_id,
        "bucket": bucket,
        "codes": [f[0] for f in findings] if findings else [],
        "evidence": {f[0]: f[2] for f in findings} if findings else {},
        "actor": actor,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        entry.update(extra)
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_all() -> list[dict]:
    """Read all ledger entries."""
    if not LEDGER_PATH.exists():
        return []
    entries = []
    with open(LEDGER_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
