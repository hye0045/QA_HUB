import React, { useState, useEffect } from 'react';
import api, { DeviceModelProfile } from '../lib/api';

const TestCaseUpload: React.FC = () => {
    const [profiles, setProfiles] = useState<DeviceModelProfile[]>([]);
    const [selectedModelId, setSelectedModelId] = useState<string>('');
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{ message: string, created: number, skipped: number } | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchProfiles = async () => {
            try {
                const res = await api.get('/defects/profiles');
                setProfiles(res.data);
                if (res.data.length > 0) {
                    setSelectedModelId(res.data[0].id);
                }
            } catch (err) {
                console.error("Failed to load profiles", err);
            }
        };
        fetchProfiles();
    }, []);

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) {
            setError("Vui lòng chọn file Excel để upload.");
            return;
        }
        if (!selectedModelId) {
            setError("Vui lòng chọn Model.");
            return;
        }

        setLoading(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.post(`/testcases/upload?model_id=${selectedModelId}`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            setResult(res.data);
            setFile(null); // Reset
            // Reset input file
            const fileInput = document.getElementById('tc-file-upload') as HTMLInputElement;
            if (fileInput) fileInput.value = '';
        } catch (err: any) {
            setError(err.response?.data?.detail || "Đã xảy ra lỗi khi upload.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '1rem' }}>
            <h2>Upload Testcase Excel vào Database</h2>
            <p style={{ color: '#7f8c8d', marginBottom: '2rem' }}>
                Tính năng này cho phép bạn import file Excel chứa các testcase có sẵn vào database để sử dụng như Base Model cho AI Generator.
            </p>

            <form onSubmit={handleUpload} style={{ background: 'white', padding: '2rem', borderRadius: '8px', maxWidth: '600px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                {error && (
                    <div style={{ background: '#f8d7da', color: '#721c24', padding: '10px', borderRadius: '4px', marginBottom: '1rem' }}>
                        ❌ {error}
                    </div>
                )}
                
                {result && (
                    <div style={{ background: '#d4edda', color: '#155724', padding: '10px', borderRadius: '4px', marginBottom: '1rem' }}>
                        ✅ {result.message} (Tạo mới: {result.created}, Bỏ qua: {result.skipped})
                    </div>
                )}

                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Chọn Dòng Máy (Model Profile):</label>
                    <select 
                        value={selectedModelId} 
                        onChange={(e) => setSelectedModelId(e.target.value)}
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #bdc3c7' }}
                        required
                    >
                        <option value="" disabled>-- Chọn dòng máy --</option>
                        {profiles.map(p => (
                            <option key={p.id} value={p.id}>{p.name} (Dự án: {p.project_id})</option>
                        ))}
                    </select>
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>File Excel Testcase (.xlsx, .xls):</label>
                    <input 
                        id="tc-file-upload"
                        type="file" 
                        accept=".xlsx, .xls"
                        onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                        style={{ width: '100%', padding: '0.5rem', border: '1px solid #bdc3c7', borderRadius: '4px' }}
                        required
                    />
                    <small style={{ color: '#7f8c8d', display: 'block', marginTop: '0.5rem' }}>
                        * Bắt buộc có cột 'title' ở dòng đầu tiên. Các cột tuỳ chọn: description, steps, expected_result, test_type, precondition.
                    </small>
                </div>

                <button 
                    type="submit" 
                    disabled={loading || !file || !selectedModelId}
                    style={{
                        background: loading ? '#95a5a6' : '#2980b9',
                        color: 'white',
                        padding: '0.75rem 1.5rem',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold',
                        width: '100%'
                    }}
                >
                    {loading ? 'Đang xử lý & Sinh Embedding...' : 'Tải lên & Lưu Database'}
                </button>
            </form>
        </div>
    );
};

export default TestCaseUpload;
