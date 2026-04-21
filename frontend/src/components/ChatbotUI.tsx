import React, { useState } from 'react';
import api, { useAIStatus } from '../lib/api';

const ChatbotUI: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<{ role: string, text: string }[]>([]);
    const [input, setInput] = useState('');
    const [mode, setMode] = useState('qa'); // qa, translate, suggest
    const [loading, setLoading] = useState(false);
    const { status } = useAIStatus();

    const sendMessage = async () => {
        if (!input.trim()) return;

        // Chặn nếu AI chưa sẵn sàng
        if (status && !status.ai_features_enabled) {
            setMessages(prev => [...prev, {
                role: 'ai',
                text: `⚠️ ${status.status_message}\n\nVui lòng đợi model tải xong rồi thử lại.`
            }]);
            return;
        }

        setMessages(prev => [...prev, { role: 'user', text: input }]);
        const currentInput = input;
        setInput('');
        setLoading(true);

        try {
            const res = await api.post('/chat', {
                mode,
                prompt: currentInput,
                source_lang: mode === 'translate' ? 'Japanese' : undefined,
                target_lang: mode === 'translate' ? 'English' : undefined
            });
            setMessages(prev => [...prev, { role: 'ai', text: res.data.response }]);
        } catch (err: any) {
            const detail = err.response?.data?.detail || err.message || 'Lỗi không xác định';
            setMessages(prev => [...prev, { role: 'ai', text: `❌ ${detail}` }]);
        } finally {
            setLoading(false);
        }
    };

    const aiReady = status?.ai_features_enabled ?? true; // mặc định ok nếu chưa load xong

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                title={aiReady ? 'AI Chat' : (status?.status_message || 'AI chưa sẵn sàng')}
                style={{
                    position: 'fixed', bottom: '2rem', right: '2rem',
                    padding: '1rem', borderRadius: '50%',
                    background: aiReady ? '#9b59b6' : '#e67e22',
                    color: 'white', border: 'none', cursor: 'pointer',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.2)',
                    fontSize: '1.2rem',
                }}
            >
                {aiReady ? '💬' : '⚠️'}
            </button>
        );
    }

    return (
        <div style={{ position: 'fixed', bottom: '2rem', right: '2rem', width: '370px', height: '520px', background: 'white', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div style={{ background: aiReady ? '#9b59b6' : '#e67e22', color: 'white', padding: '1rem', borderRadius: '8px 8px 0 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h3 style={{ margin: 0, fontSize: '1rem' }}>QA HUB Assistant</h3>
                    {!aiReady && <div style={{ fontSize: '0.7rem', opacity: 0.9, marginTop: '2px' }}>⚠️ AI đang tải...</div>}
                </div>
                <button onClick={() => setIsOpen(false)} style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1.1rem' }}>✖</button>
            </div>

            {/* AI Status notice */}
            {!aiReady && status && (
                <div style={{ background: '#fff3cd', color: '#856404', padding: '0.5rem 0.75rem', fontSize: '0.8rem', borderBottom: '1px solid #ffc107' }}>
                    {status.status_message}
                    {status.available_models.length > 0 && (
                        <span> · Có sẵn: <strong>{status.available_models.join(', ')}</strong></span>
                    )}
                </div>
            )}

            {/* Mode Selector */}
            <div style={{ padding: '0.5rem', borderBottom: '1px solid #eee', display: 'flex', gap: '0.5rem' }}>
                <select value={mode} onChange={e => setMode(e.target.value)} style={{ padding: '0.25rem', width: '100%' }}>
                    <option value="qa">QA / Query</option>
                    <option value="translate">Dịch thuật (JA→EN)</option>
                    <option value="suggest">Gợi ý Testcase</option>
                </select>
            </div>

            {/* Chat Area */}
            <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {messages.length === 0 && (
                    <div style={{ color: '#adb5bd', fontSize: '0.85rem', textAlign: 'center', marginTop: '2rem' }}>
                        {aiReady ? '👋 Xin chào! Tôi có thể giúp gì?' : '⏳ Đang chờ AI sẵn sàng...'}
                    </div>
                )}
                {messages.map((m, i) => (
                    <div key={i} style={{
                        alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                        background: m.role === 'user' ? '#9b59b6' : '#f1f2f6',
                        color: m.role === 'user' ? 'white' : 'black',
                        padding: '0.5rem 1rem', borderRadius: '8px', maxWidth: '85%',
                        whiteSpace: 'pre-wrap', fontSize: '0.9rem',
                    }}>
                        {m.text}
                    </div>
                ))}
                {loading && <div style={{ alignSelf: 'flex-start', color: '#9b59b6', fontSize: '0.9rem' }}>⏳ AI đang xử lý...</div>}
            </div>

            {/* Input */}
            <div style={{ padding: '0.75rem', borderTop: '1px solid #eee', display: 'flex', gap: '0.5rem' }}>
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                    placeholder={aiReady ? 'Nhập câu hỏi...' : 'AI chưa sẵn sàng...'}
                    disabled={loading}
                    style={{ flex: 1, padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', opacity: loading ? 0.7 : 1 }}
                />
                <button
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    style={{ background: '#9b59b6', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}
                >
                    Gửi
                </button>
            </div>
        </div>
    );
};

export default ChatbotUI;

