#!/usr/bin/env python3
"""
Validate ERDTS data files

Checks JSON file integrity, schema compliance, and referential integrity.

Usage:
    python scripts/validate_data.py --data-dir data
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json_safe(filepath: Path) -> tuple[list[dict] | None, str | None]:
    """Load JSON file with error handling."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return None, "Expected JSON array"
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
    except Exception as e:
        return None, f"File read error: {e}"


def validate_schema(records: list[dict], required_fields: list[str], name: str) -> list[str]:
    """Validate that all records have required fields."""
    errors = []
    
    for i, record in enumerate(records[:100]):  # Check first 100
        missing = [f for f in required_fields if f not in record]
        if missing:
            errors.append(f"{name}[{i}]: Missing fields: {missing}")
    
    return errors


def validate_condition_codes(data_dir: Path) -> tuple[bool, list[str], set[str]]:
    """Validate condition_codes.json"""
    filepath = data_dir / "static" / "condition_codes.json"
    errors = []
    codes = set()
    
    if not filepath.exists():
        return False, [f"File not found: {filepath}"], codes
    
    records, error = load_json_safe(filepath)
    if error:
        return False, [error], codes
    
    # Schema validation
    required = ["code", "name", "category"]
    errors.extend(validate_schema(records, required, "condition_codes"))
    
    # Collect codes
    codes = {r["code"] for r in records}
    
    # Check for duplicates
    if len(codes) != len(records):
        errors.append(f"Duplicate codes found: {len(records) - len(codes)} duplicates")
    
    return len(errors) == 0, errors, codes


def validate_medication_codes(data_dir: Path) -> tuple[bool, list[str], set[str]]:
    """Validate medication_codes.json"""
    filepath = data_dir / "static" / "medication_codes.json"
    errors = []
    codes = set()
    
    if not filepath.exists():
        return False, [f"File not found: {filepath}"], codes
    
    records, error = load_json_safe(filepath)
    if error:
        return False, [error], codes
    
    required = ["code", "name", "drugClass"]
    errors.extend(validate_schema(records, required, "medication_codes"))
    
    codes = {r["code"] for r in records}
    
    if len(codes) != len(records):
        errors.append(f"Duplicate codes found: {len(records) - len(codes)} duplicates")
    
    return len(errors) == 0, errors, codes


def validate_lab_codes(data_dir: Path) -> tuple[bool, list[str], set[str]]:
    """Validate lab_codes.json"""
    filepath = data_dir / "static" / "lab_codes.json"
    errors = []
    codes = set()
    
    if not filepath.exists():
        return False, [f"File not found: {filepath}"], codes
    
    records, error = load_json_safe(filepath)
    if error:
        return False, [error], codes
    
    required = ["code", "name", "category"]
    errors.extend(validate_schema(records, required, "lab_codes"))
    
    codes = {r["code"] for r in records}
    
    return len(errors) == 0, errors, codes


def validate_patients(data_dir: Path) -> tuple[bool, list[str], set[str]]:
    """Validate patients.json"""
    filepath = data_dir / "supabase" / "patients.json"
    errors = []
    ids = set()
    
    if not filepath.exists():
        return False, [f"File not found: {filepath}"], ids
    
    records, error = load_json_safe(filepath)
    if error:
        return False, [error], ids
    
    required = ["synthetic_id", "birth_date", "sex"]
    errors.extend(validate_schema(records, required, "patients"))
    
    # Validate sex values
    valid_sex = {"male", "female"}
    for i, r in enumerate(records[:100]):
        if r.get("sex") not in valid_sex:
            errors.append(f"patients[{i}]: Invalid sex value: {r.get('sex')}")
    
    ids = {r["synthetic_id"] for r in records}
    
    if len(ids) != len(records):
        errors.append(f"Duplicate synthetic_ids found")
    
    return len(errors) == 0, errors, ids


def validate_patient_conditions(data_dir: Path, valid_patients: set[str], valid_codes: set[str]) -> tuple[bool, list[str]]:
    """Validate patient_conditions.json"""
    filepath = data_dir / "supabase" / "patient_conditions.json"
    errors = []
    
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]
    
    records, error = load_json_safe(filepath)
    if error:
        return False, [error]
    
    required = ["patient_synthetic_id", "condition_code"]
    errors.extend(validate_schema(records, required, "patient_conditions"))
    
    # Check referential integrity (sample)
    orphan_patients = 0
    orphan_codes = 0
    
    for r in records[:1000]:
        if r.get("patient_synthetic_id") not in valid_patients:
            orphan_patients += 1
        if r.get("condition_code") not in valid_codes:
            orphan_codes += 1
    
    if orphan_patients > 0:
        errors.append(f"Found {orphan_patients} records with invalid patient_synthetic_id (in first 1000)")
    
    # Note: orphan_codes is informational only - Synthea may have more codes than we extracted
    
    return len(errors) == 0, errors


