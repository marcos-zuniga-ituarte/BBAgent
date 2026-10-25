import React, { memo, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import remarkGfm from 'remark-gfm'
import { markdownRehypePlugins } from '../../utils/markdownPlugins.js'
import {downloadFileToBrowser} from "../../api/filesApi.js";
import {getToken} from "../../utils/authStorage.js";


function normalizeMessageContent(content) {
    if (typeof content === 'string') {
        return {
            text: content,
            files: [],
        }
    }

    if (!content || typeof content !== 'object') {
        return {
            text: '',
            files: [],
        }
    }

    return {
        text:
            typeof content.text === 'string'
                ? content.text
                : content.text != null
                    ? String(content.text)
                    : '',
        files: Array.isArray(content.files) ? content.files : [],
    }
}

function getFileLabel(file, index) {
    if (file?.filename && String(file.filename).trim()) {
        return file.filename
    }

    if (file?.file_id && String(file.file_id).trim()) {
        return file.file_id
    }

    if (file?.id && String(file.id).trim()) {
        return file.id
    }

    return `file-${index + 1}`
}

function isImageFile(file) {
    if (!file || typeof file !== 'object') return false

    if (file.type === 'image') return true
    if (file.kind === 'image') return true

    const mimeType = typeof file.mime_type === 'string' ? file.mime_type : ''
    if (mimeType.startsWith('image/')) return true

    const imageUrl =
        file.image_url ||
        file.previewUrl ||
        file.preview ||
        file.url ||
        file.src

    return typeof imageUrl === 'string' && imageUrl.startsWith('data:image/')
}

function getImageSrc(file) {
    if (!file || typeof file !== 'object') return ''

    return (
        file.image_url ||
        file.previewUrl ||
        file.preview ||
        file.url ||
        file.src ||
        ''
    )
}

const CodeBlock = memo(function CodeBlock({ code, language }) {
    const [copied, setCopied] = useState(false)

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code)
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
        } catch (error) {
            console.error('Failed to copy code:', error)
        }
    }

    return (
        <div className="code-block-shell">
            <div className="code-block-header">
                <span className="code-block-language">
                    {language || 'text'}
                </span>

                <button
                    onClick={handleCopy}
                    className="copy-btn code-copy-btn"
                    type="button"
                >
                    {copied ? 'Copied!' : 'Copy'}
                </button>
            </div>

            <div className="code-block-body">
                <SyntaxHighlighter
                    language={language || 'text'}
                    useInlineStyles={false}
                    PreTag="div"
                    wrapLongLines={false}
                    className="code-block"
                    customStyle={{
                        margin: 0,
                        padding: 0,
                        background: 'transparent',
                        border: 0,
                        borderRadius: 0,
                    }}
                    codeTagProps={{
                        className: 'code-block-code',
                        style: {
                            fontFamily:
                                'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
                        },
                    }}
                >
                    {code}
                </SyntaxHighlighter>
            </div>
        </div>
    )
})

