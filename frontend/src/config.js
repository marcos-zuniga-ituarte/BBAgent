export function resolveApiBaseUrl(value) {
    const baseUrl = value?.trim() || 'http://localhost:8000'
    let url
    try {
        url = new URL(baseUrl)
    } catch {
        throw new Error('VITE_API_BASE_URL debe ser una URL absoluta HTTP o HTTPS.')
    }
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
        throw new Error('VITE_API_BASE_URL debe usar HTTP o HTTPS y no incluir credenciales.')
    }
    if (url.search || url.hash) {
        throw new Error('VITE_API_BASE_URL no debe incluir parámetros ni fragmentos.')
    }
    return url.href.replace(/\/+$/, '')
}

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env?.VITE_API_BASE_URL)
