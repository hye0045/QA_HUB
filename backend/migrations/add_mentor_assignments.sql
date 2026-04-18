-- [UC_F2] Thêm bảng Mentor Assignment
CREATE TABLE IF NOT EXISTS mentor_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mentor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    intern_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- Note: Enum "UserRole" (intern, tester, qa_lead, admin) đã được tạo từ trước theo schema.
-- Câu lệnh trên đảm bảo mỗi Intern chỉ được gán tối đa 1 Mentor ở cùng thời điểm (UNIQUE intern_id).
