"""Rule 8: Email format validation."""

import re
import pandas as pd
from . import register

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+-]+@"           # local part
    r"[a-zA-Z0-9]"                     # domain starts with alnum
    r"(?:[a-zA-Z0-9-]*[a-zA-Z0-9])?"  # rest of first label
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)*"  # additional labels
    r"\.[a-zA-Z]{2,}$"                # TLD
)


@register("email_regex")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["email_regex"]
    email = deal.get("billing_contact_email")
    if pd.isna(email) or str(email).strip() == "":
        return []  # Rule 7 handles missing; this checks format
    email = str(email).strip()
    # Quick structural checks before regex
    if email.count("@") != 1 or ".." in email:
        return [("email_regex", cfg["severity"], {
            "email": email,
            "deal_id": deal["deal_id"],
        })]
    if not _EMAIL_RE.match(email):
        return [("email_regex", cfg["severity"], {
            "email": email,
            "deal_id": deal["deal_id"],
        })]
    return []
