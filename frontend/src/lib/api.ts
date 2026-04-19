import axios from 'axios';
import { useState, useEffect } from 'react';

// -------------------------------------------------------------------
// Axios instance - baseURL lấy từ biến môi trường Vite
// -------------------------------------------------------------------
const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
    headers: { 'Content-Type': 'application/json' },
});

// -------------------------------------------------------------------
// Request Interceptor: đính JWT vào mọi request
// -------------------------------------------------------------------
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// -------------------------------------------------------------------
// Response Interceptor: tự động logout khi token hết hạn (401)
// -------------------------------------------------------------------
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token hết hạn hoặc không hợp lệ – xóa session và redirect
            localStorage.clear();
            window.location.href = '/login?reason=session_expired';
        }
        return Promise.reject(error);
    }
);

// -------------------------------------------------------------------
// TypeScript Interfaces cho API responses
// -------------------------------------------------------------------
export interface Spec {
    id: string;
    title: string;
    language: string;
    latest_version: number;
    content: string;
}

export interface Defect {
    id: string;
    redmine_id: number;
    title: string;
    status: string;
    severity: string;
    model_id: string | null;
    synced_at: string;
    // AI fields
    cleaned_description?: string;
    bug_category?: string;
    root_cause_guess?: string;
    module?: string;
}

export interface DeviceModelProfile {
    id: string;
    name: string;
    project_id: string;
    tracker_id: number;
}

export interface DeliveryDoc {
    id: string;
    title: string;
    status: 'draft' | 'pending_mentor' | 'pending_qa_lead' | 'locked';
    created_by: string;
    mentor_id: string | null;
}

export interface UserItem {
    id: string;
    email: string;
    full_name: string;
    role: string;
    is_mentor: boolean;
}

export interface AnalyticsData {
    total: number;
    by_status: { status: string; count: number }[];
    by_category: { category: string; count: number }[];
    by_model: { model: string; count: number }[];
    by_assignee: { name: string; count: number }[];
}

// -------------------------------------------------------------------
// Hook: useDefectsData
// -------------------------------------------------------------------
export const useDefectsData = () => {
    const [data, setData] = useState<AnalyticsData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;
        const fetchData = async () => {
            try {
                setLoading(true);
                const res = await api.get('/defects/analytics');
                if (isMounted) {
                    setData(res.data);
                    setError(null);
                }
            } catch (err: any) {
                if (isMounted) {
                    setError(err.response?.data?.detail || 'Lỗi khi tải dữ liệu từ máy chủ Redmine');
                }
            } finally {
                if (isMounted) setLoading(false);
            }
        };
        fetchData();
        return () => { isMounted = false; };
    }, []);

    return { data, loading, error };
};

export default api;
