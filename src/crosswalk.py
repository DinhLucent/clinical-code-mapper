"""Built-in crosswalk data for common clinical code mappings.

These are curated, high-confidence mappings between SNOMED-CT ↔ ICD-10
covering the most common clinical conditions. Production systems should
supplement this with data from UMLS, WHO, or NLM mapping files.
"""

from __future__ import annotations

from .models import (
    ClinicalCode,
    CodeSystem,
    MappingDirection,
    MappingResult,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SNOMED-CT → ICD-10 Crosswalk (Common Conditions)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SNOMED_ICD10_CROSSWALK: list[tuple[str, str, str, str, str, float]] = [
    # (snomed_code, snomed_display, icd10_code, icd10_display, direction, confidence)

    # ── Diabetes ──
    ("73211009", "Diabetes mellitus", "E14", "Unspecified diabetes mellitus", "equivalent", 0.95),
    ("46635009", "Type 1 diabetes mellitus", "E10", "Type 1 diabetes mellitus", "equivalent", 1.0),
    ("44054006", "Type 2 diabetes mellitus", "E11", "Type 2 diabetes mellitus", "equivalent", 1.0),
    ("11530004", "Gestational diabetes mellitus", "O24.4", "Gestational diabetes mellitus", "equivalent", 1.0),

    # ── Cardiovascular ──
    ("38341003", "Hypertensive disorder", "I10", "Essential (primary) hypertension", "broader", 0.90),
    ("22298006", "Myocardial infarction", "I21", "Acute myocardial infarction", "equivalent", 0.95),
    ("49436004", "Atrial fibrillation", "I48", "Atrial fibrillation and flutter", "broader", 0.90),
    ("84114007", "Heart failure", "I50", "Heart failure", "equivalent", 0.95),
    ("413758000", "Coronary artery disease", "I25.1", "Atherosclerotic heart disease", "equivalent", 0.90),

    # ── Respiratory ──
    ("195967001", "Asthma", "J45", "Asthma", "equivalent", 1.0),
    ("13645005", "Chronic obstructive pulmonary disease", "J44", "Other chronic obstructive pulmonary disease", "equivalent", 0.95),
    ("233604007", "Pneumonia", "J18", "Pneumonia, unspecified organism", "broader", 0.85),
    ("36971009", "Sinusitis", "J32", "Chronic sinusitis", "broader", 0.80),

    # ── Neurological ──
    ("37796009", "Migraine", "G43", "Migraine", "equivalent", 1.0),
    ("230690007", "Stroke", "I63", "Cerebral infarction", "broader", 0.85),
    ("84757009", "Epilepsy", "G40", "Epilepsy", "equivalent", 0.95),
    ("26929004", "Alzheimer's disease", "G30", "Alzheimer's disease", "equivalent", 1.0),

    # ── Musculoskeletal ──
    ("69896004", "Rheumatoid arthritis", "M06.9", "Rheumatoid arthritis, unspecified", "equivalent", 0.95),
    ("396275006", "Osteoarthritis", "M19.9", "Osteoarthritis, unspecified", "equivalent", 0.90),
    ("64859006", "Osteoporosis", "M81", "Osteoporosis without current pathological fracture", "equivalent", 0.90),

    # ── Endocrine / Metabolic ──
    ("40930008", "Hypothyroidism", "E03", "Other hypothyroidism", "broader", 0.85),
    ("34486009", "Hyperthyroidism", "E05", "Thyrotoxicosis [hyperthyroidism]", "equivalent", 0.90),
    ("55822004", "Hyperlipidemia", "E78", "Disorders of lipoprotein metabolism", "broader", 0.80),

    # ── Renal ──
    ("709044004", "Chronic kidney disease", "N18", "Chronic kidney disease (CKD)", "equivalent", 0.95),
    ("236423003", "Renal stone", "N20", "Calculus of kidney and ureter", "equivalent", 0.90),

    # ── Gastrointestinal ──
    ("235595009", "Gastroesophageal reflux disease", "K21", "Gastro-oesophageal reflux disease", "equivalent", 0.95),
    ("34000006", "Crohn's disease", "K50", "Crohn's disease [regional enteritis]", "equivalent", 1.0),
    ("64766004", "Ulcerative colitis", "K51", "Ulcerative colitis", "equivalent", 1.0),

    # ── Mental Health ──
    ("35489007", "Depression", "F32", "Depressive episode", "broader", 0.85),
    ("197480006", "Anxiety disorder", "F41", "Other anxiety disorders", "broader", 0.85),
    ("58214004", "Schizophrenia", "F20", "Schizophrenia", "equivalent", 1.0),
    ("13746004", "Bipolar disorder", "F31", "Bipolar affective disorder", "equivalent", 0.95),

    # ── Infectious Disease ──
    ("186747009", "Coronavirus infection", "U07.1", "COVID-19", "equivalent", 0.95),
    ("6142004", "Influenza", "J11", "Influenza due to unidentified influenza virus", "broader", 0.85),
    ("56717001", "Tuberculosis", "A15", "Respiratory tuberculosis", "broader", 0.80),

    # ── Oncology ──
    ("254837009", "Malignant neoplasm of breast", "C50", "Malignant neoplasm of breast", "equivalent", 0.95),
    ("363406005", "Malignant neoplasm of colon", "C18", "Malignant neoplasm of colon", "equivalent", 0.95),
    ("93880001", "Malignant neoplasm of lung", "C34", "Malignant neoplasm of bronchus and lung", "equivalent", 0.95),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOINC Common Lab Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOINC_COMMON: list[tuple[str, str, str]] = [
    # (loinc_code, display, category)
    ("2339-0", "Glucose [Mass/volume] in Blood", "Chemistry"),
    ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood", "Chemistry"),
    ("2093-3", "Cholesterol [Mass/volume] in Serum or Plasma", "Chemistry"),
    ("2571-8", "Triglycerides [Mass/volume] in Serum or Plasma", "Chemistry"),
    ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma", "Chemistry"),
    ("3094-0", "Urea nitrogen [Mass/volume] in Serum or Plasma", "Chemistry"),
    ("17861-6", "Calcium [Mass/volume] in Serum or Plasma", "Chemistry"),
    ("2823-3", "Potassium [Moles/volume] in Serum or Plasma", "Chemistry"),
    ("2951-2", "Sodium [Moles/volume] in Serum or Plasma", "Chemistry"),
    ("1742-6", "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma", "Liver"),
    ("1920-8", "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma", "Liver"),
    ("1975-2", "Bilirubin.total [Mass/volume] in Serum or Plasma", "Liver"),
    ("718-7", "Hemoglobin [Mass/volume] in Blood", "Hematology"),
    ("26515-7", "Platelets [#/volume] in Blood", "Hematology"),
    ("6690-2", "Leukocytes [#/volume] in Blood by Automated count", "Hematology"),
    ("789-8", "Erythrocytes [#/volume] in Blood by Automated count", "Hematology"),
    ("3016-3", "Thyrotropin [Units/volume] in Serum or Plasma", "Endocrine"),
    ("3026-2", "Thyroxine (T4) free [Mass/volume] in Serum or Plasma", "Endocrine"),
    ("14979-9", "aPTT in Platelet poor plasma by Coagulation assay", "Coagulation"),
    ("5902-2", "Prothrombin time (PT)", "Coagulation"),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CPT Common Procedure Codes (Evaluation & Management)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CPT_COMMON: list[tuple[str, str, str]] = [
    ("99213", "Office/outpatient visit, established patient, low complexity", "E&M"),
    ("99214", "Office/outpatient visit, established patient, moderate complexity", "E&M"),
    ("99215", "Office/outpatient visit, established patient, high complexity", "E&M"),
    ("99203", "Office/outpatient visit, new patient, low complexity", "E&M"),
    ("99204", "Office/outpatient visit, new patient, moderate complexity", "E&M"),
    ("99205", "Office/outpatient visit, new patient, high complexity", "E&M"),
    ("99231", "Subsequent hospital care, straightforward or low complexity", "Hospital"),
    ("99232", "Subsequent hospital care, moderate complexity", "Hospital"),
    ("99233", "Subsequent hospital care, high complexity", "Hospital"),
    ("99281", "Emergency department visit, self-limited", "ED"),
    ("99282", "Emergency department visit, low complexity", "ED"),
    ("99283", "Emergency department visit, moderate complexity", "ED"),
    ("99284", "Emergency department visit, moderately high complexity", "ED"),
    ("99285", "Emergency department visit, high complexity", "ED"),
    ("36415", "Collection of venous blood by venipuncture", "Lab"),
    ("85025", "Complete blood count (CBC) with differential, automated", "Lab"),
    ("80053", "Comprehensive metabolic panel", "Lab"),
    ("80048", "Basic metabolic panel", "Lab"),
    ("71046", "Chest X-ray, 2 views", "Radiology"),
    ("74177", "CT abdomen and pelvis with contrast", "Radiology"),
]


def build_crosswalk_mappings() -> list[MappingResult]:
    """Build the full list of MappingResult objects from the built-in crosswalk.

    Returns bidirectional mappings (SNOMED→ICD10 and ICD10→SNOMED).
    """
    mappings: list[MappingResult] = []
    direction_map = {
        "equivalent": MappingDirection.EQUIVALENT,
        "broader": MappingDirection.BROADER,
        "narrower": MappingDirection.NARROWER,
        "related": MappingDirection.RELATED,
        "approximate": MappingDirection.APPROXIMATE,
    }

    for snomed_code, snomed_disp, icd_code, icd_disp, dir_str, conf in SNOMED_ICD10_CROSSWALK:
        source = ClinicalCode(
            code=snomed_code,
            system=CodeSystem.SNOMED_CT,
            display=snomed_disp,
        )
        target = ClinicalCode(
            code=icd_code,
            system=CodeSystem.ICD_10,
            display=icd_disp,
        )
        direction = direction_map.get(dir_str, MappingDirection.APPROXIMATE)

        # Forward mapping: SNOMED → ICD-10
        mappings.append(MappingResult(
            source=source,
            target=target,
            direction=direction,
            confidence=conf,
            source_info="built-in crosswalk v1.0",
        ))

        # Reverse mapping: ICD-10 → SNOMED
        reverse_dir = {
            MappingDirection.BROADER: MappingDirection.NARROWER,
            MappingDirection.NARROWER: MappingDirection.BROADER,
        }.get(direction, direction)

        mappings.append(MappingResult(
            source=target,
            target=source,
            direction=reverse_dir,
            confidence=conf,
            source_info="built-in crosswalk v1.0 (reverse)",
        ))

    return mappings


def build_loinc_codes() -> list[ClinicalCode]:
    """Build ClinicalCode objects for common LOINC lab tests."""
    return [
        ClinicalCode(
            code=code,
            system=CodeSystem.LOINC,
            display=display,
            hierarchy=category,
        )
        for code, display, category in LOINC_COMMON
    ]


def build_cpt_codes() -> list[ClinicalCode]:
    """Build ClinicalCode objects for common CPT procedure codes."""
    return [
        ClinicalCode(
            code=code,
            system=CodeSystem.CPT,
            display=display,
            hierarchy=category,
        )
        for code, display, category in CPT_COMMON
    ]
