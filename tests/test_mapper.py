"""Comprehensive tests for clinical-code-mapper."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.models import (
    ClinicalCode,
    CodeSystem,
    HierarchyNode,
    MappingDirection,
    MappingResult,
)
from src.mapper import ClinicalCodeMapper
from src.search import FuzzySearchEngine, SearchResult
from src.crosswalk import (
    build_crosswalk_mappings,
    build_cpt_codes,
    build_loinc_codes,
    SNOMED_ICD10_CROSSWALK,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CodeSystem Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCodeSystem:
    """Tests for the CodeSystem enum."""

    def test_from_string_exact(self):
        assert CodeSystem.from_string("SNOMED-CT") == CodeSystem.SNOMED_CT

    def test_from_string_case_insensitive(self):
        assert CodeSystem.from_string("snomed-ct") == CodeSystem.SNOMED_CT

    def test_from_string_alias_snomed(self):
        assert CodeSystem.from_string("snomed") == CodeSystem.SNOMED_CT
        assert CodeSystem.from_string("SNOMEDCT") == CodeSystem.SNOMED_CT

    def test_from_string_alias_icd10(self):
        assert CodeSystem.from_string("icd10") == CodeSystem.ICD_10
        assert CodeSystem.from_string("ICD-10") == CodeSystem.ICD_10

    def test_from_string_icd10_cm(self):
        assert CodeSystem.from_string("ICD-10-CM") == CodeSystem.ICD_10_CM
        assert CodeSystem.from_string("icd10cm") == CodeSystem.ICD_10_CM

    def test_from_string_loinc(self):
        assert CodeSystem.from_string("LOINC") == CodeSystem.LOINC

    def test_from_string_cpt(self):
        assert CodeSystem.from_string("CPT") == CodeSystem.CPT

    def test_from_string_rxnorm(self):
        assert CodeSystem.from_string("RxNORM") == CodeSystem.RxNORM

    def test_from_string_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown code system"):
            CodeSystem.from_string("INVALID_SYSTEM")

    def test_enum_values(self):
        assert CodeSystem.SNOMED_CT.value == "SNOMED-CT"
        assert CodeSystem.ICD_10.value == "ICD-10"
        assert CodeSystem.LOINC.value == "LOINC"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ClinicalCode Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClinicalCode:
    """Tests for the ClinicalCode dataclass."""

    def test_creation(self):
        code = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes mellitus")
        assert code.code == "73211009"
        assert code.system == CodeSystem.SNOMED_CT
        assert code.display == "Diabetes mellitus"
        assert code.is_active is True

    def test_fhir_system_uri_snomed(self):
        code = ClinicalCode("73211009", CodeSystem.SNOMED_CT)
        assert code.fhir_system_uri == "http://snomed.info/sct"

    def test_fhir_system_uri_icd10(self):
        code = ClinicalCode("E14", CodeSystem.ICD_10)
        assert code.fhir_system_uri == "http://hl7.org/fhir/sid/icd-10"

    def test_fhir_system_uri_loinc(self):
        code = ClinicalCode("2339-0", CodeSystem.LOINC)
        assert code.fhir_system_uri == "http://loinc.org"

    def test_fhir_system_uri_cpt(self):
        code = ClinicalCode("99213", CodeSystem.CPT)
        assert code.fhir_system_uri == "http://www.ama-assn.org/go/cpt"

    def test_to_fhir_coding(self):
        code = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes mellitus")
        fhir = code.to_fhir_coding()
        assert fhir["system"] == "http://snomed.info/sct"
        assert fhir["code"] == "73211009"
        assert fhir["display"] == "Diabetes mellitus"

    def test_str_with_display(self):
        code = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes mellitus")
        assert str(code) == "SNOMED-CT:73211009 (Diabetes mellitus)"

    def test_str_without_display(self):
        code = ClinicalCode("73211009", CodeSystem.SNOMED_CT)
        assert str(code) == "SNOMED-CT:73211009"

    def test_frozen(self):
        code = ClinicalCode("73211009", CodeSystem.SNOMED_CT)
        with pytest.raises(AttributeError):
            code.code = "12345"

    def test_equality(self):
        a = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes")
        b = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes")
        assert a == b

    def test_hash(self):
        a = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes")
        b = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes")
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MappingResult Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMappingResult:
    """Tests for the MappingResult dataclass."""

    def test_creation(self):
        source = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes")
        target = ClinicalCode("E14", CodeSystem.ICD_10, "Diabetes mellitus")
        result = MappingResult(
            source=source, target=target,
            direction=MappingDirection.EQUIVALENT, confidence=0.95,
        )
        assert result.confidence == 0.95
        assert result.is_exact is True

    def test_confidence_validation(self):
        source = ClinicalCode("X", CodeSystem.SNOMED_CT)
        target = ClinicalCode("Y", CodeSystem.ICD_10)
        with pytest.raises(ValueError, match="Confidence must be between"):
            MappingResult(source=source, target=target,
                         direction=MappingDirection.EQUIVALENT, confidence=1.5)

    def test_confidence_validation_negative(self):
        source = ClinicalCode("X", CodeSystem.SNOMED_CT)
        target = ClinicalCode("Y", CodeSystem.ICD_10)
        with pytest.raises(ValueError):
            MappingResult(source=source, target=target,
                         direction=MappingDirection.EQUIVALENT, confidence=-0.1)

    def test_is_exact_true(self):
        source = ClinicalCode("X", CodeSystem.SNOMED_CT)
        target = ClinicalCode("Y", CodeSystem.ICD_10)
        r = MappingResult(source=source, target=target,
                         direction=MappingDirection.EQUIVALENT)
        assert r.is_exact is True

    def test_is_exact_false(self):
        source = ClinicalCode("X", CodeSystem.SNOMED_CT)
        target = ClinicalCode("Y", CodeSystem.ICD_10)
        r = MappingResult(source=source, target=target,
                         direction=MappingDirection.BROADER)
        assert r.is_exact is False

    def test_to_dict(self):
        source = ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes")
        target = ClinicalCode("E14", CodeSystem.ICD_10, "Unspecified diabetes")
        r = MappingResult(source=source, target=target,
                         direction=MappingDirection.EQUIVALENT, confidence=0.95)
        d = r.to_dict()
        assert d["source"]["code"] == "73211009"
        assert d["target"]["code"] == "E14"
        assert d["direction"] == "equivalent"
        assert d["confidence"] == 0.95


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HierarchyNode Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestHierarchyNode:
    """Tests for the HierarchyNode class."""

    def test_depth_root(self):
        code = ClinicalCode("ROOT", CodeSystem.SNOMED_CT, "Root")
        node = HierarchyNode(code=code)
        assert node.depth == 0

    def test_depth_child(self):
        root_code = ClinicalCode("ROOT", CodeSystem.SNOMED_CT)
        child_code = ClinicalCode("CHILD", CodeSystem.SNOMED_CT)
        root = HierarchyNode(code=root_code)
        child = HierarchyNode(code=child_code, parent=root)
        root.children.append(child)
        assert child.depth == 1

    def test_is_leaf(self):
        code = ClinicalCode("LEAF", CodeSystem.SNOMED_CT)
        node = HierarchyNode(code=code)
        assert node.is_leaf is True

    def test_is_not_leaf(self):
        parent_code = ClinicalCode("P", CodeSystem.SNOMED_CT)
        child_code = ClinicalCode("C", CodeSystem.SNOMED_CT)
        parent = HierarchyNode(code=parent_code)
        child = HierarchyNode(code=child_code, parent=parent)
        parent.children.append(child)
        assert parent.is_leaf is False

    def test_ancestors(self):
        a = ClinicalCode("A", CodeSystem.SNOMED_CT)
        b = ClinicalCode("B", CodeSystem.SNOMED_CT)
        c = ClinicalCode("C", CodeSystem.SNOMED_CT)
        na = HierarchyNode(code=a)
        nb = HierarchyNode(code=b, parent=na)
        nc = HierarchyNode(code=c, parent=nb)
        ancestors = nc.ancestors()
        assert len(ancestors) == 2
        assert ancestors[0] == b
        assert ancestors[1] == a

    def test_descendants(self):
        a = ClinicalCode("A", CodeSystem.SNOMED_CT)
        b = ClinicalCode("B", CodeSystem.SNOMED_CT)
        c = ClinicalCode("C", CodeSystem.SNOMED_CT)
        na = HierarchyNode(code=a)
        nb = HierarchyNode(code=b, parent=na)
        nc = HierarchyNode(code=c, parent=nb)
        na.children.append(nb)
        nb.children.append(nc)
        desc = na.descendants()
        assert len(desc) == 2
        assert b in desc
        assert c in desc


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FuzzySearchEngine Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFuzzySearchEngine:
    """Tests for the FuzzySearchEngine."""

    @pytest.fixture
    def engine(self):
        e = FuzzySearchEngine()
        e.add_code(ClinicalCode("73211009", CodeSystem.SNOMED_CT, "Diabetes mellitus"))
        e.add_code(ClinicalCode("46635009", CodeSystem.SNOMED_CT, "Type 1 diabetes mellitus"))
        e.add_code(ClinicalCode("44054006", CodeSystem.SNOMED_CT, "Type 2 diabetes mellitus"))
        e.add_code(ClinicalCode("195967001", CodeSystem.SNOMED_CT, "Asthma"))
        e.add_code(ClinicalCode("22298006", CodeSystem.SNOMED_CT, "Myocardial infarction"))
        e.add_code(ClinicalCode("2339-0", CodeSystem.LOINC, "Glucose [Mass/volume] in Blood"))
        return e

    def test_exact_code_search(self, engine):
        results = engine.search("73211009")
        assert len(results) >= 1
        assert results[0].score == 1.0
        assert results[0].match_type == "exact_code"

    def test_text_search(self, engine):
        results = engine.search("diabetes")
        assert len(results) >= 3
        for r in results:
            assert "diabetes" in r.code.display.lower()

    def test_system_filter(self, engine):
        results = engine.search("diabetes", system=CodeSystem.LOINC)
        assert len(results) == 0

    def test_search_glucose_loinc(self, engine):
        results = engine.search("glucose", system=CodeSystem.LOINC)
        assert len(results) == 1
        assert results[0].code.code == "2339-0"

    def test_empty_query(self, engine):
        results = engine.search("")
        assert results == []

    def test_no_results(self, engine):
        results = engine.search("zzzznotfound")
        assert len(results) == 0

    def test_limit(self, engine):
        results = engine.search("diabetes", limit=1)
        assert len(results) == 1

    def test_lookup_exact(self, engine):
        code = engine.lookup("73211009")
        assert code is not None
        assert code.display == "Diabetes mellitus"

    def test_lookup_not_found(self, engine):
        code = engine.lookup("NOTEXIST")
        assert code is None

    def test_lookup_with_system(self, engine):
        code = engine.lookup("2339-0", system=CodeSystem.LOINC)
        assert code is not None
        assert code.system == CodeSystem.LOINC

    def test_size(self, engine):
        assert engine.size == 6

    def test_prefix_match(self, engine):
        results = engine.search("7321")
        assert len(results) >= 1
        assert results[0].code.code == "73211009"

    def test_add_codes_bulk(self):
        engine = FuzzySearchEngine()
        codes = [
            ClinicalCode("A", CodeSystem.SNOMED_CT, "Alpha"),
            ClinicalCode("B", CodeSystem.SNOMED_CT, "Beta"),
        ]
        engine.add_codes(codes)
        assert engine.size == 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ClinicalCodeMapper Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestClinicalCodeMapper:
    """Tests for the main ClinicalCodeMapper engine."""

    @pytest.fixture
    def mapper(self):
        return ClinicalCodeMapper()

    def test_builtin_loaded(self, mapper):
        assert mapper.mapping_count > 0
        assert mapper.code_count > 0

    def test_map_snomed_to_icd10_diabetes(self, mapper):
        results = mapper.map_code("73211009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert len(results) >= 1
        assert results[0].target.code == "E14"

    def test_map_icd10_to_snomed_diabetes(self, mapper):
        results = mapper.map_code("E14", CodeSystem.ICD_10, CodeSystem.SNOMED_CT)
        assert len(results) >= 1
        assert results[0].target.code == "73211009"

    def test_map_type1_diabetes(self, mapper):
        results = mapper.map_code("46635009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert len(results) >= 1
        assert results[0].target.code == "E10"
        assert results[0].confidence == 1.0

    def test_map_asthma(self, mapper):
        results = mapper.map_code("195967001", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert len(results) >= 1
        assert results[0].target.code == "J45"

    def test_map_code_any(self, mapper):
        results = mapper.map_code_any("73211009", CodeSystem.SNOMED_CT)
        assert len(results) >= 1

    def test_map_not_found(self, mapper):
        results = mapper.map_code("NOTEXIST", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert results == []

    def test_min_confidence_filter(self, mapper):
        results_all = mapper.map_code("73211009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        results_high = mapper.map_code(
            "73211009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10,
            min_confidence=0.99,
        )
        assert len(results_all) >= len(results_high)

    def test_batch_map(self, mapper):
        codes = [
            ("73211009", CodeSystem.SNOMED_CT),
            ("195967001", CodeSystem.SNOMED_CT),
            ("NOTEXIST", CodeSystem.SNOMED_CT),
        ]
        results = mapper.batch_map(codes, CodeSystem.ICD_10)
        assert "73211009" in results
        assert len(results["73211009"]) >= 1
        assert len(results["NOTEXIST"]) == 0

    def test_search(self, mapper):
        results = mapper.search("diabetes")
        assert len(results) >= 1

    def test_lookup(self, mapper):
        code = mapper.lookup("73211009")
        assert code is not None

    def test_stats(self, mapper):
        stats = mapper.stats()
        assert stats["total_mappings"] > 0
        assert stats["total_indexed_codes"] > 0
        assert "SNOMED-CT" in stats["codes_by_system"]

    def test_export_json(self, mapper):
        output = mapper.export_mappings(format="json")
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_export_csv(self, mapper):
        output = mapper.export_mappings(format="csv")
        lines = output.strip().split("\n")
        assert len(lines) > 1  # Header + data
        assert "source_code" in lines[0]

    def test_export_invalid_format(self, mapper):
        with pytest.raises(ValueError, match="Unsupported format"):
            mapper.export_mappings(format="xml")

    def test_no_builtin(self):
        mapper = ClinicalCodeMapper(load_builtin=False)
        assert mapper.mapping_count == 0

    def test_add_custom_mapping(self):
        mapper = ClinicalCodeMapper(load_builtin=False)
        source = ClinicalCode("CUSTOM1", CodeSystem.SNOMED_CT, "Custom code")
        target = ClinicalCode("X99", CodeSystem.ICD_10, "Custom target")
        mapping = MappingResult(
            source=source, target=target,
            direction=MappingDirection.EQUIVALENT,
        )
        mapper.add_mapping(mapping)
        results = mapper.map_code("CUSTOM1", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert len(results) == 1
        assert results[0].target.code == "X99"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CSV/JSON Loading Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestFileLoading:
    """Tests for CSV and JSON loading."""

    def test_load_csv(self, tmp_path):
        csv_file = tmp_path / "mappings.csv"
        csv_file.write_text(
            "source_code,source_system,source_display,target_code,target_system,target_display,direction,confidence\n"
            "TEST1,SNOMED-CT,Test Source,TST1,ICD-10,Test Target,equivalent,0.9\n"
        )
        mapper = ClinicalCodeMapper(load_builtin=False)
        count = mapper.load_csv(csv_file)
        assert count == 1
        results = mapper.map_code("TEST1", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert len(results) == 1

    def test_load_json(self, tmp_path):
        json_file = tmp_path / "mappings.json"
        data = [{
            "source": {"code": "JSON1", "system": "SNOMED-CT", "display": "JSON Source"},
            "target": {"code": "JSN1", "system": "ICD-10", "display": "JSON Target"},
            "direction": "equivalent",
            "confidence": 0.85,
        }]
        json_file.write_text(json.dumps(data))
        mapper = ClinicalCodeMapper(load_builtin=False)
        count = mapper.load_json(json_file)
        assert count == 1
        results = mapper.map_code("JSON1", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert len(results) == 1
        assert results[0].confidence == 0.85

    def test_load_csv_invalid_rows(self, tmp_path):
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text(
            "source_code,source_system,source_display,target_code,target_system,target_display\n"
            "GOOD,SNOMED-CT,Good,G1,ICD-10,Good Target\n"
            "BAD,INVALID_SYS,Bad,B1,ICD-10,Bad Target\n"
        )
        mapper = ClinicalCodeMapper(load_builtin=False)
        count = mapper.load_csv(csv_file)
        assert count == 1  # Only the valid row

    def test_load_json_single_object(self, tmp_path):
        json_file = tmp_path / "single.json"
        data = {
            "source": {"code": "SINGLE", "system": "LOINC", "display": "Single"},
            "target": {"code": "S1", "system": "CPT", "display": "Single Target"},
        }
        json_file.write_text(json.dumps(data))
        mapper = ClinicalCodeMapper(load_builtin=False)
        count = mapper.load_json(json_file)
        assert count == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Crosswalk Data Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCrosswalkData:
    """Tests for the built-in crosswalk data integrity."""

    def test_crosswalk_not_empty(self):
        assert len(SNOMED_ICD10_CROSSWALK) > 30

    def test_crosswalk_builds_mappings(self):
        mappings = build_crosswalk_mappings()
        # Bidirectional: 2x the crosswalk entries
        assert len(mappings) == len(SNOMED_ICD10_CROSSWALK) * 2

    def test_crosswalk_confidence_range(self):
        for _, _, _, _, _, conf in SNOMED_ICD10_CROSSWALK:
            assert 0.0 <= conf <= 1.0

    def test_loinc_codes(self):
        codes = build_loinc_codes()
        assert len(codes) >= 20
        for code in codes:
            assert code.system == CodeSystem.LOINC

    def test_cpt_codes(self):
        codes = build_cpt_codes()
        assert len(codes) >= 20
        for code in codes:
            assert code.system == CodeSystem.CPT


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCLI:
    """Tests for the CLI module."""

    def test_parser_creation(self):
        from src.cli import create_parser
        parser = create_parser()
        assert parser is not None

    def test_map_command_parse(self):
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["map", "73211009", "SNOMED-CT", "ICD-10"])
        assert args.command == "map"
        assert args.code == "73211009"

    def test_search_command_parse(self):
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["search", "diabetes", "--limit", "5"])
        assert args.command == "search"
        assert args.query == "diabetes"
        assert args.limit == 5

    def test_stats_command_parse(self):
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["stats"])
        assert args.command == "stats"

    def test_lookup_command_parse(self):
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["lookup", "4548-4", "--system", "LOINC"])
        assert args.command == "lookup"
        assert args.code == "4548-4"

    def test_export_command_parse(self):
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["export", "--format", "csv"])
        assert args.command == "export"
        assert args.format == "csv"

    def test_main_no_args(self, capsys):
        from src.cli import main
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 0

    def test_main_stats(self, capsys):
        from src.cli import main
        main(["stats"])
        captured = capsys.readouterr()
        assert "Total Mappings" in captured.out

    def test_main_search(self, capsys):
        from src.cli import main
        main(["search", "diabetes"])
        captured = capsys.readouterr()
        assert "diabetes" in captured.out.lower()

    def test_main_map(self, capsys):
        from src.cli import main
        main(["map", "73211009", "SNOMED-CT", "ICD-10"])
        captured = capsys.readouterr()
        assert "E14" in captured.out

    def test_main_map_json(self, capsys):
        from src.cli import main
        main(["map", "73211009", "SNOMED-CT", "ICD-10", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)

    def test_main_lookup(self, capsys):
        from src.cli import main
        main(["lookup", "73211009"])
        captured = capsys.readouterr()
        assert "73211009" in captured.out


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration / Round-trip Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntegration:
    """Integration and round-trip tests."""

    def test_roundtrip_snomed_icd10_snomed(self):
        """Map SNOMED→ICD→SNOMED and verify we get back the original."""
        mapper = ClinicalCodeMapper()
        # SNOMED → ICD-10
        forward = mapper.map_code("46635009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        assert len(forward) >= 1
        icd_code = forward[0].target.code

        # ICD-10 → SNOMED
        reverse = mapper.map_code(icd_code, CodeSystem.ICD_10, CodeSystem.SNOMED_CT)
        assert len(reverse) >= 1
        assert reverse[0].target.code == "46635009"

    def test_all_crosswalk_entries_mappable(self):
        """Verify every entry in the crosswalk can be mapped."""
        mapper = ClinicalCodeMapper()
        for snomed_code, _, icd_code, _, _, _ in SNOMED_ICD10_CROSSWALK:
            forward = mapper.map_code(snomed_code, CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
            assert len(forward) >= 1, f"Missing forward mapping for SNOMED:{snomed_code}"
            reverse = mapper.map_code(icd_code, CodeSystem.ICD_10, CodeSystem.SNOMED_CT)
            assert len(reverse) >= 1, f"Missing reverse mapping for ICD-10:{icd_code}"

    def test_search_finds_mapped_codes(self):
        """Search should find codes that are in the mapping index."""
        mapper = ClinicalCodeMapper()
        results = mapper.search("myocardial infarction")
        assert any(r.code.code == "22298006" for r in results)

    def test_fhir_coding_output(self):
        """Verify FHIR coding output is valid."""
        mapper = ClinicalCodeMapper()
        results = mapper.map_code("73211009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
        fhir = results[0].target.to_fhir_coding()
        assert "system" in fhir
        assert "code" in fhir
        assert fhir["system"].startswith("http")
