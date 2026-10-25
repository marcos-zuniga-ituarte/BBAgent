import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from '../pages/LoginPage'
import ChatPage from '../pages/ChatPage'
import { getToken } from '../utils/authStorage'

function ProtectedRoute({ children }) {
    const token = getToken()

    if (!token) {
        return <Navigate to="/login" replace />
    }

    return children
}

function PublicRoute({ children }) {
    const token = getToken()

    if (token) {
        return <Navigate to="/chat" replace />
    }

    return children
}

function AppRouter() {
    return (
        <BrowserRouter>
            <Routes>
                <Route
                    path="/login"
                    element={
                        <PublicRoute>
                            <LoginPage />
                        </PublicRoute>
                    }
                />

                <Route
                    path="/chat"
                    element={
                        <ProtectedRoute>
                            <ChatPage />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/chat/:chatId"
                    element={
                        <ProtectedRoute>
                            <ChatPage />
                        </ProtectedRoute>
                    }
                />

                <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
        </BrowserRouter>
    )
}

export default AppRouter