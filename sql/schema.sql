-- ============================================================================
-- ERDTS DATABASE SCHEMA FOR SUPABASE
-- 
-- Run this SQL in Supabase SQL Editor BEFORE importing JSON data.
-- This creates all necessary tables, indexes, RLS policies, and triggers.
--
-- Generated: January 2026
-- Version: 1.0.0
-- ============================================================================


-- ============================================================================
-- CLEANUP (Optional - use if you need to reset)
-- ============================================================================
-- DROP TABLE IF EXISTS patient_labs CASCADE;
-- DROP TABLE IF EXISTS patient_medications CASCADE;
-- DROP TABLE IF EXISTS patient_conditions CASCADE;
-- DROP TABLE IF EXISTS patients CASCADE;
-- DROP TABLE IF EXISTS training_progress CASCADE;
-- DROP TABLE IF EXISTS saved_queries CASCADE;
-- DROP TABLE IF EXISTS profiles CASCADE;


-- ============================================================================
-- CORE PATIENT TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    synthetic_id TEXT UNIQUE NOT NULL,      -- Format: SYN-00001
    birth_date DATE NOT NULL,
    sex TEXT NOT NULL CHECK (sex IN ('male', 'female')),
    race TEXT,
    ethnicity TEXT,
    marital_status TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    deceased BOOLEAN DEFAULT FALSE,
    deceased_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE patients IS 'Synthetic patient demographics from Synthea';
COMMENT ON COLUMN patients.synthetic_id IS 'Unique identifier in SYN-XXXXX format';


