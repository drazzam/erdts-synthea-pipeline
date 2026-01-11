# Lovable Integration Guide

This guide explains how to integrate the ERDTS Synthea data into your Lovable project.

---

## Overview

The ERDTS data pipeline generates two types of files:

| Type | Location | Purpose | Supabase Queries |
|------|----------|---------|------------------|
| **Static** | `data/static/` | Client-side reference data | Zero |
| **Dynamic** | `data/supabase/` | Database records | On demand |

This hybrid approach **reduces Supabase load by ~91%** by keeping frequently-searched reference data on the client.

---

## Step 1: Copy Static Files to Lovable

Copy the static JSON files to your Lovable project's `src/data/` directory:

```bash
# Create the data directory if it doesn't exist
mkdir -p /path/to/lovable-project/src/data

# Copy files
cp data/static/condition_codes.json /path/to/lovable-project/src/data/
cp data/static/medication_codes.json /path/to/lovable-project/src/data/
cp data/static/lab_codes.json /path/to/lovable-project/src/data/
```

Your Lovable project structure should look like:

```
src/
├── data/
│   ├── condition_codes.json    # 260 conditions
│   ├── medication_codes.json   # 256 medications
│   └── lab_codes.json          # 276 labs
├── components/
├── hooks/
└── ...
```

---

## Step 2: Create the Reference Data Hook

Create a new file at `src/hooks/useReferenceData.ts`:

```typescript
import { useMemo, useCallback } from 'react';
import conditionCodes from '@/data/condition_codes.json';
import medicationCodes from '@/data/medication_codes.json';
import labCodes from '@/data/lab_codes.json';

// Type definitions
export interface ConditionCode {
  code: string;
  name: string;
  snomedCode: string;
  category: string;
  prevalence: number;
}

export interface MedicationCode {
  code: string;
  name: string;
  genericName: string;
  drugClass: string;
  rxnorm: string;
}

export interface LabCode {
  code: string;
  name: string;
  loincCode: string;
  category: string;
  unit: string;
  normalLow?: number;
  normalHigh?: number;
  criticalLow?: number;
  criticalHigh?: number;
}

// Type assertions
const conditions = conditionCodes as ConditionCode[];
const medications = medicationCodes as MedicationCode[];
const labs = labCodes as LabCode[];

export function useReferenceData() {
  // Memoized search functions - zero API calls!
  
  const searchConditions = useCallback((term: string, limit: number = 20): ConditionCode[] => {
    if (!term || term.length < 2) return [];
    
    const lower = term.toLowerCase();
    return conditions
      .filter(c => 
        c.name.toLowerCase().includes(lower) ||
        c.code.includes(term) ||
        c.snomedCode.includes(term) ||
        c.category.toLowerCase().includes(lower)
      )
      .slice(0, limit);
  }, []);

  const searchMedications = useCallback((term: string, limit: number = 20): MedicationCode[] => {
    if (!term || term.length < 2) return [];
    
    const lower = term.toLowerCase();
    return medications
      .filter(m =>
        m.name.toLowerCase().includes(lower) ||
        m.genericName.toLowerCase().includes(lower) ||
        m.drugClass.toLowerCase().includes(lower) ||
        m.code.includes(term)
      )
      .slice(0, limit);
  }, []);

  const searchLabs = useCallback((term: string, limit: number = 20): LabCode[] => {
    if (!term || term.length < 2) return [];
    
    const lower = term.toLowerCase();
    return labs
      .filter(l =>
        l.name.toLowerCase().includes(lower) ||
        l.code.includes(term) ||
        l.category.toLowerCase().includes(lower)
      )
      .slice(0, limit);
  }, []);

  // Get by code (for displaying selected items)
  const getConditionByCode = useCallback((code: string): ConditionCode | undefined => {
    return conditions.find(c => c.code === code);
  }, []);

  const getMedicationByCode = useCallback((code: string): MedicationCode | undefined => {
    return medications.find(m => m.code === code);
  }, []);

  const getLabByCode = useCallback((code: string): LabCode | undefined => {
    return labs.find(l => l.code === code);
  }, []);

  // Get all by category
  const getConditionsByCategory = useCallback((category: string): ConditionCode[] => {
    return conditions.filter(c => c.category === category);
  }, []);

  const getMedicationsByClass = useCallback((drugClass: string): MedicationCode[] => {
    return medications.filter(m => m.drugClass === drugClass);
  }, []);

  const getLabsByCategory = useCallback((category: string): LabCode[] => {
    return labs.filter(l => l.category === category);
  }, []);

  // Category lists for dropdowns
  const conditionCategories = useMemo(() => {
    const cats = new Set(conditions.map(c => c.category));
    return Array.from(cats).sort();
  }, []);

  const medicationClasses = useMemo(() => {
    const classes = new Set(medications.map(m => m.drugClass));
    return Array.from(classes).sort();
  }, []);

  const labCategories = useMemo(() => {
    const cats = new Set(labs.map(l => l.category));
    return Array.from(cats).sort();
  }, []);

  return {
    // Data
    conditions,
    medications,
    labs,
    
    // Search functions
    searchConditions,
    searchMedications,
    searchLabs,
    
    // Lookup functions
    getConditionByCode,
    getMedicationByCode,
    getLabByCode,
    
    // Category functions
    getConditionsByCategory,
    getMedicationsByClass,
    getLabsByCategory,
    
    // Category lists
    conditionCategories,
    medicationClasses,
    labCategories,
    
    // Counts
    counts: {
      conditions: conditions.length,
      medications: medications.length,
      labs: labs.length,
    }
  };
}
```

