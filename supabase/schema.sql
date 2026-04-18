-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Tạm thời comment pgvector vì chúng ta sẽ xử lý AI nhúng ở Phase 3 bằng Local Python 
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Create Enums
CREATE TYPE user_role AS ENUM ('intern', 'tester', 'qa_lead', 'admin');
CREATE TYPE doc_status AS ENUM ('draft', 'mentor_reviewed', 'approved', 'locked');
CREATE TYPE intern_status AS ENUM ('in_progress', 'ready');
CREATE TYPE chat_mode AS ENUM ('qa', 'translate', 'suggest');

-- 1. Users Table (Independent of Supabase)
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role user_role NOT NULL DEFAULT 'intern',
    is_mentor BOOLEAN NOT NULL DEFAULT FALSE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Delegation Table (Permission Escalation)
CREATE TABLE public.delegation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    delegator_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    delegatee_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    role_escalated user_role NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Specification Table
CREATE TABLE public.specification (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    language TEXT NOT NULL, -- EN/JA
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. SpecVersion Table
CREATE TABLE public.spec_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specification_id UUID REFERENCES public.specification(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    content TEXT NOT NULL,
    embedding JSONB, -- Sử dụng JSONB để tạm lưu vector array thay vì dùng trực tiếp pgvector ở Database
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Testcase Table
CREATE TABLE public.testcase (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    steps TEXT,
    expected_result TEXT,
    is_affected BOOLEAN NOT NULL DEFAULT FALSE,
    embedding JSONB,
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. TestcaseSpecLink Table
CREATE TABLE public.testcase_spec_link (
    testcase_id UUID REFERENCES public.testcase(id) ON DELETE CASCADE,
    specification_id UUID REFERENCES public.specification(id) ON DELETE CASCADE,
    PRIMARY KEY (testcase_id, specification_id)
);

-- 7. Defect Table (Synced from Redmine)
CREATE TABLE public.defect (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    redmine_id INT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    model_id TEXT,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. DefectHistory Table
CREATE TABLE public.defect_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    defect_id UUID REFERENCES public.defect(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 9. DeliveryDocument Table
CREATE TABLE public.delivery_document (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    status doc_status NOT NULL DEFAULT 'draft',
    mentor_id UUID REFERENCES public.users(id),
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. DeliveryVersion Table
CREATE TABLE public.delivery_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    delivery_document_id UUID REFERENCES public.delivery_document(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_by UUID REFERENCES public.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 11. ChatHistory Table
CREATE TABLE public.chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    mode chat_mode NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. InternTraining Table
CREATE TABLE public.intern_training (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    intern_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    mentor_id UUID REFERENCES public.users(id),
    status intern_status NOT NULL DEFAULT 'in_progress',
    progress_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 13. AccessLog Table (For Rate Limiting / Audit)
CREATE TABLE public.access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 14. AuditLog Table (For unlocking DeliveryDocuments, etc)
CREATE TABLE public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
