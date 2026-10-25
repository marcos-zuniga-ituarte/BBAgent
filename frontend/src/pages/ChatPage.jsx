import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
    createChat,
    getChats,
    startChatRun,
    subscribeToChat,
    stopChatRun,
} from '../api/chatApi'
import { getToken, removeToken } from '../utils/authStorage'
import ChatSidebar from '../components/chat/ChatSidebar'
import ChatMain from '../components/chat/ChatMain'
import { getConfirmationPreference } from '../utils/confirmationPreference'
import ErrorToast from '../components/toasts/ErrorToast'
import {sendToolDecision} from "../api/toolApprovalApi.js";

function normalizeMessages(data) {
    if (!Array.isArray(data)) return []

    return data.map((message, index) => ({
        id: message.id || `msg-${index}`,
        ...message,
        role: message.role?.toLowerCase(),
    }))
}

function buildStepsFromLive(live) {
    const nextSteps = []

    if (live?.current_status) {
        nextSteps.push({
            type: live.current_status.phase || live.current_status.type || 'status',
            text: live.current_status.message || '',
            toolName: live.current_status.tool_name || '',
            arguments: live.current_status.arguments || {},
        })
    }

    if (Array.isArray(live?.tool_history)) {
        for (const item of live.tool_history) {
            nextSteps.push({
                type: item.type || 'tool_result',
                text: item.output || '',
                toolName: item.tool_name || '',
                arguments: item.arguments || {},
                output: item.output || '',
            })
        }
    }

    if (live?.pending_tool_request) {
        nextSteps.push({
            type: live.pending_tool_request.type || 'tool_request',
            text: live.pending_tool_request.message || '',
            toolName: live.pending_tool_request.tool_name || '',
            arguments: live.pending_tool_request.arguments || {},
        })
    }

    return nextSteps
}