---

## Step 3: Use in Components

### Example: Condition Search Dialog

```tsx
import { useState, useMemo } from 'react';
import { useReferenceData } from '@/hooks/useReferenceData';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface ConditionSearchProps {
  open: boolean;
  onClose: () => void;
  onSelect: (code: string, name: string) => void;
}

export function ConditionSearch({ open, onClose, onSelect }: ConditionSearchProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const { searchConditions } = useReferenceData();
  
  // Client-side search - zero API calls!
  const results = useMemo(() => {
    return searchConditions(searchTerm);
  }, [searchTerm, searchConditions]);
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Search Conditions</DialogTitle>
        </DialogHeader>
        
        <Input
          placeholder="Search by name, code, or category..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          autoFocus
        />
        
        <div className="max-h-64 overflow-y-auto mt-4">
          {results.length === 0 && searchTerm.length >= 2 && (
            <p className="text-muted-foreground text-sm">No conditions found</p>
          )}
          
          {results.map((condition) => (
            <button
              key={condition.code}
              className="w-full text-left p-2 hover:bg-muted rounded"
              onClick={() => {
                onSelect(condition.code, condition.name);
                onClose();
              }}
            >
              <div className="font-medium">{condition.name}</div>
              <div className="text-sm text-muted-foreground">
                {condition.code} • {condition.category}
              </div>
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## Step 4: Configure Supabase Queries

For patient queries (when "Run Query" is clicked), use Supabase:

```typescript
import { supabase } from '@/lib/supabase';

interface CohortQuery {
  inclusionConditions: string[];
  inclusionMedications: string[];
  exclusionConditions: string[];
  ageMin?: number;
  ageMax?: number;
  sex?: 'male' | 'female' | 'any';
}

export async function runCohortQuery(query: CohortQuery) {
  let supabaseQuery = supabase
    .from('patients')
    .select(`
      id,
      synthetic_id,
      birth_date,
      sex,
      race,
      ethnicity,
      deceased
    `);
  
  // Apply sex filter
  if (query.sex && query.sex !== 'any') {
    supabaseQuery = supabaseQuery.eq('sex', query.sex);
  }
  
  // Get patient IDs matching inclusion conditions
  if (query.inclusionConditions.length > 0) {
    const { data: conditionPatients } = await supabase
      .from('patient_conditions')
      .select('patient_synthetic_id')
      .in('condition_code', query.inclusionConditions);
    
    const patientIds = [...new Set(conditionPatients?.map(p => p.patient_synthetic_id) || [])];
    supabaseQuery = supabaseQuery.in('synthetic_id', patientIds);
  }
  
  // Get patient IDs matching inclusion medications
  if (query.inclusionMedications.length > 0) {
    const { data: medPatients } = await supabase
      .from('patient_medications')
      .select('patient_synthetic_id')
      .in('medication_code', query.inclusionMedications);
    
    const patientIds = [...new Set(medPatients?.map(p => p.patient_synthetic_id) || [])];
    supabaseQuery = supabaseQuery.in('synthetic_id', patientIds);
  }
  
  // Execute query
  const { data, error, count } = await supabaseQuery
    .limit(100)
    .order('synthetic_id');
  
  return { data, error, count };
}
```

---

## Data Flow Summary

```
User types "diabetes" in search
         │
         ▼
┌─────────────────────────────┐
│   useReferenceData hook     │
│   (client-side filtering)   │
│   - Zero API calls          │
│   - Instant results         │
│   - 260 conditions cached   │
└─────────────────────────────┘
         │
         ▼
User sees matching conditions
User selects "Type 2 diabetes"
         │
         ▼
User clicks "Run Query"
         │
         ▼
┌─────────────────────────────┐
│   Supabase Query            │
│   - Joins patient tables    │
│   - Applies all filters     │
│   - Returns matching IDs    │
└─────────────────────────────┘
         │
         ▼
Results displayed in table
```

---

## Troubleshooting

### JSON import errors in TypeScript

If you get import errors, add to `tsconfig.json`:

```json
{
  "compilerOptions": {
    "resolveJsonModule": true,
    "esModuleInterop": true
  }
}
```

### Large bundle size

The static JSON files are ~135KB total (gzipped: ~25KB). This is acceptable for the performance benefits.

If needed, implement code splitting:

```typescript
const conditionCodes = await import('@/data/condition_codes.json');
```

### Supabase RLS errors

Ensure RLS policies are set up correctly. Run the `sql/schema.sql` file in Supabase SQL Editor.

---

## Performance Comparison

| Action | Without Static Data | With Static Data | Improvement |
|--------|---------------------|------------------|-------------|
| Condition search (10 keystrokes) | 10 API calls | 0 API calls | **100%** |
| Medication search (10 keystrokes) | 10 API calls | 0 API calls | **100%** |
| Run cohort query | 3 API calls | 3 API calls | Same |
| **Per session (typical)** | **~35 API calls** | **~3 API calls** | **~91%** |

---

## Next Steps

1. Import data to Supabase (see `scripts/import_to_supabase.py`)
2. Connect CohortForge to use `useReferenceData` hook
3. Build additional modules using the same pattern
