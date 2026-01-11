"""
ERDTS Schema Mappers

Functions to transform Synthea data rows into ERDTS-compatible dictionaries.
"""

import re
import pandas as pd
from typing import Any, Optional


# =============================================================================
# PATIENT MAPPING
# =============================================================================

def map_patient(row: pd.Series, index: int) -> dict[str, Any]:
    """Map a Synthea patient row to ERDTS patient format."""
    return {
        "synthetic_id": f"SYN-{index:05d}",
        "birth_date": row["BIRTHDATE"],
        "sex": "male" if row["GENDER"] == "M" else "female",
        "race": _normalize_race(row.get("RACE")),
        "ethnicity": _normalize_ethnicity(row.get("ETHNICITY")),
        "marital_status": row.get("MARITAL") if pd.notna(row.get("MARITAL")) else None,
        "city": row.get("CITY") if pd.notna(row.get("CITY")) else None,
        "state": row.get("STATE") if pd.notna(row.get("STATE")) else None,
        "zip": str(row.get("ZIP")) if pd.notna(row.get("ZIP")) else None,
        "deceased": bool(pd.notna(row.get("DEATHDATE"))),
        "deceased_date": row.get("DEATHDATE") if pd.notna(row.get("DEATHDATE")) else None,
    }


def _normalize_race(race: Any) -> str:
    """Normalize race values to consistent format."""
    if pd.isna(race):
        return "Unknown"
    
    race_lower = str(race).lower()
    race_map = {
        "white": "White",
        "black": "Black",
        "asian": "Asian",
        "native": "Native American",
        "hawaiian": "Pacific Islander",
        "other": "Other",
    }
    
    for key, value in race_map.items():
        if key in race_lower:
            return value
    
    return "Unknown"


def _normalize_ethnicity(ethnicity: Any) -> str:
    """Normalize ethnicity values to consistent format."""
    if pd.isna(ethnicity):
        return "Unknown"
    
    ethnicity_lower = str(ethnicity).lower().replace(" ", "")
    
    if "hispanic" in ethnicity_lower and "non" not in ethnicity_lower:
        return "Hispanic"
    elif "nonhispanic" in ethnicity_lower:
        return "Not Hispanic"
    
    return "Unknown"


# =============================================================================
# CONDITION CODE MAPPING
# =============================================================================

def map_condition_code(row: pd.Series) -> dict[str, Any]:
    """Map a Synthea condition to ERDTS condition code format."""
    description = str(row["DESCRIPTION"])
    
    # Clean up description - remove common suffixes
    clean_name = description
    for suffix in [" (disorder)", " (finding)", " (situation)", " (procedure)"]:
        clean_name = clean_name.replace(suffix, "")
    
    return {
        "code": str(row["CODE"]),
        "name": clean_name.strip()[:200],  # Truncate to 200 chars
        "snomedCode": str(row["CODE"]),
        "category": _categorize_condition(description),
        "prevalence": _estimate_prevalence(str(row["CODE"])),
    }


def _categorize_condition(description: str) -> str:
    """Categorize a condition based on its description."""
    desc_lower = description.lower()
    
    categories = [
        (["hypertension", "heart", "cardiac", "coronary", "atrial", "angina", "cardiomyopathy", "aortic", "arrhythmia"], "Cardiovascular"),
        (["diabetes", "thyroid", "metabolic", "obesity", "hyperlipidemia", "cholesterol", "insulin"], "Endocrine"),
        (["asthma", "copd", "bronchitis", "pneumonia", "respiratory", "lung", "pulmonary"], "Respiratory"),
        (["cancer", "carcinoma", "tumor", "neoplasm", "malignant", "lymphoma", "leukemia", "melanoma"], "Oncology"),
        (["depression", "anxiety", "bipolar", "schizophrenia", "mental", "psychiatric", "stress", "panic", "ptsd"], "Mental Health"),
        (["arthritis", "osteo", "fracture", "back pain", "joint", "musculoskeletal", "sprain", "strain"], "Musculoskeletal"),
        (["kidney", "renal", "urinary", "bladder", "cystitis", "nephro"], "Genitourinary"),
        (["gastritis", "reflux", "gerd", "liver", "hepatitis", "bowel", "colitis", "digestive", "intestin"], "Digestive"),
        (["stroke", "alzheimer", "dementia", "parkinson", "epilepsy", "seizure", "neuropathy", "migraine", "cerebr"], "Nervous System"),
        (["infection", "sepsis", "bacterial", "viral", "hiv", "tuberculosis", "pneumonia"], "Infectious"),
        (["anemia", "blood", "coagulation", "platelet", "hemophilia", "thrombocyt"], "Blood/Immune"),
        (["pregnancy", "prenatal", "childbirth", "miscarriage", "gestation", "fetal"], "Pregnancy"),
        (["dermatitis", "eczema", "psoriasis", "skin", "acne", "rash", "wound"], "Skin"),
        (["employment", "education", "housing", "social", "finding", "situation"], "Social/Administrative"),
    ]
    
    for keywords, category in categories:
        if any(kw in desc_lower for kw in keywords):
            return category
    
    return "Other"


