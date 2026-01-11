#!/usr/bin/env python3
"""
Import ERDTS JSON data to Supabase

Usage:
    python scripts/import_to_supabase.py --data-dir data/supabase
    python scripts/import_to_supabase.py --data-dir data/supabase --clear-existing
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional

from supabase import create_client, Client
from tqdm import tqdm


BATCH_SIZE = 500  # Supabase recommended batch size


def load_json(filepath: Path) -> list[dict]:
    """Load JSON file and return list of records."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def batch_insert(
    client: Client,
    table: str,
    records: list[dict],
    batch_size: int = BATCH_SIZE
) -> int:
    """Insert records in batches. Returns total inserted count."""
    total = len(records)
    inserted = 0
    
    for i in tqdm(range(0, total, batch_size), desc=f"  {table}"):
        batch = records[i:i + batch_size]
        try:
            client.table(table).insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"    ⚠️ Error inserting batch {i//batch_size + 1}: {e}")
            # Continue with next batch
    
    return inserted


def clear_table(client: Client, table: str) -> None:
    """Clear all data from a table."""
    try:
        # Delete all records (Supabase doesn't support TRUNCATE via API)
        client.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"  ✓ Cleared {table}")
    except Exception as e:
        print(f"  ⚠️ Could not clear {table}: {e}")


def verify_connection(client: Client) -> bool:
    """Verify Supabase connection is working."""
    try:
        # Try a simple query
        client.table("patients").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Import ERDTS data to Supabase")
    parser.add_argument("--data-dir", type=Path, required=True, help="Path to Supabase JSON files")
    parser.add_argument("--supabase-url", type=str, default=os.environ.get("SUPABASE_URL"), help="Supabase project URL")
    parser.add_argument("--supabase-key", type=str, default=os.environ.get("SUPABASE_SERVICE_KEY"), help="Supabase service role key")
    parser.add_argument("--clear-existing", action="store_true", help="Clear existing data before import")
    parser.add_argument("--skip-patients", action="store_true", help="Skip patients table")
    parser.add_argument("--skip-conditions", action="store_true", help="Skip patient_conditions table")
    parser.add_argument("--skip-medications", action="store_true", help="Skip patient_medications table")
    parser.add_argument("--skip-labs", action="store_true", help="Skip patient_labs table")
    args = parser.parse_args()
    
    # Validate credentials
    if not args.supabase_url or not args.supabase_key:
        print("❌ Error: Missing Supabase credentials")
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        print("Or use --supabase-url and --supabase-key arguments")
        sys.exit(1)
    
    # Validate data directory
    if not args.data_dir.exists():
        print(f"❌ Error: Data directory not found: {args.data_dir}")
        sys.exit(1)
    
    print("=" * 70)
    print("ERDTS SUPABASE IMPORT")
    print("=" * 70)
    print(f"Data directory: {args.data_dir}")
    print(f"Supabase URL: {args.supabase_url}")
    print(f"Clear existing: {args.clear_existing}")
    print("=" * 70)
    
    # Create Supabase client
    print("\n🔌 Connecting to Supabase...")
    client = create_client(args.supabase_url, args.supabase_key)
    
    # Define import order (respects foreign key dependencies)
    import_order = []
    
    if not args.skip_patients:
        import_order.append(("patients", "patients.json", "synthetic_id"))
    if not args.skip_conditions:
        import_order.append(("patient_conditions", "patient_conditions.json", "patient_synthetic_id"))
    if not args.skip_medications:
        import_order.append(("patient_medications", "patient_medications.json", "patient_synthetic_id"))
    if not args.skip_labs:
        import_order.append(("patient_labs", "patient_labs.json", "patient_synthetic_id"))
    
    # Clear existing data if requested (reverse order for FK constraints)
    if args.clear_existing:
        print("\n🗑️ Clearing existing data...")
        for table, _, _ in reversed(import_order):
            clear_table(client, table)
    
    # Import data
    print("\n📥 Importing data...")
    results = {}
    
    for table, filename, id_field in import_order:
        filepath = args.data_dir / filename
        
        if not filepath.exists():
            print(f"\n⚠️ Skipping {table}: {filename} not found")
            continue
        
        print(f"\n📋 {table}:")
        records = load_json(filepath)
        print(f"  Loaded {len(records):,} records from {filename}")
        
        # Remove internal fields if present
        for record in records:
            record.pop("_synthea_id", None)
        
        inserted = batch_insert(client, table, records)
        results[table] = {"loaded": len(records), "inserted": inserted}
        print(f"  ✓ Inserted {inserted:,} records")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ IMPORT COMPLETE")
    print("=" * 70)
    
    total_loaded = 0
    total_inserted = 0
    
    for table, counts in results.items():
        print(f"  {table}: {counts['inserted']:,} / {counts['loaded']:,} records")
        total_loaded += counts["loaded"]
        total_inserted += counts["inserted"]
    
    print("-" * 70)
    print(f"  TOTAL: {total_inserted:,} / {total_loaded:,} records")
    
    if total_inserted < total_loaded:
        print("\n⚠️ Some records failed to import. Check the logs above.")
        sys.exit(1)
    
    print("=" * 70)


if __name__ == "__main__":
    main()
