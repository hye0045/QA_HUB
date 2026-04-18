import React, { useState } from 'react';
import api from '../lib/api';
import { useNavigate } from 'react-router-dom';
import './Login.css';

const Login: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const params = new URLSearchParams();
            params.append('username', email); // FastAPI OAuth2 format requires 'username'
            params.append('password', password);
            
            const res = await api.post('/auth/login', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            if (res.data.access_token) {
                localStorage.setItem('token', res.data.access_token);
                localStorage.setItem('role', res.data.role);
                localStorage.setItem('email', email);
                // Trigger a full reload to sync state in App.tsx easily
                window.location.href = '/';
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Đăng nhập thất bại. Vui lòng kiểm tra lại.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            {/* Kính trong suốt (Glassmorphism) */}
            <div className="glass-panel">
                <h2 className="login-title">QA HUB</h2>
                <p className="login-subtitle">Đăng nhập để tiếp tục</p>

                {error && <div className="error-message">{error}</div>}

                <form onSubmit={handleLogin} className="login-form">
                    <div className="input-group">
                        <label>Email</label>
                        <input
                            type="email"
                            placeholder="nhanvien@thundersoft.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label>Mật khẩu</label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button type="submit" className="login-button" disabled={loading}>
                        {loading ? 'Đang xử lý...' : 'Đăng nhập'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Login;