def _estimate_prevalence(code: str) -> float:
    """Estimate prevalence based on code hash (pseudo-random but deterministic)."""
    # Generate a consistent prevalence value based on code
    hash_val = hash(code) % 30  # 0-29
    return round(0.01 + hash_val / 100, 2)  # 0.01 - 0.30


# =============================================================================
# MEDICATION CODE MAPPING
# =============================================================================

def map_medication_code(row: pd.Series) -> dict[str, Any]:
    """Map a Synthea medication to ERDTS medication code format."""
    description = str(row["DESCRIPTION"])
    
    return {
        "code": str(row["CODE"]),
        "name": description[:150],  # Truncate to 150 chars
        "genericName": _extract_generic_name(description),
        "drugClass": _categorize_drug(description),
        "rxnorm": str(row["CODE"]),
    }


def _extract_generic_name(description: str) -> str:
    """Extract generic drug name from description."""
    # Take first word(s) before dosage information
    match = re.match(r"^([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", description)
    if match:
        return match.group(1).lower()
    
    parts = description.split()
    return parts[0].lower() if parts else "unknown"


def _categorize_drug(description: str) -> str:
    """Categorize a drug based on its description."""
    desc_lower = description.lower()
    
    drug_classes = [
        (["lisinopril", "enalapril", "ramipril", "captopril", "benazepril"], "ACE Inhibitor"),
        (["losartan", "valsartan", "irbesartan", "olmesartan", "candesartan"], "ARB"),
        (["metoprolol", "atenolol", "carvedilol", "propranolol", "bisoprolol"], "Beta Blocker"),
        (["amlodipine", "nifedipine", "diltiazem", "verapamil"], "Calcium Channel Blocker"),
        (["hydrochlorothiazide", "furosemide", "spironolactone", "chlorthalidone", "bumetanide"], "Diuretic"),
        (["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin", "lovastatin"], "Statin"),
        (["metformin", "glipizide", "glyburide", "pioglitazone", "sitagliptin", "empagliflozin"], "Antidiabetic"),
        (["insulin"], "Insulin"),
        (["warfarin", "apixaban", "rivaroxaban", "dabigatran", "heparin", "enoxaparin"], "Anticoagulant"),
        (["aspirin", "clopidogrel", "ticagrelor", "prasugrel"], "Antiplatelet"),
        (["omeprazole", "pantoprazole", "esomeprazole", "lansoprazole", "rabeprazole"], "Proton Pump Inhibitor"),
        (["sertraline", "fluoxetine", "escitalopram", "citalopram", "paroxetine"], "SSRI Antidepressant"),
        (["gabapentin", "pregabalin", "topiramate", "levetiracetam", "carbamazepine", "phenytoin", "valproic"], "Anticonvulsant"),
        (["albuterol", "salbutamol", "ipratropium", "tiotropium", "budesonide", "fluticasone"], "Respiratory"),
        (["penicillin", "amoxicillin", "azithromycin", "ciprofloxacin", "levofloxacin", "doxycycline", "cephalexin"], "Antibiotic"),
        (["acetaminophen", "ibuprofen", "naproxen", "diclofenac", "meloxicam", "celecoxib"], "Analgesic/NSAID"),
        (["oxycodone", "hydrocodone", "morphine", "fentanyl", "tramadol", "codeine"], "Opioid"),
        (["levothyroxine", "synthroid"], "Thyroid Hormone"),
        (["prednisone", "methylprednisolone", "dexamethasone", "hydrocortisone"], "Corticosteroid"),
        (["contraceptive", "levonorgestrel", "ethinyl estradiol", "norethindrone"], "Contraceptive"),
    ]
    
    for keywords, drug_class in drug_classes:
        if any(kw in desc_lower for kw in keywords):
            return drug_class
    
    return "Other"


# =============================================================================
# LAB CODE MAPPING
# =============================================================================

def map_lab_code(row: pd.Series) -> dict[str, Any]:
    """Map a Synthea observation to ERDTS lab code format."""
    description = str(row["DESCRIPTION"])
    unit = str(row["UNITS"]) if pd.notna(row["UNITS"]) else ""
    
    lab = {
        "code": str(row["CODE"]),
        "name": description[:150],
        "loincCode": str(row["CODE"]),
        "category": _categorize_lab(description),
        "unit": unit[:20],
    }
    
    # Add normal ranges for common labs
    ranges = _get_normal_range(description, unit)
    if ranges:
        lab.update(ranges)
    
    return lab


