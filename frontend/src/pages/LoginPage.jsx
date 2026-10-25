import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginRequest } from '../api/authApi'
import { getToken, setToken } from '../utils/authStorage'
import AuthInput from '../components/auth/AuthInput'
import AuthButton from '../components/auth/AuthButton'
import ErrorToast from '../components/toasts/ErrorToast'
import BrandIcon from '../components/BrandIcon.jsx'

function LoginPage() {
    const navigate = useNavigate()

    const [login, setLogin] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        const token = getToken()
        if (token) {
            navigate('/chat', { replace: true })
        }
    }, [navigate])

    async function handleSubmit(event) {
        event.preventDefault()
        setError('')
        setLoading(true)

        try {
            const token = await loginRequest(login, password)
            setToken(token)
            navigate('/chat', { replace: true })
        } catch (err) {
            setError(err.message || 'No se pudo iniciar sesión')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={styles.page}>
            <ErrorToast
                message={error}
                visible={!!error}
                onClose={() => setError('')}
                duration={5000}
            />

            <div style={styles.card}>
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 16 }}>
                    <BrandIcon size={44} label="BBAgent" />
                </div>
                <h1 style={styles.title}>Login</h1>

                <form onSubmit={handleSubmit} style={styles.form}>
                    <AuthInput
                        id="login"
                        label="Nombre de usuario"
                        type="text"
                        value={login}
                        onChange={(e) => setLogin(e.target.value)}
                        placeholder="User"
                        autoComplete="username"
                        required
                    />

                    <AuthInput
                        id="password"
                        label="Contraseña"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Password"
                        autoComplete="current-password"
                        required
                    />

                    <AuthButton type="submit" loading={loading}>
                        Entrar
                    </AuthButton>
                </form>
            </div>
        </div>
    )
}

const styles = {
    page: {
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        background: 'var(--bg)',
    },
    card: {
        width: '100%',
        maxWidth: '420px',
        background: 'var(--bg)',
        borderRadius: '16px',
        padding: '32px',
        boxShadow: '0 10px 30px rgba(0,0,0,0.08)',
        border: '1px solid var(--border)',
    },
    title: {
        margin: '0 0 24px 0',
        fontSize: '28px',
        textAlign: 'center',
        color: 'var(--text)',
    },
    form: {
        display: 'flex',
        flexDirection: 'column',
        gap: '18px',
    },
}

export default LoginPage
