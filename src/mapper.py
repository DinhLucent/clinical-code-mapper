"""Core mapper engine for clinical code translation."""

from __future__ import annotations

import json
import csv
import io
from pathlib import Path
from typing import Optional

from .models import (
    ClinicalCode,
    CodeSystem,
    HierarchyNode,
    MappingDirection,
    MappingResult,
)
from .crosswalk import (
    build_crosswalk_mappings,
    build_cpt_codes,
    build_loinc_codes,
)
from .search import FuzzySearchEngine


class ClinicalCodeMapper:
    """Main mapper engine for translating between clinical coding systems.

    Supports:
    - Direct code lookup
    - Code-to-code mapping across systems (SNOMED↔ICD-10, etc.)
    - Fuzzy text search across all loaded codes
    - Batch mapping operations
    - Custom mapping file loading (CSV, JSON)
    - Hierarchy navigation

    Example:
        >>> mapper = ClinicalCodeMapper()
        >>> results = mapper.map_code("73211009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        >>> results[0].target.code
        'E14'
    """

    def __init__(self, *, load_builtin: bool = True) -> None:
        """Initialize the mapper.

        Args:
            load_builtin: If True, load built-in crosswalk data on init.
        """
        self._mappings: list[MappingResult] = []
        self._mapping_index: dict[str, list[int]] = {}  # source_key → indices
        self._search_engine = FuzzySearchEngine()
        self._hierarchy_roots: dict[CodeSystem, list[HierarchyNode]] = {}

        if load_builtin:
            self._load_builtin()

    def _load_builtin(self) -> None:
        """Load built-in crosswalk data and code catalogs."""
        # Load SNOMED↔ICD-10 mappings
        for mapping in build_crosswalk_mappings():
            self.add_mapping(mapping)

        # Load LOINC and CPT catalogs into search engine
        for code in build_loinc_codes():
            self._search_engine.add_code(code)

        for code in build_cpt_codes():
            self._search_engine.add_code(code)

    def add_mapping(self, mapping: MappingResult) -> None:
        """Add a single mapping to the mapper."""
        idx = len(self._mappings)
        self._mappings.append(mapping)

        key = self._make_key(mapping.source.code, mapping.source.system)
        self._mapping_index.setdefault(key, []).append(idx)

        # Also index source and target codes in search engine
        self._search_engine.add_code(mapping.source)
        self._search_engine.add_code(mapping.target)

    def map_code(
        self,
        code: str,
        source_system: CodeSystem,
        target_system: CodeSystem,
        *,
        min_confidence: float = 0.0,
    ) -> list[MappingResult]:
        """Map a code from one system to another.

        Args:
            code: The source code value.
            source_system: The source coding system.
            target_system: The desired target coding system.
            min_confidence: Minimum confidence threshold (0.0 to 1.0).

        Returns:
            List of MappingResult sorted by confidence descending.
        """
        key = self._make_key(code, source_system)
        indices = self._mapping_index.get(key, [])

        results = []
        for idx in indices:
            mapping = self._mappings[idx]
            if mapping.target.system == target_system:
                if mapping.confidence >= min_confidence:
                    results.append(mapping)

        return sorted(results, key=lambda m: -m.confidence)

    def map_code_any(
        self,
        code: str,
        source_system: CodeSystem,
        *,
        min_confidence: float = 0.0,
    ) -> list[MappingResult]:
        """Map a code to all available target systems.

        Args:
            code: The source code value.
            source_system: The source coding system.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of all mappings from this code.
        """
        key = self._make_key(code, source_system)
        indices = self._mapping_index.get(key, [])

        results = []
        for idx in indices:
            mapping = self._mappings[idx]
            if mapping.confidence >= min_confidence:
                results.append(mapping)

        return sorted(results, key=lambda m: -m.confidence)

    def batch_map(
        self,
        codes: list[tuple[str, CodeSystem]],
        target_system: CodeSystem,
    ) -> dict[str, list[MappingResult]]:
        """Map multiple codes in a single batch operation.

        Args:
            codes: List of (code_value, source_system) tuples.
            target_system: Target coding system.

        Returns:
            Dictionary mapping source code → list of mapping results.
        """
        results: dict[str, list[MappingResult]] = {}
        for code_value, source_system in codes:
            mapped = self.map_code(code_value, source_system, target_system)
            results[code_value] = mapped
        return results

    def search(
        self,
        query: str,
        system: Optional[CodeSystem] = None,
        limit: int = 10,
    ) -> list:
        """Search for clinical codes by text or code value.

        Args:
            query: Search query (code or description text).
            system: Optional filter to a specific coding system.
            limit: Maximum results to return.

        Returns:
            List of SearchResult objects.
        """
        return self._search_engine.search(query, system=system, limit=limit)

    def lookup(self, code: str, system: Optional[CodeSystem] = None) -> Optional[ClinicalCode]:
        """Look up a specific code by exact value.

        Args:
            code: Code value to look up.
            system: Optional coding system filter.

        Returns:
            ClinicalCode if found, None otherwise.
        """
        return self._search_engine.lookup(code, system=system)

    def load_csv(self, filepath: str | Path, *, delimiter: str = ",") -> int:
        """Load mappings from a CSV file.

        Expected columns: source_code, source_system, source_display,
                         target_code, target_system, target_display,
                         direction, confidence

        Args:
            filepath: Path to the CSV file.
            delimiter: CSV delimiter character.

        Returns:
            Number of mappings loaded.
        """
        filepath = Path(filepath)
        count = 0

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                try:
                    source = ClinicalCode(
                        code=row["source_code"].strip(),
                        system=CodeSystem.from_string(row["source_system"].strip()),
                        display=row.get("source_display", "").strip(),
                    )
                    target = ClinicalCode(
                        code=row["target_code"].strip(),
                        system=CodeSystem.from_string(row["target_system"].strip()),
                        display=row.get("target_display", "").strip(),
                    )
                    direction = MappingDirection(
                        row.get("direction", "equivalent").strip().lower()
                    )
                    confidence = float(row.get("confidence", "1.0").strip())

                    self.add_mapping(MappingResult(
                        source=source,
                        target=target,
                        direction=direction,
                        confidence=confidence,
                        source_info=f"csv:{filepath.name}",
                    ))
                    count += 1
                except (ValueError, KeyError) as e:
                    continue  # Skip invalid rows

        return count

    def load_json(self, filepath: str | Path) -> int:
        """Load mappings from a JSON file.

        Expected format: list of objects with source, target, direction, confidence.

        Args:
            filepath: Path to the JSON file.

        Returns:
            Number of mappings loaded.
        """
        filepath = Path(filepath)
        count = 0

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        for item in data:
            try:
                source = ClinicalCode(
                    code=item["source"]["code"],
                    system=CodeSystem.from_string(item["source"]["system"]),
                    display=item["source"].get("display", ""),
                )
                target = ClinicalCode(
                    code=item["target"]["code"],
                    system=CodeSystem.from_string(item["target"]["system"]),
                    display=item["target"].get("display", ""),
                )
                direction = MappingDirection(
                    item.get("direction", "equivalent").lower()
                )
                confidence = float(item.get("confidence", 1.0))

                self.add_mapping(MappingResult(
                    source=source,
                    target=target,
                    direction=direction,
                    confidence=confidence,
                    source_info=f"json:{filepath.name}",
                ))
                count += 1
            except (ValueError, KeyError):
                continue

        return count

    def export_mappings(self, format: str = "json") -> str:
        """Export all mappings to a string in the specified format.

        Args:
            format: Output format ('json' or 'csv').

        Returns:
            Formatted string with all mappings.
        """
        if format == "json":
            return json.dumps(
                [m.to_dict() for m in self._mappings],
                indent=2,
            )
        elif format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "source_code", "source_system", "source_display",
                "target_code", "target_system", "target_display",
                "direction", "confidence",
            ])
            for m in self._mappings:
                writer.writerow([
                    m.source.code, m.source.system.value, m.source.display,
                    m.target.code, m.target.system.value, m.target.display,
                    m.direction.value, m.confidence,
                ])
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")

    @property
    def mapping_count(self) -> int:
        """Total number of loaded mappings."""
        return len(self._mappings)

    @property
    def code_count(self) -> int:
        """Total number of indexed codes."""
        return self._search_engine.size

    def stats(self) -> dict:
        """Return statistics about the loaded mappings and codes."""
        systems: dict[str, int] = {}
        for idx in range(self._search_engine.size):
            code = self._search_engine._codes[idx]
            key = code.system.value
            systems[key] = systems.get(key, 0) + 1

        direction_counts: dict[str, int] = {}
        for m in self._mappings:
            key = m.direction.value
            direction_counts[key] = direction_counts.get(key, 0) + 1

        return {
            "total_mappings": self.mapping_count,
            "total_indexed_codes": self.code_count,
            "codes_by_system": systems,
            "mappings_by_direction": direction_counts,
        }

    @staticmethod
    def _make_key(code: str, system: CodeSystem) -> str:
        """Create a lookup key from a code and system."""
        return f"{system.value}:{code.upper()}"
