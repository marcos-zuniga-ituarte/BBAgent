// src/api/userApi.js
import { API_BASE_URL } from '../config'

async function readError(res) {
    try {
        const contentType = res.headers.get('content-type') || ''

        if (contentType.includes('application/json')) {
            const data = await res.json()
            if (typeof data?.detail === 'string' && data.detail.trim()) {
                return data.detail
            }
            return JSON.stringify(data)
        }

        const text = await res.text()
        return text || `HTTP ${res.status}`
    } catch {
        return `HTTP ${res.status}`
    }
}

export async function getSystemPrompt(authToken) {
    const res = await fetch(`${API_BASE_URL}/user/system-prompt`, {
        method: 'GET',
        headers: {
            Authorization: `Bearer ${authToken}`,
            Accept: 'application/json',
        },
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const data = await res.json()
    return data.prompt ?? ''
}

export async function setSystemPrompt(authToken, systemPrompt) {
    const res = await fetch(`${API_BASE_URL}/user/system-prompt`, {
        method: 'PUT',
        headers: {
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json',
            Accept: 'application/json',
        },
        body: JSON.stringify({
            prompt: systemPrompt,
        }),
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
        return await res.json()
    }

    return 'ok'
}