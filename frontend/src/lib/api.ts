import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request interceptor for adding the JWT token
import { useState, useEffect } from 'react';

// ... existing code ...
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export const useDefectsData = () => {
    const [data, setData] = useState<any>(null);
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
                    setError(err.response?.data?.detail || "Lỗi khi tải dữ liệu từ máy chủ Redmine");
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
