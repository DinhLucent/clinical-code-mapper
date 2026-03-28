# Clinical Code Mapper

> Python library for mapping between SNOMED-CT, ICD-10, CPT, and LOINC clinical coding systems with fuzzy search, hierarchical navigation, and FHIR-compatible output.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-86%20passed-brightgreen.svg)]()

## Why This Exists

Clinical systems use different coding standards — a single diagnosis like "Type 2 Diabetes" is `44054006` in SNOMED-CT, `E11` in ICD-10, and maps to specific LOINC lab panels. This library provides **instant cross-system translation** with a clean Python API and CLI.

## Features

| Feature | Description |
|---|---|
| **Cross-system Mapping** | SNOMED-CT ↔ ICD-10 bidirectional mappings with confidence scores |
| **Fuzzy Search** | Find codes by description text with trigram-based typo tolerance |
| **FHIR Output** | Generate FHIR Coding resources directly from any code |
| **Batch Operations** | Map hundreds of codes in a single call |
| **Custom Data** | Load your own mappings from CSV or JSON files |
| **CLI** | Full command-line interface for quick lookups |
| **Built-in Data** | 40 common condition mappings + 20 LOINC labs + 20 CPT procedures |

## Quick Start

```python
from src import ClinicalCodeMapper, CodeSystem

mapper = ClinicalCodeMapper()

# Map SNOMED-CT → ICD-10
results = mapper.map_code("73211009", CodeSystem.SNOMED_CT, CodeSystem.ICD_10)
print(results[0].target)
# ICD-10:E14 (Unspecified diabetes mellitus)

# Fuzzy search
results = mapper.search("myocardial infarction")
for r in results:
    print(f"  [{r.code.system.value}] {r.code.code}: {r.code.display}")

# FHIR output
code = mapper.lookup("73211009")
print(code.to_fhir_coding())
# {"system": "http://snomed.info/sct", "code": "73211009", "display": "Diabetes mellitus"}

# Batch mapping
batch = mapper.batch_map([
    ("73211009", CodeSystem.SNOMED_CT),
    ("195967001", CodeSystem.SNOMED_CT),
], CodeSystem.ICD_10)
```

## CLI Usage

```bash
# Map a SNOMED code to ICD-10
python -m src.cli map 73211009 SNOMED-CT ICD-10

# Search by text
python -m src.cli search "diabetes" --limit 5

# Lookup a specific code
python -m src.cli lookup 4548-4 --system LOINC

# Export all mappings
python -m src.cli export --format csv

# View statistics
python -m src.cli stats
```

## Architecture

```
src/
├── models.py      # CodeSystem, ClinicalCode, MappingResult, HierarchyNode
├── crosswalk.py   # Built-in SNOMED↔ICD-10, LOINC, CPT data
├── mapper.py      # Core mapping engine with CSV/JSON import/export
├── search.py      # Fuzzy search with trigram matching
└── cli.py         # Command-line interface
```

## Supported Code Systems

| System | FHIR URI | Example |
|---|---|---|
| SNOMED-CT | `http://snomed.info/sct` | `73211009` (Diabetes) |
| ICD-10 | `http://hl7.org/fhir/sid/icd-10` | `E14` (Diabetes) |
| ICD-10-CM | `http://hl7.org/fhir/sid/icd-10-cm` | `E11.9` |
| CPT | `http://www.ama-assn.org/go/cpt` | `99213` (Office visit) |
| LOINC | `http://loinc.org` | `4548-4` (HbA1c) |
| HCPCS | CMS | `J0120` |
| RxNORM | NLM | Medications |

## Extending with Custom Data

### CSV Format
```csv
source_code,source_system,source_display,target_code,target_system,target_display,direction,confidence
CUSTOM1,SNOMED-CT,Custom Condition,X99,ICD-10,Custom ICD Code,equivalent,0.9
```

```python
mapper.load_csv("my_mappings.csv")
```

### JSON Format
```json
[{
  "source": {"code": "CUSTOM1", "system": "SNOMED-CT", "display": "Custom"},
  "target": {"code": "X99", "system": "ICD-10", "display": "Custom ICD"},
  "direction": "equivalent",
  "confidence": 0.9
}]
```

## Testing

```bash
pytest tests/ -v
```

**86 tests** covering models, search engine, mapper, CLI, file loading, crosswalk integrity, and integration round-trips.

## License

MIT License — see [LICENSE](LICENSE) for details.
