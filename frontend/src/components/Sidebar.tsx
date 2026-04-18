import React from 'react';
import { Link } from 'react-router-dom';

const Sidebar: React.FC = () => {
    const role = localStorage.getItem('role') || 'intern';
    const email = localStorage.getItem('email') || 'User';

    const handleLogout = () => {
        localStorage.clear();
        window.location.href = '/login';
    };

    return (
        <div style={{ width: '250px', background: '#2c3e50', color: 'white', padding: '1rem', display: 'flex', flexDirection: 'column' }}>
            <Link to="/" style={{ textDecoration: 'none' }}>
                <h2 style={{ color: '#e74c3c' }}>THUNDERSOFT<br />QA HUB</h2>
            </Link>
            
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '2rem', flex: 1 }}>
                <Link to="/" style={{ color: '#ecf0f1', textDecoration: 'none' }}>Dashboard</Link>
                
                {/* Dành chung cho mọi người làm testcase/spec */}
                {(role === 'tester' || role === 'qa_lead' || role === 'admin') && (
                    <Link to="/specs/diff" style={{ color: '#ecf0f1', textDecoration: 'none' }}>Spec Diff Viewer</Link>
                )}

                {/* Dành riêng cho Analytics (QA Lead, Admin) */}
                {(role === 'qa_lead' || role === 'admin') && (
                    <Link to="/analytics" style={{ color: '#ecf0f1', textDecoration: 'none' }}>Defect Analytics</Link>
                )}

                {/* Dành riêng cho User Management (Admin) */}
                {role === 'admin' && (
                    <Link to="/users" style={{ color: '#f39c12', textDecoration: 'none' }}>Quản lý Users</Link>
                )}
            </nav>
            
            <div style={{ padding: '1rem 0', borderTop: '1px solid #34495e', fontSize: '0.9rem' }}>
                <p>User: {email}</p>
                <p style={{marginTop: '0.2rem', color: '#bdc3c7'}}>Vai trò: {role.toUpperCase()}</p>
                <button
                    onClick={handleLogout}
                    style={{ background: 'transparent', color: '#e74c3c', border: '1px solid #e74c3c', padding: '0.5rem', width: '100%', borderRadius: '4px', cursor: 'pointer', marginTop: '1rem' }}
                >
                    Đăng xuất
                </button>
            </div>
        </div>
    );
};

export default Sidebar;
