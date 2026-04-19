import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import SpecCreator from './pages/SpecCreator';
import SpecDiffViewer from './pages/SpecDiffViewer';
import DefectAnalytics from './pages/DefectAnalytics';
import TestCaseGenerator from './pages/TestCaseGenerator';
import ChatbotUI from './components/ChatbotUI';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import SpecViewer from './pages/SpecViewer';
import UserManagement from './pages/UserManagement';
import Sidebar from './components/Sidebar';
import RoleRoute from './components/RoleRoute';

function App() {
    const [sessionToken, setSessionToken] = useState<string | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            setSessionToken(token);
        }
    }, []);

    return (
        <Router>
            <Routes>
                <Route path="/login" element={!sessionToken ? <Login /> : <Navigate to="/" />} />

                <Route path="/*" element={
                    sessionToken ? (
                        <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'sans-serif' }}>
                            <Sidebar />

                            {/* Main Content */}
                            <div style={{ flex: 1, padding: '2rem', background: '#ecf0f1', overflowY: 'auto', maxHeight: '100vh' }}>
                                <Routes>
                                    <Route path="/" element={<Dashboard />} />
                                    <Route path="/specs/view/:id" element={<SpecViewer />} />
                                    
                                    <Route element={<RoleRoute allowedRoles={['admin', 'qa_lead', 'tester']} />}>
                                        <Route path="/specs/new" element={<SpecCreator />} />
                                        <Route path="/specs/diff" element={<SpecDiffViewer />} />
                                        <Route path="/testcases/generate" element={<TestCaseGenerator />} />
                                    </Route>

                                    {/* Chỉ QA Lead & Admin được xem /analytics */}
                                    <Route element={<RoleRoute allowedRoles={['admin', 'qa_lead']} />}>
                                        <Route path="/analytics" element={<DefectAnalytics />} />
                                    </Route>

                                    {/* Chỉ Admin được xem quản lý User */}
                                    <Route element={<RoleRoute allowedRoles={['admin']} />}>
                                        <Route path="/users" element={<UserManagement />} />
                                    </Route>
                                </Routes>
                            </div>

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