def _categorize_lab(description: str) -> str:
    """Categorize a lab test based on its description."""
    desc_lower = description.lower()
    
    lab_categories = [
        (["glucose", "hemoglobin a1c", "hba1c"], "Glucose/Diabetes"),
        (["cholesterol", "ldl", "hdl", "triglyceride", "lipid"], "Lipid Panel"),
        (["creatinine", "bun", "egfr", "urea"], "Kidney Function"),
        (["alt", "ast", "bilirubin", "alkaline phosphatase", "liver", "albumin"], "Liver Function"),
        (["hemoglobin", "hematocrit", "wbc", "rbc", "platelet", "mcv", "mch", "leukocyte", "erythrocyte"], "Hematology"),
        (["sodium", "potassium", "chloride", "bicarbonate", "calcium", "magnesium", "phosph"], "Electrolytes"),
        (["tsh", "t3", "t4", "thyroid"], "Thyroid"),
        (["troponin", "bnp", "prothrombin", "inr", "ptt"], "Cardiac/Coagulation"),
        (["urine", "urinalysis"], "Urinalysis"),
        (["ige", "allerg"], "Allergy"),
        (["blood pressure", "heart rate", "respiratory rate", "temperature", "oxygen", "bmi", "weight", "height", "pain"], "Vital Signs"),
        (["psa", "cancer", "tumor", "cea", "ca-125", "afp"], "Tumor Markers"),
    ]
    
    for keywords, category in lab_categories:
        if any(kw in desc_lower for kw in keywords):
            return category
    
    return "Other"


def _get_normal_range(description: str, unit: str) -> Optional[dict]:
    """Get normal range for common lab tests."""
    desc_lower = description.lower()
    unit_lower = unit.lower()
    
    # Common lab reference ranges
    ranges = {
        ("glucose", "mg"): {"normalLow": 70, "normalHigh": 100, "criticalLow": 50, "criticalHigh": 400},
        ("hemoglobin a1c", ""): {"normalLow": 4.0, "normalHigh": 5.6},
        ("creatinine", "mg"): {"normalLow": 0.7, "normalHigh": 1.3},
        ("cholesterol", "mg"): {"normalLow": 0, "normalHigh": 200},
        ("ldl", "mg"): {"normalLow": 0, "normalHigh": 100},
        ("hdl", "mg"): {"normalLow": 40, "normalHigh": 60},
        ("triglyceride", "mg"): {"normalLow": 0, "normalHigh": 150},
        ("hemoglobin", "g/dl"): {"normalLow": 12, "normalHigh": 17.5},
        ("platelet", ""): {"normalLow": 150000, "normalHigh": 400000},
        ("sodium", "mmol"): {"normalLow": 136, "normalHigh": 145},
        ("potassium", "mmol"): {"normalLow": 3.5, "normalHigh": 5.0, "criticalLow": 2.5, "criticalHigh": 6.5},
    }
    
    for (keyword, unit_hint), values in ranges.items():
        if keyword in desc_lower:
            if not unit_hint or unit_hint in unit_lower:
                return values
    
    return None


# =============================================================================
# RELATIONSHIP MAPPING
# =============================================================================

def map_patient_condition(synthetic_id: str, row: pd.Series) -> dict[str, Any]:
    """Map a patient-condition relationship."""
    return {
        "patient_synthetic_id": synthetic_id,
        "condition_code": str(row["CODE"]),
        "onset_date": row["START"] if pd.notna(row["START"]) else None,
        "resolution_date": row["STOP"] if pd.notna(row["STOP"]) else None,
    }


def map_patient_medication(synthetic_id: str, row: pd.Series) -> dict[str, Any]:
    """Map a patient-medication relationship."""
    return {
        "patient_synthetic_id": synthetic_id,
        "medication_code": str(row["CODE"]),
        "start_date": row["START"] if pd.notna(row["START"]) else None,
        "end_date": row["STOP"] if pd.notna(row["STOP"]) else None,
    }


def map_patient_lab(synthetic_id: str, row: pd.Series) -> dict[str, Any]:
    """Map a patient-lab relationship."""
    value = row.get("VALUE")
    value_numeric = None
    value_text = None
    
    if pd.notna(value):
        # Try to parse as numeric
        try:
            value_numeric = float(value)
            value_text = str(value)[:100]
        except (ValueError, TypeError):
            value_text = str(value)[:100]
    
    return {
        "patient_synthetic_id": synthetic_id,
        "lab_code": str(row["CODE"]),
        "result_date": row["DATE"] if pd.notna(row["DATE"]) else None,
        "value_numeric": value_numeric,
        "value_text": value_text,
        "unit": str(row["UNITS"])[:20] if pd.notna(row["UNITS"]) else None,
    }