const ChatMessage = memo(function ChatMessage({
                                                  message,
                                                  isGroupedWithPrev = false,
                                                  isGroupedWithNext = false,
                                              }) {
    const isUser = message.role === 'user'
    const normalizedContent = normalizeMessageContent(message.content)
    const textContent = normalizedContent.text || ''
    const files = normalizedContent.files || []
    const hasFiles = isUser && files.length > 0
    const assistantLineSpacing = '0px'

    const rowStyle = useMemo(() => {
        return {
            ...styles.messageRow,
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            marginTop: isGroupedWithPrev
                ? isUser
                    ? '8px'
                    : assistantLineSpacing
                : isUser
                    ? '16px'
                    : '10px',
            marginBottom: isGroupedWithNext
                ? isUser
                    ? '8px'
                    : assistantLineSpacing
                : isUser
                    ? '16px'
                    : '10px',
        }
    }, [isUser, isGroupedWithPrev, isGroupedWithNext])

    const bubbleStyle = useMemo(() => {
        return {
            ...styles.messageBubble,
            ...(isUser ? styles.userBubble : styles.assistantBubble),
            padding: isUser ? '12px 16px' : '10px 14px',
            borderTopRightRadius: isUser
                ? isGroupedWithPrev
                    ? '10px'
                    : '18px'
                : '18px',
            borderBottomRightRadius: isUser
                ? isGroupedWithNext
                    ? '10px'
                    : '6px'
                : '18px',
            borderTopLeftRadius: isUser
                ? '18px'
                : isGroupedWithPrev
                    ? '10px'
                    : '18px',
            borderBottomLeftRadius: isUser
                ? '18px'
                : isGroupedWithNext
                    ? '10px'
                    : '6px',
        }
    }, [isUser, isGroupedWithPrev, isGroupedWithNext])

    const markdownComponents = useMemo(() => {
        return {
            code({ node, className, children, ...props }) {
                const isInline =
                    node?.position?.start?.line === node?.position?.end?.line &&
                    !className

                if (isInline) {
                    return (
                        <code className="inline-code" {...props}>
                            {children}
                        </code>
                    )
                }

                return (
                    <code className={className} {...props}>
                        {children}
                    </code>
                )
            },
            pre({ children }) {
                const child = React.Children.toArray(children)[0]

                if (React.isValidElement(child) && child.props) {
                    const className = child.props.className || ''
                    const match = /language-(\w+)/.exec(className)
                    const codeString = String(child.props.children || '').replace(
                        /\n$/,
                        ''
                    )

                    return <CodeBlock code={codeString} language={match?.[1]} />
                }

                return <pre>{children}</pre>
            },
        }
    }, [])

    const handleFileClick = async (file) => {
        const fileId = file?.id || file?.file_id
        if (!fileId) return

        const authToken = getToken()
        if (!authToken) {
            console.error('Missing auth token')
            return
        }

        try {
            await downloadFileToBrowser(
                authToken,
                fileId,
                file?.filename
            )
        } catch (error) {
            console.error('Failed to download file:', error)
        }
    }

    return (
        <div style={rowStyle}>
            <div style={bubbleStyle}>
                {isUser ? (
                    <div style={styles.userContentWrapper}>
                        {hasFiles ? (
                            <div style={styles.filesContainer}>
                                {files.map((file, index) => {
                                    const imageSrc = getImageSrc(file)
                                    const imageFile = isImageFile(file) && imageSrc

                                    if (imageFile) {
                                        return (
                                            <button
                                                key={`${file?.id || file?.file_id || 'image'}-${index}`}
                                                type="button"
                                                style={styles.imageThumbButton}
                                                title={getFileLabel(file, index)}
                                                onClick={() => handleFileClick(file)}
                                            >
                                                <img
                                                    src={imageSrc}
                                                    alt={getFileLabel(file, index)}
                                                    style={styles.imageThumbImg}
                                                />
                                            </button>
                                        )
                                    }

                                    return (
                                        <button
                                            key={`${file?.id || file?.file_id || file?.filename || 'file'}-${index}`}
                                            type="button"
                                            style={styles.fileChipButton}
                                            title={getFileLabel(file, index)}
                                            onClick={() => handleFileClick(file)}
                                        >
                                            <span style={styles.fileChipIcon}>📎</span>
                                            <span style={styles.fileChipText}>
                                                {getFileLabel(file, index)}
                                            </span>
                                        </button>
                                    )
                                })}
                            </div>
                        ) : null}

                        {textContent ? (
                            <div style={styles.plainText}>{textContent}</div>
                        ) : null}
                    </div>
                ) : (
                    <div className="markdown-content" style={styles.markdownContent}>
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={markdownRehypePlugins}
                            components={markdownComponents}
                        >
                            {textContent}
                        </ReactMarkdown>
                    </div>
                )}
            </div>
        </div>
    )
})

const styles = {
    messageRow: {
        display: 'flex',
        width: '100%',
    },
    messageBubble: {
        maxWidth: '100%',
        borderRadius: '18px',
        fontSize: '15px',
        lineHeight: 1.6,
        wordBreak: 'break-word',
    },
    userBubble: {
        background: 'var(--bubble-user)',
        color: 'var(--text-user-message)',
    },
    assistantBubble: {
        color: 'var(--text-assistant-message)',
    },
    plainText: {
        whiteSpace: 'pre-wrap',
    },
    markdownContent: {
        minWidth: 0,
    },
    userContentWrapper: {
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
    },
    filesContainer: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '6px',
        maxWidth: '100%',
    },
    imageThumbButton: {
        width: '72px',
        height: '72px',
        borderRadius: '12px',
        overflow: 'hidden',
        background: 'rgba(255,255,255,0.18)',
        border: '1px solid rgba(255,255,255,0.18)',
        flexShrink: 0,
        padding: 0,
        cursor: 'pointer',
        appearance: 'none',
        WebkitAppearance: 'none',
    },
    imageThumbImg: {
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        display: 'block',
    },
    fileChip: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        minWidth: 0,
        maxWidth: '280px',
        padding: '4px 10px',
        borderRadius: '999px',
        background: 'rgba(255,255,255,0.18)',
        border: '1px solid rgba(255,255,255,0.18)',
    },
    fileChipButton: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        minWidth: 0,
        maxWidth: '280px',
        padding: '4px 10px',
        borderRadius: '999px',
        background: 'rgba(255,255,255,0.18)',
        border: '1px solid rgba(255,255,255,0.18)',
        cursor: 'pointer',
        appearance: 'none',
        WebkitAppearance: 'none',
        color: 'inherit',
        font: 'inherit',
        textAlign: 'left',
    },
    fileChipIcon: {
        flexShrink: 0,
        fontSize: '12px',
        lineHeight: 1,
        opacity: 0.9,
    },
    fileChipText: {
        minWidth: 0,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        fontSize: '12px',
        lineHeight: '16px',
    },
}

export default ChatMessage
