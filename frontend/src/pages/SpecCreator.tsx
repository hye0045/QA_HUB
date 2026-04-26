import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';
import api from '../lib/api';

interface SheetData {
    name: string;
    headers: string[];
    rows: string[][];
}

const SpecCreator: React.FC = () => {
    const navigate = useNavigate();
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [title, setTitle] = useState('');
    const [language, setLanguage] = useState('vietnamese');
    const [versionNumber, setVersionNumber] = useState(1);
    const [content, setContent] = useState('');
    const [fileName, setFileName] = useState<string | null>(null);
    const [featureName, setFeatureName] = useState('');
    const [selectedModelIds, setSelectedModelIds] = useState<string[]>([]);
    const [profiles, setProfiles] = useState<{id: string, name: string}[]>([]);

    useEffect(() => {
        api.get('/defects/profiles')
            .then(res => setProfiles(res.data))
            .catch(err => console.error('Error fetching profiles', err));
    }, []);

    // Sheet preview state
    const [sheets, setSheets] = useState<SheetData[]>([]);
    const [activeSheet, setActiveSheet] = useState(0);
    const [showPreview, setShowPreview] = useState(true);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    // Xử lý upload file Excel (.xlsx, .xls)
    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setFileName(file.name);
        setError(null);
        setSheets([]);
        setActiveSheet(0);
        setLoading(true);

        const reader = new FileReader();
        reader.onload = (evt) => {
            // Sử dụng setTimeout để tránh chặn main thread ngay lập tức, cho phép UI hiển thị trạng thái loading
            setTimeout(() => {
                try {
                    const bstr = evt.target?.result;
                    const workbook = XLSX.read(bstr, { type: 'binary' });

                    const parsedSheets: SheetData[] = [];
                    let fullContent = '';

                    workbook.SheetNames.forEach((sheetName, idx) => {
                        const sheet = workbook.Sheets[sheetName];

                        // Lấy dữ liệu dạng mảng 2D (cho preview bảng)
                        const rawData: string[][] = XLSX.utils.sheet_to_json(sheet, {
                            header: 1,
                            defval: '',
                            raw: false,
                        }) as string[][];

                        // Lọc bỏ hàng toàn empty
                        const filtered = rawData.filter(row => row.some(cell => cell !== ''));

                        const headers = filtered[0] || [];
                        const rows = filtered.slice(1);

                        parsedSheets.push({ name: sheetName, headers, rows });

                        // Tạo text content gửi lên backend
                        const sheetText = XLSX.utils.sheet_to_txt(sheet);
                        fullContent += `=== Sheet ${idx + 1}: ${sheetName} ===\n${sheetText}\n\n`;
                    });

                    setSheets(parsedSheets);
                    setContent(fullContent);
                    setShowPreview(true);

                    // Tự động đặt title nếu chưa có
                    if (!title.trim()) {
                        const baseName = file.name.replace(/\.(xlsx|xls)$/i, '');
                        setTitle(baseName);
                    }
                } catch (err) {
                    setError('❌ Không thể đọc file Excel. Vui lòng kiểm tra định dạng file.');
                } finally {
                    setLoading(false);
                }
            }, 50);
        };
        reader.readAsBinaryString(file);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!title.trim() || !content.trim()) {
            setError('Title và Content là bắt buộc! Hãy nhập tay hoặc Upload file Excel.');
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
                content,
                feature_name: featureName || null,
                model_profile_ids: selectedModelIds
            });
            if (res.data.spec_id) {
                setSuccess(`✅ Upload thành công! Spec ID: ${res.data.spec_id}`);

                setTitle('');
                setLanguage('vietnamese');
                setVersionNumber(1);
                setContent('');
                setFileName(null);
                setSheets([]);
                if (fileInputRef.current) fileInputRef.current.value = '';

                setTimeout(() => {
                    navigate(`/specs/view/${res.data.spec_id}`);
                }, 1500);
            }
        } catch (err: any) {
            setError(`❌ Lỗi upload Specification: ${err.response?.data?.detail || err.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '1rem', maxWidth: '1100px', margin: '0 auto' }}>
            <h2 style={{ color: '#2c3e50', borderBottom: '2px solid #3498db', paddingBottom: '0.5rem' }}>
                📄 Upload / Tạo mới Specification
            </h2>
            <p style={{ color: '#7f8c8d', marginBottom: '1.5rem' }}>
                Dành cho Tester và QA Lead. Hỗ trợ nhập tay hoặc Upload file Excel (.xlsx / .xls).
            </p>

            {error && (
                <div style={{ background: '#fdecea', color: '#c0392b', padding: '1rem', borderRadius: '4px', marginBottom: '1rem', fontWeight: 'bold' }}>
                    {error}
                </div>
            )}
            {success && (
                <div style={{ background: '#d4edda', color: '#155724', padding: '1rem', borderRadius: '4px', marginBottom: '1rem', fontWeight: 'bold' }}>
                    {success}
                </div>
            )}

            <form onSubmit={handleSubmit} style={{ background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>

                {/* Upload Zone */}
                <div
                    style={{ marginBottom: '1.5rem', border: '2px dashed #3498db', borderRadius: '8px', padding: '1.5rem', textAlign: 'center', background: '#f0f8ff', cursor: 'pointer' }}
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
                        <p style={{ color: '#27ae60', fontWeight: 'bold', margin: 0 }}>
                            ✅ Đã chọn: {fileName} ({sheets.length} sheet)
                        </p>
                    ) : (
                        <>
                            <p style={{ color: '#3498db', fontWeight: 'bold', margin: '0.25rem 0' }}>Bấm vào đây để Upload file Excel</p>
                            <p style={{ color: '#95a5a6', fontSize: '0.85rem', margin: 0 }}>Hỗ trợ .xlsx và .xls — Nội dung sẽ được hiển thị dạng bảng</p>
                        </>
                    )}
                </div>

                {/* Sheet Preview dạng bảng */}
                {sheets.length > 0 && (
                    <div style={{ marginBottom: '1.5rem', border: '1px solid #dee2e6', borderRadius: '8px', overflow: 'hidden' }}>
                        {/* Tab header */}
                        <div style={{ display: 'flex', alignItems: 'center', background: '#f8f9fa', borderBottom: '1px solid #dee2e6', flexWrap: 'wrap' }}>
                            {sheets.map((sheet, idx) => (
                                <button
                                    key={idx}
                                    type="button"
                                    onClick={() => setActiveSheet(idx)}
                                    style={{
                                        padding: '0.6rem 1.2rem',
                                        border: 'none',
                                        borderBottom: idx === activeSheet ? '3px solid #3498db' : '3px solid transparent',
                                        background: idx === activeSheet ? 'white' : 'transparent',
                                        cursor: 'pointer',
                                        fontWeight: idx === activeSheet ? 'bold' : 'normal',
                                        color: idx === activeSheet ? '#3498db' : '#6c757d',
                                        fontSize: '0.9rem',
                                    }}
                                >
                                    📋 {sheet.name}
                                </button>
                            ))}
                            <button
                                type="button"
                                onClick={() => setShowPreview(p => !p)}
                                style={{ marginLeft: 'auto', padding: '0.4rem 1rem', border: 'none', background: 'transparent', cursor: 'pointer', color: '#6c757d', fontSize: '0.85rem' }}
                            >
                                {showPreview ? '🔼 Ẩn Preview' : '🔽 Hiện Preview'}
                            </button>
                        </div>

                        {/* Bảng dữ liệu */}
                        {showPreview && sheets[activeSheet] && (
                            <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                                    {sheets[activeSheet].headers.length > 0 && (
                                        <thead>
                                            <tr style={{ background: '#3498db', color: 'white', position: 'sticky', top: 0 }}>
                                                <th style={{ padding: '0.5rem 0.75rem', border: '1px solid #2980b9', fontWeight: 'bold', textAlign: 'center', minWidth: '30px', color: '#b2d8f0' }}>#</th>
                                                {sheets[activeSheet].headers.map((h, i) => (
                                                    <th key={i} style={{ padding: '0.5rem 0.75rem', border: '1px solid #2980b9', fontWeight: 'bold', textAlign: 'left', whiteSpace: 'nowrap' }}>
                                                        {String(h) || `Cột ${i + 1}`}
                                                    </th>
                                                ))}
                                            </tr>
                                        </thead>
                                    )}
                                    <tbody>
                                        {sheets[activeSheet].rows.slice(0, 100).map((row, rIdx) => (
                                            <tr key={rIdx} style={{ background: rIdx % 2 === 0 ? 'white' : '#f8fafb' }}>
                                                <td style={{ padding: '0.4rem 0.75rem', border: '1px solid #dee2e6', color: '#adb5bd', textAlign: 'center', fontSize: '0.8rem' }}>
                                                    {rIdx + 1}
                                                </td>
                                                {sheets[activeSheet].headers.map((_, cIdx) => (
                                                    <td key={cIdx} style={{ padding: '0.4rem 0.75rem', border: '1px solid #dee2e6', whiteSpace: 'pre-wrap', maxWidth: '350px' }}>
                                                        {String(row[cIdx] ?? '')}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                        {sheets[activeSheet].rows.length > 100 && (
                                            <tr>
                                                <td colSpan={sheets[activeSheet].headers.length + 1} style={{ padding: '1rem', textAlign: 'center', color: '#7f8c8d', fontStyle: 'italic', background: '#f8f9fa' }}>
                                                    ... Và {sheets[activeSheet].rows.length - 100} hàng khác không được hiển thị để đảm bảo hiệu suất ...
                                                </td>
                                            </tr>
                                        )}
                                        {sheets[activeSheet].rows.length === 0 && (
                                            <tr>
                                                <td colSpan={sheets[activeSheet].headers.length + 1} style={{ padding: '1rem', textAlign: 'center', color: '#adb5bd' }}>
                                                    Sheet này không có dữ liệu
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        )}
                        <div style={{ padding: '0.4rem 0.75rem', background: '#f8f9fa', borderTop: '1px solid #dee2e6', fontSize: '0.8rem', color: '#6c757d', display: 'flex', justifyContent: 'space-between' }}>
                            <span>{sheets[activeSheet]?.rows.length} hàng dữ liệu · {sheets[activeSheet]?.headers.length} cột</span>
                            {sheets[activeSheet]?.rows.length > 100 && <span style={{ color: '#e67e22' }}>⚠️ Chỉ hiển thị 100 hàng đầu tiên trong preview</span>}
                        </div>
                    </div>
                )}

                {/* Title */}
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

                {/* Feature Name & Models */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div>
                        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Feature Name (Nhóm chức năng):</label>
                        <input
                            type="text"
                            value={featureName}
                            onChange={e => setFeatureName(e.target.value)}
                            placeholder="Ví dụ: Login, Camera, Wifi..."
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontSize: '1rem', boxSizing: 'border-box' }}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>Dòng máy hỗ trợ (Models):</label>
                        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', padding: '0.5rem', border: '1px solid #eee', borderRadius: '4px' }}>
                            {profiles.map(p => (
                                <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                    <input 
                                        type="checkbox" 
                                        checked={selectedModelIds.includes(p.id)}
                                        onChange={e => {
                                            if (e.target.checked) setSelectedModelIds([...selectedModelIds, p.id]);
                                            else setSelectedModelIds(selectedModelIds.filter(id => id !== p.id));
                                        }}
                                    />
                                    {p.name}
                                </label>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Language & Version */}
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

                {/* Manual content textarea (only show if no file uploaded) */}
                {!fileName && (
                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                            Nội dung Spec (nhập tay hoặc copy/paste):
                        </label>
                        <textarea
                            value={content}
                            onChange={e => setContent(e.target.value)}
                            placeholder="1. Giới thiệu chức năng...&#10;2. Quy trình xử lý...&#10;3. Ngoại lệ..."
                            style={{ width: '100%', height: '300px', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontFamily: 'monospace', fontSize: '0.9rem', boxSizing: 'border-box' }}
                        />
                    </div>
                )}

                <button
                    type="submit"
                    disabled={loading}
                    style={{ background: loading ? '#95a5a6' : '#2980b9', color: 'white', padding: '1rem 2rem', border: 'none', borderRadius: '4px', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '1rem', width: '100%' }}
                >
                    {loading ? '⏳ Đang Upload lên Server...' : '🚀 Upload Specification'}
                </button>
            </form>
        </div>
    );
};

export default SpecCreator;
