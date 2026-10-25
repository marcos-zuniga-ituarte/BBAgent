import { useToastTimer } from '../../hooks/useToastTimer.js'

function ErrorToast({ message, visible, onClose, duration = 4000 }) {
    const { handleMouseEnter, handleMouseLeave } = useToastTimer({ visible, message, onClose, duration })

    if (!visible || !message) return null

    return (
        <div style={styles.wrapper}>
            <div
                style={styles.toast}
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
            >
                <div style={styles.content}>
                    <span style={styles.icon}>⚠</span>
                    <span style={styles.text}>{message}</span>
                </div>

                <button type="button" onClick={onClose} style={styles.closeButton}>
                    ×
                </button>
            </div>
        </div>
    )
}

const styles = {
    wrapper: {
        position: 'fixed',
        top: '16px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 9999,
        pointerEvents: 'none',
    },
    toast: {
        minWidth: '320px',
        maxWidth: '680px',
        background: '#dc2626',
        color: '#fff',
        borderRadius: '14px',
        boxShadow: '0 12px 30px rgba(0,0,0,0.25)',
        padding: '14px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        pointerEvents: 'auto',
        animation: 'slideDownFade 0.25s ease',
    },
    content: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        minWidth: 0,
        flex: 1,
    },
    icon: {
        fontSize: '18px',
        lineHeight: 1,
        flexShrink: 0,
    },
    text: {
        fontSize: '14px',
        lineHeight: 1.45,
        wordBreak: 'break-word',
    },
    closeButton: {
        border: 'none',
        background: 'transparent',
        color: '#fff',
        fontSize: '22px',
        lineHeight: 1,
        cursor: 'pointer',
        padding: 0,
        flexShrink: 0,
    },
}

export default ErrorToast