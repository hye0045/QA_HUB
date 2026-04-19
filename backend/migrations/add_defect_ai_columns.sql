-- Migration: Thêm các cột AI cho bảng Defect
-- Chạy trên database QA_HUB

ALTER TABLE defect ADD COLUMN IF NOT EXISTS cleaned_description VARCHAR;
ALTER TABLE defect ADD COLUMN IF NOT EXISTS bug_category VARCHAR;
ALTER TABLE defect ADD COLUMN IF NOT EXISTS root_cause_guess VARCHAR;
ALTER TABLE defect ADD COLUMN IF NOT EXISTS module VARCHAR;

SELECT 'Migration applied successfully: AI Columns added to Defect' AS result;
