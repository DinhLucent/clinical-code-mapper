"""Command-line interface for clinical-code-mapper."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .mapper import ClinicalCodeMapper
from .models import CodeSystem


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="clinical-code-mapper",
        description="Map between SNOMED-CT, ICD-10, CPT, and LOINC clinical coding systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s map 73211009 SNOMED-CT ICD-10
  %(prog)s map 73211009 SNOMED-CT --all
  %(prog)s search "diabetes"
  %(prog)s search "hemoglobin" --system LOINC
  %(prog)s lookup 4548-4 --system LOINC
  %(prog)s stats
  %(prog)s export --format csv
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── map command ──
    map_parser = subparsers.add_parser("map", help="Map a code to another system")
    map_parser.add_argument("code", help="Source code value")
    map_parser.add_argument("source_system", help="Source coding system")
    map_parser.add_argument("target_system", nargs="?", help="Target coding system")
    map_parser.add_argument("--all", action="store_true", help="Map to all available systems")
    map_parser.add_argument("--min-confidence", type=float, default=0.0, help="Minimum confidence")
    map_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # ── search command ──
    search_parser = subparsers.add_parser("search", help="Search codes by text")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--system", help="Filter by coding system")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    search_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # ── lookup command ──
    lookup_parser = subparsers.add_parser("lookup", help="Look up a specific code")
    lookup_parser.add_argument("code", help="Code value")
    lookup_parser.add_argument("--system", help="Coding system")
    lookup_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # ── stats command ──
    subparsers.add_parser("stats", help="Show mapping statistics")

    # ── export command ──
    export_parser = subparsers.add_parser("export", help="Export all mappings")
    export_parser.add_argument("--format", choices=["json", "csv"], default="json")

    return parser


def cmd_map(args: argparse.Namespace, mapper: ClinicalCodeMapper) -> None:
    """Handle the 'map' command."""
    try:
        source_system = CodeSystem.from_string(args.source_system)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.all or not args.target_system:
        results = mapper.map_code_any(
            args.code, source_system, min_confidence=args.min_confidence
        )
    else:
        try:
            target_system = CodeSystem.from_string(args.target_system)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        results = mapper.map_code(
            args.code, source_system, target_system,
            min_confidence=args.min_confidence,
        )

    if not results:
        print(f"No mappings found for {source_system.value}:{args.code}")
        return

    if getattr(args, "json", False):
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  Mappings for {source_system.value}:{args.code}")
        src_display = results[0].source.display if results else ""
        if src_display:
            print(f"  Description: {src_display}")
        print(f"{'='*60}\n")
        for r in results:
            direction_icon = {
                "equivalent": "≡",
                "broader": "⊃",
                "narrower": "⊂",
                "related": "~",
                "approximate": "≈",
            }.get(r.direction.value, "?")
            confidence_bar = "█" * int(r.confidence * 10) + "░" * (10 - int(r.confidence * 10))
            print(f"  {direction_icon}  {r.target.system.value}:{r.target.code}")
            print(f"     {r.target.display}")
            print(f"     Confidence: [{confidence_bar}] {r.confidence:.0%}")
            print(f"     Direction:  {r.direction.value}")
            print()


def cmd_search(args: argparse.Namespace, mapper: ClinicalCodeMapper) -> None:
    """Handle the 'search' command."""
    system = None
    if args.system:
        try:
            system = CodeSystem.from_string(args.system)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    results = mapper.search(args.query, system=system, limit=args.limit)

    if not results:
        print(f"No results found for '{args.query}'")
        return

    if getattr(args, "json", False):
        print(json.dumps([
            {
                "code": r.code.code,
                "system": r.code.system.value,
                "display": r.code.display,
                "score": round(r.score, 3),
                "match_type": r.match_type,
            }
            for r in results
        ], indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  Search results for '{args.query}'")
        print(f"{'='*60}\n")
        for i, r in enumerate(results, 1):
            score_bar = "█" * int(r.score * 10) + "░" * (10 - int(r.score * 10))
            print(f"  {i:2d}. [{r.code.system.value}] {r.code.code}")
            print(f"      {r.code.display}")
            print(f"      Score: [{score_bar}] {r.score:.1%}  ({r.match_type})")
            print()


def cmd_lookup(args: argparse.Namespace, mapper: ClinicalCodeMapper) -> None:
    """Handle the 'lookup' command."""
    system = None
    if args.system:
        try:
            system = CodeSystem.from_string(args.system)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    code = mapper.lookup(args.code, system=system)
    if code is None:
        print(f"Code not found: {args.code}")
        sys.exit(1)

    if getattr(args, "json", False):
        print(json.dumps(code.to_fhir_coding(), indent=2))
    else:
        print(f"\n  Code:    {code.code}")
        print(f"  System:  {code.system.value}")
        print(f"  Display: {code.display}")
        print(f"  FHIR:    {code.fhir_system_uri}")
        if code.hierarchy:
            print(f"  Category: {code.hierarchy}")
        print()


def cmd_stats(mapper: ClinicalCodeMapper) -> None:
    """Handle the 'stats' command."""
    stats = mapper.stats()
    print(f"\n{'='*60}")
    print(f"  Clinical Code Mapper Statistics")
    print(f"{'='*60}\n")
    print(f"  Total Mappings:      {stats['total_mappings']}")
    print(f"  Total Indexed Codes: {stats['total_indexed_codes']}")
    print()
    print("  Codes by System:")
    for sys_name, count in sorted(stats["codes_by_system"].items()):
        print(f"    {sys_name:15s}  {count:5d}")
    print()
    print("  Mappings by Direction:")
    for dir_name, count in sorted(stats["mappings_by_direction"].items()):
        print(f"    {dir_name:15s}  {count:5d}")
    print()


def main(argv: Optional[list[str]] = None) -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    mapper = ClinicalCodeMapper()

    handlers = {
        "map": lambda: cmd_map(args, mapper),
        "search": lambda: cmd_search(args, mapper),
        "lookup": lambda: cmd_lookup(args, mapper),
        "stats": lambda: cmd_stats(mapper),
        "export": lambda: print(mapper.export_mappings(format=args.format)),
    }

    handler = handlers.get(args.command)
    if handler:
        handler()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
