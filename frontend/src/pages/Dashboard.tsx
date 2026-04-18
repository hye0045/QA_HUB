import React, { useEffect, useState } from 'react';
import api, { Spec, DeliveryDoc } from '../lib/api';
import { Link } from 'react-router-dom';

// -------------------------------------------------------------------
// Sub-Components
// -------------------------------------------------------------------

const AdminDashboard = () => (
    <div style={{ background: '#34495e', color: 'white', padding: '1.5rem', borderRadius: '8px' }}>
        <h2>Xin chào, System Administrator!</h2>
        <p style={{ marginTop: '0.5rem', color: '#bdc3c7' }}>
            Bạn có quyền cao nhất hệ thống.
        </p>
        <Link
            to="/users"
            style={{ display: 'inline-block', marginTop: '1.5rem', background: '#e74c3c', color: 'white', textDecoration: 'none', padding: '0.75rem 1.5rem', borderRadius: '4px', fontWeight: 'bold' }}
        >
            Quản trị User Management →
        </Link>
    </div>
);

const QALeadDashboard = () => {
    const [delegateTarget, setDelegateTarget] = useState('');
    const [duration, setDuration] = useState('24');
    const [pendingDeliveries, setPendingDeliveries] = useState<DeliveryDoc[]>([]);

    useEffect(() => {
        api.get('/delivery/').then(res => {
            setPendingDeliveries(res.data.filter((d: DeliveryDoc) => d.status === 'pending_qa_lead'));
        }).catch(console.error);
    }, []);

    const handleDelegate = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/users/delegate', {
                tester_id: delegateTarget,
                duration_hours: parseInt(duration)
            });
            alert('Ủy quyền [Final Approve] thành công!');
            setDelegateTarget('');
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Lỗi ủy quyền');
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ background: '#27ae60', color: 'white', padding: '1.5rem', borderRadius: '8px' }}>
                <h2>Xin chào, QA Lead!</h2>
                <p>Khu vực quản lý dự án và theo dõi chất lượng.</p>
                <Link to="/analytics" style={{ display: 'inline-block', marginTop: '1rem', background: 'white', color: '#27ae60', textDecoration: 'none', padding: '0.5rem 1rem', borderRadius: '4px', fontWeight: 'bold' }}>
                    Xem Analytics Báo cáo →
                </Link>
            </div>

            {/* Pending QA Lead Approvals */}
            {pendingDeliveries.length > 0 && (
                <div style={{ background: '#e8f4f8', padding: '1.5rem', borderRadius: '8px', border: '1px solid #bee5eb' }}>
                    <h3 style={{ margin: '0 0 1rem' }}>📋 Chờ duyệt ({pendingDeliveries.length})</h3>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {pendingDeliveries.map(d => (
                            <li key={d.id} style={{ padding: '0.5rem 0', borderBottom: '1px solid #bee5eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <strong>{d.title}</strong>
                                <span style={{ background: '#17a2b8', color: 'white', padding: '3px 10px', borderRadius: '12px', fontSize: '0.8rem' }}>
                                    Chờ duyệt QA Lead
                                </span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Delegation Panel */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                <h3 style={{ marginTop: 0 }}>Ủy Quyền Tạm thời (Delegation)</h3>
                <p style={{ color: '#7f8c8d', marginBottom: '1rem' }}>
                    Cấp quyền <strong>Final Approve</strong> cho Tester khi bạn vắng mặt.
                </p>
                <form onSubmit={handleDelegate} style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <input
                        type="text"
                        placeholder="ID UUID của Tester"
                        value={delegateTarget}
                        onChange={e => setDelegateTarget(e.target.value)}
                        style={{ padding: '0.5rem', flex: 1, minWidth: '200px', borderRadius: '4px', border: '1px solid #ccc' }}
                        required
                    />
                    <select value={duration} onChange={e => setDuration(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}>
                        <option value="8">8 Giờ</option>
                        <option value="24">24 Giờ</option>
                        <option value="168">1 Tuần</option>
                    </select>
                    <button type="submit" style={{ background: '#f39c12', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                        Ủy Quyền
                    </button>
                </form>
            </div>
        </div>
    );
};

const TesterDashboard = ({ specs, defects, isMentor }: { specs: Spec[]; defects: any[]; isMentor: boolean }) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ background: '#2980b9', color: 'white', padding: '1.5rem', borderRadius: '8px' }}>
            <h2>Xin chào, Tester / Intern!</h2>
            <p>Nhiệm vụ trong ngày: Kiểm tra Specs và Verify Bugs.</p>
        </div>

        {/* Mentor Section — chỉ hiện nếu user là Mentor */}
        {isMentor && (
            <div style={{ background: '#fff3cd', border: '1px solid #ffc107', padding: '1.5rem', borderRadius: '8px' }}>
                <h3 style={{ marginTop: 0 }}>👥 Intern Management (Mentor)</h3>
                <p style={{ color: '#856404', margin: '0.5rem 0 1rem' }}>
                    Bạn đang được gán vai trò Mentor. Các Intern đang chờ bạn xem xét tài liệu.
                </p>
                <Link to={`/users/${localStorage.getItem('user_id')}/mentees`} style={{ color: '#f39c12', fontWeight: 'bold' }}>
                    Xem Danh sách Mentees →
                </Link>
            </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: '1.5rem' }}>
            {/* Specs Panel */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
                <h3 style={{ margin: 0 }}>Specifications Mới Nhất</h3>
                <hr style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #eee' }} />
                {specs.length === 0 ? <p style={{ color: '#95a5a6' }}>Chưa có Spec nào.</p> : (
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        {specs.slice(0, 5).map(s => (
                            <li key={s.id} style={{ padding: '0.5rem', borderBottom: '1px solid #f1f2f6', display: 'flex', justifyContent: 'space-between' }}>
                                <strong>{s.title}</strong>
                                <Link to={`/specs/view/${s.id}`} style={{ textDecoration: 'none', color: '#2ecc71', fontWeight: 'bold' }}>Xem</Link>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {/* Defects Panel */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
                <h3 style={{ margin: 0 }}>Defects (Redmine)</h3>
                <hr style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #eee' }} />
                {defects.length === 0 ? <p style={{ color: '#95a5a6' }}>Chưa có Defect nào.</p> : (
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        {defects.slice(0, 5).map(d => (
                            <li key={d.id} style={{ padding: '0.5rem', borderBottom: '1px solid #f1f2f6', display: 'flex', justifyContent: 'space-between' }}>
                                <span>#{d.redmine_id} - {d.title?.substring(0, 25)}...</span>
                                <span style={{ color: d.status === 'open' ? '#e74c3c' : '#bdc3c7', fontSize: '0.8rem' }}>
                                    {d.status?.toUpperCase()}
                                </span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    </div>
);

// -------------------------------------------------------------------
// Main Dashboard Dispatcher
// -------------------------------------------------------------------
const Dashboard: React.FC = () => {
    const role = localStorage.getItem('role') || 'intern';
    // Đọc is_mentor thực từ localStorage (được ghi lúc login)
    const isMentor = localStorage.getItem('is_mentor') === 'true';

    const [defects, setDefects] = useState<any[]>([]);
    const [specs, setSpecs] = useState<Spec[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (role === 'admin' || role === 'qa_lead') {
            setLoading(false);
            return;
        }

        const initData = async () => {
            try {
                const [defRes, specRes] = await Promise.all([
                    api.get('/defects/'),
                    api.get('/specs/')
                ]);
                setDefects(defRes.data);
                setSpecs(specRes.data);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Lỗi tải dữ liệu Dashboard');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        initData();
    }, [role]);

    if (loading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '50vh', color: '#7f8c8d' }}>
                Đang tải Dashboard ({role.toUpperCase()})...
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ background: '#fdecea', color: '#c0392b', padding: '1.5rem', borderRadius: '8px' }}>
                ⚠️ {error}
            </div>
        );
    }

    return (
        <div>
            {role === 'admin' && <AdminDashboard />}
            {role === 'qa_lead' && <QALeadDashboard />}
            {(role === 'tester' || role === 'intern') && (
                <TesterDashboard specs={specs} defects={defects} isMentor={isMentor} />
            )}
        </div>
    );
};

export default Dashboard;
