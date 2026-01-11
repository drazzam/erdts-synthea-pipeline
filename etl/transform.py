#!/usr/bin/env python3
"""
ERDTS ETL Transform Pipeline

Main orchestrator for transforming Synthea CSV data into ERDTS-compatible JSON.

Usage:
    python etl/transform.py --input-dir data/raw --output-dir data
    python etl/transform.py --input-dir data/raw --output-dir data --patient-limit 1000
"""

import argparse
import json
import gc
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from tqdm import tqdm

from mappers import (
    map_patient,
    map_condition_code,
    map_medication_code,
    map_lab_code,
    map_patient_condition,
    map_patient_medication,
    map_patient_lab,
)


def load_synthea_csv(input_dir: Path, filename: str, usecols: Optional[list] = None) -> pd.DataFrame:
    """Load a Synthea CSV file with optional column selection."""
    filepath = input_dir / filename
    if not filepath.exists():
        print(f"Warning: {filename} not found at {filepath}")
        return pd.DataFrame()
    
    df = pd.read_csv(filepath, usecols=usecols, low_memory=True)
    print(f"  Loaded {filename}: {len(df):,} rows")
    return df


def transform_patients(df: pd.DataFrame, limit: int) -> tuple[list[dict], dict[str, str]]:
    """
    Transform Synthea patients to ERDTS format.
    
    Returns:
        tuple: (list of patient dicts, mapping of synthea_id -> synthetic_id)
    """
    patients = []
    id_mapping = {}
    
    for idx, row in tqdm(df.head(limit).iterrows(), total=min(limit, len(df)), desc="Patients"):
        patient = map_patient(row, idx + 1)
        synthea_id = row["Id"]
        synthetic_id = patient["synthetic_id"]
        
        # Store mapping for relationship building
        id_mapping[synthea_id] = synthetic_id
        
        # Remove internal synthea_id before saving
        patients.append(patient)
    
    return patients, id_mapping


def extract_condition_codes(df: pd.DataFrame, patient_synthea_ids: set) -> list[dict]:
    """Extract unique condition codes from filtered conditions."""
    filtered = df[df["PATIENT"].isin(patient_synthea_ids)]
    unique_codes = filtered.drop_duplicates(subset=["CODE"])
    
    conditions = []
    for _, row in tqdm(unique_codes.iterrows(), total=len(unique_codes), desc="Condition codes"):
        conditions.append(map_condition_code(row))
    
    return conditions


def extract_medication_codes(df: pd.DataFrame, patient_synthea_ids: set) -> list[dict]:
    """Extract unique medication codes from filtered medications."""
    filtered = df[df["PATIENT"].isin(patient_synthea_ids)]
    unique_codes = filtered.drop_duplicates(subset=["CODE"])
    
    medications = []
    for _, row in tqdm(unique_codes.iterrows(), total=len(unique_codes), desc="Medication codes"):
        medications.append(map_medication_code(row))
    
    return medications


def extract_lab_codes(input_dir: Path, patient_synthea_ids: set, chunk_size: int = 50000) -> list[dict]:
    """Extract unique lab codes from observations using chunked processing."""
    unique_labs = {}
    
    filepath = input_dir / "observations.csv"
    if not filepath.exists():
        print("  Warning: observations.csv not found")
        return []
    
    for chunk in tqdm(
        pd.read_csv(filepath, usecols=["PATIENT", "CODE", "DESCRIPTION", "UNITS", "VALUE"], chunksize=chunk_size),
        desc="Lab codes (chunked)"
    ):
        filtered = chunk[chunk["PATIENT"].isin(patient_synthea_ids)]
        for _, row in filtered.drop_duplicates(subset=["CODE"]).iterrows():
            code = str(row["CODE"])
            if code not in unique_labs:
                unique_labs[code] = map_lab_code(row)
        del chunk
        gc.collect()
    
    return list(unique_labs.values())


def build_patient_conditions(df: pd.DataFrame, id_mapping: dict[str, str]) -> list[dict]:
    """Build patient-condition relationship records."""
    relationships = []
    
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Patient conditions"):
        synthea_id = row["PATIENT"]
        if synthea_id not in id_mapping:
            continue
        relationships.append(map_patient_condition(id_mapping[synthea_id], row))
    
    return relationships


