import React, { useState, useEffect } from 'react';
import api from '../lib/api';

interface DeviceProfile {
    id: string;
    name: string;
}

interface GeneratedTC {
    id: string;
    title: string;
    precondition: string;
    steps: string;
    expected_result: string;
    ref_bug?: string;
    selected?: boolean;
}

const TestCaseGenerator: React.FC = () => {
    const [specText, setSpecText] = useState('');
    const [baseModel, setBaseModel] = useState('');
    const [newModel, setNewModel] = useState('');
    const [profiles, setProfiles] = useState<DeviceProfile[]>([]);
    const [generating, setGenerating] = useState(false);
    
    const [functionalTCs, setFunctionalTCs] = useState<GeneratedTC[]>([]);
    const [bugListTCs, setBugListTCs] = useState<GeneratedTC[]>([]);
    const [activeTab, setActiveTab] = useState<'functional' | 'bug_list'>('functional');
    
    const [error, setError] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        api.get('/defects/profiles')
            .then(res => {
                setProfiles(res.data);
                if (res.data.length > 0) {
                    setBaseModel(res.data[0].name);
                }
            })
            .catch(err => console.error('Error fetching profiles:', err));
    }, []);

    const handleGenerate = async () => {
        if (!specText.trim() || !baseModel.trim() || !newModel.trim()) {
            setError('Vui lòng nhập đầy đủ Spec Text, Base Model và New Model Name.');
            return;
        }

        setGenerating(true);
        setError(null);
        setSuccessMsg(null);
        setFunctionalTCs([]);
        setBugListTCs([]);

        try {
            const res = await api.post('/testcases/generate-from-base-model', {
                spec_text: specText,
                base_model_name: baseModel,
                new_model_name: newModel,
                tc_k: 5,
                bug_k: 5
            });
            
            const funcTCs = (res.data.functional || []).map((tc: any) => ({ ...tc, selected: true }));
            const bugTCs = (res.data.bug_list || []).map((tc: any) => ({ ...tc, selected: true }));
            
            setFunctionalTCs(funcTCs);
            setBugListTCs(bugTCs);
            
            if (funcTCs.length === 0 && bugTCs.length === 0) {
                setError('AI không sinh được testcase nào hợp lệ.');
            }
        } catch (err: any) {
            setError(`❌ Lỗi sinh testcases: ${err.response?.data?.detail || err.message}`);
        } finally {
            setGenerating(false);
        }
    };

    const toggleSelection = (type: 'functional' | 'bug_list', index: number) => {
        if (type === 'functional') {
            const updated = [...functionalTCs];
            updated[index].selected = !updated[index].selected;
            setFunctionalTCs(updated);
        } else {
            const updated = [...bugListTCs];
            updated[index].selected = !updated[index].selected;
            setBugListTCs(updated);
        }
    };

    const handleSaveSelected = async (type: 'functional' | 'bug_list') => {
        const selectedTCs = type === 'functional' 
            ? functionalTCs.filter(tc => tc.selected) 
            : bugListTCs.filter(tc => tc.selected);

        if (selectedTCs.length === 0) {
            setError('Vui lòng chọn ít nhất 1 Testcase để lưu.');
            return;
        }

        setSaving(true);
        setError(null);
        setSuccessMsg(null);

        try {
            await api.post('/testcases/generate-from-base-model/save', {
                model_id: newModel,
                tc_type: type,
                testcases: selectedTCs
            });
            
            setSuccessMsg(`✅ Đã lưu thành công ${selectedTCs.length} ${type} testcases cho model ${newModel}.`);
            // Xóa các TC đã lưu khỏi danh sách hiện tại
            if (type === 'functional') {
                setFunctionalTCs(functionalTCs.filter(tc => !tc.selected));
            } else {
                setBugListTCs(bugListTCs.filter(tc => !tc.selected));
            }
        } catch (err: any) {
            setError(`❌ Lỗi khi lưu testcases: ${err.response?.data?.detail || err.message}`);
        } finally {
            setSaving(false);
        }
    };

    const renderTable = (type: 'functional' | 'bug_list', data: GeneratedTC[]) => {
        if (data.length === 0) return <p style={{ padding: '1rem', color: '#7f8c8d' }}>Không có testcase nào.</p>;

        return (
            <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                    <thead>
                        <tr style={{ background: '#f8f9fa' }}>
                            <th style={{ border: '1px solid #ddd', padding: '8px', width: '5%', textAlign: 'center' }}>Chọn</th>
                            <th style={{ border: '1px solid #ddd', padding: '8px', width: '15%' }}>Tiêu đề</th>
                            <th style={{ border: '1px solid #ddd', padding: '8px', width: '15%' }}>Tiền đề</th>
                            <th style={{ border: '1px solid #ddd', padding: '8px', width: '25%' }}>Steps</th>
                            <th style={{ border: '1px solid #ddd', padding: '8px', width: '20%' }}>Mong đợi</th>
                            {type === 'bug_list' && <th style={{ border: '1px solid #ddd', padding: '8px', width: '20%' }}>Bug gốc</th>}
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((tc, idx) => (
                            <tr key={idx} style={{ background: tc.selected ? '#ffffff' : '#f9f9f9', opacity: tc.selected ? 1 : 0.6 }}>
                                <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'center' }}>
                                    <input 
                                        type="checkbox" 
                                        checked={tc.selected || false} 
                                        onChange={() => toggleSelection(type, idx)} 
                                        style={{ transform: 'scale(1.2)', cursor: 'pointer' }}
                                    />
                                </td>
                                <td style={{ border: '1px solid #ddd', padding: '8px' }}>{tc.title}</td>
                                <td style={{ border: '1px solid #ddd', padding: '8px', whiteSpace: 'pre-wrap' }}>{tc.precondition}</td>
                                <td style={{ border: '1px solid #ddd', padding: '8px', whiteSpace: 'pre-wrap' }}>{tc.steps}</td>
                                <td style={{ border: '1px solid #ddd', padding: '8px', whiteSpace: 'pre-wrap' }}>{tc.expected_result}</td>
                                {type === 'bug_list' && <td style={{ border: '1px solid #ddd', padding: '8px', color: '#c0392b', fontWeight: 'bold' }}>{tc.ref_bug}</td>}
                            </tr>
                        ))}
                    </tbody>
                </table>
                <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
                    <button 
                        onClick={() => handleSaveSelected(type)} 
                        disabled={saving}
                        style={{ background: '#27ae60', color: 'white', padding: '0.6rem 1.2rem', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
                    >
                        {saving ? '⏳ Đang lưu...' : `💾 Lưu ${data.filter(t => t.selected).length} Testcases Đã Chọn`}
                    </button>
                </div>
            </div>
        );
    };

    return (
        <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ background: '#8e44ad', color: 'white', padding: '1.5rem', borderRadius: '8px' }}>
                <h2 style={{ margin: 0 }}>🤖 AI Testcase Generator (Từ Base Model - RAG)</h2>
                <p style={{ marginTop: '0.5rem', color: '#ecf0f1' }}>
                    Sinh hàng loạt Testcase cho Model mới, học hỏi văn phong và regression từ Base Model.
                </p>
            </div>

            {/* Input Section */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                
                <div style={{ gridColumn: '1 / -1' }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        Tài liệu Specification (Model Mới):
                    </label>
                    <textarea 
                        value={specText}
                        onChange={e => setSpecText(e.target.value)}
                        placeholder="Paste nội dung Spec của tính năng cần test..."
                        style={{ width: '100%', height: '120px', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', fontFamily: 'monospace', boxSizing: 'border-box' }}
                    />
                </div>

                <div>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        Base Model (Học hỏi từ đây):
                    </label>
                    <select 
                        value={baseModel} 
                        onChange={e => setBaseModel(e.target.value)}
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
                    >
                        {profiles.map(p => (
                            <option key={p.id} value={p.name}>{p.name}</option>
                        ))}
                        {profiles.length === 0 && <option value="">Đang tải...</option>}
                    </select>
                </div>

                <div>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem', color: '#e67e22' }}>
                        New Model Name (Dòng máy mới):
                    </label>
                    <input 
                        type="text"
                        value={newModel}
                        onChange={e => setNewModel(e.target.value)}
                        placeholder="VD: Samsung S25 Ultra"
                        style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid #e67e22', boxSizing: 'border-box' }}
                    />
                </div>

                {error && <div style={{ gridColumn: '1 / -1', color: '#e74c3c', fontWeight: 'bold', padding: '0.5rem', background: '#fadbd8', borderRadius: '4px' }}>{error}</div>}
                {successMsg && <div style={{ gridColumn: '1 / -1', color: '#27ae60', fontWeight: 'bold', padding: '0.5rem', background: '#d5f5e3', borderRadius: '4px' }}>{successMsg}</div>}

                <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'center', marginTop: '1rem' }}>
                    <button 
                        onClick={handleGenerate} 
                        disabled={generating || profiles.length === 0}
                        style={{ background: generating ? '#95a5a6' : '#2980b9', color: 'white', padding: '0.75rem 2.5rem', border: 'none', borderRadius: '30px', cursor: generating ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '1.1rem', boxShadow: '0 4px 6px rgba(41, 128, 185, 0.3)' }}
                    >
                        {generating ? '⏳ AI đang phân tích và sinh TC...' : '✨ Bắt Đầu Sinh Testcase'}
                    </button>
                </div>
            </div>

            {/* Results Preview Section */}
            {(functionalTCs.length > 0 || bugListTCs.length > 0) && (
                <div style={{ background: 'white', padding: '0', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
                    
                    <div style={{ display: 'flex', borderBottom: '1px solid #ccc', background: '#f1f2f6' }}>
                        <button 
                            onClick={() => setActiveTab('functional')}
                            style={{ flex: 1, padding: '1rem', fontWeight: 'bold', fontSize: '1rem', cursor: 'pointer', background: activeTab === 'functional' ? 'white' : 'transparent', border: 'none', borderBottom: activeTab === 'functional' ? '3px solid #3498db' : '3px solid transparent', color: activeTab === 'functional' ? '#2980b9' : '#7f8c8d' }}
                        >
                            📋 Functional TCs ({functionalTCs.length})
                        </button>
                        <button 
                            onClick={() => setActiveTab('bug_list')}
                            style={{ flex: 1, padding: '1rem', fontWeight: 'bold', fontSize: '1rem', cursor: 'pointer', background: activeTab === 'bug_list' ? 'white' : 'transparent', border: 'none', borderBottom: activeTab === 'bug_list' ? '3px solid #e74c3c' : '3px solid transparent', color: activeTab === 'bug_list' ? '#c0392b' : '#7f8c8d' }}
                        >
                            🐞 Bug-list TCs (Regression) ({bugListTCs.length})
                        </button>
                    </div>

                    <div style={{ padding: '1.5rem' }}>
                        {activeTab === 'functional' && renderTable('functional', functionalTCs)}
                        {activeTab === 'bug_list' && renderTable('bug_list', bugListTCs)}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TestCaseGenerator;
