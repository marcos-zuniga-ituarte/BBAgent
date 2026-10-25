// src/api/toolApprovalApi.js
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

export async function sendToolDecision(authToken, sessionId, decision) {
    const res = await fetch(
        `${API_BASE_URL}/tool-approval/sessions/${sessionId}/response`,
        {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${authToken}`,
                'Content-Type': 'application/json',
                Accept: 'application/json',
            },
            body: JSON.stringify({
                decision: Boolean(decision),
            }),
        }
    )

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
        return await res.json()
    }

    const text = await res.text()
    return text ? text.replaceAll('"', '').trim() : 'ok'
}