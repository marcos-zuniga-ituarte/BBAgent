// src/api/authApi.js
import { API_BASE_URL } from '../config'

async function readError(res) {
    try {
        const text = await res.text()
        return text || `HTTP ${res.status}`
    } catch {
        return `HTTP ${res.status}`
    }
}

export async function loginRequest(username, password) {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            login: username,
            password: password,
        }),
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const data = await res.json()
    return data.access_token
}

export async function logoutRequest(accessToken) {
    const res = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const data = await res.json()
    return data.result
}

export async function changePasswordRequest(
    accessToken,
    currentPassword,
    newPassword
) {
    const res = await fetch(`${API_BASE_URL}/auth/users/password`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
        }),
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const data = await res.json()
    return data.result
}