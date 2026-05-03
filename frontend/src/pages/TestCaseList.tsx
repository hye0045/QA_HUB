import React, { useEffect, useState } from 'react';
import api from '../lib/api';

interface Testcase {
    id: string;
    title: string;
    description: string;
    status: string;
    model_id: string;
    test_type: string;
    created_at: string;
    steps?: string;
    expected_result?: string;
    precondition?: string;
}

const TestCaseList: React.FC = () => {
    const [testcases, setTestcases] = useState<Testcase[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedTc, setSelectedTc] = useState<Testcase | null>(null);

    useEffect(() => {
        const fetchTCs = async () => {
            try {
                const res = await api.get('/testcases/');
                setTestcases(res.data);
            } catch (err) {
                console.error("Failed to load testcases", err);
            } finally {
                setLoading(false);
            }
        };
        fetchTCs();
    }, []);

    if (loading) return <p>Đang tải danh sách Testcase...</p>;

    return (
        <div>
            <h2>Danh sách Testcase ({testcases.length})</h2>
            <div style={{ background: 'white', padding: '1rem', borderRadius: '8px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                        <tr style={{ background: '#ecf0f1' }}>
                            <th style={{ padding: '10px' }}>Title</th>
                            <th>Model</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Ngày tạo</th>
                            <th>Thao tác</th>
                        </tr>
                    </thead>
                    <tbody>
                        {testcases.map(tc => (
                            <tr key={tc.id} style={{ borderBottom: '1px solid #eee' }}>
                                <td style={{ padding: '10px' }}>{tc.title}</td>
                                <td>{tc.model_id}</td>
                                <td>{tc.test_type}</td>
                                <td>
                                    <span style={{ 
                                        padding: '4px 8px', 
                                        borderRadius: '12px', 
                                        fontSize: '0.8rem',
                                        background: tc.status === 'active' ? '#d4edda' : tc.status === 'draft' ? '#fff3cd' : '#f8d7da',
                                        color: tc.status === 'active' ? '#155724' : tc.status === 'draft' ? '#856404' : '#721c24'
                                    }}>
                                        {tc.status}
                                    </span>
                                </td>
                                <td>{new Date(tc.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button 
                                        onClick={() => setSelectedTc(tc)}
                                        style={{ background: '#3498db', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem' }}
                                    >
                                        Xem
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {testcases.length === 0 && <p style={{ textAlign: 'center', marginTop: '1rem' }}>Chưa có testcase nào.</p>}
            </div>

            {/* Modal hiển thị chi tiết Testcase */}
            {selectedTc && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', 
                    background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
                }}>
                    <div style={{ background: 'white', width: '800px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', borderRadius: '8px', padding: '2rem', position: 'relative' }}>
                        <button 
                            onClick={() => setSelectedTc(null)}
                            style={{ position: 'absolute', top: '10px', right: '15px', background: 'transparent', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                        >&times;</button>
                        
                        <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '20px', color: '#2c3e50' }}>{selectedTc.title}</h3>
                        
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '20px' }}>
                            <div><strong>Dòng máy (Model):</strong> {selectedTc.model_id || 'N/A'}</div>
                            <div><strong>Loại:</strong> {selectedTc.test_type || 'N/A'}</div>
                            <div><strong>Trạng thái:</strong> {selectedTc.status}</div>
                            <div><strong>Ngày tạo:</strong> {new Date(selectedTc.created_at).toLocaleString()}</div>
                        </div>

                        {selectedTc.description && (
                            <div style={{ marginBottom: '15px' }}>
                                <strong>Description:</strong>
                                <div style={{ background: '#f8f9fa', padding: '10px', borderRadius: '4px', marginTop: '5px', whiteSpace: 'pre-wrap' }}>{selectedTc.description}</div>
                            </div>
                        )}

                        {selectedTc.precondition && (
                            <div style={{ marginBottom: '15px' }}>
                                <strong>Tiền điều kiện (Precondition):</strong>
                                <div style={{ background: '#f8f9fa', padding: '10px', borderRadius: '4px', marginTop: '5px', whiteSpace: 'pre-wrap' }}>{selectedTc.precondition}</div>
                            </div>
                        )}

                        <div style={{ marginBottom: '15px' }}>
                            <strong>Các bước thực hiện (Steps):</strong>
                            <div style={{ background: '#f8f9fa', padding: '10px', borderRadius: '4px', marginTop: '5px', whiteSpace: 'pre-wrap' }}>{selectedTc.steps || 'N/A'}</div>
                        </div>

                        <div style={{ marginBottom: '15px' }}>
                            <strong>Kết quả mong đợi (Expected Result):</strong>
                            <div style={{ background: '#f8f9fa', padding: '10px', borderRadius: '4px', marginTop: '5px', whiteSpace: 'pre-wrap' }}>{selectedTc.expected_result || 'N/A'}</div>
                        </div>
                        
                        <div style={{ textAlign: 'right', marginTop: '20px' }}>
                            <button onClick={() => setSelectedTc(null)} style={{ padding: '8px 20px', background: '#95a5a6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Đóng</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TestCaseList;
