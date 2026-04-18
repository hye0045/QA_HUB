import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

interface RoleRouteProps {
    allowedRoles: string[];
}

const RoleRoute: React.FC<RoleRouteProps> = ({ allowedRoles }) => {
    const role = localStorage.getItem('role');

    // Nếu không có role (chưa login) hoặc role không nằm trong mảng cho phép
    if (!role || !allowedRoles.includes(role)) {
        return <Navigate to="/" replace />;
    }

    // Nếu hợp lệ, render component con (Outlet dùng cho nested routes)
    return <Outlet />;
};

export default RoleRoute;
