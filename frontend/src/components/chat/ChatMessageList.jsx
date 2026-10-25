import { memo, useMemo } from 'react'
import ChatMessage from './ChatMessage'
import ChatStreamSteps from './ChatStreamSteps'

const ChatMessageList = memo(function ChatMessageList({
                                                          messages,
                                                          isStreaming,
                                                          assistantDraft,
                                                          streamSteps,
                                                          pendingTool,
                                                          sendingDecision,
                                                          onConfirmTool,
                                                          onRejectTool,
                                                          messagesEndRef,
                                                      }) {
    const renderedMessages = useMemo(() => {
        return messages.map((message, index) => {
            const prevMessage = messages[index - 1]
            const nextMessage = messages[index + 1]

            return (
                <ChatMessage
                    key={message.id || `${message.role}-${index}`}
                    message={message}
                    isGroupedWithPrev={prevMessage?.role === message.role}
                    isGroupedWithNext={nextMessage?.role === message.role}
                />
            )
        })
    }, [messages])

    const draftMessage = useMemo(() => {
        if (!assistantDraft) return null

        return (
            <ChatMessage
                message={{
                    role: 'assistant',
                    content: assistantDraft,
                }}
                isGroupedWithPrev={messages[messages.length - 1]?.role === 'assistant'}
                isGroupedWithNext={false}
            />
        )
    }, [assistantDraft, messages])

    return (
        <div style={styles.messagesContainer}>
            <div style={styles.messageColumn}>
                {messages.length === 0 && !isStreaming ? (
                    <p style={styles.emptyChatText}>
                        Este chat todavía no tiene mensajes.
                    </p>
                ) : null}

                {renderedMessages}

                {draftMessage}

                <ChatStreamSteps
                    streamSteps={streamSteps}
                    pendingTool={pendingTool}
                    sendingDecision={sendingDecision}
                    onConfirmTool={onConfirmTool}
                    onRejectTool={onRejectTool}
                />

                <div ref={messagesEndRef} />
            </div>
        </div>
    )
})

const styles = {
    messagesContainer: {
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
    },
    messageColumn: {
        width: '100%',
        maxWidth: '820px',
        display: 'flex',
        flexDirection: 'column',
    },
    emptyChatText: {
        color: 'var(--text)',
        fontSize: '15px',
        opacity: 0.7,
    },
}

export default ChatMessageList