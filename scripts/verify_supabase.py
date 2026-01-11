#!/usr/bin/env python3
"""
Verify ERDTS data in Supabase after import

Usage:
    python scripts/verify_supabase.py --supabase-url URL --supabase-key KEY
"""

import argparse
import os
import sys

from supabase import create_client


def main():
    parser = argparse.ArgumentParser(description="Verify ERDTS data in Supabase")
    parser.add_argument("--supabase-url", type=str, default=os.environ.get("SUPABASE_URL"))
    parser.add_argument("--supabase-key", type=str, default=os.environ.get("SUPABASE_SERVICE_KEY"))
    args = parser.parse_args()
    
    if not args.supabase_url or not args.supabase_key:
        print("❌ Error: Missing Supabase credentials")
        sys.exit(1)
    
    print("=" * 70)
    print("ERDTS SUPABASE VERIFICATION")
    print("=" * 70)
    
    client = create_client(args.supabase_url, args.supabase_key)
    
    tables = [
        "patients",
        "patient_conditions",
        "patient_medications",
        "patient_labs"
    ]
    
    total = 0
    all_ok = True
    
    print("\n📊 Table record counts:")
    
    for table in tables:
        try:
            # Get count
            result = client.table(table).select("*", count="exact").limit(0).execute()
            count = result.count or 0
            total += count
            print(f"  {table}: {count:,} records ✓")
        except Exception as e:
            print(f"  {table}: ERROR - {e} ✗")
            all_ok = False
    
    print(f"\n  TOTAL: {total:,} records")
    
    # Sample verification
    print("\n📋 Sample data verification:")
    
    try:
        # Check first patient
        result = client.table("patients").select("*").limit(1).execute()
        if result.data:
            patient = result.data[0]
            print(f"  First patient: {patient.get('synthetic_id')} ✓")
        else:
            print("  ⚠️ No patients found")
            all_ok = False
    except Exception as e:
        print(f"  Patient check failed: {e}")
        all_ok = False
    
    try:
        # Check patient with conditions
        result = client.table("patient_conditions").select("patient_synthetic_id").limit(1).execute()
        if result.data:
            pid = result.data[0].get("patient_synthetic_id")
            # Verify patient exists
            patient = client.table("patients").select("synthetic_id").eq("synthetic_id", pid).execute()
            if patient.data:
                print(f"  Referential integrity: ✓")
            else:
                print(f"  ⚠️ Orphan condition found for {pid}")
                all_ok = False
    except Exception as e:
        print(f"  Referential integrity check failed: {e}")
    
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ VERIFICATION PASSED")
    else:
        print("⚠️ VERIFICATION COMPLETED WITH WARNINGS")
    print("=" * 70)
    
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