def build_patient_medications(df: pd.DataFrame, id_mapping: dict[str, str]) -> list[dict]:
    """Build patient-medication relationship records."""
    relationships = []
    
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Patient medications"):
        synthea_id = row["PATIENT"]
        if synthea_id not in id_mapping:
            continue
        relationships.append(map_patient_medication(id_mapping[synthea_id], row))
    
    return relationships


def build_patient_labs(
    input_dir: Path,
    id_mapping: dict[str, str],
    max_records: int = 50000,
    chunk_size: int = 25000
) -> list[dict]:
    """Build patient-lab relationship records with chunked processing and record limit."""
    relationships = []
    
    filepath = input_dir / "observations.csv"
    if not filepath.exists():
        print("  Warning: observations.csv not found")
        return []
    
    synthea_ids = set(id_mapping.keys())
    
    for chunk in tqdm(
        pd.read_csv(filepath, usecols=["PATIENT", "CODE", "DATE", "VALUE", "UNITS", "TYPE"], chunksize=chunk_size),
        desc="Patient labs (chunked)"
    ):
        if len(relationships) >= max_records:
            break
        
        for _, row in chunk.iterrows():
            if len(relationships) >= max_records:
                break
            
            synthea_id = row["PATIENT"]
            if synthea_id not in synthea_ids:
                continue
            
            relationships.append(map_patient_lab(id_mapping[synthea_id], row))
        
        del chunk
        gc.collect()
    
    return relationships


