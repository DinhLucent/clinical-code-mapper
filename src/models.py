"""Data models for clinical coding systems."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class CodeSystem(str, enum.Enum):
    """Supported clinical coding systems."""

    SNOMED_CT = "SNOMED-CT"
    ICD_10 = "ICD-10"
    ICD_10_CM = "ICD-10-CM"
    CPT = "CPT"
    LOINC = "LOINC"
    HCPCS = "HCPCS"
    RxNORM = "RxNORM"

    @classmethod
    def from_string(cls, value: str) -> CodeSystem:
        """Parse a code system from a flexible string input.

        Handles common aliases like 'snomed', 'icd10', 'icd-10-cm', etc.
        """
        normalized = value.upper().replace(" ", "").replace("_", "")
        aliases: dict[str, CodeSystem] = {
            "SNOMED": cls.SNOMED_CT,
            "SNOMEDCT": cls.SNOMED_CT,
            "SNOMED-CT": cls.SNOMED_CT,
            "ICD10": cls.ICD_10,
            "ICD-10": cls.ICD_10,
            "ICD10CM": cls.ICD_10_CM,
            "ICD-10-CM": cls.ICD_10_CM,
            "ICD10-CM": cls.ICD_10_CM,
            "CPT": cls.CPT,
            "LOINC": cls.LOINC,
            "HCPCS": cls.HCPCS,
            "RXNORM": cls.RxNORM,
        }
        result = aliases.get(normalized)
        if result is None:
            # Try direct enum lookup
            for member in cls:
                if member.value.upper().replace("-", "") == normalized.replace("-", ""):
                    return member
            raise ValueError(
                f"Unknown code system '{value}'. "
                f"Supported: {', '.join(m.value for m in cls)}"
            )
        return result


class MappingDirection(str, enum.Enum):
    """Direction of a mapping relationship."""

    EQUIVALENT = "equivalent"
    BROADER = "broader"
    NARROWER = "narrower"
    RELATED = "related"
    APPROXIMATE = "approximate"
    NOT_MAPPED = "not_mapped"


@dataclass(frozen=True)
class ClinicalCode:
    """Represents a single code in a clinical coding system.

    Attributes:
        code: The code value (e.g., '73211009', 'J45.0', '99213').
        system: The coding system this code belongs to.
        display: Human-readable description of the code.
        hierarchy: Dot-separated hierarchy path (e.g., 'Disorder.Respiratory').
        is_active: Whether the code is currently active in the terminology.
    """

    code: str
    system: CodeSystem
    display: str = ""
    hierarchy: str = ""
    is_active: bool = True

    @property
    def fhir_system_uri(self) -> str:
        """Return the FHIR system URI for this code's coding system."""
        uris = {
            CodeSystem.SNOMED_CT: "http://snomed.info/sct",
            CodeSystem.ICD_10: "http://hl7.org/fhir/sid/icd-10",
            CodeSystem.ICD_10_CM: "http://hl7.org/fhir/sid/icd-10-cm",
            CodeSystem.CPT: "http://www.ama-assn.org/go/cpt",
            CodeSystem.LOINC: "http://loinc.org",
            CodeSystem.HCPCS: "https://www.cms.gov/Medicare/Coding/HCPCSReleaseCodeSets",
            CodeSystem.RxNORM: "http://www.nlm.nih.gov/research/umls/rxnorm",
        }
        return uris[self.system]

    def to_fhir_coding(self) -> dict:
        """Convert to a FHIR Coding resource dictionary."""
        return {
            "system": self.fhir_system_uri,
            "code": self.code,
            "display": self.display,
        }

    def __str__(self) -> str:
        label = f"{self.system.value}:{self.code}"
        if self.display:
            label += f" ({self.display})"
        return label


@dataclass(frozen=True)
class MappingResult:
    """Result of a code mapping operation.

    Attributes:
        source: The original source code.
        target: The mapped target code.
        direction: The relationship direction (equivalent, broader, etc.).
        confidence: Confidence score from 0.0 to 1.0.
        source_info: Optional additional context about the mapping source.
    """

    source: ClinicalCode
    target: ClinicalCode
    direction: MappingDirection
    confidence: float = 1.0
    source_info: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    @property
    def is_exact(self) -> bool:
        """Return True if this is an exact/equivalent mapping."""
        return self.direction == MappingDirection.EQUIVALENT

    def to_dict(self) -> dict:
        """Serialize the mapping result to a dictionary."""
        return {
            "source": {
                "code": self.source.code,
                "system": self.source.system.value,
                "display": self.source.display,
            },
            "target": {
                "code": self.target.code,
                "system": self.target.system.value,
                "display": self.target.display,
            },
            "direction": self.direction.value,
            "confidence": self.confidence,
            "source_info": self.source_info,
        }


@dataclass
class HierarchyNode:
    """A node in a code hierarchy tree.

    Used to represent parent-child relationships in coding systems
    like SNOMED-CT's concept hierarchy.
    """

    code: ClinicalCode
    children: list[HierarchyNode] = field(default_factory=list)
    parent: Optional[HierarchyNode] = field(default=None, repr=False)

    @property
    def depth(self) -> int:
        """Calculate the depth of this node from the root."""
        depth = 0
        node = self.parent
        while node is not None:
            depth += 1
            node = node.parent
        return depth

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def ancestors(self) -> list[ClinicalCode]:
        """Return all ancestor codes from this node to the root."""
        result: list[ClinicalCode] = []
        node = self.parent
        while node is not None:
            result.append(node.code)
            node = node.parent
        return result

    def descendants(self) -> list[ClinicalCode]:
        """Return all descendant codes (BFS)."""
        result: list[ClinicalCode] = []
        queue = list(self.children)
        while queue:
            child = queue.pop(0)
            result.append(child.code)
            queue.extend(child.children)
        return result
