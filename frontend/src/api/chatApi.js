// src/api/chatApi.js
import { API_BASE_URL } from '../config'

async function readError(res) {
    try {
        const text = await res.text()
        return text || `HTTP ${res.status}`
    } catch {
        return `HTTP ${res.status}`
    }
}

const DEFAULT_SSE_EVENTS = [
    'start',
    'snapshot',
    'status',
    'token',
    'tool_request',
    'tool_result',
    'notification',
    'stopping',
    'stopped',
    'done',
    'error',
    'message',
    'message_close',
]

function createFetchSseSubscription({ url, authToken, onEvent, onError, eventNames = DEFAULT_SSE_EVENTS }) {
    const controller = new AbortController()
    let closed = false

    const emitParsedEvent = (eventName, rawData) => {
        if (!eventNames.includes(eventName)) {
            return
        }

        let data = {}
        try {
            data = rawData ? JSON.parse(rawData) : {}
        } catch {
            data = { raw: rawData }
        }

        onEvent?.({
            event: eventName,
            data,
            receivedAt: Date.now(),
        })
    }

    const parseSseChunkStream = async (response) => {
            if (!response.ok) {
                throw new Error(await readError(response))
            }

            if (!response.body) {
                throw new Error('SSE response body is empty')
            }

            const reader = response.body.getReader()
            const decoder = new TextDecoder('utf-8')
            let buffer = ''

            const processBuffer = (flush = false) => {
                const normalized = buffer.replace(/\r\n/g, '\n')
                const parts = normalized.split('\n\n')

                if (!flush) {
                    buffer = parts.pop() ?? ''
                } else {
                    buffer = ''
                }

                for (const part of parts) {
                    const block = part.trim()
                    if (!block) continue

                    const lines = block.split('\n')
                    let eventName = 'message'
                    const dataLines = []

                    for (const line of lines) {
                        if (line.startsWith(':')) {
                            continue
                        }

                        if (line.startsWith('event:')) {
                            eventName = line.slice(6).trim() || 'message'
                            continue
                        }

                        if (line.startsWith('data:')) {
                            dataLines.push(line.slice(5).trimStart())
                        }
                    }

                    emitParsedEvent(eventName, dataLines.join('\n'))
                }
            }

            while (true) {
                const { value, done } = await reader.read()

                if (done) {
                    processBuffer(true)
                    break
                }

                buffer += decoder.decode(value, { stream: true })
                processBuffer(false)
            }
        }

    ;(async () => {
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${authToken}`,
                    Accept: 'text/event-stream',
                },
                signal: controller.signal,
            })

            await parseSseChunkStream(response)
        } catch (error) {
            if (closed || controller.signal.aborted) {
                return
            }
            onError?.(error)
        }
    })()

    return {
        close() {
            closed = true
            controller.abort()
        },
    }
}

export async function getChats(authToken) {
    const res = await fetch(`${API_BASE_URL}/chat`, {
        headers: {
            Authorization: `Bearer ${authToken}`,
        },
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    return await res.json()
}

export async function createChat(authToken) {
    const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${authToken}`,
        },
    })

    if (!res.ok) {
        throw new Error(await readError(res))
    }

    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
        const value = await res.json()
        return typeof value === 'string' ? value : String(value)
    }

    return (await res.text()).replaceAll('"', '').trim()
}

export function subscribeToChat({ authToken, chatId, onEvent, onError }) {
    const url = `${API_BASE_URL}/chat/subscribe/${chatId}`

    return createFetchSseSubscription({
        url,
        authToken,
        onEvent,
        onError,
    })
}

export function subscribeToDevil({ authToken, onEvent, onError }) {
    const url = `${API_BASE_URL}/chat/devil/subscribe`

    return createFetchSseSubscription({
        url,
        authToken,
        onEvent,
        onError,
    })
}

export async function startChatRun({
                                       authToken,
                                       chatId,
                                       message,
                                       confirmationMode,
                                       audioFile,
                                       files = [],
                                   }) {
    const formData = new FormData()

    formData.append('askForConfirmation', String(confirmationMode ?? 0))

    if (message != null && message.trim() !== '') {
        formData.append('message', message)
    }

    if (audioFile) {
        formData.append('audio', audioFile)
    }

    if (Array.isArray(files)) {
        for (const file of files) {
            if (file) {
                formData.append('files', file)
            }
        }
    }

    const res = await fetch(`${API_BASE_URL}/chat/runs/${chatId}`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${authToken}`,
        },
        body: formData,
    })

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

export async function startDevilRun({
                                        authToken,
                                        message,
                                        confirmationMode,
                                    }) {
    const res = await fetch(`${API_BASE_URL}/chat/devil/request`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
            message,
            askForConfirmation: confirmationMode ?? 0,
        }),
    })

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

export async function stopChatRun(authToken, chatId) {
    const res = await fetch(`${API_BASE_URL}/chat/runs/${chatId}/stop`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${authToken}`,
        },
    })

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