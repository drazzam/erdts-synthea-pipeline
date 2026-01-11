# ERDTS Synthea Data Pipeline

A complete data pipeline for generating, transforming, and deploying synthetic patient data from [Synthea](https://github.com/synthetichealth/synthea)
---

## 🏗️ Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│     SYNTHEA         │     │   GITHUB ACTIONS    │     │      SUPABASE       │
│  (Data Generation)  │────▶│   (ETL Pipeline)    │────▶│    (PostgreSQL)     │
│                     │     │                     │     │                     │
│  • 1,345 patients   │     │  • Transform        │     │  • patients         │
│  • Conditions       │     │  • Validate         │     │  • patient_*        │
│  • Medications      │     │  • Push to DB       │     │  • RLS enabled      │
│  • Labs             │     │                     │     │                     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                                   │
                                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOVABLE (Frontend)                             │
│                                                                             │
│  Static Data (Client-Side):          Dynamic Data (Supabase Queries):       │
│  • condition_codes.json (260)        • patients (1,345)                     │
│  • medication_codes.json (256)       • patient_conditions (70,630)          │
│  • lab_codes.json (276)              • patient_medications (96,819)         │
│                                      • patient_labs (50,000)                │
│                                                                             │
│  Zero API calls for searches!        Only on "Run Query" execution          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Current Data Inventory

| Category | File | Records | Size | Destination |
|----------|------|---------|------|-------------|
| **Static** | `condition_codes.json` | 260 | 41 KB | Lovable `src/data/` |
| **Static** | `medication_codes.json` | 256 | 45 KB | Lovable `src/data/` |
| **Static** | `lab_codes.json` | 276 | 48 KB | Lovable `src/data/` |
| **Dynamic** | `patients.json` | 1,345 | 465 KB | Supabase |
| **Dynamic** | `patient_conditions.json` | 70,630 | 11 MB | Supabase |
| **Dynamic** | `patient_medications.json` | 96,819 | 16 MB | Supabase |
| **Dynamic** | `patient_labs.json` | 50,000 | 8 MB | Supabase |

**Total: 219,586 records**

---

## 🚀 Quick Start

### Option 1: Use Pre-Generated Data

The repository already contains generated data. Simply:

1. **Copy static files to Lovable:**
   ```bash
   # Copy to your Lovable project
   cp data/static/*.json /path/to/lovable-project/src/data/
   ```

2. **Import to Supabase:**
   ```bash
   # Set environment variables
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_SERVICE_KEY="your-service-role-key"
   
   # Run schema first
   # (Copy sql/schema.sql to Supabase SQL Editor and run)
   
   # Then import data
   python scripts/import_to_supabase.py
   ```

### Option 2: Regenerate from Synthea

1. **Generate Synthea data locally:**
   ```bash
   git clone https://github.com/synthetichealth/synthea.git
   cd synthea
   ./run_synthea -p 2000 --exporter.csv.export=true
   ```

2. **Copy CSVs to this repo:**
   ```bash
   cp synthea/output/csv/*.csv data/raw/
   ```

3. **Run ETL pipeline:**
   ```bash
   pip install -r requirements.txt
   python etl/transform.py --input-dir data/raw --output-dir data
   ```

### Option 3: Use GitHub Actions

1. Add secrets to your repository:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`

2. Trigger the workflow manually or push to `main` branch.

---

## 📁 Repository Structure

```
erdts-synthea-pipeline/
├── .github/
│   └── workflows/
│       └── sync-to-supabase.yml    # Automated ETL + Supabase sync
├── data/
│   ├── raw/                        # Synthea CSV files (Git LFS)
│   │   ├── patients.csv
│   │   ├── conditions.csv
│   │   ├── medications.csv
│   │   └── observations.csv
│   ├── static/                     # For Lovable (client-side)
│   │   ├── condition_codes.json
│   │   ├── medication_codes.json
│   │   └── lab_codes.json
│   └── supabase/                   # For Supabase import
│       ├── patients.json
│       ├── patient_conditions.json
│       ├── patient_medications.json
│       └── patient_labs.json
├── etl/
│   ├── __init__.py
│   ├── transform.py                # Main ETL orchestrator
│   ├── loaders.py                  # CSV loading utilities
│   ├── mappers.py                  # Synthea → ERDTS schema mapping
│   ├── extractors.py               # Extract unique codes
│   └── validators.py               # Data validation
├── sql/
│   ├── schema.sql                  # Supabase table definitions
│   ├── indexes.sql                 # Performance indexes
│   └── seed_sample.sql             # Sample data for testing
├── scripts/
│   ├── import_to_supabase.py       # Import JSON to Supabase
│   ├── validate_data.py            # Validate generated files
│   └── generate_stats.py           # Generate data statistics
├── docs/
│   ├── LOVABLE_INTEGRATION.md      # How to integrate with Lovable
│   ├── SUPABASE_SETUP.md           # Supabase configuration guide
│   └── DATA_DICTIONARY.md          # Field definitions
├── .gitignore
├── .gitattributes                  # Git LFS configuration
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes (for import) |
| `SUPABASE_SERVICE_KEY` | Service role key (not anon key) | Yes (for import) |
| `PATIENT_LIMIT` | Max patients to process | No (default: 2000) |
| `LAB_LIMIT` | Max lab records to process | No (default: 50000) |

### GitHub Secrets (for Actions)

Add these in **Settings → Secrets and variables → Actions**:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

---

## 📈 Data Quality

### Condition Categories (260 codes)
| Category | Count |
|----------|-------|
| Other | 85 |
| Social/Administrative | 58 |
| Musculoskeletal | 23 |
| Respiratory | 15 |
| Endocrine | 13 |
| Genitourinary | 12 |
| Cardiovascular | 11 |
| Oncology | 10 |
| Pregnancy | 8 |
| Nervous System | 7 |
| Infectious | 7 |
| Mental Health | 4 |
| Skin | 3 |
| Blood/Immune | 2 |
| Digestive | 2 |

### Medication Classes (256 codes)
| Drug Class | Count |
|------------|-------|
| Other | 117 |
| Analgesic/NSAID | 16 |
| Contraceptive | 16 |
| Antibiotic | 15 |
| Beta Blocker | 14 |
| Statin | 13 |
| Respiratory | 13 |
| ACE Inhibitor | 9 |
| Opioid | 8 |
| Anticoagulant | 7 |
| And more... | ... |

### Lab Categories (276 codes)
| Category | Count |
|----------|-------|
| Other | 125 |
| Liver Function | 33 |
| Hematology | 28 |
| Vital Signs | 17 |
| Urinalysis | 17 |
| Allergy | 15 |
| Electrolytes | 13 |
| Tumor Markers | 8 |
| And more... | ... |

### Patient Demographics
- **Total**: 1,345 patients
- **Male**: 704 (52.3%)
- **Female**: 641 (47.7%)
- **Deceased**: 183 (13.6%)
- **Race Distribution**: White 82%, Black 9%, Asian 7%, Other 2%

---

## 🔄 GitHub Actions Workflow

The workflow automatically:

1. ✅ Validates existing data files
2. ✅ Runs ETL transformation (if raw data changed)
3. ✅ Pushes to Supabase (with batching)
4. ✅ Generates statistics report

**Triggers:**
- Manual dispatch (with patient count option)
- Push to `main` branch (if `data/raw/` changed)

---

## 🛡️ Security

- **Synthetic Data Only**: All patient data is artificially generated by Synthea. No real patient information is included.
- **Service Role Key**: Used only in GitHub Actions, never exposed in client code.
- **Row Level Security**: Supabase RLS policies restrict data access appropriately.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

Synthea is licensed under Apache 2.0. See [Synthea License](https://github.com/synthetichealth/synthea/blob/master/LICENSE).

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run validation: `python scripts/validate_data.py`
5. Submit a pull request

---

## 📞 Support

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions

---

*Generated with Synthea Synthetic Patient Generator*
