import React, { useState } from 'react';
import axios from 'axios';

const ChatbotUI: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<{ role: string, text: string }[]>([]);
    const [input, setInput] = useState('');
    const [mode, setMode] = useState('qa'); // qa, translate, suggest
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim()) return;

        setMessages(prev => [...prev, { role: 'user', text: input }]);
        const currentInput = input;
        setInput('');
        setLoading(true);

        try {
            const res = await axios.post('http://localhost:8000/api/chat', {
                mode,
                prompt: currentInput,
                source_lang: mode === 'translate' ? 'Japanese' : undefined,
                target_lang: mode === 'translate' ? 'English' : undefined
            });

            setMessages(prev => [...prev, { role: 'ai', text: res.data.response }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'ai', text: 'Error connecting to AI' }]);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                style={{ position: 'fixed', bottom: '2rem', right: '2rem', padding: '1rem', borderRadius: '50%', background: '#9b59b6', color: 'white', border: 'none', cursor: 'pointer', boxShadow: '0 4px 6px rgba(0,0,0,0.2)' }}
            >
                💬 AI
            </button>
        );
    }

    return (
        <div style={{ position: 'fixed', bottom: '2rem', right: '2rem', width: '350px', height: '500px', background: 'white', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div style={{ background: '#9b59b6', color: 'white', padding: '1rem', borderRadius: '8px 8px 0 0', display: 'flex', justifyContent: 'space-between' }}>
                <h3 style={{ margin: 0 }}>QA HUB Assistant</h3>
                <button onClick={() => setIsOpen(false)} style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}>✖</button>
            </div>

            {/* Mode Selector */}
            <div style={{ padding: '0.5rem', borderBottom: '1px solid #eee', display: 'flex', gap: '0.5rem' }}>
                <select value={mode} onChange={e => setMode(e.target.value)} style={{ padding: '0.25rem', width: '100%' }}>
                    <option value="qa">QA / Query</option>
                    <option value="translate">Translate (JA to EN)</option>
                    <option value="suggest">Testcase Suggestion</option>
                </select>
            </div>

            {/* Chat Area */}
            <div style={{ flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {messages.map((m, i) => (
                    <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', background: m.role === 'user' ? '#3498db' : '#f1f2f6', color: m.role === 'user' ? 'white' : 'black', padding: '0.5rem 1rem', borderRadius: '8px', maxWidth: '80%' }}>
                        {m.text}
                    </div>
                ))}
                {loading && <div style={{ alignSelf: 'flex-start', color: '#999' }}>AI typing...</div>}
            </div>

            {/* Input */}
            <div style={{ padding: '1rem', borderTop: '1px solid #eee', display: 'flex', gap: '0.5rem' }}>
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && sendMessage()}
                    placeholder="Ask something..."
                    style={{ flex: 1, padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
                />
                <button onClick={sendMessage} style={{ background: '#9b59b6', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>Send</button>
            </div>
        </div>
    );
};

export default ChatbotUI;
