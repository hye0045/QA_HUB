import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const DefectAnalytics: React.FC = () => {
    const [analytics, setAnalytics] = useState<any>(null);

    useEffect(() => {
        const fetchAnalytics = async () => {
            try {
                const res = await axios.get('http://localhost:8000/api/defects/analytics');
                setAnalytics(res.data);
            } catch (err) {
                console.error(err);
            }
        };
        fetchAnalytics();
    }, []);

    if (!analytics) return <div>Loading Analytics...</div>;

    const statusData = {
        labels: Object.keys(analytics.by_status),
        datasets: [{
            data: Object.values(analytics.by_status),
            backgroundColor: ['#e74c3c', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6'],
        }],
    };

    const severityData = {
        labels: Object.keys(analytics.by_severity),
        datasets: [{
            label: 'Defects by Severity',
            data: Object.values(analytics.by_severity),
            backgroundColor: '#e67e22',
        }],
    };

    return (
        <div>
            <h2>Defect Analytics Dashboard</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '2rem' }}>
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                    <h3>Defects by Status</h3>
                    <div style={{ width: '300px', margin: '0 auto' }}>
                        <Pie data={statusData} />
                    </div>
                </div>
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                    <h3>Defects by Severity</h3>
                    <Bar data={severityData} />
                </div>
            </div>
        </div>
    );
};

export default DefectAnalytics;
