import { useState } from 'react'


function AuthButton({ type = 'button', disabled = false, loading = false, children }) {
    const [hover, setHover] = useState(false)

    return (
        <button
            type={type}
            disabled={disabled || loading}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
            style={{
                ...styles.button,
                ...(hover ? styles.hover : {}),
                ...(loading ? styles.loading : {}),
            }}
        >
            {loading ? <span style={styles.spinner} /> : children}
        </button>
    )
}

const styles = {
    button: {
        height: '46px',
        border: 'none',
        borderRadius: '12px',
        fontSize: '16px',
        fontWeight: 700,
        cursor: 'pointer',
        background: '#2563eb',
        color: '#ffffff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'background 0.2s ease, opacity 0.2s ease',
    },
    hover: {
        background: '#1d4ed8', // más oscuro
    },
    loading: {
        cursor: 'default',
        opacity: 0.8,
    },
    spinner: {
        width: '18px',
        height: '18px',
        border: '2px solid rgba(255,255,255,0.4)',
        borderTop: '2px solid #ffffff',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
    },
}

export default AuthButton