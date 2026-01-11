#!/usr/bin/env python3
"""
Generate statistics for ERDTS data files

Usage:
    python scripts/generate_stats.py --data-dir data
    python scripts/generate_stats.py --data-dir data --output-file stats.json
"""

import argparse
import json
from pathlib import Path
from collections import Counter
from datetime import datetime


def load_json(filepath: Path) -> list[dict]:
    """Load JSON file."""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_age(birth_date: str) -> int:
    """Calculate age from birth date string."""
    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d")
        today = datetime.now()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return age
    except:
        return 0


def main():
    parser = argparse.ArgumentParser(description="Generate ERDTS data statistics")
    parser.add_argument("--data-dir", type=Path, required=True, help="Path to data directory")
    parser.add_argument("--output-file", type=Path, default=None, help="Output JSON file (optional)")
    args = parser.parse_args()
    
    stats = {
        "generated_at": datetime.now().isoformat(),
        "files": {},
        "summary": {}
    }
    
    # Static files
    condition_codes = load_json(args.data_dir / "static" / "condition_codes.json")
    medication_codes = load_json(args.data_dir / "static" / "medication_codes.json")
    lab_codes = load_json(args.data_dir / "static" / "lab_codes.json")
    
    stats["files"]["condition_codes"] = {
        "count": len(condition_codes),
        "categories": dict(Counter(c.get("category", "Unknown") for c in condition_codes))
    }
    
    stats["files"]["medication_codes"] = {
        "count": len(medication_codes),
        "drug_classes": dict(Counter(m.get("drugClass", "Unknown") for m in medication_codes))
    }
    
    stats["files"]["lab_codes"] = {
        "count": len(lab_codes),
        "categories": dict(Counter(l.get("category", "Unknown") for l in lab_codes))
    }
    
    # Supabase files
    patients = load_json(args.data_dir / "supabase" / "patients.json")
    patient_conditions = load_json(args.data_dir / "supabase" / "patient_conditions.json")
    patient_medications = load_json(args.data_dir / "supabase" / "patient_medications.json")
    patient_labs = load_json(args.data_dir / "supabase" / "patient_labs.json")
    
    # Patient demographics
    ages = [calculate_age(p.get("birth_date", "")) for p in patients if p.get("birth_date")]
    
    stats["files"]["patients"] = {
        "count": len(patients),
        "demographics": {
            "sex": dict(Counter(p.get("sex", "unknown") for p in patients)),
            "race": dict(Counter(p.get("race", "Unknown") for p in patients)),
            "ethnicity": dict(Counter(p.get("ethnicity", "Unknown") for p in patients)),
            "deceased": sum(1 for p in patients if p.get("deceased")),
            "age_stats": {
                "min": min(ages) if ages else 0,
                "max": max(ages) if ages else 0,
                "mean": round(sum(ages) / len(ages), 1) if ages else 0
            }
        }
    }
    
    stats["files"]["patient_conditions"] = {
        "count": len(patient_conditions),
        "avg_per_patient": round(len(patient_conditions) / len(patients), 1) if patients else 0
    }
    
    stats["files"]["patient_medications"] = {
        "count": len(patient_medications),
        "avg_per_patient": round(len(patient_medications) / len(patients), 1) if patients else 0
    }
    
    stats["files"]["patient_labs"] = {
        "count": len(patient_labs),
        "avg_per_patient": round(len(patient_labs) / len(patients), 1) if patients else 0
    }
    
    # Summary
    stats["summary"] = {
        "total_records": (
            len(condition_codes) + len(medication_codes) + len(lab_codes) +
            len(patients) + len(patient_conditions) + len(patient_medications) + len(patient_labs)
        ),
        "static_records": len(condition_codes) + len(medication_codes) + len(lab_codes),
        "supabase_records": len(patients) + len(patient_conditions) + len(patient_medications) + len(patient_labs)
    }
    
    # Output
    if args.output_file:
        with open(args.output_file, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"Statistics saved to {args.output_file}")
    else:
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
