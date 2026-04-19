import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import api from '../lib/api';

const SpecCreator: React.FC = () => {
    const navigate = useNavigate();
    const fileInputRef = useRef<HTMLInputElement>(null);
    
    const [title, setTitle] = useState('');
    const [language, setLanguage] = useState('vietnamese');
    const [versionNumber, setVersionNumber] = useState(1);
    const [content, setContent] = useState('');
    const [fileName, setFileName] = useState<string | null>(null);
    
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Xử lý upload file Excel (.xlsx, .xls)
    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        
        setFileName(file.name);
        setError(null);
        
        const reader = new FileReader();
        reader.onload = (evt) => {
            try {
                const bstr = evt.target?.result;
                const workbook = XLSX.read(bstr, { type: 'binary' });
                
                // Ghép tất cả sheet thành 1 đoạn text
                let fullContent = '';
                workbook.SheetNames.forEach((sheetName, idx) => {
                    const sheet = workbook.Sheets[sheetName];
                    const sheetText = XLSX.utils.sheet_to_txt(sheet);
                    fullContent += `=== Sheet ${idx + 1}: ${sheetName} ===\n${sheetText}\n\n`;
                });
                
                setContent(fullContent);
                
                // Tự động đặt title nếu chưa có
                if (!title.trim()) {
                    const baseName = file.name.replace(/\.(xlsx|xls)$/i, '');
                    setTitle(baseName);
                }
            } catch (err) {
                setError('❌ Không thể đọc file Excel. Vui lòng kiểm tra định dạng file.');
            }
        };
        reader.readAsBinaryString(file);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!title.trim() || !content.trim()) {
            setError("Title và Content là bắt buộc! Hãy nhập tay hoặc Upload file Excel.");
            return;
        }

        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const res = await api.post('/specs/sync', {
                title,
                language,
                version_number: versionNumber,
                content
            });
            
            setSuccess(`✅ Upload thành công! Spec ID: ${res.data.spec_id}`);
            
            if (res.data.spec_id) {
                setTimeout(() => navigate(`/specs/view/${res.data.spec_id}`), 1500);
            }
        } catch (err: any) {
            setError(`❌ Lỗi upload Specification: ${err.response?.data?.detail || err.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '1rem', maxWidth: '850px', margin: '0 auto' }}>
            <h2 style={{ color: '#2c3e50', borderBottom: '2px solid #3498db', paddingBottom: '0.5rem' }}>📄 Upload / Tạo mới Specification</h2>
            <p style={{ color: '#7f8c8d', marginBottom: '1.5rem' }}>
                Dành cho Tester và QA Lead. Hỗ trợ nhập tay hoặc Upload file Excel (.xlsx / .xls).
            </p>
            
            {error && <div style={{ background: '#fdecea', color: '#c0392b', padding: '1rem', borderRadius: '4px', marginBottom: '1rem', fontWeight: 'bold' }}>{error}</div>}
            {success && <div style={{ background: '#d4edda', color: '#155724', padding: '1rem', borderRadius: '4px', marginBottom: '1rem', fontWeight: 'bold' }}>{success}</div>}

            <form onSubmit={handleSubmit} style={{ background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                {/* Upload Excel Zone */}
                <div style={{ marginBottom: '1.5rem', border: '2px dashed #3498db', borderRadius: '8px', padding: '1.5rem', textAlign: 'center', background: '#f0f8ff', cursor: 'pointer' }}
                     onClick={() => fileInputRef.current?.click()}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".xlsx,.xls"
                        onChange={handleFileUpload}
                        style={{ display: 'none' }}
                    />
                    <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📁</div>
                    {fileName ? (
                        <p style={{ color: '#27ae60', fontWeight: 'bold' }}>✅ Đã chọn: {fileName}</p>
                    ) : (
                        <>
                            <p style={{ color: '#3498db', fontWeight: 'bold', margin: '0.25rem 0' }}>Bấm vào đây để Upload file Excel</p>
                            <p style={{ color: '#95a5a6', fontSize: '0.85rem', margin: 0 }}>Hỗ trợ .xlsx và .xls — Nội dung sẽ được trích xuất tự động</p>
                        </>
                    )}
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Tiêu đề Đặc tả (Title):</label>
                    <input 
                        type="text" 
                        value={title} 
                        onChange={e => setTitle(e.target.value)}
                        placeholder="Ví dụ: Module Đăng Nhập Hệ Thống"
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontSize: '1rem', boxSizing: 'border-box' }}
                    />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div>
                        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Ngôn ngữ:</label>
                        <select 
                            value={language} 
                            onChange={e => setLanguage(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontSize: '1rem' }}
                        >
                            <option value="vietnamese">Tiếng Việt</option>
                            <option value="english">English</option>
                            <option value="japanese">Japanese</option>
                        </select>
                    </div>

                    <div>
                        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Phiên bản (Version):</label>
                        <input 
                            type="number" 
                            min="1"
                            value={versionNumber} 
                            onChange={e => setVersionNumber(parseInt(e.target.value) || 1)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontSize: '1rem' }}
                        />
                    </div>
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        Nội dung Spec {fileName ? '(trích xuất từ Excel)' : '(nhập tay hoặc copy/paste)'}:
                    </label>
                    <textarea 
                        value={content}
                        onChange={e => setContent(e.target.value)}
                        placeholder="1. Giới thiệu chức năng...&#10;2. Quy trình xử lý...&#10;3. Ngoại lệ..."
                        style={{ width: '100%', height: '300px', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontFamily: 'monospace', fontSize: '0.9rem', boxSizing: 'border-box' }}
                    />
                </div>

                <button 
                    type="submit" 
                    disabled={loading}
                    style={{ background: loading ? '#95a5a6' : '#2980b9', color: 'white', padding: '1rem 2rem', border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '1rem', width: '100%' }}
                >
                    {loading ? '⏳ Đang Upload lên AI Server...' : '🚀 Upload Specification'}
                </button>
            </form>
        </div>
    );
};

export default SpecCreator;