def save_json(filepath: Path, data: list[dict], indent: int = 2) -> int:
    """Save data as JSON and return byte count."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
    return filepath.stat().st_size


def generate_manifest(output_dir: Path, stats: dict) -> None:
    """Generate a manifest file with generation statistics."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "generator": "ERDTS Synthea ETL Pipeline v1.0.0",
        "statistics": stats,
        "files": {
            "static": [
                "condition_codes.json",
                "medication_codes.json",
                "lab_codes.json"
            ],
            "supabase": [
                "patients.json",
                "patient_conditions.json",
                "patient_medications.json",
                "patient_labs.json"
            ]
        }
    }
    
    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Transform Synthea data to ERDTS format")
    parser.add_argument("--input-dir", type=Path, required=True, help="Path to Synthea CSV files")
    parser.add_argument("--output-dir", type=Path, required=True, help="Path for output JSON files")
    parser.add_argument("--patient-limit", type=int, default=2000, help="Max patients to process")
    parser.add_argument("--lab-limit", type=int, default=50000, help="Max lab records to process")
    args = parser.parse_args()
    
    # Validate input directory
    if not args.input_dir.exists():
        print(f"Error: Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    # Create output directories
    static_dir = args.output_dir / "static"
    supabase_dir = args.output_dir / "supabase"
    static_dir.mkdir(parents=True, exist_ok=True)
    supabase_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("ERDTS SYNTHEA ETL PIPELINE")
    print("=" * 70)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Patient limit: {args.patient_limit:,}")
    print(f"Lab limit: {args.lab_limit:,}")
    print("=" * 70)
    
    stats = {}
    
    # Phase 1: Load and transform patients
    print("\n📋 Phase 1: Loading patients...")
    patients_df = load_synthea_csv(args.input_dir, "patients.csv")
    if patients_df.empty:
        print("Error: No patients found. Aborting.")
        sys.exit(1)
    
    patients, id_mapping = transform_patients(patients_df, args.patient_limit)
    stats["patients"] = len(patients)
    print(f"  ✓ Transformed {len(patients):,} patients")
    
    synthea_ids = set(id_mapping.keys())
    del patients_df
    gc.collect()
    
    # Phase 2: Extract condition codes
    print("\n💊 Phase 2: Extracting condition codes...")
    conditions_df = load_synthea_csv(args.input_dir, "conditions.csv", usecols=["PATIENT", "CODE", "DESCRIPTION"])
    condition_codes = extract_condition_codes(conditions_df, synthea_ids)
    stats["condition_codes"] = len(condition_codes)
    print(f"  ✓ Extracted {len(condition_codes):,} unique condition codes")
    
    # Phase 3: Extract medication codes
    print("\n💉 Phase 3: Extracting medication codes...")
    medications_df = load_synthea_csv(args.input_dir, "medications.csv", usecols=["PATIENT", "CODE", "DESCRIPTION"])
    medication_codes = extract_medication_codes(medications_df, synthea_ids)
    stats["medication_codes"] = len(medication_codes)
    print(f"  ✓ Extracted {len(medication_codes):,} unique medication codes")
    
    # Phase 4: Extract lab codes
    print("\n🧪 Phase 4: Extracting lab codes...")
    lab_codes = extract_lab_codes(args.input_dir, synthea_ids)
    stats["lab_codes"] = len(lab_codes)
    print(f"  ✓ Extracted {len(lab_codes):,} unique lab codes")
    
    # Phase 5: Build patient conditions
    print("\n🔗 Phase 5: Building patient conditions...")
    conditions_df = load_synthea_csv(args.input_dir, "conditions.csv", usecols=["PATIENT", "CODE", "START", "STOP"])
    patient_conditions = build_patient_conditions(conditions_df, id_mapping)
    stats["patient_conditions"] = len(patient_conditions)
    print(f"  ✓ Built {len(patient_conditions):,} patient-condition records")
    del conditions_df
    gc.collect()
    
    # Phase 6: Build patient medications
    print("\n🔗 Phase 6: Building patient medications...")
    medications_df = load_synthea_csv(args.input_dir, "medications.csv", usecols=["PATIENT", "CODE", "START", "STOP"])
    patient_medications = build_patient_medications(medications_df, id_mapping)
    stats["patient_medications"] = len(patient_medications)
    print(f"  ✓ Built {len(patient_medications):,} patient-medication records")
    del medications_df
    gc.collect()
    
    # Phase 7: Build patient labs
    print("\n🔗 Phase 7: Building patient labs...")
    patient_labs = build_patient_labs(args.input_dir, id_mapping, max_records=args.lab_limit)
    stats["patient_labs"] = len(patient_labs)
    print(f"  ✓ Built {len(patient_labs):,} patient-lab records")
    
    # Phase 8: Save all files
    print("\n💾 Phase 8: Saving output files...")
    
    # Static files (for Lovable)
    size = save_json(static_dir / "condition_codes.json", condition_codes)
    print(f"  ✓ condition_codes.json: {size:,} bytes")
    
    size = save_json(static_dir / "medication_codes.json", medication_codes)
    print(f"  ✓ medication_codes.json: {size:,} bytes")
    
    size = save_json(static_dir / "lab_codes.json", lab_codes)
    print(f"  ✓ lab_codes.json: {size:,} bytes")
    
    # Supabase files
    size = save_json(supabase_dir / "patients.json", patients)
    print(f"  ✓ patients.json: {size:,} bytes")
    
    size = save_json(supabase_dir / "patient_conditions.json", patient_conditions)
    print(f"  ✓ patient_conditions.json: {size:,} bytes")
    
    size = save_json(supabase_dir / "patient_medications.json", patient_medications)
    print(f"  ✓ patient_medications.json: {size:,} bytes")
    
    size = save_json(supabase_dir / "patient_labs.json", patient_labs)
    print(f"  ✓ patient_labs.json: {size:,} bytes")
    
    # Generate manifest
    generate_manifest(args.output_dir, stats)
    print(f"  ✓ manifest.json")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ ETL PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Patients:            {stats['patients']:>10,}")
    print(f"  Condition codes:     {stats['condition_codes']:>10,}")
    print(f"  Medication codes:    {stats['medication_codes']:>10,}")
    print(f"  Lab codes:           {stats['lab_codes']:>10,}")
    print(f"  Patient conditions:  {stats['patient_conditions']:>10,}")
    print(f"  Patient medications: {stats['patient_medications']:>10,}")
    print(f"  Patient labs:        {stats['patient_labs']:>10,}")
    print("-" * 70)
    total = sum(stats.values())
    print(f"  TOTAL RECORDS:       {total:>10,}")
    print("=" * 70)


if __name__ == "__main__":
    main()
