// src/api/filesApi.js
import { API_BASE_URL } from '../config'

async function readError(res) {
    try {
        const text = await res.text()
        return text || `HTTP ${res.status}`
    } catch {
        return `HTTP ${res.status}`
    }
}

export async function downloadFile(authToken, fileId) {
    const res = await fetch(`${API_BASE_URL}/files/${fileId}`, {
        method: 'GET',
        headers: {
            Authorization: `Bearer ${authToken}`,
        },
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const blob = await res.blob()

    const contentDisposition = res.headers.get('content-disposition') || ''
    let filename = 'download'

    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
    const plainMatch = contentDisposition.match(/filename="([^"]+)"/i)

    if (utf8Match?.[1]) {
        filename = decodeURIComponent(utf8Match[1])
    } else if (plainMatch?.[1]) {
        filename = plainMatch[1]
    }

    return {
        blob,
        filename,
        contentType: res.headers.get('content-type') || 'application/octet-stream',
    }
}

export async function downloadFileToBrowser(authToken, fileId, forcedFilename) {
    const { blob, filename } = await downloadFile(authToken, fileId)

    const finalName = forcedFilename || filename

    const objectUrl = window.URL.createObjectURL(blob)

    try {
        const link = document.createElement('a')
        link.href = objectUrl
        link.download = finalName
        document.body.appendChild(link)
        link.click()
        link.remove()
    } finally {
        window.URL.revokeObjectURL(objectUrl)
    }
}