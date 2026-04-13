-- Đảm bảo extension pgcrypto được bật để tạo mật khẩu mã hóa (Supabase mặc định đã bật)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ==============================================================================
-- 1. TẠO DỮ LIỆU NGƯỜI DÙNG VÀO BẢNG auth.users (Tất cả mật khẩu là: password123)
-- ==============================================================================
INSERT INTO auth.users (
  id,
  instance_id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  raw_app_meta_data,
  raw_user_meta_data,
  created_at,
  updated_at
)
VALUES
  -- 1. Admin
  (
    '11111111-1111-1111-1111-111111111111', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 
    'admin@thundersoft.com', crypt('password123', gen_salt('bf')), current_timestamp, 
    '{"provider":"email","providers":["email"]}', '{"full_name":"Nguyen Admin"}', current_timestamp, current_timestamp
  ),
  -- 2. QA Lead
  (
    '22222222-2222-2222-2222-222222222222', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 
    'qalead@thundersoft.com', crypt('password123', gen_salt('bf')), current_timestamp, 
    '{"provider":"email","providers":["email"]}', '{"full_name":"Tran QA Lead"}', current_timestamp, current_timestamp
  ),
  -- 3. Tester (kiêm Mentor)
  (
    '33333333-3333-3333-3333-333333333333', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 
    'tester.mentor@thundersoft.com', crypt('password123', gen_salt('bf')), current_timestamp, 
    '{"provider":"email","providers":["email"]}', '{"full_name":"Le Tester (Mentor)"}', current_timestamp, current_timestamp
  ),
  -- 4. Tester (Bình thường)
  (
    '44444444-4444-4444-4444-444444444444', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 
    'tester@thundersoft.com', crypt('password123', gen_salt('bf')), current_timestamp, 
    '{"provider":"email","providers":["email"]}', '{"full_name":"Pham Tester"}', current_timestamp, current_timestamp
  ),
  -- 5. Intern
  (
    '55555555-5555-5555-5555-555555555555', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 
    'intern@thundersoft.com', crypt('password123', gen_salt('bf')), current_timestamp, 
    '{"provider":"email","providers":["email"]}', '{"full_name":"Hoang Intern"}', current_timestamp, current_timestamp
  );


-- ==============================================================================
-- 2. ĐỒNG BỘ THÔNG TIN VÀ PHÂN QUYỀN VÀO BẢNG public.users CỦA CHÚNG TA
-- ==============================================================================
INSERT INTO public.users (id, role, is_mentor, email, full_name)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'admin', false, 'admin@thundersoft.com', 'Nguyen Admin'),
  ('22222222-2222-2222-2222-222222222222', 'qa_lead', false, 'qalead@thundersoft.com', 'Tran QA Lead'),
  ('33333333-3333-3333-3333-333333333333', 'tester', true, 'tester.mentor@thundersoft.com', 'Le Tester (Mentor)'),
  ('44444444-4444-4444-4444-444444444444', 'tester', false, 'tester@thundersoft.com', 'Pham Tester'),
  ('55555555-5555-5555-5555-555555555555', 'intern', false, 'intern@thundersoft.com', 'Hoang Intern');


-- ==============================================================================
-- 3. TẠO DỮ LIỆU ĐỂ TEST: TESTCASE & SPECIFICATION
-- ==============================================================================

-- 3.1. Tạo một Specification giả lập
INSERT INTO public.specification (id, title, language, created_by)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Login Flow Specification', 'EN', '22222222-2222-2222-2222-222222222222');

INSERT INTO public.spec_version (specification_id, version_number, content, created_by)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 1, 'The user must be able to log in using email and password. Password must be hashed.', '22222222-2222-2222-2222-222222222222');

-- 3.2. Tạo Testcases giả lập
INSERT INTO public.testcase (id, title, description, steps, expected_result, created_by)
VALUES
  (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 
    'Verify successful login', 
    'Test with valid credentials', 
    '1. Open Login page. 2. Enter admin@thundersoft.com. 3. Enter password123. 4. Click Login.', 
    'User is redirected to Dashboard.', 
    '33333333-3333-3333-3333-333333333333'
  ),
  (
    'cccccccc-cccc-cccc-cccc-cccccccccccc', 
    'Verify failed login', 
    'Test with invalid credentials', 
    '1. Open Login page. 2. Enter wrong@email.com. 3. Enter password123. 4. Click Login.', 
    'Error message is displayed.', 
    '44444444-4444-4444-4444-444444444444'
  );

-- Link Testcase với Spec
INSERT INTO public.testcase_spec_link (testcase_id, specification_id)
VALUES
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
  ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');

-- 3.3. Tạo Defect giả lập (Từ Redmine)
INSERT INTO public.defect (redmine_id, title, status, severity, model_id)
VALUES
  (1001, 'Login button overlapping on mobile', 'open', 'high', 'Galaxy_S23'),
  (1002, 'API timeout on Spec Sync', 'in_progress', 'critical', 'Backend_Core'),
  (1003, 'Typo in translation JA', 'closed', 'low', 'Frontend_UI');

-- ==============================================================================
-- THE END
-- ==============================================================================
