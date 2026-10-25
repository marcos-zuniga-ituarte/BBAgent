import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ChatInput from './input/ChatInput.jsx'
import ChatMessageList from './ChatMessageList'

function ChatMain({
                      selectedChatId,
                      messages,
                      loadingMessages,
                      onSubmitComposer,
                      onAudioError,
                      onStopMessage,
                      isStreaming,
                      isStopping,
                      assistantDraft,
                      streamSteps,
                      pendingTool,
                      sendingDecision,
                      onConfirmTool,
                      onRejectTool,
                      focusTrigger,
                      composerResetKey,
                      isMobile,
                      onOpenSidebar,
                      isMobileSidebarOpen,
                      pendingFiles,
                      onAddFiles,
                      onRemovePendingFile,
                  }) {
    const messagesEndRef = useRef(null)
    const messagesContainerRef = useRef(null)
    const scrollAnimationRef = useRef(null)
    const previousSelectedChatIdRef = useRef(selectedChatId)
    const previousLoadingMessagesRef = useRef(loadingMessages)
    const previousIsStreamingRef = useRef(isStreaming)
    const [mobileMenuTop, setMobileMenuTop] = useState(12)

    const userMessageHistory = useMemo(() => {
        return messages?.filter((m) => m.role === 'user').map((m) => m.content) || []
    }, [messages])

    const cancelScrollAnimation = useCallback(() => {
        if (!scrollAnimationRef.current) return
        cancelAnimationFrame(scrollAnimationRef.current)
        scrollAnimationRef.current = null
    }, [])

    const getDistanceFromBottom = useCallback(() => {
        const container = messagesContainerRef.current
        if (!container) return 0
        return container.scrollHeight - container.scrollTop - container.clientHeight
    }, [])

    const isNearBottom = useCallback((threshold = 120) => {
        return getDistanceFromBottom() < threshold
    }, [getDistanceFromBottom])

    const scrollToBottomInstant = useCallback(() => {
        const container = messagesContainerRef.current
        if (!container) return

        cancelScrollAnimation()
        container.scrollTop = container.scrollHeight
    }, [cancelScrollAnimation])

    const scrollToBottomAnimated = useCallback(() => {
        const container = messagesContainerRef.current
        if (!container) return

        cancelScrollAnimation()

        const animateScrollToBottom = () => {
            const target = container.scrollHeight - container.clientHeight
            const current = container.scrollTop
            const diff = target - current

            if (diff <= 1) {
                container.scrollTop = target
                scrollAnimationRef.current = null
                return
            }

            container.scrollTop = current + diff * 0.16
            scrollAnimationRef.current = requestAnimationFrame(animateScrollToBottom)
        }

        scrollAnimationRef.current = requestAnimationFrame(animateScrollToBottom)
    }, [cancelScrollAnimation])

    useEffect(() => {
        const selectedChatChanged = previousSelectedChatIdRef.current !== selectedChatId
        const finishedLoadingNow = previousLoadingMessagesRef.current && !loadingMessages

        if (selectedChatId && !loadingMessages && (selectedChatChanged || finishedLoadingNow)) {
            requestAnimationFrame(scrollToBottomInstant)
        }

        previousSelectedChatIdRef.current = selectedChatId
        previousLoadingMessagesRef.current = loadingMessages
    }, [selectedChatId, loadingMessages, scrollToBottomInstant])

    useEffect(() => {
        const startedStreamingNow = !previousIsStreamingRef.current && isStreaming

        if (startedStreamingNow) {
            requestAnimationFrame(scrollToBottomAnimated)
        }

        previousIsStreamingRef.current = isStreaming
    }, [isStreaming, scrollToBottomAnimated])

    useEffect(() => {
        const shouldFollow =
            isStreaming || !!assistantDraft || !!pendingTool || streamSteps.length > 0

        if (!shouldFollow || !isNearBottom()) return

        scrollToBottomAnimated()
        return cancelScrollAnimation
    }, [messages, assistantDraft, streamSteps, pendingTool, isStreaming, isNearBottom, scrollToBottomAnimated, cancelScrollAnimation])

    useEffect(() => {
        if (!isMobile) return

        function updateMenuPosition() {
            const visualViewport = window.visualViewport
            setMobileMenuTop(visualViewport ? visualViewport.offsetTop + 12 : 12)
        }

        updateMenuPosition()
        window.addEventListener('resize', updateMenuPosition)
        window.addEventListener('scroll', updateMenuPosition)
        window.visualViewport?.addEventListener('resize', updateMenuPosition)
        window.visualViewport?.addEventListener('scroll', updateMenuPosition)

        return () => {
            window.removeEventListener('resize', updateMenuPosition)
            window.removeEventListener('scroll', updateMenuPosition)
            window.visualViewport?.removeEventListener('resize', updateMenuPosition)
            window.visualViewport?.removeEventListener('scroll', updateMenuPosition)
        }
    }, [isMobile])

    return (
        <main style={styles.main}>
            <div style={styles.chatShell}>
                {isMobile && !isMobileSidebarOpen ? (
                    <button
                        type="button"
                        onClick={onOpenSidebar}
                        style={{
                            ...styles.mobileMenuButton,
                            top: `${mobileMenuTop}px`,
                        }}
                        aria-label="Abrir menú"
                    >
                        ☰
                    </button>
                ) : null}

                <div
                    ref={messagesContainerRef}
                    className="sidebar-scroll"
                    style={{
                        ...styles.messagesArea,
                        ...(isMobile ? styles.messagesAreaMobile : {}),
                    }}
                >
                    {!selectedChatId ? (
                        <div style={styles.empty}>
                            <h1 style={styles.emptyTitle}>
                                <span>¿En qué puedo ayudarte?</span>
                            </h1>
                        </div>
                    ) : loadingMessages ? (
                        <div style={styles.empty}>
                            <p style={styles.loadingText}>Cargando mensajes...</p>
                        </div>
                    ) : (
                        <ChatMessageList
                            messages={messages}
                            isStreaming={isStreaming}
                            assistantDraft={assistantDraft}
                            streamSteps={streamSteps}
                            pendingTool={pendingTool}
                            sendingDecision={sendingDecision}
                            onConfirmTool={onConfirmTool}
                            onRejectTool={onRejectTool}
                            messagesEndRef={messagesEndRef}
                        />
                    )}
                </div>

                <ChatInput
                    onSubmitComposer={onSubmitComposer}
                    onAudioError={onAudioError}
                    onStopMessage={onStopMessage}
                    isStreaming={isStreaming}
                    isStopping={isStopping}
                    focusTrigger={focusTrigger}
                    resetKey={composerResetKey}
                    isMobile={isMobile}
                    userMessages={userMessageHistory}
                    pendingTool={pendingTool}
                    sendingDecision={sendingDecision}
                    onConfirmTool={onConfirmTool}
                    onRejectTool={onRejectTool}
                    pendingFiles={pendingFiles}
                    onAddFiles={onAddFiles}
                    onRemovePendingFile={onRemovePendingFile}
                />
            </div>
        </main>
    )
}

