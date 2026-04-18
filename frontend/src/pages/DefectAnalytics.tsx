import React from 'react';
import { useDefectsData } from '../lib/api';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const DefectAnalytics: React.FC = () => {
    // [UC_G1] Sử dụng Hook để get data thay cho call thô
    const { data: analytics, loading, error } = useDefectsData();

    // 1. Error state
    if (error) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '50vh', color: '#e74c3c' }}>
                <h2>⚠️ Oops! Lỗi đồng bộ dữ liệu</h2>
                <p>{error}</p>
            </div>
        );
    }

    // 2. Loading state
    if (loading || !analytics) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '50vh' }}>
                <div style={{ width: '40px', height: '40px', border: '4px solid #f3f3f3', borderTop: '4px solid #3498db', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                <p style={{ marginTop: '1rem', color: '#7f8c8d' }}>Đang tải dữ liệu từ Redmine...</p>
                <style>{`
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                `}</style>
            </div>
        );
    }

    // Prepare Doughnut Chart Data (By Status)
    const statusData = {
        labels: analytics.by_status.map((item: any) => item.status.toUpperCase()),
        datasets: [{
            data: analytics.by_status.map((item: any) => item.count),
            backgroundColor: ['#e74c3c', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6'],
            borderWidth: 0,
            hoverOffset: 4
        }],
    };

    const doughnutOptions = {
        cutout: '70%',
        plugins: {
            legend: { position: 'bottom' as const }
        }
    };

    // Prepare Bar Chart Data (By Assignee - Mock)
    const assigneeData = {
        labels: analytics.by_assignee.map((item: any) => item.name),
        datasets: [{
            label: 'Tổng số Lỗi (Defects)',
            data: analytics.by_assignee.map((item: any) => item.count),
            backgroundColor: '#3498db',
            borderRadius: 6,
        }],
    };

    return (
        <div>
            <h2 style={{ marginBottom: '0.5rem' }}>Đánh giá Hiệu năng QA (UC_G1)</h2>
            <p style={{ color: '#7f8c8d', marginBottom: '2rem' }}>Tổng số lỗi toàn dự án: <strong>{analytics.total}</strong></p>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '2rem' }}>
                {/* DOUGHNUT CHART */}
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                    <h3 style={{ borderBottom: '1px solid #ecf0f1', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>
                        Trạng thái Defect
                    </h3>
                    <div style={{ position: 'relative', width: '100%', maxWidth: '300px', margin: '0 auto', aspectRatio: '1/1' }}>
                        <Doughnut data={statusData} options={doughnutOptions} />
                    </div>
                </div>

                {/* BAR CHART */}
                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                    <h3 style={{ borderBottom: '1px solid #ecf0f1', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>
                        Năng suất theo Thành viên
                    </h3>
                    <div style={{ width: '100%' }}>
                        <Bar 
                            data={assigneeData} 
                            options={{ 
                                responsive: true, 
                                plugins: { legend: { display: false } },
                                scales: { y: { beginAtZero: true } }
                            }} 
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DefectAnalytics;
