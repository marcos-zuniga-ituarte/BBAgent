const COOKIE_NAME = 'chat_sidebar_collapsed'
const DEFAULT_VALUE = false

function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split('; ') : []

    for (const cookie of cookies) {
        const [key, ...rest] = cookie.split('=')

        if (key === name) {
            return decodeURIComponent(rest.join('='))
        }
    }

    return null
}

export function getSidebarCollapsedPreference() {
    const value = getCookie(COOKIE_NAME)

    if (value === null) {
        return DEFAULT_VALUE
    }

    return value === 'true'
}

export function setSidebarCollapsedPreference(isCollapsed) {
    const maxAge = 60 * 60 * 24 * 365 // 1 año

    document.cookie = `${COOKIE_NAME}=${encodeURIComponent(
        String(isCollapsed)
    )}; path=/; max-age=${maxAge}; samesite=lax`
}