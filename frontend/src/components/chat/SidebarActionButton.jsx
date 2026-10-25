import { useState } from 'react'

function SidebarActionButton({
                                 icon,
                                 text,
                                 onClick,
                                 disabled = false,
                                 title,
                                 ariaLabel,
                                 fullWidth = false,
                                 active = false,
                                 primary = false,
                                 stableIcon = false,
                                 ariaExpanded,
                                 ariaControls,
                                 collapsed = false,
                             }) {
    const [hovered, setHovered] = useState(false)

    const hasIcon = Boolean(icon)
    const hasText = Boolean(text)
    const iconOnly = hasIcon && !hasText

    return (
        <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            title={title}
            aria-label={ariaLabel || title || text}
            aria-expanded={ariaExpanded}
            aria-controls={ariaControls}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            style={{
                ...styles.button,
                ...(fullWidth ? styles.fullWidth : {}),
                ...(iconOnly ? styles.iconOnly : {}),
                ...(stableIcon ? styles.stableIconButton : {}),
                ...(primary ? styles.primary : {}),
                ...(hovered && !active ? styles.hover : {}),
                ...(active ? styles.active : {}),
                ...(disabled ? styles.disabled : {}),
            }}
        >
            {hasIcon ? <span style={{ ...styles.icon, ...(stableIcon ? styles.stableIcon : {}) }}>{icon}</span> : null}
            {hasText ? <span className={`sidebar-action-label${collapsed ? ' is-collapsed' : ''}`} aria-hidden={collapsed || undefined} style={styles.text}>{text}</span> : null}
        </button>
    )
}

const styles = {
    button: {
        width: '100%',
        minHeight: '48px',
        textAlign: 'left',
        border: 'none',
        borderRadius: '12px',
        background: 'transparent',
        color: 'var(--text)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        padding: '12px 14px',
        flexShrink: 0,
        overflow: 'hidden',
        transition: 'background 0.2s ease',
    },
    hover: {
        background: 'var(--sidebar-hover)',
    },
    primary: {
        background: 'var(--sidebar-hover)',
        border: '1px solid var(--border)',
    },
    active: {
        background: 'var(--sidebar-active)',
    },
    fullWidth: {
        justifyContent: 'flex-start',
    },
    iconOnly: {
        width: '44px',
        height: '44px',
        minHeight: '44px',
        padding: 0,
        justifyContent: 'center',
    },
    disabled: {
        opacity: 0.6,
        cursor: 'not-allowed',
    },
    stableIconButton: {
        minHeight: '48px',
        height: '48px',
        padding: 0,
        gap: '10px',
        boxSizing: 'border-box',
    },
    stableIcon: {
        width: '42px',
        height: '46px',
    },
    icon: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
    },
    text: {
        fontSize: '15px',
        fontWeight: 600,
        color: 'var(--text)',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
    },
}

export default SidebarActionButton
