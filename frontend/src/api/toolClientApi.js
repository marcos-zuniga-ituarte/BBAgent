// src/api/toolClientApi.js
import { API_BASE_URL } from '../config'

async function readError(res) {
    try {
        const text = await res.text()
        return text || `HTTP ${res.status}`
    } catch {
        return `HTTP ${res.status}`
    }
}

export async function downloadToolClientZip(authToken) {
    const res = await fetch(`${API_BASE_URL}/tool-client/download`, {
        method: 'GET',
        headers: {
            Authorization: `Bearer ${authToken}`,
        },
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const blob = await res.blob()
    const downloadUrl = window.URL.createObjectURL(blob)

    try {
        const link = document.createElement('a')
        link.href = downloadUrl
        link.download = 'clients.zip'
        document.body.appendChild(link)
        link.click()
        link.remove()
    } finally {
        window.URL.revokeObjectURL(downloadUrl)
    }

    return 'ok'
}