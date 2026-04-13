import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { supabase } from '../lib/supabase';

const SpecViewer: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const [spec, setSpec] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [translating, setTranslating] = useState(false);
    const [translatedText, setTranslatedText] = useState<string | null>(null);

    useEffect(() => {
        const fetchSpec = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession();
                if (!session) return;

                // Fetch specific spec config details (Assuming listed via specs API)
                const config = { headers: { Authorization: `Bearer ${session.access_token}` } };
                const res = await axios.get(`http://localhost:8000/api/specs/`, config);

                // Filter out the requested Spec because `/specs/` returns all
                // In a real app, create a `GET /specs/{id}` endpoint. For now filtering frontend is okay for POC
                const target = res.data.find((s: any) => s.id === id);
                setSpec(target);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchSpec();
    }, [id]);

    const handleTranslate = async (targetLang: string) => {
        if (!spec?.content) return;
        setTranslating(true);
        setTranslatedText('AI đang dịch tài liệu...');

        try {
            const { data: { session } } = await supabase.auth.getSession();
            const config = { headers: { Authorization: `Bearer ${session?.access_token}` } };

            const payload = {
                mode: 'translate',
                prompt: spec.content,
                target_lang: targetLang
            };

            const res = await axios.post('http://localhost:8000/api/chat', payload, config);
            setTranslatedText(res.data.response);
        } catch (err) {
            setTranslatedText('Lỗi dịch vụ dịch thuật.');
            console.error(err);
        } finally {
            setTranslating(false);
        }
    };

    if (loading) return <div>Đang tải tài liệu...</div>;
    if (!spec) return <div>Không tìm thấy Specification.</div>;

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h2>Tài liệu: {spec.title} <span style={{ fontSize: '1rem', color: '#7f8c8d' }}>(v{spec.latest_version})</span></h2>

                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button
                        onClick={() => handleTranslate('English')}
                        disabled={translating}
                        style={{ padding: '0.6rem 1rem', background: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        A→E (Dịch sang Tiếng Anh)
                    </button>
                    <button
                        onClick={() => handleTranslate('Japanese')}
                        disabled={translating}
                        style={{ padding: '0.6rem 1rem', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                    >
                        A→J (Dịch sang Tiếng Nhật)
                    </button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                {/* Original Content */}
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                    <h3 style={{ borderBottom: '2px solid #ecf0f1', paddingBottom: '0.5rem' }}>Bản Gốc ({spec.language})</h3>
                    <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', marginTop: '1rem' }}>
                        {spec.content}
                    </div>
                </div>

                {/* Translated Content */}
                <div style={{ background: '#f8f9fa', padding: '1.5rem', borderRadius: '8px', boxShadow: 'translate-panel', border: '1px solid #ecf0f1' }}>
                    <h3 style={{ borderBottom: '2px solid #ecf0f1', paddingBottom: '0.5rem', color: '#8e44ad' }}>Bản Dịch AI</h3>
                    <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', marginTop: '1rem', color: translatedText ? '#2c3e50' : '#95a5a6' }}>
                        {translatedText ? translatedText : "Bấm nút dịch ở trên để AI tiến hành phân tích và dịch tài liệu này..."}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SpecViewer;