def validate_patient_medications(data_dir: Path, valid_patients: set[str], valid_codes: set[str]) -> tuple[bool, list[str]]:
    """Validate patient_medications.json"""
    filepath = data_dir / "supabase" / "patient_medications.json"
    errors = []
    
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]
    
    records, error = load_json_safe(filepath)
    if error:
        return False, [error]
    
    required = ["patient_synthetic_id", "medication_code"]
    errors.extend(validate_schema(records, required, "patient_medications"))
    
    orphan_patients = 0
    for r in records[:1000]:
        if r.get("patient_synthetic_id") not in valid_patients:
            orphan_patients += 1
    
    if orphan_patients > 0:
        errors.append(f"Found {orphan_patients} records with invalid patient_synthetic_id (in first 1000)")
    
    return len(errors) == 0, errors


def validate_patient_labs(data_dir: Path, valid_patients: set[str], valid_codes: set[str]) -> tuple[bool, list[str]]:
    """Validate patient_labs.json"""
    filepath = data_dir / "supabase" / "patient_labs.json"
    errors = []
    
    if not filepath.exists():
        return False, [f"File not found: {filepath}"]
    
    records, error = load_json_safe(filepath)
    if error:
        return False, [error]
    
    required = ["patient_synthetic_id", "lab_code"]
    errors.extend(validate_schema(records, required, "patient_labs"))
    
    orphan_patients = 0
    for r in records[:1000]:
        if r.get("patient_synthetic_id") not in valid_patients:
            orphan_patients += 1
    
    if orphan_patients > 0:
        errors.append(f"Found {orphan_patients} records with invalid patient_synthetic_id (in first 1000)")
    
    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate ERDTS data files")
    parser.add_argument("--data-dir", type=Path, required=True, help="Path to data directory")
    args = parser.parse_args()
    
    print("=" * 70)
    print("ERDTS DATA VALIDATION")
    print("=" * 70)
    print(f"Data directory: {args.data_dir}")
    print("=" * 70)
    
    all_valid = True
    
    # Validate static files
    print("\n📋 Validating static files...")
    
    valid, errors, condition_codes = validate_condition_codes(args.data_dir)
    print(f"  condition_codes.json: {'✓' if valid else '✗'} ({len(condition_codes)} codes)")
    for e in errors:
        print(f"    ⚠️ {e}")
    all_valid = all_valid and valid
    
    valid, errors, medication_codes = validate_medication_codes(args.data_dir)
    print(f"  medication_codes.json: {'✓' if valid else '✗'} ({len(medication_codes)} codes)")
    for e in errors:
        print(f"    ⚠️ {e}")
    all_valid = all_valid and valid
    
    valid, errors, lab_codes = validate_lab_codes(args.data_dir)
    print(f"  lab_codes.json: {'✓' if valid else '✗'} ({len(lab_codes)} codes)")
    for e in errors:
        print(f"    ⚠️ {e}")
    all_valid = all_valid and valid
    
    # Validate Supabase files
    print("\n📋 Validating Supabase files...")
    
    valid, errors, patient_ids = validate_patients(args.data_dir)
    print(f"  patients.json: {'✓' if valid else '✗'} ({len(patient_ids)} patients)")
    for e in errors:
        print(f"    ⚠️ {e}")
    all_valid = all_valid and valid
    
    valid, errors = validate_patient_conditions(args.data_dir, patient_ids, condition_codes)
    filepath = args.data_dir / "supabase" / "patient_conditions.json"
    count = len(load_json_safe(filepath)[0] or [])
    print(f"  patient_conditions.json: {'✓' if valid else '✗'} ({count:,} records)")
    for e in errors:
        print(f"    ⚠️ {e}")
    all_valid = all_valid and valid
    
    valid, errors = validate_patient_medications(args.data_dir, patient_ids, medication_codes)
    filepath = args.data_dir / "supabase" / "patient_medications.json"
    count = len(load_json_safe(filepath)[0] or [])
    print(f"  patient_medications.json: {'✓' if valid else '✗'} ({count:,} records)")
    for e in errors:
        print(f"    ⚠️ {e}")
    all_valid = all_valid and valid
    
    valid, errors = validate_patient_labs(args.data_dir, patient_ids, lab_codes)
    filepath = args.data_dir / "supabase" / "patient_labs.json"
    count = len(load_json_safe(filepath)[0] or [])
    print(f"  patient_labs.json: {'✓' if valid else '✗'} ({count:,} records)")
    for e in errors:
        print(f"    ⚠️ {e}")
    all_valid = all_valid and valid
    
    # Summary
    print("\n" + "=" * 70)
    if all_valid:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ VALIDATION FAILED - See errors above")
    print("=" * 70)
    
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
