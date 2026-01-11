# Synthea Raw Data Directory

This directory is for Synthea CSV output files.

## Files (not included - too large for git without LFS)

- patients.csv
- conditions.csv
- medications.csv
- observations.csv

## How to Generate

```bash
git clone https://github.com/synthetichealth/synthea.git
cd synthea
./run_synthea -p 2000 --exporter.csv.export=true --exporter.fhir.export=false
cp output/csv/*.csv /path/to/erdts-synthea-pipeline/data/raw/
```

The ETL pipeline will transform these into ERDTS-compatible JSON.

