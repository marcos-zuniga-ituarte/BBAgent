import { useEffect, useRef } from 'react'

export function useToastTimer({ visible, message, onClose, duration }) {
    const timeout = useRef(null)
    const startedAt = useRef(null)
    const remaining = useRef(duration)
    const close = useRef(onClose)

    useEffect(() => { close.current = onClose }, [onClose])

    useEffect(() => {
        clearTimeout(timeout.current)
        remaining.current = duration
        startedAt.current = null
        if (!visible || !message) return
        startedAt.current = Date.now()
        timeout.current = setTimeout(() => close.current(), duration)
        return () => clearTimeout(timeout.current)
    }, [visible, message, duration])

    function handleMouseEnter() {
        if (!visible || startedAt.current === null) return
        clearTimeout(timeout.current)
        remaining.current = Math.max(remaining.current - (Date.now() - startedAt.current), 0)
        startedAt.current = null
    }

    function handleMouseLeave() {
        if (!visible || startedAt.current !== null) return
        startedAt.current = Date.now()
        timeout.current = setTimeout(() => close.current(), remaining.current)
    }

    return { handleMouseEnter, handleMouseLeave }
}
