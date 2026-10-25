import { useEffect, useMemo, useRef, useState } from 'react'
import { getToken } from '../../utils/authStorage'
import {
    getConfirmationPreference,
    setConfirmationPreference,
} from '../../utils/confirmationPreference'
import { getSystemPrompt, setSystemPrompt } from '../../api/userApi.js'
import { downloadToolClientZip } from '../../api/toolClientApi.js'
import { changePasswordRequest } from '../../api/authApi.js'
import { API_BASE_URL } from '../../config'
import ErrorToast from "../toasts/ErrorToast.jsx";
import SuccessToast from "../toasts/SuccessToast.jsx";

function ConfigurationModal({ open, onClose, onLogout }) {
    const [systemPrompt, setSystemPromptValue] = useState('')
    const [initialSystemPrompt, setInitialSystemPrompt] = useState('')
    const [confirmationMode, setConfirmationMode] = useState(2)
    const [initialConfirmationMode, setInitialConfirmationMode] = useState(2)
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [downloadingClients, setDownloadingClients] = useState(false)
    const [updatingPassword, setUpdatingPassword] = useState(false)

    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [showCurrentPassword, setShowCurrentPassword] = useState(false)
    const [showNewPassword, setShowNewPassword] = useState(false)

    const [errorToastMessage, setErrorToastMessage] = useState('')
    const [successToastMessage, setSuccessToastMessage] = useState('')

    const textareaRef = useRef(null)
    const shouldCloseOnMouseUpRef = useRef(false)

    const apiDocsUrl = `${API_BASE_URL}/docs`

    const hasChanges = useMemo(() => {
        return (
            systemPrompt !== initialSystemPrompt ||
            confirmationMode !== initialConfirmationMode
        )
    }, [
        systemPrompt,
        initialSystemPrompt,
        confirmationMode,
        initialConfirmationMode,
    ])

    function showErrorToast(message) {
        setSuccessToastMessage('')
        setErrorToastMessage(message || 'Ha ocurrido un error')
    }

    function showSuccessToast(message) {
        setErrorToastMessage('')
        setSuccessToastMessage(message || 'Operación completada correctamente')
    }

    useEffect(() => {
        if (!open) return

        let cancelled = false

        async function loadPrompt() {
            const token = getToken()

            if (!token) {
                onLogout?.()
                return
            }

            setLoading(true)
            setErrorToastMessage('')
            setSuccessToastMessage('')

            try {
                const promptValue = await getSystemPrompt(token)

                if (cancelled) return

                const savedConfirmationMode = getConfirmationPreference()

                setSystemPromptValue(promptValue || '')
                setInitialSystemPrompt(promptValue || '')
                setConfirmationMode(savedConfirmationMode)
                setInitialConfirmationMode(savedConfirmationMode)
            } catch (err) {
                if (cancelled) return

                showErrorToast(err.message || 'No se pudo cargar la configuración')
                setSystemPromptValue('')
                setInitialSystemPrompt('')
                setConfirmationMode(2)
                setInitialConfirmationMode(2)
            } finally {
                if (!cancelled) {
                    setLoading(false)
                }
            }
        }

        loadPrompt()

        return () => {
            cancelled = true
        }
    }, [open, onLogout])

    useEffect(() => {
        const textarea = textareaRef.current

        if (!textarea || loading || !open) return

        textarea.style.height = 'auto'

        const maxHeight = window.innerHeight * 0.5
        const nextHeight = Math.min(textarea.scrollHeight, maxHeight)

        textarea.style.height = `${Math.max(nextHeight, 44)}px`
        textarea.style.overflowY =
            textarea.scrollHeight > maxHeight ? 'auto' : 'hidden'
    }, [systemPrompt, loading, open])

    function handleOverlayMouseDown(e) {
        shouldCloseOnMouseUpRef.current = e.target === e.currentTarget
    }

    function handleOverlayMouseUp(e) {
        if (
            shouldCloseOnMouseUpRef.current &&
            e.target === e.currentTarget
        ) {
            onClose?.()
        }

        shouldCloseOnMouseUpRef.current = false
    }

    function handleModalMouseDown() {
        shouldCloseOnMouseUpRef.current = false
    }

    async function handleSave() {
        const token = getToken()

        if (!token) {
            onLogout?.()
            return
        }

        if (!hasChanges || saving) {
            return
        }

        setSaving(true)
        setErrorToastMessage('')
        setSuccessToastMessage('')

        try {
            await setSystemPrompt(token, systemPrompt)
            setConfirmationPreference(confirmationMode)

            setInitialSystemPrompt(systemPrompt)
            setInitialConfirmationMode(confirmationMode)

            showSuccessToast('Configuración guardada correctamente')
        } catch (err) {
            showErrorToast(err.message || 'No se pudo guardar la configuración')
        } finally {
            setSaving(false)
        }
    }

    async function handleDownloadClients(e) {
        e.preventDefault()

        const token = getToken()

        if (!token) {
            onLogout?.()
            return
        }

        if (downloadingClients) {
            return
        }

        setDownloadingClients(true)
        setErrorToastMessage('')
        setSuccessToastMessage('')

        try {
            await downloadToolClientZip(token)
            showSuccessToast('Clients descargados correctamente')
        } catch (err) {
            showErrorToast(err.message || 'No se pudieron descargar los clients')
        } finally {
            setDownloadingClients(false)
        }
    }

    async function handleUpdatePassword() {
        const token = getToken()

        if (!token) {
            onLogout?.()
            return
        }

        if (!currentPassword.trim()) {
            showErrorToast('Introduce tu contraseña actual')
            return
        }

        if (!newPassword.trim()) {
            showErrorToast('Introduce una nueva contraseña')
            return
        }

        if (updatingPassword) {
            return
        }

        setUpdatingPassword(true)
        setErrorToastMessage('')
        setSuccessToastMessage('')

        try {
            await changePasswordRequest(token, currentPassword, newPassword)

            setCurrentPassword('')
            setNewPassword('')
            setShowCurrentPassword(false)
            setShowNewPassword(false)

            showSuccessToast('Contraseña actualizada correctamente. Cerrando sesión...')

            setTimeout(() => {
                onLogout?.()
            }, 1400)
        } catch (err) {
            showErrorToast(err.message || 'No se pudo actualizar la contraseña')
        } finally {
            setUpdatingPassword(false)
        }
    }

    if (!open) return null

    return (
        <>
            <ErrorToast
                message={errorToastMessage}
                visible={Boolean(errorToastMessage)}
                onClose={() => setErrorToastMessage('')}
            />

            <SuccessToast
                message={successToastMessage}
                visible={Boolean(successToastMessage)}
                onClose={() => setSuccessToastMessage('')}
            />

            <div
                style={styles.overlay}
                onMouseDown={handleOverlayMouseDown}
                onMouseUp={handleOverlayMouseUp}
            >
                <div
                    style={styles.modal}
                    onMouseDown={handleModalMouseDown}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div style={styles.header}>
                        <h2 style={styles.title}>Configuration</h2>

                        <button
                            type="button"
                            onClick={onClose}
                            style={styles.closeButton}
                            aria-label="Cerrar configuración"
                        >
                            ×
                        </button>
                    </div>

                    <div style={styles.body}>
                        <div style={styles.linksRow}>
                            <a
                                href="#"
                                onClick={handleDownloadClients}
                                style={styles.topLink}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.textDecoration = 'underline'
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.textDecoration = 'none'
                                }}
                            >
                                {downloadingClients
                                    ? 'Downloading clients...'
                                    : 'Download clients'}
                            </a>

                            <span style={styles.linkSeparator}>·</span>

                            <a
                                href={apiDocsUrl}
                                target="_blank"
                                rel="noreferrer"
                                style={styles.topLink}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.textDecoration = 'underline'
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.textDecoration = 'none'
                                }}
                            >
                                See API
                            </a>
                        </div>

                        <label htmlFor="system-prompt" style={styles.label}>
                            System prompt
                        </label>

                        {loading ? (
                            <p style={styles.helperText}>Cargando configuración...</p>
                        ) : (
                            <textarea
                                ref={textareaRef}
                                id="system-prompt"
                                className="chat-input-textarea"
                                value={systemPrompt}
                                onChange={(e) => setSystemPromptValue(e.target.value)}
                                style={styles.textarea}
                                placeholder="Escribe aquí el system prompt..."
                                rows={1}
                            />
                        )}

                        <label htmlFor="ask-confirmation" style={styles.label}>
                            Command execution mode
                        </label>

                        <div style={styles.selectWrapper}>
                            <select
                                id="ask-confirmation"
                                value={String(confirmationMode)}
                                onChange={(e) =>
                                    setConfirmationMode(Number(e.target.value))
                                }
                                style={styles.select}
                            >
                                <option value="2">Always ask</option>
                                <option value="1">Auto</option>
                                <option value="0">Never ask</option>
                            </select>

                            <span style={styles.selectChevron} aria-hidden="true">
                                ▾
                            </span>
                        </div>

                        <label htmlFor="current-password" style={styles.label}>
                            Current password
                        </label>

                        <div style={styles.passwordRow}>
                            <input
                                id="current-password"
                                type={showCurrentPassword ? 'text' : 'password'}
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                style={styles.passwordInput}
                                placeholder="Write your current password..."
                                autoComplete="current-password"
                            />

                            <button
                                type="button"
                                onClick={() =>
                                    setShowCurrentPassword((current) => !current)
                                }
                                style={styles.secondaryButton}
                                aria-label={
                                    showCurrentPassword
                                        ? 'Ocultar contraseña actual'
                                        : 'Mostrar contraseña actual'
                                }
                            >
                                {showCurrentPassword ? 'Hide' : 'Show'}
                            </button>
                        </div>

                        <label htmlFor="new-password" style={styles.label}>
                            New password
                        </label>

                        <div style={styles.passwordRow}>
                            <input
                                id="new-password"
                                type={showNewPassword ? 'text' : 'password'}
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                style={styles.passwordInput}
                                placeholder="Write your new password..."
                                autoComplete="new-password"
                            />

                            <button
                                type="button"
                                onClick={() =>
                                    setShowNewPassword((current) => !current)
                                }
                                style={styles.secondaryButton}
                                aria-label={
                                    showNewPassword
                                        ? 'Ocultar nueva contraseña'
                                        : 'Mostrar nueva contraseña'
                                }
                            >
                                {showNewPassword ? 'Hide' : 'Show'}
                            </button>
                        </div>

                        <div style={styles.passwordActions}>
                            <button
                                type="button"
                                onClick={handleUpdatePassword}
                                disabled={
                                    updatingPassword ||
                                    !currentPassword.trim() ||
                                    !newPassword.trim()
                                }
                                style={{
                                    ...styles.saveButton,
                                    ...(updatingPassword ||
                                    !currentPassword.trim() ||
                                    !newPassword.trim()
                                        ? styles.saveButtonDisabled
                                        : {}),
                                }}
                            >
                                {updatingPassword
                                    ? 'Updating...'
                                    : 'Update password'}
                            </button>
                        </div>
                    </div>

                    <div style={styles.footer}>
                        <button
                            type="button"
                            onClick={onLogout}
                            style={styles.logoutButton}
                        >
                            Cerrar sesión
                        </button>

                        <button
                            type="button"
                            onClick={handleSave}
                            disabled={loading || saving || !hasChanges}
                            style={{
                                ...styles.saveButton,
                                ...(loading || saving || !hasChanges
                                    ? styles.saveButtonDisabled
                                    : {}),
                            }}
                        >
                            {saving ? 'Guardando...' : 'Guardar'}
                        </button>
                    </div>
                </div>
            </div>
        </>
    )
}

