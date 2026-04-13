import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import axios from 'axios';
import { Link } from 'react-router-dom';

const Dashboard: React.FC = () => {
    const [roleInfo, setRoleInfo] = useState<{ role: string, is_mentor: boolean } | null>(null);
    const [defects, setDefects] = useState<any[]>([]);
    const [specs, setSpecs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const initData = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession();
                if (!session) return;

                // Fetch User Role Mapping
                const { data: userRecord } = await supabase
                    .from('users')
                    .select('role, is_mentor')
                    .eq('id', session.user.id)
                    .single();

                if (userRecord) setRoleInfo(userRecord);

                // Fetch Data from Backend
                const token = session.access_token;
                const config = { headers: { Authorization: `Bearer ${token}` } };

                const [defRes, specRes] = await Promise.all([
                    axios.get('http://localhost:8000/api/defects/', config),
                    axios.get('http://localhost:8000/api/specs/', config)
                ]);

                setDefects(defRes.data);
                setSpecs(specRes.data);

            } catch (err) {
                console.error('Failed to load dashboard data:', err);
            } finally {
                setLoading(false);
            }
        };

        initData();
    }, []);

    if (loading) return <div>Đang tải dữ liệu...</div>;

    return (
        <div>
            <h1 style={{ marginBottom: '0.5rem' }}>Dashboard</h1>

            {/* Role Notice */}
            {roleInfo && (
                <div style={{ background: '#3498db', color: 'white', padding: '1rem', borderRadius: '8px', marginBottom: '2rem' }}>
                    Tuyệt vời! Bạn đã đăng nhập với vai trò: <strong>{roleInfo.role.toUpperCase()}</strong>
                    {roleInfo.is_mentor && ' (Có quyền Mentor)'}
                    <p style={{ margin: '0.5rem 0 0' }}>
                        {roleInfo.role === 'admin' && 'Bạn có toàn quyền hệ thống. Quản lý user và hệ thống tại đây.'}
                        {roleInfo.role === 'qa_lead' && 'Bạn là nhóm trưởng QA. Bạn có quyền duyệt Delivery Documents và theo dõi tiến độ tổng thể.'}
                        {roleInfo.role === 'tester' && 'Bạn là Tester. Tiến hành tạo Testcase và liên kết với Specification tại đây.'}
                        {roleInfo.role === 'intern' && 'Bạn là Thực tập sinh. Hãy đọc Specification và nhờ Mentor Review Delivery Docs của bạn nhé.'}
                    </p>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                {/* Specifications Panel */}
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0 }}>Specifications (Đồng bộ)</h3>
                    </div>
                    <hr style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #eee' }} />
                    {specs.length === 0 ? <p>Chưa có Spec nào.</p> : (
                        <ul style={{ listStyle: 'none', padding: 0 }}>
                            {specs.map(s => (
                                <li key={s.id} style={{ padding: '0.5rem', borderBottom: '1px solid #f1f2f6', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span>
                                        <strong>{s.title}</strong> (v{s.latest_version})
                                    </span>
                                    <Link to={`/specs/view/${s.id}`} style={{ textDecoration: 'none', background: '#2ecc71', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '0.85rem' }}>
                                        Xem & Dịch
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {/* Defects Panel */}
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                    <h3 style={{ margin: 0 }}>Tickets / Defects (Từ Redmine)</h3>
                    <hr style={{ margin: '1rem 0', border: 'none', borderTop: '1px solid #eee' }} />
                    {defects.length === 0 ? <p>Chưa có Defect nào.</p> : (
                        <ul style={{ listStyle: 'none', padding: 0 }}>
                            {defects.slice(0, 5).map(d => (
                                <li key={d.id} style={{ padding: '0.5rem', borderBottom: '1px solid #f1f2f6' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <span style={{ fontWeight: 500 }}>#{d.redmine_id} - {d.title}</span>
                                        <span style={{ padding: '2px 6px', background: d.status === 'open' ? '#e74c3c' : '#bdc3c7', color: 'white', borderRadius: '4px', fontSize: '0.8rem' }}>
                                            {d.status.toUpperCase()}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: '0.85rem', color: '#7f8c8d', marginTop: '4px' }}>
                                        Mức độ: {d.severity.toUpperCase()} | Thiết bị: {d.model_id}
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                    {defects.length > 5 && <Link to="/analytics" style={{ display: 'block', marginTop: '1rem', textAlign: 'center', color: '#3498db' }}>Xem Analytics...</Link>}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
