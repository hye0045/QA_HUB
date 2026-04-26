-- ════════════════════════════════════════════════════
-- Bước 1: Thêm feature_name vào Specification
-- ════════════════════════════════════════════════════
ALTER TABLE specification
ADD COLUMN IF NOT EXISTS feature_name VARCHAR;

-- Gán giá trị mặc định cho dữ liệu cũ
UPDATE specification SET feature_name = title WHERE feature_name IS NULL;

-- ════════════════════════════════════════════════════
-- Bước 2: Bảng liên kết SpecVersion ↔ DeviceModel
-- ════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS spec_version_model_link (
    spec_version_id UUID NOT NULL REFERENCES spec_version(id) ON DELETE CASCADE,
    model_profile_id UUID NOT NULL REFERENCES device_model_profiles(id) ON DELETE CASCADE,
    PRIMARY KEY (spec_version_id, model_profile_id)
);

-- ════════════════════════════════════════════════════
-- Bước 3: Thêm embedding cho Defect (cần cho RAG)
-- ════════════════════════════════════════════════════
ALTER TABLE defect
ADD COLUMN IF NOT EXISTS embedding JSONB;

-- ════════════════════════════════════════════════════
-- Bước 4: Bảng Audit Log (hiện chưa tồn tại trong code)
-- ════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,
    entity_id UUID,
    reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Index để query nhanh theo user/entity
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
