import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { supabase } from './lib/supabase';
import SpecDiffViewer from './pages/SpecDiffViewer';
import DefectAnalytics from './pages/DefectAnalytics';
import ChatbotUI from './components/ChatbotUI';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import SpecViewer from './pages/SpecViewer';

function App() {
    const [session, setSession] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        supabase.auth.getSession().then(({ data: { session } }) => {
            setSession(session);
            setLoading(false);
        });

        const {
            data: { subscription },
        } = supabase.auth.onAuthStateChange((_event, session) => {
            setSession(session);
        });

        return () => subscription.unsubscribe();
    }, []);

    if (loading) {
        return <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center' }}>Loading...</div>;
    }

    return (
        <Router>
            <Routes>
                <Route path="/login" element={!session ? <Login /> : <Navigate to="/" />} />

                <Route path="/*" element={
                    session ? (
                        <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'sans-serif' }}>
                            {/* Sidebar */}
                            <div style={{ width: '250px', background: '#2c3e50', color: 'white', padding: '1rem', display: 'flex', flexDirection: 'column' }}>
                                <Link to="/" style={{ textDecoration: 'none' }}><h2 style={{ color: '#e74c3c' }}>THUNDERSOFT<br />QA HUB</h2></Link>
                                <nav style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '2rem', flex: 1 }}>
                                    <Link to="/" style={{ color: '#ecf0f1', textDecoration: 'none' }}>Dashboard</Link>
                                    <Link to="/specs/diff" style={{ color: '#ecf0f1', textDecoration: 'none' }}>Spec Diff Viewer</Link>
                                    <Link to="/analytics" style={{ color: '#ecf0f1', textDecoration: 'none' }}>Defect Analytics</Link>
                                </nav>
                                <div style={{ padding: '1rem 0', borderTop: '1px solid #34495e', fontSize: '0.9rem' }}>
                                    <p>User: {session.user.email}</p>
                                    <button
                                        onClick={() => supabase.auth.signOut()}
                                        style={{ background: 'transparent', color: '#e74c3c', border: '1px solid #e74c3c', padding: '0.5rem', width: '100%', borderRadius: '4px', cursor: 'pointer', marginTop: '0.5rem' }}
                                    >
                                        Đăng xuất
                                    </button>
                                </div>
                            </div>

                            {/* Main Content */}
                            <div style={{ flex: 1, padding: '2rem', background: '#ecf0f1', overflowY: 'auto', maxHeight: '100vh' }}>
                                <Routes>
                                    <Route path="/" element={<Dashboard />} />
                                    <Route path="/specs/view/:id" element={<SpecViewer />} />
                                    <Route path="/specs/diff" element={<SpecDiffViewer />} />
                                    <Route path="/analytics" element={<DefectAnalytics />} />
                                </Routes>
                            </div>

                            {/* Floating Chatbot */}
                            <ChatbotUI />
                        </div>
                    ) : (
                        <Navigate to="/login" />
                    )
                } />
            </Routes>
        </Router>
    );
}

export default App;
