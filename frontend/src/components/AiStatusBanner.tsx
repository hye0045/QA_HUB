import React from 'react';
import { useAIStatus } from '../lib/api';

interface Props {
    /** Nếu true, chỉ hiện banner khi AI KHÔNG sẵn sàng */
    onlyShowWhenUnavailable?: boolean;
    compact?: boolean;
}

/**
 * Banner hiển thị trạng thái AI (Ollama) hiện tại.
 * Tự động polling mỗi 30s.
 */
const AiStatusBanner: React.FC<Props> = ({ onlyShowWhenUnavailable = true, compact = false }) => {
    const { status, loading, refetch } = useAIStatus();

    if (loading) {
        return (
            <div style={bannerStyle('#f8f9fa', '#6c757d', compact)}>
                ⏳ Đang kiểm tra trạng thái AI...
            </div>
        );
    }

    if (!status) return null;

    // Nếu AI đang OK và chỉ muốn hiển thị khi lỗi → ẩn
    if (onlyShowWhenUnavailable && status.ai_features_enabled) return null;

    const bg = status.ai_features_enabled
        ? '#d4edda'
        : status.server_running
        ? '#fff3cd'
        : '#fdecea';

    const color = status.ai_features_enabled
        ? '#155724'
        : status.server_running
        ? '#856404'
        : '#c0392b';

    return (
        <div style={bannerStyle(bg, color, compact)}>
            <span>{status.status_message}</span>
            {!status.model_ready && status.server_running && status.available_models.length > 0 && (
                <span style={{ marginLeft: '1rem', fontSize: '0.85em', opacity: 0.8 }}>
                    (Model có sẵn: {status.available_models.join(', ')})
                </span>
            )}
            {!status.model_ready && !compact && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.85em' }}>
                    💡 Hướng dẫn: Mở terminal → chạy{' '}
                    <code style={{ background: 'rgba(0,0,0,0.1)', padding: '0 4px', borderRadius: '3px' }}>
                        {status.server_running
                            ? `ollama pull ${status.model_name || 'qwen2.5:0.5b'}`
                            : 'ollama serve'}
                    </code>
                </div>
            )}
            <button
                onClick={refetch}
                title="Kiểm tra lại"
                style={{
                    marginLeft: '1rem',
                    padding: '0.2rem 0.6rem',
                    border: `1px solid ${color}`,
                    borderRadius: '4px',
                    background: 'transparent',
                    color,
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    opacity: 0.8,
                    flexShrink: 0,
                }}
            >
                🔄 Kiểm tra lại
            </button>
        </div>
    );
};

function bannerStyle(bg: string, color: string, compact: boolean): React.CSSProperties {
    return {
        display: 'flex',
        alignItems: compact ? 'center' : 'flex-start',
        flexDirection: compact ? 'row' : 'column',
        flexWrap: 'wrap',
        gap: '0.5rem',
        background: bg,
        color,
        padding: compact ? '0.5rem 1rem' : '0.75rem 1rem',
        borderRadius: '6px',
        marginBottom: '1rem',
        fontSize: '0.9rem',
        border: `1px solid ${color}33`,
    };
}

export default AiStatusBanner;