-- ============================================================================
-- PATIENT-CONDITION RELATIONSHIPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS patient_conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_synthetic_id TEXT NOT NULL,
    condition_code TEXT NOT NULL,           -- SNOMED code from condition_codes.json
    onset_date DATE,
    resolution_date DATE,                   -- NULL if ongoing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_patient_conditions_patient 
        FOREIGN KEY (patient_synthetic_id) 
        REFERENCES patients(synthetic_id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE patient_conditions IS 'Patient diagnoses/conditions from Synthea';
COMMENT ON COLUMN patient_conditions.condition_code IS 'References static condition_codes.json';


-- ============================================================================
-- PATIENT-MEDICATION RELATIONSHIPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS patient_medications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_synthetic_id TEXT NOT NULL,
    medication_code TEXT NOT NULL,          -- RxNorm code from medication_codes.json
    start_date DATE,
    end_date DATE,                          -- NULL if ongoing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_patient_medications_patient 
        FOREIGN KEY (patient_synthetic_id) 
        REFERENCES patients(synthetic_id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE patient_medications IS 'Patient prescriptions from Synthea';
COMMENT ON COLUMN patient_medications.medication_code IS 'References static medication_codes.json';


-- ============================================================================
-- PATIENT-LAB RESULTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS patient_labs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_synthetic_id TEXT NOT NULL,
    lab_code TEXT NOT NULL,                 -- LOINC code from lab_codes.json
    result_date TIMESTAMPTZ,
    value_numeric NUMERIC,                  -- For numeric results
    value_text TEXT,                        -- For text/coded results
    unit TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT fk_patient_labs_patient 
        FOREIGN KEY (patient_synthetic_id) 
        REFERENCES patients(synthetic_id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE patient_labs IS 'Patient lab/observation results from Synthea';
COMMENT ON COLUMN patient_labs.lab_code IS 'References static lab_codes.json';


-- ============================================================================
-- USER PROFILE TABLE (extends auth.users)
-- ============================================================================

CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    institution TEXT,
    role TEXT DEFAULT 'trainee' CHECK (role IN ('trainee', 'instructor', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE profiles IS 'User profiles extending Supabase auth';


-- ============================================================================
-- SAVED QUERIES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS saved_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    query_json JSONB NOT NULL,              -- Stores cohort criteria
    result_count INTEGER,                   -- Cached result count
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE saved_queries IS 'User-saved cohort queries';


-- ============================================================================
-- TRAINING PROGRESS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS training_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,              -- e.g., 'cohort-forge', 'burden-scope'
    lesson_id TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, module_name, lesson_id)
);

COMMENT ON TABLE training_progress IS 'User training module progress';


-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Patient table indexes
CREATE INDEX IF NOT EXISTS idx_patients_synthetic_id ON patients(synthetic_id);
CREATE INDEX IF NOT EXISTS idx_patients_sex ON patients(sex);
CREATE INDEX IF NOT EXISTS idx_patients_deceased ON patients(deceased);
CREATE INDEX IF NOT EXISTS idx_patients_birth_date ON patients(birth_date);
CREATE INDEX IF NOT EXISTS idx_patients_race ON patients(race);

-- Patient conditions indexes
CREATE INDEX IF NOT EXISTS idx_pc_patient ON patient_conditions(patient_synthetic_id);
CREATE INDEX IF NOT EXISTS idx_pc_code ON patient_conditions(condition_code);
CREATE INDEX IF NOT EXISTS idx_pc_onset ON patient_conditions(onset_date);
CREATE INDEX IF NOT EXISTS idx_pc_patient_code ON patient_conditions(patient_synthetic_id, condition_code);

-- Patient medications indexes
CREATE INDEX IF NOT EXISTS idx_pm_patient ON patient_medications(patient_synthetic_id);
CREATE INDEX IF NOT EXISTS idx_pm_code ON patient_medications(medication_code);
CREATE INDEX IF NOT EXISTS idx_pm_start ON patient_medications(start_date);
CREATE INDEX IF NOT EXISTS idx_pm_patient_code ON patient_medications(patient_synthetic_id, medication_code);

-- Patient labs indexes
CREATE INDEX IF NOT EXISTS idx_pl_patient ON patient_labs(patient_synthetic_id);
CREATE INDEX IF NOT EXISTS idx_pl_code ON patient_labs(lab_code);
CREATE INDEX IF NOT EXISTS idx_pl_date ON patient_labs(result_date);
CREATE INDEX IF NOT EXISTS idx_pl_patient_code ON patient_labs(patient_synthetic_id, lab_code);

-- User data indexes
CREATE INDEX IF NOT EXISTS idx_saved_queries_user ON saved_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_training_progress_user ON training_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_training_progress_module ON training_progress(module_name);


-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_conditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_medications ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_labs ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_progress ENABLE ROW LEVEL SECURITY;

-- Patient data: Public read access for all authenticated users (training data)
CREATE POLICY "patients_read_authenticated" ON patients
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "patient_conditions_read_authenticated" ON patient_conditions
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "patient_medications_read_authenticated" ON patient_medications
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "patient_labs_read_authenticated" ON patient_labs
    FOR SELECT TO authenticated USING (true);

-- Profiles: Users can only access their own profile
CREATE POLICY "profiles_select_own" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "profiles_update_own" ON profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "profiles_insert_own" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Saved queries: Users can only access their own queries
CREATE POLICY "saved_queries_all_own" ON saved_queries
    FOR ALL USING (auth.uid() = user_id);

-- Training progress: Users can only access their own progress
CREATE POLICY "training_progress_all_own" ON training_progress
    FOR ALL USING (auth.uid() = user_id);


-- ============================================================================
-- AUTO-CREATE PROFILE ON SIGNUP
-- ============================================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name)
    VALUES (
        new.id,
        COALESCE(new.raw_user_meta_data->>'full_name', '')
    );
    RETURN new;
END;
$$;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();


-- ============================================================================
-- HELPER FUNCTIONS (Optional)
-- ============================================================================

-- Function to calculate age from birth_date
CREATE OR REPLACE FUNCTION calculate_age(birth_date DATE)
RETURNS INTEGER
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT EXTRACT(YEAR FROM age(CURRENT_DATE, birth_date))::INTEGER;
$$;

-- Function to get patient count by condition
CREATE OR REPLACE FUNCTION get_patients_with_condition(condition_code_param TEXT)
RETURNS TABLE(patient_count BIGINT)
LANGUAGE sql
STABLE
AS $$
    SELECT COUNT(DISTINCT patient_synthetic_id)
    FROM patient_conditions
    WHERE condition_code = condition_code_param;
$$;


-- ============================================================================
-- VERIFICATION QUERY (Run after import to verify data)
-- ============================================================================

-- SELECT 
--     'patients' as table_name, COUNT(*) as record_count FROM patients
-- UNION ALL SELECT 
--     'patient_conditions', COUNT(*) FROM patient_conditions
-- UNION ALL SELECT 
--     'patient_medications', COUNT(*) FROM patient_medications
-- UNION ALL SELECT 
--     'patient_labs', COUNT(*) FROM patient_labs;


-- ============================================================================
-- DONE
-- ============================================================================
