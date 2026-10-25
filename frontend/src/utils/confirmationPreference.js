const COOKIE_NAME = 'confirmation_mode'
const DEFAULT_CONFIRMATION_MODE = 2

export const CONFIRMATION_MODES = {
    NEVER_ASK: 0,
    AUTO: 1,
    ALWAYS_ASK: 2,
}

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

export function getConfirmationPreference() {
    const rawValue = getCookie(COOKIE_NAME)

    if (rawValue === null || rawValue === undefined || rawValue === '') {
        return DEFAULT_CONFIRMATION_MODE
    }

    const parsed = Number(rawValue)

    if (![0, 1, 2].includes(parsed)) {
        return DEFAULT_CONFIRMATION_MODE
    }

    return parsed
}

export function setConfirmationPreference(mode) {
    const normalizedMode = [0, 1, 2].includes(Number(mode))
        ? Number(mode)
        : DEFAULT_CONFIRMATION_MODE

    const maxAge = 60 * 60 * 24 * 365

    document.cookie = `${COOKIE_NAME}=${encodeURIComponent(
        normalizedMode
    )}; path=/; max-age=${maxAge}; samesite=lax`
}