const styles = {
    main: {
        flex: 1,
        height: '100vh',
        background: 'var(--bg)',
        color: 'var(--text)',
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0,
        overflow: 'hidden',
        position: 'relative',
    },
    chatShell: {
        flex: 1,
        position: 'relative',
        minWidth: 0,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
    },
    mobileMenuButton: {
        position: 'fixed',
        left: '12px',
        zIndex: 60,
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        color: 'var(--button-text)',
        borderRadius: '10px',
        padding: '10px 12px',
        cursor: 'pointer',
        fontSize: '18px',
        lineHeight: 1,
        boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
    },
    messagesArea: {
        flex: 1,
        overflowY: 'auto',
        minHeight: 0,
        padding: '24px 24px 120px',
    },
    messagesAreaMobile: {
        padding: '72px 16px 120px',
    },
    empty: {
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    emptyTitle: {
        fontSize: '36px',
        fontWeight: 600,
        margin: 0,
        color: 'var(--text)',
        textAlign: 'center',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        flexWrap: 'wrap',
    },
    loadingText: {
        color: 'var(--text)',
        fontSize: '15px',
        opacity: 0.7,
    },
    error: {
        color: 'var(--text)',
        background: 'var(--bubble-user)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '12px 14px',
        fontSize: '14px',
        lineHeight: 1.4,
    },
}

export default ChatMain