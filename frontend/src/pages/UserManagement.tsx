import React, { useEffect, useState } from 'react';
import api from '../lib/api';

const UserManagement: React.FC = () => {
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Form states
    const [email, setEmail] = useState('');
    const [fullName, setFullName] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('tester');

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const res = await api.get('/users/');
            setUsers(res.data);
            setError(null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Lỗi khi tải danh sách User');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleCreateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.post('/users/', {
                email,
                full_name: fullName,
                password,
                role
            });
            setEmail('');
            setFullName('');
            setPassword('');
            setRole('tester');
            fetchUsers(); // Refresh list
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Lỗi khi tạo user');
        }
    };

    const handleDeleteUser = async (id: string) => {
        if (!window.confirm("Bạn có chắc chắn muốn xóa user này không?")) return;
        try {
            await api.delete(`/users/${id}`);
            fetchUsers();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Lỗi khi xóa user');
        }
    };

    if (loading) return <div>Đang tải dữ liệu Users...</div>;
    if (error) return <div style={{ color: 'red' }}>{error}</div>;

    return (
        <div>
            <h2>Quản lý Người dùng (Admin Only)</h2>
            
            {/* Form tạo mới */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', marginBottom: '2rem', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                <h3>Tạo Tài khoản mới</h3>
                <form onSubmit={handleCreateUser} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
                    <input required type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }} />
                    <input required type="text" placeholder="Họ và Tên" value={fullName} onChange={e => setFullName(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }} />
                    <input required type="password" placeholder="Mật khẩu" value={password} onChange={e => setPassword(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }} />
                    <select value={role} onChange={e => setRole(e.target.value)} style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}>
                        <option value="intern">Intern</option>
                        <option value="tester">Tester</option>
                        <option value="qa_lead">QA Lead</option>
                        <option value="admin">Admin</option>
                    </select>
                    <button type="submit" style={{ gridColumn: 'span 2', padding: '0.75rem', background: '#2ecc71', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                        + TẠO TÀI KHOẢN
                    </button>
                </form>
            </div>

            {/* Danh sách */}
            <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                <h3>Danh sách User hệ thống</h3>
                <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
                    <thead>
                        <tr style={{ background: '#f8f9fa', textAlign: 'left' }}>
                            <th style={{ padding: '0.75rem', borderBottom: '2px solid #dee2e6' }}>Email</th>
                            <th style={{ padding: '0.75rem', borderBottom: '2px solid #dee2e6' }}>Tên</th>
                            <th style={{ padding: '0.75rem', borderBottom: '2px solid #dee2e6' }}>Phân quyền</th>
                            <th style={{ padding: '0.75rem', borderBottom: '2px solid #dee2e6' }}>Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map(u => (
                            <tr key={u.id} style={{ borderBottom: '1px solid #eee' }}>
                                <td style={{ padding: '0.75rem' }}>{u.email}</td>
                                <td style={{ padding: '0.75rem' }}>{u.full_name}</td>
                                <td style={{ padding: '0.75rem' }}>
                                    <span style={{ background: u.role === 'admin' ? '#e74c3c' : '#3498db', color: 'white', padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem' }}>
                                        {u.role.toUpperCase()}
                                    </span>
                                </td>
                                <td style={{ padding: '0.75rem' }}>
                                    <button 
                                        onClick={() => handleDeleteUser(u.id)}
                                        style={{ background: '#e74c3c', color: 'white', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default UserManagement;