function ChatPage() {
    const navigate = useNavigate()
    const { chatId } = useParams()

    const eventSourceRef = useRef(null)
    const assistantDraftRef = useRef('')
    const pendingFilesRef = useRef([])

    const isDraftChat = !chatId || chatId === 'new'

    const [pendingTool, setPendingTool] = useState(null)
    const [sendingDecision, setSendingDecision] = useState(false)

    const [chats, setChats] = useState([])
    const [selectedChatId, setSelectedChatId] = useState(
        chatId && chatId !== 'new' ? chatId : null,
    )

    const [loadingChats, setLoadingChats] = useState(true)
    const [creatingChat, setCreatingChat] = useState(false)

    const [messages, setMessages] = useState([])
    const [loadingMessages, setLoadingMessages] = useState(false)

    const [pendingFiles, setPendingFiles] = useState([])
    const [composerResetKey, setComposerResetKey] = useState(0)

    const [isStreaming, setIsStreaming] = useState(false)
    const [isStopping, setIsStopping] = useState(false)
    const [assistantDraft, setAssistantDraft] = useState('')
    const [streamSteps, setStreamSteps] = useState([])

    const [error, setError] = useState('')
    const [focusTrigger, setFocusTrigger] = useState(0)

    const [isMobile, setIsMobile] = useState(() => window.innerWidth <= 768)
    const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)

    pendingFilesRef.current = pendingFiles

    function triggerInputFocus() {
        setFocusTrigger((previous) => previous + 1)
    }

    function closeCurrentSubscription() {
        if (!eventSourceRef.current) return
        eventSourceRef.current.close()
        eventSourceRef.current = null
    }

    function resetComposerVisualState() {
        pendingFilesRef.current = []
        setPendingFiles([])
        setComposerResetKey((previous) => previous + 1)
    }

    function addPendingFiles(files) {
        if (!Array.isArray(files) || files.length === 0) return

        pendingFilesRef.current = [...pendingFilesRef.current, ...files]
        setPendingFiles((previousFiles) => [...previousFiles, ...files])
        setError('')
    }

    function removePendingFile(indexToRemove) {
        pendingFilesRef.current = pendingFilesRef.current.filter(
            (_, index) => index !== indexToRemove,
        )
        setPendingFiles((previousFiles) =>
            previousFiles.filter((_, index) => index !== indexToRemove),
        )
    }

    useEffect(() => {
        function handleResize() {
            const mobile = window.innerWidth <= 768
            setIsMobile(mobile)

            if (!mobile) {
                setIsMobileSidebarOpen(false)
            }
        }

        handleResize()
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    useEffect(() => {
        setSelectedChatId(chatId && chatId !== 'new' ? chatId : null)
    }, [chatId])

    useEffect(() => {
        async function loadChats() {
            const token = getToken()

            if (!token) {
                navigate('/login', { replace: true })
                return
            }

            setLoadingChats(true)
            setError('')

            try {
                const data = await getChats(token)
                setChats(data)

                if (chatId && chatId !== 'new' && data.length > 0) {
                    const exists = data.some((chat) => String(chat.id) === String(chatId))

                    if (!exists) {
                        navigate('/chat', { replace: true })
                    }
                }
            } catch (error) {
                setError(error.message || 'No se pudieron cargar los chats')
            } finally {
                setLoadingChats(false)
            }
        }

        loadChats()
    }, [navigate, chatId])

    useEffect(() => {
        assistantDraftRef.current = assistantDraft
    }, [assistantDraft])

    useEffect(() => {
        closeCurrentSubscription()

        if (!selectedChatId) {
            setMessages([])
            setAssistantDraft('')
            assistantDraftRef.current = ''
            setStreamSteps([])
            setPendingTool(null)
            setIsStreaming(false)
            setIsStopping(false)
            setLoadingMessages(false)
            return
        }

        const token = getToken()

        if (!token) {
            navigate('/login', { replace: true })
            return
        }

        setLoadingMessages(true)
        setError('')

        const es = subscribeToChat({
            authToken: token,
            chatId: selectedChatId,
            onEvent: ({ event, data }) => {
                if (event === 'start') return

                if (event === 'snapshot') {
                    const snapshotMessages = normalizeMessages(data?.messages)
                    const live = data?.live || {}

                    setMessages(snapshotMessages)

                    const partialResponse = live.is_running ? live.partial_response || '' : ''
                    setAssistantDraft(partialResponse)
                    assistantDraftRef.current = partialResponse

                    setPendingTool(
                        live.pending_tool_request
                            ? {
                                chatId: selectedChatId,
                                toolName: live.pending_tool_request.tool_name || '',
                                arguments: live.pending_tool_request.arguments || {},
                                text:
                                    live.pending_tool_request.message ||
                                    '¿Deseas ejecutar esta tool?',
                            }
                            : null,
                    )

                    setIsStreaming(!!live.is_running)
                    setIsStopping(false)
                    setStreamSteps(
                        live.is_running || live.pending_tool_request
                            ? buildStepsFromLive(live)
                            : [],
                    )
                    setLoadingMessages(false)
                    return
                }

                if (event === 'stopping') {
                    setIsStopping(true)
                    setIsStreaming(true)
                    setStreamSteps((previousSteps) => [
                        ...previousSteps,
                        {
                            type: 'stopping',
                            text: data?.message || 'Deteniendo ejecución...',
                        },
                    ])
                    return
                }

                if (event === 'stopped') {
                    const finalText = assistantDraftRef.current.trim()

                    setIsStopping(false)
                    setIsStreaming(false)
                    setPendingTool(null)
                    setStreamSteps([])

                    if (finalText) {
                        setMessages((previousMessages) => [
                            ...previousMessages,
                            {
                                id: `local-assistant-stopped-${Date.now()}`,
                                role: 'assistant',
                                content: finalText,
                            },
                        ])
                    }

                    setAssistantDraft('')
                    assistantDraftRef.current = ''
                    return
                }

                if (event === 'message') {
                    const incoming = data?.message
                    if (!incoming) return

                    setMessages((previousMessages) => {
                        const normalized = {
                            id: incoming.id || `msg-${Date.now()}`,
                            ...incoming,
                            role: incoming.role?.toLowerCase(),
                        }

                        const alreadyExists = previousMessages.some(
                            (message) => String(message.id) === String(normalized.id),
                        )

                        return alreadyExists ? previousMessages : [...previousMessages, normalized]
                    })

                    return
                }

                if (event === 'message_close') {
                    const finalText = assistantDraftRef.current.trim()

                    if (finalText) {
                        setMessages((previousMessages) => [
                            ...previousMessages,
                            {
                                id: `local-assistant-close-${Date.now()}`,
                                role: 'assistant',
                                content: finalText,
                            },
                        ])
                    }

                    setAssistantDraft('')
                    assistantDraftRef.current = ''
                    return
                }

                if (event === 'token') {
                    const delta = data?.delta || ''
                    if (!delta) return

                    setIsStreaming(true)

                    setAssistantDraft((previousDraft) => {
                        const nextDraft = previousDraft + delta
                        assistantDraftRef.current = nextDraft
                        return nextDraft
                    })

                    return
                }

                if (event === 'done') {
                    setIsStopping(false)
                    setIsStreaming(false)
                    setPendingTool(null)
                    setStreamSteps([])

                    const finalText = assistantDraftRef.current.trim()

                    if (finalText) {
                        setMessages((previousMessages) => [
                            ...previousMessages,
                            {
                                id: `local-assistant-${Date.now()}`,
                                role: 'assistant',
                                content: finalText,
                            },
                        ])
                    }

                    setAssistantDraft('')
                    assistantDraftRef.current = ''
                    return
                }

                if (event === 'status') {
                    setIsStreaming(true)
                    setStreamSteps((previousSteps) => [
                        ...previousSteps,
                        {
                            type: data?.phase || data?.type || 'status',
                            text: data?.message || '',
                            toolName: data?.tool_name || '',
                            arguments: data?.arguments || {},
                        },
                    ])
                    return
                }

                if (event === 'notification') {
                    setIsStreaming(true)

                    if (data?.type === 'executing_tool') {
                        setPendingTool(null)
                    }

                    setStreamSteps((previousSteps) => [
                        ...previousSteps,
                        {
                            type: data?.type || 'notification',
                            text: data?.message || '',
                            toolName: data?.tool_name || '',
                            arguments: data?.arguments || {},
                        },
                    ])
                    return
                }

                if (event === 'tool_request') {
                    setIsStreaming(true)

                    setPendingTool({
                        chatId: selectedChatId,
                        toolName: data?.tool_name || '',
                        arguments: data?.arguments || {},
                        text: data?.message || '¿Deseas ejecutar esta tool?',
                    })

                    setStreamSteps((previousSteps) => [
                        ...previousSteps,
                        {
                            type: 'tool_request',
                            text: data?.message || 'Se requiere confirmación',
                            toolName: data?.tool_name || '',
                            arguments: data?.arguments || {},
                        },
                    ])
                    return
                }

                if (event === 'tool_result') {
                    setPendingTool(null)

                    setStreamSteps((previousSteps) => [
                        ...previousSteps,
                        {
                            type: 'tool_result',
                            text: data?.output || 'Tool ejecutada',
                            toolName: data?.tool_name || '',
                            arguments: data?.arguments || {},
                            output: data?.output || '',
                        },
                    ])
                    return
                }

                if (event === 'error') {
                    setIsStopping(false)
                    setIsStreaming(false)
                    setPendingTool(null)
                    setAssistantDraft('')
                    assistantDraftRef.current = ''
                    setStreamSteps([])
                    setError(data?.message || 'Error en el stream')
                }
            },
            onError: () => {},
        })

        eventSourceRef.current = es
        return closeCurrentSubscription
    }, [selectedChatId, navigate])

    useEffect(() => {
        if (!chatId || chatId === 'new') {
            closeCurrentSubscription()
            setSelectedChatId(null)
            setMessages([])
            setAssistantDraft('')
            setStreamSteps([])
            resetComposerVisualState()
            setError('')
            setPendingTool(null)
            setSendingDecision(false)
            setIsStreaming(false)
            setLoadingMessages(false)
            setIsMobileSidebarOpen(false)
            setIsStopping(false)
            triggerInputFocus()
        }
    }, [chatId])

    useEffect(() => {
        if (!loadingChats && isDraftChat && !pendingTool && !isStreaming) {
            triggerInputFocus()
        }
    }, [loadingChats, isDraftChat, pendingTool, isStreaming])

    useEffect(() => {
        if (selectedChatId && !loadingMessages && !pendingTool && !isStreaming) {
            triggerInputFocus()
        }
    }, [selectedChatId, loadingMessages, pendingTool, isStreaming])

    useEffect(() => {
        if (!pendingTool && !isStreaming) {
            triggerInputFocus()
        }
    }, [pendingTool, isStreaming])

    function handleSelectChat(id) {
        navigate(`/chat/${id}`)
        setIsMobileSidebarOpen(false)
    }

    function handleNewChat() {
        closeCurrentSubscription()
        setSelectedChatId(null)
        setMessages([])
        setAssistantDraft('')
        setStreamSteps([])
        resetComposerVisualState()
        setError('')
        setPendingTool(null)
        setSendingDecision(false)
        setIsStreaming(false)
        setLoadingMessages(false)
        setIsMobileSidebarOpen(false)
        setIsStopping(false)

        navigate('/chat')
        triggerInputFocus()
    }

    async function ensureChatSelected(token) {
        if (selectedChatId) {
            return { effectiveChatId: selectedChatId, createdNow: false }
        }

        setCreatingChat(true)
        const newChatId = await createChat(token)
        setSelectedChatId(newChatId)
        navigate(`/chat/${newChatId}`, { replace: true })

        return { effectiveChatId: newChatId, createdNow: true }
    }

    async function handleSubmitComposer({ text = '', audioFile = null, files = [] } = {}) {
        const token = getToken()
        const trimmedText = String(text || '').trim()
        const normalizedFiles = Array.isArray(files) ? files : pendingFilesRef.current
        const hasSomethingToSend = !!audioFile || !!trimmedText || normalizedFiles.length > 0

        if (!token) {
            navigate('/login', { replace: true })
            return
        }

        if (!hasSomethingToSend || isStreaming) {
            return
        }

        setError('')
        setAssistantDraft('')
        assistantDraftRef.current = ''
        setStreamSteps([])
        setPendingTool(null)
        setIsStopping(false)
        setIsStreaming(true)
        resetComposerVisualState()

        try {
            const { effectiveChatId, createdNow } = await ensureChatSelected(token)
            const confirmationMode = getConfirmationPreference()

            await startChatRun({
                authToken: token,
                chatId: effectiveChatId,
                confirmationMode,
                audioFile,
                files: normalizedFiles,
                ...(audioFile ? {} : { message: trimmedText }),
            })

            if (createdNow) {
                const updatedChats = await getChats(token)
                setChats(updatedChats)
            }
        } catch (error) {
            setIsStreaming(false)
            setStreamSteps([])
            setError(
                error.message ||
                (audioFile ? 'No se pudo enviar el audio' : 'No se pudo enviar el mensaje'),
            )
            pendingFilesRef.current = normalizedFiles
            setPendingFiles(normalizedFiles)
        } finally {
            setCreatingChat(false)
        }
    }

    async function handleStopMessage() {
        const token = getToken()

        if (!token) {
            navigate('/login', { replace: true })
            return
        }

        if (!selectedChatId || !isStreaming || isStopping) return

        try {
            setError('')
            setIsStopping(true)
            await stopChatRun(token, selectedChatId)
        } catch (error) {
            setIsStopping(false)
            setError(error.message || 'No se pudo detener la ejecución')
        }
    }

    async function handleToolDecision(decision) {
        const token = getToken()

        if (!token) {
            navigate('/login', { replace: true })
            return
        }

        if (!pendingTool || sendingDecision) return

        try {
            setSendingDecision(true)
            await sendToolDecision(token, pendingTool.chatId, decision)
            setPendingTool(null)
        } catch (error) {
            setError(error.message || 'No se pudo enviar la decisión')
        } finally {
            setSendingDecision(false)
        }
    }

    function handleLogout() {
        closeCurrentSubscription()
        removeToken()
        navigate('/login', { replace: true })
    }

    return (
        <div style={styles.page}>
            <ErrorToast
                message={error}
                visible={!!error}
                onClose={() => setError('')}
                duration={5000}
            />

            <ChatSidebar
                chats={chats}
                loading={loadingChats}
                selectedChatId={isDraftChat ? 'new' : selectedChatId}
                creatingChat={creatingChat}
                onSelectChat={handleSelectChat}
                onNewChat={handleNewChat}
                onLogout={handleLogout}
                onConfigClose={triggerInputFocus}
                isMobile={isMobile}
                isMobileOpen={isMobileSidebarOpen}
                onCloseMobile={() => setIsMobileSidebarOpen(false)}
            />

            <ChatMain
                selectedChatId={selectedChatId}
                messages={messages}
                loadingMessages={loadingMessages}
                error={error}
                onSubmitComposer={handleSubmitComposer}
                onAudioError={setError}
                onStopMessage={handleStopMessage}
                isStreaming={isStreaming}
                isStopping={isStopping}
                assistantDraft={assistantDraft}
                streamSteps={streamSteps}
                pendingTool={pendingTool}
                sendingDecision={sendingDecision}
                onConfirmTool={() => handleToolDecision(true)}
                onRejectTool={() => handleToolDecision(false)}
                focusTrigger={focusTrigger}
                composerResetKey={composerResetKey}
                isMobile={isMobile}
                onOpenSidebar={() => setIsMobileSidebarOpen(true)}
                isMobileSidebarOpen={isMobileSidebarOpen}
                pendingFiles={pendingFiles}
                onAddFiles={addPendingFiles}
                onRemovePendingFile={removePendingFile}
            />
        </div>
    )
}

const styles = {
    page: {
        display: 'flex',
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--bg)',
    },
}

export default ChatPage