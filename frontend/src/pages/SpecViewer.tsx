import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api, { Spec } from '../lib/api';

const SpecViewer: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [spec, setSpec] = useState<Spec | null>(null);
    const [loading, setLoading] = useState(true);
    const [translating, setTranslating] = useState(false);
    const [translatedText, setTranslatedText] = useState<string | null>(null);

    // Version selector state
    const [versions, setVersions] = useState<number[]>([]);
    const [selectedVersion, setSelectedVersion] = useState<number>(1);

    // Diff state
    const [diffV1, setDiffV1] = useState(1);
    const [diffV2, setDiffV2] = useState(2);
    const [diff, setDiff] = useState<string | null>(null);
    const [diffLoading, setDiffLoading] = useState(false);

    useEffect(() => {
        const fetchSpec = async () => {
            try {
                const res = await api.get(`/specs/`);
                const target: Spec = res.data.find((s: Spec) => s.id === id);
                if (target) {
                    setSpec(target);
                    const versionNums = Array.from(
                        { length: target.latest_version },
                        (_, i) => i + 1
                    );
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

    const handleTranslate = async (targetLang: string) => {
        if (!spec?.content) return;
        setTranslating(true);
        setTranslatedText('AI đang dịch tài liệu...');
        try {
            const res = await api.post('/chat', {
                mode: 'translate',
                prompt: spec.content,
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
                <h2 style={{ margin: 0 }}>
                    {spec.title}{' '}
                    <span style={{ fontSize: '1rem', color: '#7f8c8d' }}>(v{selectedVersion})</span>
                </h2>

                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button
                        onClick={() => handleTranslate('English')}
                        disabled={translating}
                        style={{ padding: '0.6rem 1rem', background: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        A→E Dịch Tiếng Anh
                    </button>
                    <button
                        onClick={() => handleTranslate('Japanese')}
                        disabled={translating}
                        style={{ padding: '0.6rem 1rem', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        A→J Dịch Tiếng Nhật
                    </button>
                </div>
            </div>

            {/* Version Selector */}
            {versions.length > 1 && (
                <div style={{ background: 'white', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.07)', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <label style={{ fontWeight: 'bold' }}>Xem phiên bản:</label>
                    <select
                        value={selectedVersion}
                        onChange={e => setSelectedVersion(Number(e.target.value))}
                        style={{ padding: '0.4rem 0.8rem', borderRadius: '4px', border: '1px solid #ccc' }}
                    >
                        {versions.map(v => (
                            <option key={v} value={v}>v{v}{v === spec.latest_version ? ' (mới nhất)' : ''}</option>
                        ))}
                    </select>

                    {/* So sánh 2 phiên bản */}
                    <span style={{ color: '#95a5a6' }}>|</span>
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
                        {diffLoading ? 'Đang so sánh...' : '📊 So sánh'}
                    </button>
                </div>
            )}

            {/* Diff Result */}
            {diff && (
                <div style={{ background: '#1e1e2e', color: '#cdd6f4', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem', fontFamily: 'monospace', whiteSpace: 'pre-wrap', overflowX: 'auto' }}>
                    <div style={{ marginBottom: '0.5rem', color: '#a6e3a1', fontSize: '0.85rem' }}>
                        Diff v{diffV1} → v{diffV2}
                    </div>
                    {diff}
                </div>
            )}

            {/* Content Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: '1.5rem' }}>
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
                    <h3 style={{ borderBottom: '2px solid #ecf0f1', paddingBottom: '0.5rem' }}>Bản Gốc ({spec.language})</h3>
                    <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', marginTop: '1rem', fontSize: '0.9rem' }}>
                        {spec.content}
                    </div>
                </div>

                <div style={{ background: '#f8f9fa', padding: '1.5rem', borderRadius: '8px', border: '1px solid #ecf0f1' }}>
                    <h3 style={{ borderBottom: '2px solid #ecf0f1', paddingBottom: '0.5rem', color: '#8e44ad' }}>Bản Dịch AI</h3>
                    <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', marginTop: '1rem', color: translatedText ? '#2c3e50' : '#95a5a6', fontSize: '0.9rem' }}>
                        {translatedText || 'Bấm nút dịch ở trên để AI phân tích và dịch tài liệu này...'}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SpecViewer;
