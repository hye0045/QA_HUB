import React, { useState } from 'react';
import api from '../lib/api';

const TestCaseGenerator: React.FC = () => {
    const [specText, setSpecText] = useState('');
    const [baseModel, setBaseModel] = useState('iPhone 15'); // default
    const [generating, setGenerating] = useState(false);
    const [result, setResult] = useState<any[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleGenerate = async () => {
        if (!specText.trim()) {
            setError('Please paste Specification text first.');
            return;
        }

        setGenerating(true);
        setError(null);
        setResult(null);

        try {
            const res = await api.post('/testcases/generate', {
                spec_text: specText,
                base_model: baseModel
            });
            
            if (res.data.testcases) {
                setResult(res.data.testcases);
            } else {
                setError('AI returned an empty or invalid array.');
            }
        } catch (err: any) {
            setError(`❌ Error generating testcases: ${err.response?.data?.detail || err.message}`);
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ background: '#2980b9', color: 'white', padding: '1.5rem', borderRadius: '8px' }}>
                <h2 style={{ margin: 0 }}>🤖 AI Testcase Generator (RAG)</h2>
                <p style={{ marginTop: '0.5rem', color: '#ecf0f1' }}>
                    Sinh hàng loạt Testcase từ tài liệu Spec kết hợp học hỏi văn phong của dòng máy Base Model.
                </p>
            </div>

            {/* Input Section */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        Base Model Tham Chiếu (RAG):
                    </label>
                    <select 
                        value={baseModel} 
                        onChange={e => setBaseModel(e.target.value)}
                        style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', minWidth: '200px' }}
                    >
                        <option value="iPhone 15">Apple iPhone 15</option>
                        <option value="Samsung S24">Samsung Galaxy S24</option>
                        <option value="Xiaomi 14">Xiaomi 14</option>
                        <option value="General Web">General Web App</option>
                    </select>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        Tài liệu Specification gốc (Paste text):
                    </label>
                    <textarea 
                        value={specText}
                        onChange={e => setSpecText(e.target.value)}
                        placeholder="VD: Chức năng Login. Bấm vào nút thì hiển thị Toast thông báo. Quá 3 lần sẽ bị khóa tài khoản..."
                        style={{ width: '100%', height: '150px', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', fontFamily: 'monospace' }}
                    />
                </div>

                {error && <div style={{ color: '#e74c3c', marginBottom: '1rem', fontWeight: 'bold' }}>{error}</div>}

                <button 
                    onClick={handleGenerate} 
                    disabled={generating}
                    style={{ background: generating ? '#95a5a6' : '#8e44ad', color: 'white', padding: '0.75rem 1.5rem', border: 'none', borderRadius: '4px', cursor: generating ? 'not-allowed' : 'pointer', fontWeight: 'bold', fontSize: '1rem' }}
                >
                    {generating ? '⏳ Đang phân tích và sinh AI...' : '✨ Tạo Testcase bằng AI'}
                </button>
            </div>

            {/* Results Preview Section */}
            {result && (
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', overflowX: 'auto' }}>
                    <h3 style={{ marginTop: 0, color: '#27ae60' }}>🎉 Kết quả Sinh ({result.length} Testcases)</h3>
                    <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ background: '#f8f9fa' }}>
                                <th style={{ border: '1px solid #ddd', padding: '8px', width: '5%' }}>ID</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px', width: '20%' }}>Tiêu đề</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px', width: '20%' }}>Tiền đề</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px', width: '30%' }}>Steps</th>
                                <th style={{ border: '1px solid #ddd', padding: '8px', width: '25%' }}>Mong đợi</th>
                            </tr>
                        </thead>
                        <tbody>
                            {result.map((tc, idx) => (
                                <tr key={idx}>
                                    <td style={{ border: '1px solid #ddd', padding: '8px', fontWeight: 'bold' }}>{tc.test_id || idx + 1}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px' }}>{tc.title}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px', whiteSpace: 'pre-wrap' }}>{tc.precondition}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px', whiteSpace: 'pre-wrap' }}>{tc.steps}</td>
                                    <td style={{ border: '1px solid #ddd', padding: '8px', whiteSpace: 'pre-wrap' }}>{tc.expected_result}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    
                    <button style={{ marginTop: '1.5rem', background: '#3498db', color: 'white', padding: '0.6rem 1.2rem', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                        💾 Lưu vào CSDL
                    </button>
                </div>
            )}
        </div>
    );
};

export default TestCaseGenerator;
