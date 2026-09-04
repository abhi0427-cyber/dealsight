"""Base parser interface."""

from typing import TypedDict


class RampYear(TypedDict, total=False):
    year: int
    amount: float


class ParseResult(TypedDict, total=False):
    type: str          # "coterm" | "ramp" | "none"
    sub_id: str | None
    coterm_end: str | None
    prorate: bool | None
    ramp: list[RampYear]


class BaseParser:
    def __init__(self, config: dict):
        self.config = config

    def parse(self, text: str, deal) -> ParseResult:
        raise NotImplementedError