const styles = {
    overlay: {
        position: 'fixed',
        inset: 0,
        background: 'var(--modal-overlay, rgba(0, 0, 0, 0.45))',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        zIndex: 9998,
    },
    modal: {
        width: 'min(720px, 100%)',
        maxHeight: '85vh',
        background: 'var(--bg)',
        color: 'var(--text)',
        border: '1px solid var(--border)',
        borderRadius: '16px',
        boxShadow: 'var(--shadow)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
    },
    header: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        padding: '18px 20px',
        borderBottom: '1px solid var(--border)',
    },
    title: {
        margin: 0,
        fontSize: '20px',
        fontWeight: 600,
        color: 'var(--text)',
    },
    closeButton: {
        width: '36px',
        height: '36px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        color: 'var(--text)',
        cursor: 'pointer',
        fontSize: '24px',
        lineHeight: 1,
    },
    body: {
        padding: '20px',
        overflowY: 'auto',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
    },
    linksRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '2px',
        flexWrap: 'wrap',
    },
    topLink: {
        color: 'var(--text)',
        textDecoration: 'none',
        textUnderlineOffset: '2px',
        background: 'transparent',
        border: 'none',
        padding: 0,
        margin: 0,
        font: 'inherit',
        fontSize: '14px',
        lineHeight: 1.4,
        cursor: 'pointer',
        transition: 'opacity 0.15s ease',
    },
    topLinkHover: {
        textDecoration: 'underline',
    },
    topLinkDisabled: {
        opacity: 0.65,
        cursor: 'default',
        pointerEvents: 'none',
    },
    linkSeparator: {
        color: 'var(--text)',
        opacity: 0.45,
        fontSize: '14px',
        lineHeight: 1,
    },
    label: {
        fontSize: '14px',
        fontWeight: 600,
        color: 'var(--text)',
    },
    helperText: {
        color: 'var(--text)',
        opacity: 0.7,
        margin: 0,
    },
    textarea: {
        width: '100%',
        minHeight: '44px',
        maxHeight: '50vh',
        resize: 'none',
        overflowY: 'hidden',
        boxSizing: 'border-box',
        borderRadius: '12px',
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        color: 'var(--text)',
        padding: '12px 14px',
        fontSize: '14px',
        lineHeight: 1.5,
        outline: 'none',
    },
    selectWrapper: {
        position: 'relative',
        width: '100%',
        height: '44px',
        borderRadius: '12px',
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        overflow: 'hidden',
        boxSizing: 'border-box',
    },
    select: {
        width: '100%',
        height: '100%',
        border: 'none',
        borderRadius: '12px',
        background: 'transparent',
        color: 'var(--text)',
        padding: '0 40px 0 14px',
        fontSize: '14px',
        fontWeight: 500,
        outline: 'none',
        appearance: 'none',
        WebkitAppearance: 'none',
        MozAppearance: 'none',
        cursor: 'pointer',
    },
    selectChevron: {
        position: 'absolute',
        top: '50%',
        right: '14px',
        transform: 'translateY(-50%)',
        color: 'var(--text)',
        opacity: 0.7,
        pointerEvents: 'none',
        fontSize: '12px',
    },
    passwordRow: {
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: '10px',
        alignItems: 'center',
    },
    passwordInput: {
        width: '100%',
        height: '44px',
        boxSizing: 'border-box',
        borderRadius: '12px',
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        color: 'var(--text)',
        padding: '0 14px',
        fontSize: '14px',
        lineHeight: 1.5,
        outline: 'none',
    },
    passwordActions: {
        display: 'flex',
        justifyContent: 'flex-end',
        marginTop: '4px',
    },
    secondaryButton: {
        height: '42px',
        padding: '0 16px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        color: 'var(--text)',
        cursor: 'pointer',
        fontWeight: 600,
        whiteSpace: 'nowrap',
    },
    footer: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        padding: '16px 20px',
        borderTop: '1px solid var(--border)',
    },
    logoutButton: {
        height: '42px',
        padding: '0 16px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        color: 'var(--text)',
        cursor: 'pointer',
        fontWeight: 600,
    },
    saveButton: {
        height: '42px',
        padding: '0 18px',
        borderRadius: '10px',
        border: '1px solid var(--accent-border)',
        background: 'var(--accent)',
        color: '#fff',
        cursor: 'pointer',
        fontWeight: 700,
        whiteSpace: 'nowrap',
    },
    saveButtonDisabled: {
        opacity: 0.5,
        cursor: 'not-allowed',
    },
}

export default ConfigurationModal