function AuthInput({
                       id,
                       label,
                       type = 'text',
                       value,
                       onChange,
                       placeholder,
                       autoComplete,
                       required = false,
                   }) {
    return (
        <div style={styles.field}>
            <input
                id={id}
                aria-label={label}
                type={type}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                style={styles.input}
                autoComplete={autoComplete}
                required={required}
            />
        </div>
    )
}

const styles = {
    field: {
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
    },
    input: {
        height: '44px',
        padding: '0 14px',
        borderRadius: '14px',
        border: '1px solid var(--border)',
        fontSize: '15px',
        outline: 'none',
        background: 'var(--bg)',
        color: 'var(--text)',
        boxSizing: 'border-box',
        transition: 'border 0.2s ease, box-shadow 0.2s ease',
    },
}

export default AuthInput
