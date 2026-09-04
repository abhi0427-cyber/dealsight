"""Special-terms parser — RegexParser (default), LLMParser if API key set."""

import os
from .base import BaseParser, ParseResult
from .regex_parser import RegexParser
from .llm_parser import LLMParser


def get_parser(config: dict) -> BaseParser:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return LLMParser(config)
    return RegexParser(config)


def parse_special_terms(text: str, deal, config: dict) -> ParseResult:
    parser = get_parser(config)
    return parser.parse(text, deal)
