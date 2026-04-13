-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create Enums
CREATE TYPE user_role AS ENUM ('intern', 'tester', 'qa_lead', 'admin');
CREATE TYPE doc_status AS ENUM ('draft', 'mentor_reviewed', 'approved', 'locked');
CREATE TYPE intern_status AS ENUM ('in_progress', 'ready');
CREATE TYPE chat_mode AS ENUM ('qa', 'translate', 'suggest');

-- 1. Users Table (Extending Supabase auth.users)
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role user_role NOT NULL DEFAULT 'intern',
    is_mentor BOOLEAN NOT NULL DEFAULT FALSE,
    email TEXT UNIQUE,
    full_name TEXT,
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
    embedding vector(1536), -- 1536 for OpenAI / 1024 or 768 for other models depending on AI service
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
    embedding vector(1536),
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

-- ==========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==========================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.delegation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.specification ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spec_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.testcase ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.testcase_spec_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.defect ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.defect_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.delivery_document ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.delivery_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intern_training ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.access_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;


-- Utility wrapper for auth user id
CREATE OR REPLACE FUNCTION public.current_user_id()
RETURNS UUID AS $$
  SELECT auth.uid()
$$ LANGUAGE sql STABLE;


-- 1. Users RLS
-- Users can view their own profile. Admins and QA Leads can view all.
CREATE POLICY "Users can view all users" ON public.users FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON public.users FOR UPDATE USING (id = current_user_id());

-- 2. DeliveryDocument RLS
-- Admins/QA Leads can do anything.
CREATE POLICY "Admins and Leads see all delivery docs" ON public.delivery_document
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.users u WHERE u.id = current_user_id() AND u.role IN ('admin', 'qa_lead')
        )
    );

-- Mentors see docs where they are assigned.
CREATE POLICY "Mentors can see assigned delivery docs" ON public.delivery_document
    FOR SELECT
    USING (mentor_id = current_user_id());

-- Creators (Interns/Testers) can view and edit their own docs UNLESS it is locked.
CREATE POLICY "Creators can view their unlocked docs" ON public.delivery_document
    FOR SELECT
    USING (created_by = current_user_id());

-- We will handle document lock updates and strict state machine via FastAPI Backend logic.
-- So we allow basic access here but backend enforces strict transitions and locks.

-- 3. Specifications & Testcases
-- Generally readable by authenticated users in the intranet.
CREATE POLICY "All authenticated users can view specs" ON public.specification FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY "All authenticated users can view testcases" ON public.testcase FOR SELECT USING (auth.uid() IS NOT NULL);

-- Inserts/Updates to Specs/Testcases are restricted by Backend mostly, but we can set up basic RLS
CREATE POLICY "Testers, Leads, Admins can create/edit testcases" ON public.testcase
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.users u WHERE u.id = current_user_id() AND u.role IN ('tester', 'qa_lead', 'admin')
        )
    );

-- 4. Chat History
-- Users can only see their own chat history.
CREATE POLICY "Users view own chat history" ON public.chat_history FOR SELECT USING (user_id = current_user_id());
CREATE POLICY "Users create own chat history" ON public.chat_history FOR INSERT WITH CHECK (user_id = current_user_id());

-- Note: In a real Supabase environment with FastAPI, the FastAPI Service Role Key bypasses RLS,
-- OR FastAPI issues JWTs representing the user, and the RLS works smoothly.
-- For QA HUB, we enforce rate limiting and business logic on FastAPI side using a Service Role client to read/write,
-- and potentially evaluate policies via auth middlewares.
