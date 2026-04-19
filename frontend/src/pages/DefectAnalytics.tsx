import React, { useState, useEffect } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Pie } from 'react-chartjs-2';
import api, { useDefectsData, Defect, DeviceModelProfile } from '../lib/api';

ChartJS.register(ArcElement, Tooltip, Legend);

const DefectAnalytics: React.FC = () => {
    const { data, loading, error } = useDefectsData();
    const [defectsList, setDefectsList] = useState<Defect[]>([]);
    const [profiles, setProfiles] = useState<DeviceModelProfile[]>([]);
    const [selectedProfile, setSelectedProfile] = useState<string>('');
    
    const [syncing, setSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState<string | null>(null);

    // Form thêm Model mới
    const [showAddForm, setShowAddForm] = useState(false);
    const [newName, setNewName] = useState('');
    const [newProjectId, setNewProjectId] = useState('');
    const [newTrackerId, setNewTrackerId] = useState(38);
    const [addingProfile, setAddingProfile] = useState(false);

    const fetchDataList = async () => {
        try {
            const listRes = await api.get('/defects/');
            setDefectsList(listRes.data);
            
            const profRes = await api.get('/defects/profiles');
            setProfiles(profRes.data);
            if (profRes.data.length > 0 && !selectedProfile) {
                setSelectedProfile(profRes.data[0].id);
            }
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        fetchDataList();
    }, []);

    const handleAddProfile = async () => {
        if (!newName.trim() || !newProjectId.trim()) {
            setSyncMessage('❌ Tên Model và Project ID là bắt buộc!');
            return;
        }
        setAddingProfile(true);
        try {
            await api.post('/defects/profiles', {
                name: newName,
                project_id: newProjectId,
                tracker_id: newTrackerId
            });
            setSyncMessage(`✅ Đã thêm Model "${newName}" thành công!`);
            setNewName('');
            setNewProjectId('');
            setNewTrackerId(38);
            setShowAddForm(false);
            await fetchDataList();
        } catch (err: any) {
            setSyncMessage(`❌ Lỗi thêm Model: ${err.response?.data?.detail || err.message}`);
        } finally {
            setAddingProfile(false);
        }
    };

    const handleSync = async () => {
        if (!selectedProfile) {
            setSyncMessage('❌ Vui lòng chọn Model để Sync');
            return;
        }

        setSyncing(true);
        setSyncMessage(null);
        try {
            const res = await api.post('/defects/sync', { profile_id: selectedProfile });
            setSyncMessage(res.data.message || 'Đồng bộ thành công!');
            await fetchDataList();
        } catch (err: any) {
            setSyncMessage(`❌ Lỗi: ${err.response?.data?.detail || err.message}`);
        } finally {
            setSyncing(false);
        }
    };

    if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Đang tải dữ liệu biểu đồ...</div>;
    if (error) return <div style={{ background: '#fdecea', color: '#c0392b', padding: '1rem' }}>Lỗi tải dữ liệu: {error}</div>;
    if (!data) return <div>Không có dữ liệu.</div>;

    const categoryLabels = data.by_category.map(item => item.category);
    const categoryValues = data.by_category.map(item => item.count);

    const chartData = {
        labels: categoryLabels.length ? categoryLabels : ['Chưa có dữ liệu phân loại'],
        datasets: [
            {
                label: 'Số lượng Bug',
                data: categoryValues.length ? categoryValues : [1],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                ],
                borderWidth: 1,
            },
        ],
    };

    return (
        <div style={{ padding: '1rem' }}>
            {/* Header + Sync Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
                <h2 style={{ margin: 0 }}>📊 Analytics Defect & AI Classification</h2>
                
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <select 
                        value={selectedProfile} 
                        onChange={e => setSelectedProfile(e.target.value)}
                        style={{ padding: '0.6rem', borderRadius: '4px', border: '1px solid #ccc', fontWeight: 'bold', minWidth: '200px' }}
                    >
                        <option value="" disabled>-- Chọn Model --</option>
                        {profiles.map(p => (
                            <option key={p.id} value={p.id}>{p.name} (Prj: {p.project_id})</option>
                        ))}
                    </select>

                    <button
                        onClick={() => setShowAddForm(!showAddForm)}
                        style={{ background: '#8e44ad', color: 'white', padding: '0.6rem 0.8rem', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1rem' }}
                        title="Thêm Model mới"
                    >
                        ＋
                    </button>

                    <button
                        onClick={handleSync}
                        disabled={syncing || !selectedProfile}
                        style={{ background: syncing ? '#95a5a6' : '#27ae60', color: 'white', padding: '0.6rem 1.2rem', border: 'none', borderRadius: '4px', cursor: syncing ? 'not-allowed' : 'pointer', fontWeight: 'bold' }}
                    >
                        {syncing ? '⏳ AI đang phân tích...' : '🔄 Sync & Phân Loại AI'}
                    </button>
                </div>
            </div>

            {/* Add Model Form (inline, toggleable) */}
            {showAddForm && (
                <div style={{ background: '#f5f0ff', padding: '1.5rem', borderRadius: '8px', marginBottom: '1rem', border: '2px solid #8e44ad' }}>
                    <h4 style={{ marginTop: 0, color: '#8e44ad' }}>➕ Thêm Dòng Máy / Project Redmine Mới</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 120px auto', gap: '0.5rem', alignItems: 'end' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Tên Model</label>
                            <input
                                value={newName}
                                onChange={e => setNewName(e.target.value)}
                                placeholder="VD: Samsung S24 Ultra"
                                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Project ID (Redmine)</label>
                            <input
                                value={newProjectId}
                                onChange={e => setNewProjectId(e.target.value)}
                                placeholder="VD: eb1242"
                                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 'bold' }}>Tracker ID</label>
                            <input
                                type="number"
                                value={newTrackerId}
                                onChange={e => setNewTrackerId(parseInt(e.target.value) || 38)}
                                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
                            />
                        </div>
                        <button
                            onClick={handleAddProfile}
                            disabled={addingProfile}
                            style={{ background: '#8e44ad', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', height: '38px' }}
                        >
                            {addingProfile ? '...' : 'Lưu'}
                        </button>
                    </div>
                </div>
            )}

            {syncMessage && (
                <div style={{ background: syncMessage.startsWith('❌') ? '#fdecea' : '#e8f4f8', color: syncMessage.startsWith('❌') ? '#c0392b' : '#17a2b8', padding: '1rem', borderRadius: '4px', marginBottom: '1rem', fontWeight: 'bold' }}>
                    {syncMessage}
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: '2rem', marginBottom: '2rem' }}>
                {/* Chart Box */}
                <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                    <h3 style={{ textAlign: 'center', margin: '0 0 1rem' }}>Tỷ lệ Bug theo Phân loại (AI)</h3>
                    <div style={{ width: '100%', maxWidth: '350px', margin: '0 auto' }}>
                        <Pie data={chartData} />
                    </div>
                </div>

                {/* Summary Box */}
                <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                    <h3 style={{ marginTop: 0 }}>Thống kê Nhanh</h3>
                    <p style={{ margin: '0.5rem 0' }}><strong>Tổng số Bug lưu trữ:</strong> <span style={{ color: '#e74c3c', fontSize: '1.2rem', fontWeight: 'bold' }}>{data.total}</span></p>
                    <hr style={{ border: 'none', borderTop: '1px solid #ecf0f1', margin: '1rem 0' }} />
                    <h4 style={{ margin: '0 0 0.5rem' }}>Trạng thái</h4>
                    <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
                        {data.by_status.map(s => (
                            <li key={s.status} style={{ padding: '0.2rem 0' }}>{s.status.toUpperCase()}: <strong>{s.count}</strong></li>
                        ))}
                    </ul>
                    <hr style={{ border: 'none', borderTop: '1px solid #ecf0f1', margin: '1rem 0' }} />
                    <h4 style={{ margin: '0 0 0.5rem' }}>Danh sách Model đã cấu hình</h4>
                    <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
                        {profiles.map(p => (
                            <li key={p.id} style={{ padding: '0.2rem 0', fontSize: '0.9rem' }}>
                                <strong>{p.name}</strong> <span style={{ color: '#7f8c8d' }}>(project: {p.project_id}, tracker: {p.tracker_id})</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            {/* AI Bug List Data Table */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', overflowX: 'auto' }}>
                <h3 style={{ marginTop: 0, color: '#34495e' }}>🧠 Danh sách Bug kèm Chẩn đoán của AI</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem', textAlign: 'left', minWidth: '900px' }}>
                    <thead>
                        <tr style={{ background: '#f8f9fa', color: '#2c3e50' }}>
                            <th style={{ border: '1px solid #ddd', padding: '10px' }}>REDMINE ID</th>
                            <th style={{ border: '1px solid #ddd', padding: '10px' }}>MODEL</th>
                            <th style={{ border: '1px solid #ddd', padding: '10px' }}>PHÂN LOẠI (AI)</th>
                            <th style={{ border: '1px solid #ddd', padding: '10px' }}>TIÊU ĐỀ REDMINE</th>
                            <th style={{ border: '1px solid #ddd', padding: '10px' }}>MÔ TẢ NGẮN (AI)</th>
                            <th style={{ border: '1px solid #ddd', padding: '10px' }}>PHỎNG ĐOÁN LỖI (AI)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {defectsList.length === 0 ? (
                            <tr><td colSpan={6} style={{ padding: '1rem', textAlign: 'center', color: '#7f8c8d' }}>Chưa có Bug nào được phân tích. Chọn Model rồi bấm "Sync".</td></tr>
                        ) : (
                            defectsList.map(defect => (
                                <tr key={defect.id} style={{ borderBottom: '1px solid #ecf0f1' }}>
                                    <td style={{ padding: '10px', fontWeight: 'bold' }}>
                                        <a href={`https://redhornet.csg.kyocera.co.jp/redmine/issues/${defect.redmine_id}`} target="_blank" rel="noreferrer" style={{ color: '#3498db' }}>
                                            #{defect.redmine_id}
                                        </a>
                                    </td>
                                    <td style={{ padding: '10px', fontSize: '0.85rem', color: '#7f8c8d' }}>{defect.model_id || '---'}</td>
                                    <td style={{ padding: '10px' }}>
                                        {defect.bug_category ? (
                                            <span style={{ background: '#e8f4f8', color: '#2980b9', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem', fontWeight: 'bold' }}>
                                                {defect.bug_category}
                                            </span>
                                        ) : (
                                            <span style={{ color: '#bdc3c7' }}>Chưa phân loại</span>
                                        )}
                                    </td>
                                    <td style={{ padding: '10px' }}>{defect.title}</td>
                                    <td style={{ padding: '10px', fontSize: '0.9rem', color: '#555', whiteSpace: 'pre-wrap' }}>{defect.cleaned_description || '---'}</td>
                                    <td style={{ padding: '10px', fontSize: '0.9rem', color: '#d35400' }}>{defect.root_cause_guess || '---'}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default DefectAnalytics;
