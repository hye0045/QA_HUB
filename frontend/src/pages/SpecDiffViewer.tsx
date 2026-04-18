import React, { useState } from 'react';
import api from '../lib/api';

const SpecDiffViewer: React.FC = () => {
    const [specId, setSpecId] = useState('');
    const [v1, setV1] = useState(1);
    const [v2, setV2] = useState(2);
    const [diff, setDiff] = useState<string>('');
    const [loading, setLoading] = useState(false);

    const fetchDiff = async () => {
        setLoading(true);
        try {
            // Endpoint created earlier GET /api/specs/:id/diff?v1=&v2=
            const res = await api.get(`/specs/${specId}/diff?v1=${v1}&v2=${v2}`);
            setDiff(res.data.diff);
        } catch (err) {
            console.error(err);
            setDiff('Error fetching diff');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
            <h2>Specification Diff Viewer</h2>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                <input
                    placeholder="Spec ID (UUID)"
                    value={specId}
                    onChange={(e) => setSpecId(e.target.value)}
                    style={{ padding: '0.5rem', flex: 1 }}
                />
                <input
                    type="number"
                    placeholder="Version 1"
                    value={v1}
                    onChange={(e) => setV1(Number(e.target.value))}
                    style={{ padding: '0.5rem', width: '100px' }}
                />
                <input
                    type="number"
                    placeholder="Version 2"
                    value={v2}
                    onChange={(e) => setV2(Number(e.target.value))}
                    style={{ padding: '0.5rem', width: '100px' }}
                />
                <button
                    onClick={fetchDiff}
                    style={{ padding: '0.5rem 1rem', background: '#3498db', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                    {loading ? 'Loading...' : 'Compare'}
                </button>
            </div>

            <div style={{ background: '#f8f9fa', padding: '1rem', borderRadius: '4px', minHeight: '300px', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                {diff || 'No diff to display yet.'}
            </div>
        </div>
    );
};

export default SpecDiffViewer;
