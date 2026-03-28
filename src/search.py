"""Fuzzy search engine for clinical codes and descriptions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .models import ClinicalCode, CodeSystem


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    code: ClinicalCode
    score: float  # 0.0 to 1.0
    match_type: str  # "exact_code", "prefix_code", "text_match", "fuzzy"


class FuzzySearchEngine:
    """Search clinical codes by code or description with fuzzy matching.

    Supports exact code lookup, prefix matching, keyword search, and
    trigram-based fuzzy matching for typo tolerance.

    Example:
        >>> engine = FuzzySearchEngine()
        >>> engine.add_code(ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes mellitus"))
        >>> results = engine.search("diabetes")
        >>> results[0].code.display
        'Diabetes mellitus'
    """

    def __init__(self) -> None:
        self._codes: list[ClinicalCode] = []
        self._code_index: dict[str, list[int]] = {}  # code_value → indices
        self._trigrams: dict[str, set[int]] = {}  # trigram → indices

    def add_code(self, code: ClinicalCode) -> None:
        """Add a clinical code to the search index."""
        idx = len(self._codes)
        self._codes.append(code)

        # Index by code value
        key = code.code.upper()
        self._code_index.setdefault(key, []).append(idx)

        # Index trigrams from display text
        text = code.display.lower()
        for trigram in self._extract_trigrams(text):
            self._trigrams.setdefault(trigram, set()).add(idx)

    def add_codes(self, codes: list[ClinicalCode]) -> None:
        """Add multiple codes to the search index."""
        for code in codes:
            self.add_code(code)

    def search(
        self,
        query: str,
        system: Optional[CodeSystem] = None,
        limit: int = 10,
        min_score: float = 0.2,
    ) -> list[SearchResult]:
        """Search for clinical codes matching the query.

        Args:
            query: Search term (code or description text).
            system: Optional filter to a specific coding system.
            limit: Maximum number of results to return.
            min_score: Minimum relevance score threshold.

        Returns:
            List of SearchResult sorted by score descending.
        """
        if not query.strip():
            return []

        results: dict[int, SearchResult] = {}
        query_upper = query.strip().upper()
        query_lower = query.strip().lower()

        # 1. Exact code match (highest priority)
        if query_upper in self._code_index:
            for idx in self._code_index[query_upper]:
                code = self._codes[idx]
                if system and code.system != system:
                    continue
                results[idx] = SearchResult(code=code, score=1.0, match_type="exact_code")

        # 2. Prefix code match
        for code_val, indices in self._code_index.items():
            if code_val.startswith(query_upper) and code_val != query_upper:
                for idx in indices:
                    if idx in results:
                        continue
                    code = self._codes[idx]
                    if system and code.system != system:
                        continue
                    score = len(query) / len(code_val)
                    results[idx] = SearchResult(
                        code=code, score=min(0.95, score), match_type="prefix_code"
                    )

        # 3. Keyword match on display text
        keywords = re.split(r"\s+", query_lower)
        for idx, code in enumerate(self._codes):
            if idx in results:
                continue
            if system and code.system != system:
                continue
            display_lower = code.display.lower()
            matched_keywords = sum(1 for kw in keywords if kw in display_lower)
            if matched_keywords > 0:
                score = matched_keywords / len(keywords) * 0.85
                # Boost if all keywords match
                if matched_keywords == len(keywords):
                    score = 0.90
                results[idx] = SearchResult(
                    code=code, score=score, match_type="text_match"
                )

        # 4. Trigram fuzzy match (fallback)
        query_trigrams = self._extract_trigrams(query_lower)
        if query_trigrams:
            candidate_scores: dict[int, float] = {}
            for trigram in query_trigrams:
                if trigram in self._trigrams:
                    for idx in self._trigrams[trigram]:
                        if idx in results:
                            continue
                        if system and self._codes[idx].system != system:
                            continue
                        candidate_scores[idx] = candidate_scores.get(idx, 0) + 1

            for idx, match_count in candidate_scores.items():
                code = self._codes[idx]
                target_trigrams = self._extract_trigrams(code.display.lower())
                if not target_trigrams:
                    continue
                # Jaccard similarity on trigrams
                overlap = match_count
                union = len(query_trigrams) + len(target_trigrams) - overlap
                score = (overlap / union) * 0.75 if union > 0 else 0
                if score >= min_score:
                    results[idx] = SearchResult(
                        code=code, score=score, match_type="fuzzy"
                    )

        # Sort by score descending, then by display name
        sorted_results = sorted(
            results.values(),
            key=lambda r: (-r.score, r.code.display),
        )

        return sorted_results[:limit]

    def lookup(self, code_value: str, system: Optional[CodeSystem] = None) -> Optional[ClinicalCode]:
        """Look up a specific code by its exact code value.

        Args:
            code_value: The code to look up (e.g., '73211009', 'J45').
            system: Optional coding system filter.

        Returns:
            The matching ClinicalCode, or None if not found.
        """
        key = code_value.strip().upper()
        indices = self._code_index.get(key, [])
        for idx in indices:
            code = self._codes[idx]
            if system is None or code.system == system:
                return code
        return None

    @property
    def size(self) -> int:
        """Number of codes in the index."""
        return len(self._codes)

    @staticmethod
    def _extract_trigrams(text: str) -> set[str]:
        """Extract character trigrams from text for fuzzy matching."""
        if len(text) < 3:
            return {text} if text else set()
        return {text[i:i + 3] for i in range(len(text) - 2)}
