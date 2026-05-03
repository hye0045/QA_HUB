import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api, { SpecExtended, SpecVersionInfo } from '../lib/api';

const SpecViewer: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [spec, setSpec] = useState<SpecExtended | null>(null);
    const [loading, setLoading] = useState(true);
    const [translating, setTranslating] = useState(false);
    const [activeSheetIdx, setActiveSheetIdx] = useState(0);

    const [translatedText, setTranslatedText] = useState<string | null>(null);
    const [versions, setVersions] = useState<number[]>([]);
    const [selectedVersion, setSelectedVersion] = useState<number>(1);
    const [diffV1, setDiffV1] = useState(1);
    const [diffV2, setDiffV2] = useState(2);
    const [diff, setDiff] = useState<string | null>(null);
    const [diffLoading, setDiffLoading] = useState(false);

    useEffect(() => {
        const fetchSpec = async () => {
            try {
                const res = await api.get(`/specs/`);
                const target: SpecExtended = res.data.find((s: SpecExtended) => s.id === id);
                if (target) {
                    setSpec(target);
                    const versionNums = target.versions.map(v => v.version_number).sort((a,b) => b-a);
                    setVersions(versionNums);
                    setSelectedVersion(target.latest_version);
                    setDiffV1(Math.max(1, target.latest_version - 1));
                    setDiffV2(target.latest_version);
                }
            } catch (err: any) {
                console.error('Lỗi tải Spec:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchSpec();
    }, [id]);

    // Phân tách nội dung thành các Sheet dựa trên marker "=== Sheet X: Name ==="
    const parseSheets = (text: string) => {
        if (!text) return [];
        const sheets: { name: string, content: string }[] = [];
        const parts = text.split(/=== Sheet \d+: (.*?) ===/);
        
        if (parts.length <= 1) {
            return [{ name: 'Nội dung', content: text }];
        }

        for (let i = 1; i < parts.length; i += 2) {
            sheets.push({
                name: parts[i],
                content: parts[i+1]?.trim() || ''
            });
        }
        return sheets;
    };

    const sheetList = parseSheets(spec?.content || '');

    const handleTranslate = async (targetLang: string) => {
        const currentContent = sheetList[activeSheetIdx]?.content;
        if (!currentContent) return;

        setTranslating(true);
        setTranslatedText('AI đang dịch sheet này...');
        try {
            const res = await api.post('/chat', {
                mode: 'translate',
                prompt: currentContent.substring(0, 20000), // Giới hạn 20k ký tự để tránh treo Ollama
                target_lang: targetLang
            });
            setTranslatedText(res.data.response);
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Lỗi không xác định';
            setTranslatedText(`❌ Lỗi dịch thuật: ${msg}`);
        } finally {
            setTranslating(false);
        }
    };

    const handleCompareDiff = async () => {
        if (!id) return;
        setDiffLoading(true);
        setDiff(null);
        try {
            const res = await api.get(`/specs/${id}/diff?v1=${diffV1}&v2=${diffV2}`);
            setDiff(res.data.diff || '(Không có sự khác biệt)');
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Lỗi không xác định';
            setDiff(`❌ Lỗi: ${msg}`);
        } finally {
            setDiffLoading(false);
        }
    };

    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#7f8c8d' }}>
                Đang tải tài liệu...
            </div>
        );
    }
    if (!spec) {
        return (
            <div style={{ background: '#fdecea', color: '#c0392b', padding: '1.5rem', borderRadius: '8px' }}>
                ❌ Không tìm thấy Specification với ID này.
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <h2 style={{ margin: 0 }}>
                        {spec.title}{' '}
                        <span style={{ fontSize: '1rem', color: '#7f8c8d' }}>(v{selectedVersion})</span>
                    </h2>
                    <div style={{ fontSize: '0.9rem', color: '#34495e' }}>
                        <strong>Feature:</strong> {spec.feature_name} | <strong>Models Hỗ Trợ:</strong>{' '}
                        {spec.versions.find(v => v.version_number === selectedVersion)?.supported_models.map(m => m.name).join(', ') || 'N/A'}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button
                        onClick={() => handleTranslate('English')}
                        disabled={translating}
                        style={{ padding: '0.6rem 1rem', background: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        A→E Dịch Sheet Hiện Tại (Anh)
                    </button>
                    <button
                        onClick={() => handleTranslate('Japanese')}
                        disabled={translating}
                        style={{ padding: '0.6rem 1rem', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        A→J Dịch Sheet Hiện Tại (Nhật)
                    </button>
                </div>
            </div>

            {/* Version & Sheet Selector */}
            <div style={{ background: 'white', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.07)', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <label style={{ fontWeight: 'bold' }}>Phiên bản:</label>
                    <select
                        value={selectedVersion}
                        onChange={e => setSelectedVersion(Number(e.target.value))}
                        style={{ padding: '0.4rem 0.8rem', borderRadius: '4px', border: '1px solid #ccc' }}
                    >
                        {versions.map(v => (
                            <option key={v} value={v}>v{v}{v === spec.latest_version ? ' (mới nhất)' : ''}</option>
                        ))}
                    </select>
                </div>

                <span style={{ color: '#ecf0f1' }}>|</span>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <label style={{ fontWeight: 'bold' }}>Chọn Sheet:</label>
                    <select
                        value={activeSheetIdx}
                        onChange={e => {
                            setActiveSheetIdx(Number(e.target.value));
                            setTranslatedText(null);
                        }}
                        style={{ padding: '0.4rem 0.8rem', borderRadius: '4px', border: '1px solid #3498db', color: '#2980b9', fontWeight: 'bold' }}
                    >
                        {sheetList.map((sh, idx) => (
                            <option key={idx} value={idx}>{sh.name}</option>
                        ))}
                    </select>
                </div>

                <span style={{ color: '#ecf0f1' }}>|</span>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <label style={{ fontWeight: 'bold' }}>So sánh:</label>
                    <select value={diffV1} onChange={e => setDiffV1(Number(e.target.value))} style={{ padding: '0.4rem', borderRadius: '4px', border: '1px solid #ccc' }}>
                        {versions.map(v => <option key={v} value={v}>v{v}</option>)}
                    </select>
                    <span>↔</span>
                    <select value={diffV2} onChange={e => setDiffV2(Number(e.target.value))} style={{ padding: '0.4rem', borderRadius: '4px', border: '1px solid #ccc' }}>
                        {versions.map(v => <option key={v} value={v}>v{v}</option>)}
                    </select>
                    <button
                        onClick={handleCompareDiff}
                        disabled={diffLoading}
                        style={{ padding: '0.4rem 1rem', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        📊 So sánh
                    </button>
                </div>
            </div>

            {/* Diff Result */}
            {diff && (
                <div style={{ 
                    background: '#1e1e2e', 
                    color: '#cdd6f4', 
                    padding: '1.5rem', 
                    borderRadius: '8px', 
                    marginBottom: '1.5rem', 
                    fontFamily: 'monospace', 
                    whiteSpace: 'pre-wrap', 
                    overflowX: 'auto', 
                    borderLeft: '5px solid #f38ba8',
                    maxHeight: '400px',
                    overflowY: 'auto'
                }}>
                    <div style={{ marginBottom: '0.5rem', color: '#f5c2e7', fontWeight: 'bold' }}>
                        Kết quả so sánh v{diffV1} và v{diffV2}:
                        {diff.length > 30000 && <span style={{ color: '#fab387', marginLeft: '1rem' }}>(Đã rút gọn vì nội dung quá lớn)</span>}
                    </div>
                    {diff.length > 30000 ? diff.substring(0, 30000) + '\n\n... (Dữ liệu quá lớn, vui lòng tải file để xem đầy đủ) ...' : diff}
                </div>
            )}

            {/* Content Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', minHeight: '500px' }}>
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)', display: 'flex', flexDirection: 'column' }}>
                    <h3 style={{ borderBottom: '2px solid #3498db', paddingBottom: '0.5rem', marginTop: 0 }}>
                        Bản Gốc: {sheetList[activeSheetIdx]?.name}
                    </h3>
                    <div style={{ 
                        whiteSpace: 'pre-wrap', 
                        fontFamily: 'monospace', 
                        marginTop: '1rem', 
                        fontSize: '0.85rem', 
                        overflowY: 'auto', 
                        maxHeight: '600px',
                        flex: 1,
                        lineHeight: '1.6',
                        background: '#fafafa',
                        padding: '1rem',
                        border: '1px solid #f1f1f1'
                    }}>
                        {sheetList[activeSheetIdx]?.content || 'Sheet này không có nội dung.'}
                    </div>
                </div>

                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)', display: 'flex', flexDirection: 'column' }}>
                    <h3 style={{ borderBottom: '2px solid #8e44ad', paddingBottom: '0.5rem', color: '#8e44ad', marginTop: 0 }}>
                        Bản Dịch AI (Sheet: {sheetList[activeSheetIdx]?.name})
                    </h3>
                    <div style={{ 
                        whiteSpace: 'pre-wrap', 
                        fontFamily: 'monospace', 
                        marginTop: '1rem', 
                        color: translatedText ? '#2c3e50' : '#95a5a6', 
                        fontSize: '0.85rem',
                        overflowY: 'auto',
                        maxHeight: '600px',
                        flex: 1,
                        lineHeight: '1.6',
                        background: '#fcfcfc',
                        padding: '1rem',
                        border: '1px solid #f1f1f1'
                    }}>
                        {translatedText || 'Chọn ngôn ngữ ở trên để AI dịch nội dung của sheet hiện tại...'}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SpecViewer;
