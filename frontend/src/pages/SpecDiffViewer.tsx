import React, { useState, useEffect } from 'react';
import api, { Spec } from '../lib/api';

const SpecDiffViewer: React.FC = () => {
    const [mode, setMode] = useState<'versions' | 'models'>('versions');

    const [specs, setSpecs] = useState<Spec[]>([]);
    
    // Mode: versions
    const [selectedSpecId, setSelectedSpecId] = useState('');
    const [v1, setV1] = useState(1);
    const [v2, setV2] = useState(2);

    // Mode: models
    const [specAId, setSpecAId] = useState('');
    const [vA, setVA] = useState(1);
    const [specBId, setSpecBId] = useState('');
    const [vB, setVB] = useState(1);

    const [diff, setDiff] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [aiAnalysis, setAiAnalysis] = useState<string>('');
    const [aiLoading, setAiLoading] = useState(false);

    useEffect(() => {
        const loadSpecs = async () => {
            try {
                const res = await api.get('/specs/');
                setSpecs(res.data);
                if (res.data.length > 0) {
                    const firstSpec = res.data[0];
                    setSelectedSpecId(firstSpec.id);
                    setSpecAId(firstSpec.id);
                    setSpecBId(res.data.length > 1 ? res.data[1].id : firstSpec.id);
                    
                    const maxVer = firstSpec.latest_version || 1;
                    setV1(Math.max(1, maxVer - 1));
                    setV2(maxVer);
                    setVA(maxVer);
                    
                    if (res.data.length > 1) {
                        setVB(res.data[1].latest_version || 1);
                    } else {
                        setVB(maxVer);
                    }
                }
            } catch (err) {
                console.error(err);
            }
        };
        loadSpecs();
    }, []);

    const handleSpecChange = (specId: string) => {
        setSelectedSpecId(specId);
        const spec = specs.find(s => s.id === specId);
        if (spec) {
            const maxVer = spec.latest_version || 1;
            setV1(Math.max(1, maxVer - 1));
            setV2(maxVer);
        }
        setDiff('');
        setAiAnalysis('');
    };

    const handleSpecAChange = (specId: string) => {
        setSpecAId(specId);
        const spec = specs.find(s => s.id === specId);
        if (spec) setVA(spec.latest_version || 1);
        setDiff('');
        setAiAnalysis('');
    };

    const handleSpecBChange = (specId: string) => {
        setSpecBId(specId);
        const spec = specs.find(s => s.id === specId);
        if (spec) setVB(spec.latest_version || 1);
        setDiff('');
        setAiAnalysis('');
    };

    const fetchDiff = async () => {
        setLoading(true);
        setDiff('');
        setAiAnalysis('');
        try {
            let res;
            if (mode === 'versions') {
                if (!selectedSpecId) return;
                res = await api.get(`/specs/${selectedSpecId}/diff?v1=${v1}&v2=${v2}`);
            } else {
                if (!specAId || !specBId) return;
                res = await api.get(`/specs/cross-model-diff?spec_id_a=${specAId}&version_a=${vA}&spec_id_b=${specBId}&version_b=${vB}`);
            }
            setDiff(res.data.diff || 'Không có sự khác biệt giữa 2 mục này.');
        } catch (err: any) {
            setDiff(`❌ Lỗi: ${err.response?.data?.detail || err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const analyzeWithAI = async () => {
        if (!diff || diff.startsWith('❌')) return;
        setAiLoading(true);
        try {
            const reqBody = mode === 'versions' 
                ? { spec_id: selectedSpecId, v1, v2, diff_text: diff }
                : { spec_id: specAId, v1: vA, v2: vB, diff_text: diff }; // reusing the same endpoint with dummy id
            
            const res = await api.post('/specs/ai-diff-analyze', reqBody);
            setAiAnalysis(res.data.analysis);
        } catch (err: any) {
            setAiAnalysis(`❌ AI Error: ${err.response?.data?.detail || err.message}`);
        } finally {
            setAiLoading(false);
        }
    };

    return (
        <div style={{ padding: '1rem' }}>
            <h2 style={{ color: '#2c3e50', borderBottom: '2px solid #e67e22', paddingBottom: '0.5rem' }}>🔍 Spec Diff & AI Analysis</h2>
            
            {/* Toggle Mode */}
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                <button 
                    onClick={() => { setMode('versions'); setDiff(''); setAiAnalysis(''); }}
                    style={{ padding: '0.6rem 1.2rem', fontWeight: 'bold', cursor: 'pointer', border: '1px solid #3498db', background: mode === 'versions' ? '#3498db' : 'white', color: mode === 'versions' ? 'white' : '#3498db', borderRadius: '4px' }}
                >
                    So sánh 2 Versions (Cùng Spec)
                </button>
                <button 
                    onClick={() => { setMode('models'); setDiff(''); setAiAnalysis(''); }}
                    style={{ padding: '0.6rem 1.2rem', fontWeight: 'bold', cursor: 'pointer', border: '1px solid #e67e22', background: mode === 'models' ? '#e67e22' : 'white', color: mode === 'models' ? 'white' : '#e67e22', borderRadius: '4px' }}
                >
                    So sánh 2 Specs (Khác Models)
                </button>
            </div>

            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', marginBottom: '1.5rem' }}>
                {mode === 'versions' ? (
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto auto', gap: '0.75rem', alignItems: 'end' }}>
                        <div>
                            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '0.85rem' }}>Specification</label>
                            <select
                                value={selectedSpecId}
                                onChange={e => handleSpecChange(e.target.value)}
                                style={{ width: '100%', padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc' }}
                            >
                                <option value="" disabled>-- Chọn Spec --</option>
                                {specs.map(s => (
                                    <option key={s.id} value={s.id}>{s.feature_name || s.title} (v{s.latest_version})</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '0.85rem' }}>Version Cũ</label>
                            <input
                                type="number" min={1} value={v1} onChange={(e) => setV1(Number(e.target.value))}
                                style={{ width: '100%', padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '0.85rem' }}>Version Mới</label>
                            <input
                                type="number" min={1} value={v2} onChange={(e) => setV2(Number(e.target.value))}
                                style={{ width: '100%', padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
                            />
                        </div>
                        <button onClick={fetchDiff} disabled={loading || !selectedSpecId} style={{ padding: '0.6rem 1rem', background: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', height: '38px' }}>
                            {loading ? '...' : '⚡ So sánh'}
                        </button>
                        <button onClick={analyzeWithAI} disabled={aiLoading || !diff || diff.startsWith('❌')} style={{ padding: '0.6rem 1rem', background: aiLoading ? '#95a5a6' : '#8e44ad', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', height: '38px' }}>
                            {aiLoading ? '...' : '🤖 AI Analyze'}
                        </button>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: '0.75rem', alignItems: 'end' }}>
                        <div>
                            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '0.85rem' }}>Spec A (Nguồn)</label>
                            <div style={{ display: 'flex', gap: '4px' }}>
                                <select value={specAId} onChange={e => handleSpecAChange(e.target.value)} style={{ flex: 1, padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc' }}>
                                    {specs.map(s => <option key={`A_${s.id}`} value={s.id}>{s.feature_name || s.title}</option>)}
                                </select>
                                <input type="number" min={1} value={vA} onChange={(e) => setVA(Number(e.target.value))} style={{ width: '60px', padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc' }} title="Version A" />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '4px', fontSize: '0.85rem' }}>Spec B (Đích)</label>
                            <div style={{ display: 'flex', gap: '4px' }}>
                                <select value={specBId} onChange={e => handleSpecBChange(e.target.value)} style={{ flex: 1, padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc' }}>
                                    {specs.map(s => <option key={`B_${s.id}`} value={s.id}>{s.feature_name || s.title}</option>)}
                                </select>
                                <input type="number" min={1} value={vB} onChange={(e) => setVB(Number(e.target.value))} style={{ width: '60px', padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc' }} title="Version B" />
                            </div>
                        </div>
                        <button onClick={fetchDiff} disabled={loading || !specAId || !specBId} style={{ padding: '0.6rem 1rem', background: '#e67e22', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', height: '38px' }}>
                            {loading ? '...' : '⚡ So sánh Models'}
                        </button>
                        <button onClick={analyzeWithAI} disabled={aiLoading || !diff || diff.startsWith('❌')} style={{ padding: '0.6rem 1rem', background: aiLoading ? '#95a5a6' : '#8e44ad', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', height: '38px' }}>
                            {aiLoading ? '...' : '🤖 AI Analyze'}
                        </button>
                    </div>
                )}
            </div>

            {/* Diff Output */}
            {diff && (
                <div style={{ background: '#1e1e2e', padding: '1.5rem', borderRadius: '8px', marginBottom: '1.5rem', overflowX: 'auto' }}>
                    <h3 style={{ color: '#cdd6f4', marginTop: 0 }}>📝 Kết quả so sánh</h3>
                    <pre style={{ color: '#a6e3a1', fontFamily: 'monospace', fontSize: '0.9rem', whiteSpace: 'pre-wrap', margin: 0 }}>
                        {diff.split('\n').map((line, idx) => {
                            let color = '#cdd6f4'; // default white
                            if (line.startsWith('+')) color = '#a6e3a1'; // green
                            if (line.startsWith('-')) color = '#f38ba8'; // red
                            if (line.startsWith('@@')) color = '#89b4fa'; // blue
                            return <div key={idx} style={{ color }}>{line}</div>;
                        })}
                    </pre>
                </div>
            )}

            {/* AI Analysis Output */}
            {aiAnalysis && (
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', border: '2px solid #8e44ad' }}>
                    <h3 style={{ marginTop: 0, color: '#8e44ad' }}>🤖 Phân tích AI về sự thay đổi</h3>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: '#2c3e50' }}>
                        {aiAnalysis}
                    </div>
                </div>
            )}
        </div>
    );
};

export default SpecDiffViewer;
