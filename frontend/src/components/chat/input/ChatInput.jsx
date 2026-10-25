import { memo, useEffect, useEffectEvent, useRef, useState } from 'react'
import PendingFilesBar from './PendingFilesBar.jsx'
import TextComposer from './TextComposer.jsx'
import RecordingComposer from './RecordingComposer.jsx'
import ChatInputActions from './ChatInputActions.jsx'
import { AttachIcon } from './ChatInputIcons.jsx'
import { styles } from './chatInputStyles.js'
import {
    buildRecordedAudioFile,
    formatRecordingTime,
    getSupportedMimeType,
} from './chatInputAudio.utils.js'

const ChatInput = memo(function ChatInput({
                                              onSubmitComposer,
                                              onAudioError,
                                              onStopMessage,
                                              isStreaming,
                                              isStopping = false,
                                              disabled = false,
                                              focusTrigger,
                                              resetKey = 0,
                                              isMobile,
                                              userMessages = [],
                                              pendingTool,
                                              sendingDecision,
                                              onConfirmTool,
                                              onRejectTool,
                                              pendingFiles = [],
                                              onAddFiles,
                                              onRemovePendingFile,
                                          }) {
    const textareaRef = useRef(null)
    const fileInputRef = useRef(null)
    const mediaRecorderRef = useRef(null)
    const mediaStreamRef = useRef(null)
    const audioChunksRef = useRef([])
    const recordingTimerRef = useRef(null)
    const recordingSecondsRef = useRef(0)
    const shouldSendAfterRecordingRef = useRef(false)
    const recordedAudioFileRef = useRef(null)
    const recordedAudioSecondsRef = useRef(0)
    const pendingFilesRef = useRef(pendingFiles)
    const inputValueRef = useRef('')
    const isStreamingRef = useRef(isStreaming)
    const isStoppingRef = useRef(isStopping)
    const disabledRef = useRef(disabled)
    const pendingToolRef = useRef(pendingTool)
    const sendingDecisionRef = useRef(sendingDecision)
    const isRecordingRef = useRef(false)
    const dragCounterRef = useRef(0)

    const [inputValue, setInputValue] = useState('')
    const [historyIndex, setHistoryIndex] = useState(-1)
    const [draftValue, setDraftValue] = useState('')
    const [isRecording, setIsRecording] = useState(false)
    const [recordingSeconds, setRecordingSeconds] = useState(0)
    const [recordingPulse, setRecordingPulse] = useState(0)
    const [recordedAudioFile, setRecordedAudioFile] = useState(null)
    const [recordedAudioSeconds, setRecordedAudioSeconds] = useState(0)
    const [isDraggingFiles, setIsDraggingFiles] = useState(false)

    const hasPendingTool = !!pendingTool
    const hasTextToSend = !!inputValue.trim()
    const hasAudioToSend = !!recordedAudioFile
    const hasFilesToSend = pendingFiles.length > 0

    useEffect(() => {
        pendingFilesRef.current = pendingFiles
    }, [pendingFiles])

    useEffect(() => {
        isStreamingRef.current = isStreaming
    }, [isStreaming])

    useEffect(() => {
        isStoppingRef.current = isStopping
    }, [isStopping])

    useEffect(() => {
        disabledRef.current = disabled
    }, [disabled])

    useEffect(() => {
        pendingToolRef.current = pendingTool
    }, [pendingTool])

    useEffect(() => {
        sendingDecisionRef.current = sendingDecision
    }, [sendingDecision])

    useEffect(() => {
        isRecordingRef.current = isRecording
    }, [isRecording])

    function setComposerText(nextValue) {
        inputValueRef.current = nextValue
        setInputValue(nextValue)
    }

    function moveCursorToEnd() {
        requestAnimationFrame(() => {
            const el = textareaRef.current
            if (!el) return
            const len = el.value.length
            el.focus()
            el.setSelectionRange(len, len)
        })
    }

    function stopMediaTracks() {
        if (!mediaStreamRef.current) return
        mediaStreamRef.current.getTracks().forEach((track) => track.stop())
        mediaStreamRef.current = null
    }

    function stopRecordingTimer() {
        if (recordingTimerRef.current) {
            clearInterval(recordingTimerRef.current)
            recordingTimerRef.current = null
        }
    }

    function setRecordedAudioState(file, seconds) {
        recordedAudioFileRef.current = file
        recordedAudioSecondsRef.current = seconds
        setRecordedAudioFile(file)
        setRecordedAudioSeconds(seconds)
    }

    function clearRecordedAudioState() {
        recordedAudioFileRef.current = null
        recordedAudioSecondsRef.current = 0
        setRecordedAudioFile(null)
        setRecordedAudioSeconds(0)
    }

    function resetComposerHistory() {
        setHistoryIndex(-1)
        setDraftValue('')
    }

    function getFilesFromClipboardEvent(event) {
        const clipboardData = event.clipboardData
        if (!clipboardData) return []

        const files = []

        if (clipboardData.items?.length) {
            for (const item of clipboardData.items) {
                if (item.kind === 'file') {
                    const file = item.getAsFile()
                    if (file) files.push(file)
                }
            }
        }

        if (!files.length && clipboardData.files?.length) {
            for (const file of Array.from(clipboardData.files)) {
                files.push(file)
            }
        }

        return files
    }

    function hasFilesInDataTransfer(dataTransfer) {
        if (!dataTransfer) return false

        if (dataTransfer.items?.length) {
            return Array.from(dataTransfer.items).some((item) => item.kind === 'file')
        }

        if (dataTransfer.files?.length) {
            return true
        }

        return Array.from(dataTransfer.types || []).includes('Files')
    }

    function getFilesFromDataTransfer(dataTransfer) {
        if (!dataTransfer?.files?.length) return []

        return Array.from(dataTransfer.files).filter(
            (file) =>
                file &&
                typeof file.name === 'string' &&
                typeof file.size === 'number',
        )
    }

    function addPendingFiles(files) {
        if (!Array.isArray(files) || !files.length) return

        const normalizedFiles = files.filter(Boolean)
        if (!normalizedFiles.length) return

        pendingFilesRef.current = [...pendingFilesRef.current, ...normalizedFiles]
        onAddFiles?.(normalizedFiles)

        requestAnimationFrame(() => {
            textareaRef.current?.focus()
        })
    }

    function handleRemovePendingFile(indexToRemove) {
        pendingFilesRef.current = pendingFilesRef.current.filter(
            (_, index) => index !== indexToRemove,
        )
        onRemovePendingFile?.(indexToRemove)
    }

    function handlePaste(event) {
        if (disabledRef.current) return

        const pastedFiles = getFilesFromClipboardEvent(event)
        if (!pastedFiles.length) return

        event.preventDefault()
        addPendingFiles(pastedFiles)
    }

    useEffect(() => {
        const textarea = textareaRef.current
        if (!textarea) return

        textarea.style.height = '0px'
        const nextHeight = Math.min(textarea.scrollHeight, 220)
        textarea.style.height = `${nextHeight}px`
    }, [inputValue])

    useEffect(() => {
        const textarea = textareaRef.current
        if (!textarea || disabledRef.current || isRecording || recordedAudioFile) return
        const frame = requestAnimationFrame(() => {
            textarea.focus()
            const length = textarea.value.length
            textarea.setSelectionRange(length, length)
        })
        return () => cancelAnimationFrame(frame)
    }, [isRecording, recordedAudioFile, focusTrigger])

    useEffect(() => {
        if (!isRecording) return

        const interval = setInterval(() => {
            setRecordingPulse((prev) => (prev + 1) % 6)
        }, 140)

        return () => clearInterval(interval)
    }, [isRecording])

    useEffect(() => {
        shouldSendAfterRecordingRef.current = false
        stopRecordingTimer()

        const recorder = mediaRecorderRef.current
        if (recorder && recorder.state !== 'inactive') {
            recorder.ondataavailable = null
            recorder.onstop = null
            try {
                recorder.stop()
            } catch {
                // ignore stop failures
            }
        }

        mediaRecorderRef.current = null
        stopMediaTracks()
        audioChunksRef.current = []
        recordingSecondsRef.current = 0

        setIsRecording(false)
        setRecordingSeconds(0)
        setRecordingPulse(0)
        clearRecordedAudioState()
        setComposerText('')
        resetComposerHistory()
        dragCounterRef.current = 0
        setIsDraggingFiles(false)
    }, [resetKey])

    function isEditableElement(element) {
        if (!element) return false

        const tagName = element.tagName?.toLowerCase()

        return (
            tagName === 'input' ||
            tagName === 'textarea' ||
            tagName === 'select' ||
            element.isContentEditable
        )
    }

    function isTypingKey(event) {
        if (event.ctrlKey || event.metaKey || event.altKey) {
            return false
        }

        return event.key.length === 1
    }

    async function submitComposer({ forceAudioSend = false } = {}) {
        const text = String(inputValueRef.current || '').trim()
        const audioFile = recordedAudioFileRef.current
        const files = pendingFilesRef.current

        if (disabledRef.current) return

        if (forceAudioSend) {
            if (!audioFile || isStreamingRef.current) return

            try {
                await onSubmitComposer?.({
                    text: '',
                    audioFile,
                    files,
                })
                clearRecordedAudioState()
                resetComposerHistory()
            } catch (err) {
                setRecordedAudioState(audioFile, recordedAudioSecondsRef.current)
                onAudioError?.(err?.message || 'No se pudo enviar el audio')
            } finally {
                requestAnimationFrame(() => {
                    textareaRef.current?.focus()
                })
            }
            return
        }

        if (audioFile) {
            if (isStreamingRef.current) return

            try {
                await onSubmitComposer?.({
                    text: '',
                    audioFile,
                    files,
                })
                clearRecordedAudioState()
                resetComposerHistory()
            } catch (err) {
                setRecordedAudioState(audioFile, recordedAudioSecondsRef.current)
                onAudioError?.(err?.message || 'No se pudo enviar el audio')
            } finally {
                requestAnimationFrame(() => {
                    textareaRef.current?.focus()
                })
            }
            return
        }

        if (isStreamingRef.current) return
        if (!text && files.length === 0) return

        setComposerText('')
        resetComposerHistory()

        await onSubmitComposer?.({
            text,
            audioFile: null,
            files,
        })

        requestAnimationFrame(() => {
            textareaRef.current?.focus()
        })
    }

    function handleStopCurrentMessage() {
        if (!isStreamingRef.current || isStoppingRef.current) return
        onStopMessage?.()
    }

    function handleStopRecording() {
        shouldSendAfterRecordingRef.current = false

        const recorder = mediaRecorderRef.current
        if (!recorder || recorder.state === 'inactive') return

        recorder.stop()
    }

    function handleStopRecordingAndSend() {
        if (disabledRef.current) return
        if (isStreamingRef.current) return
        if (!isRecordingRef.current) return

        const recorder = mediaRecorderRef.current
        if (!recorder || recorder.state === 'inactive') return

        shouldSendAfterRecordingRef.current = true
        recorder.stop()
    }

    function handlePrimarySendAction() {
        if (isStreamingRef.current) return

        if (isRecordingRef.current) {
            handleStopRecordingAndSend()
            return
        }

        submitComposer()
    }

    const sendFromGlobalKey = useEffectEvent(() => handlePrimarySendAction())
    const addFilesFromDrop = useEffectEvent((files) => addPendingFiles(files))

    useEffect(() => {
        function handleGlobalKeyDown(event) {
            if (disabledRef.current) return

            const textarea = textareaRef.current
            const activeElement = document.activeElement
            const activeIsEditable = isEditableElement(activeElement)
            const textareaHasFocus = activeElement === textarea
            const hasModifier = event.ctrlKey || event.metaKey

            if (
                hasModifier &&
                pendingToolRef.current &&
                !sendingDecisionRef.current
            ) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    onConfirmTool?.()
                    return
                }

                if (event.key === 'Backspace') {
                    event.preventDefault()
                    onRejectTool?.()
                    return
                }
            }

            if (textareaHasFocus) return
            if (activeIsEditable) return

            if (event.key === 'Enter' && !event.shiftKey) {
                if (!isStreamingRef.current) {
                    event.preventDefault()
                    sendFromGlobalKey()
                }
                return
            }

            if (isRecordingRef.current || recordedAudioFileRef.current) return
            if (!textarea) return
            if (!isTypingKey(event)) return

            event.preventDefault()

            textarea.focus()

            const currentValue = inputValueRef.current
            const start = textarea.selectionStart ?? currentValue.length
            const end = textarea.selectionEnd ?? currentValue.length
            const nextValue =
                currentValue.slice(0, start) + event.key + currentValue.slice(end)

            setComposerText(nextValue)

            requestAnimationFrame(() => {
                const pos = start + event.key.length
                textarea.setSelectionRange(pos, pos)
            })
        }

        window.addEventListener('keydown', handleGlobalKeyDown)

        return () => {
            window.removeEventListener('keydown', handleGlobalKeyDown)
        }
    }, [onConfirmTool, onRejectTool])

    useEffect(() => {
        function hideDragOverlay() {
            dragCounterRef.current = 0
            setIsDraggingFiles(false)
        }

        function handleWindowDragEnter(event) {
            if (!hasFilesInDataTransfer(event.dataTransfer)) return

            event.preventDefault()
            dragCounterRef.current += 1
            setIsDraggingFiles(true)
        }

        function handleWindowDragOver(event) {
            if (!hasFilesInDataTransfer(event.dataTransfer)) return

            event.preventDefault()

            if (event.dataTransfer) {
                event.dataTransfer.dropEffect = 'copy'
            }

            if (!isDraggingFiles) {
                setIsDraggingFiles(true)
            }
        }

        function handleWindowDragLeave(event) {
            if (!hasFilesInDataTransfer(event.dataTransfer)) return

            event.preventDefault()
            dragCounterRef.current = Math.max(0, dragCounterRef.current - 1)

            if (dragCounterRef.current === 0) {
                setIsDraggingFiles(false)
            }
        }

        function handleWindowDrop(event) {
            if (!hasFilesInDataTransfer(event.dataTransfer)) return

            event.preventDefault()

            const droppedFiles = getFilesFromDataTransfer(event.dataTransfer)
            hideDragOverlay()

            if (!droppedFiles.length) return

            addFilesFromDrop(droppedFiles)
        }

        function handleWindowBlur() {
            hideDragOverlay()
        }

        window.addEventListener('dragenter', handleWindowDragEnter)
        window.addEventListener('dragover', handleWindowDragOver)
        window.addEventListener('dragleave', handleWindowDragLeave)
        window.addEventListener('drop', handleWindowDrop)
        window.addEventListener('blur', handleWindowBlur)

        return () => {
            window.removeEventListener('dragenter', handleWindowDragEnter)
            window.removeEventListener('dragover', handleWindowDragOver)
            window.removeEventListener('dragleave', handleWindowDragLeave)
            window.removeEventListener('drop', handleWindowDrop)
            window.removeEventListener('blur', handleWindowBlur)
        }
    }, [isDraggingFiles])

    useEffect(() => {
        return () => {
            shouldSendAfterRecordingRef.current = false
            stopRecordingTimer()

            const recorder = mediaRecorderRef.current
            if (recorder && recorder.state !== 'inactive') {
                recorder.ondataavailable = null
                recorder.onstop = null
                recorder.stop()
            }

            stopMediaTracks()
        }
    }, [])

    function handleDeleteRecordedAudio() {
        shouldSendAfterRecordingRef.current = false
        clearRecordedAudioState()

        requestAnimationFrame(() => {
            textareaRef.current?.focus()
        })
    }

    async function handleStartRecording() {
        if (disabledRef.current) return
        if (isRecordingRef.current) return
        if (recordedAudioFileRef.current) return

        if (!navigator.mediaDevices?.getUserMedia) {
            onAudioError?.('Tu navegador no soporta grabación de audio')
            return
        }

        if (typeof MediaRecorder === 'undefined') {
            onAudioError?.('MediaRecorder no está disponible en este navegador')
            return
        }

        try {
            shouldSendAfterRecordingRef.current = false
            setComposerText('')
            clearRecordedAudioState()
            resetComposerHistory()
            recordingSecondsRef.current = 0
            setRecordingSeconds(0)

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const mimeType = getSupportedMimeType()

            mediaStreamRef.current = stream
            audioChunksRef.current = []

            const recorder = mimeType
                ? new MediaRecorder(stream, { mimeType })
                : new MediaRecorder(stream)

            mediaRecorderRef.current = recorder

            recorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunksRef.current.push(event.data)
                }
            }

            recorder.onstop = async () => {
                stopRecordingTimer()
                setIsRecording(false)

                const finalMimeType = recorder.mimeType || mimeType || 'audio/webm'
                const chunks = [...audioChunksRef.current]
                const finalSeconds = recordingSecondsRef.current
                const shouldSendAfterRecording = shouldSendAfterRecordingRef.current

                shouldSendAfterRecordingRef.current = false
                audioChunksRef.current = []
                mediaRecorderRef.current = null
                stopMediaTracks()

                const file = buildRecordedAudioFile(chunks, finalMimeType)
                if (!file) return

                setRecordedAudioState(file, finalSeconds)

                if (shouldSendAfterRecording) {
                    await submitComposer({ forceAudioSend: true })
                    return
                }

                requestAnimationFrame(() => {
                    textareaRef.current?.focus()
                })
            }

            recorder.start()
            setIsRecording(true)
            setRecordingSeconds(0)
            recordingSecondsRef.current = 0

            recordingTimerRef.current = setInterval(() => {
                recordingSecondsRef.current += 1
                setRecordingSeconds(recordingSecondsRef.current)
            }, 1000)
        } catch {
            shouldSendAfterRecordingRef.current = false
            stopRecordingTimer()
            stopMediaTracks()
            setIsRecording(false)
            onAudioError?.('No se pudo acceder al micrófono')
        }
    }

    function handleAudioButtonClick() {
        if (isRecording) {
            handleStopRecording()
            return
        }

        handleStartRecording()
    }

    function handleInputChange(nextValue) {
        setComposerText(nextValue)
    }

    function handleKeyDown(event) {
        if (hasPendingTool && !sendingDecision) {
            const hasModifier = event.ctrlKey || event.metaKey

            if (hasModifier && event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onConfirmTool?.()
                return
            }

            if (hasModifier && event.key === 'Backspace') {
                event.preventDefault()
                onRejectTool?.()
                return
            }
        }

        if (event.key === 'Enter' && !event.shiftKey) {
            if (!isStreamingRef.current) {
                event.preventDefault()
                handlePrimarySendAction()
            }
            return
        }

        if (event.key === 'ArrowUp') {
            if (userMessages.length === 0) return

            event.preventDefault()

            if (historyIndex === -1) {
                setDraftValue(inputValueRef.current)
            }

            const nextIndex = Math.min(historyIndex + 1, userMessages.length - 1)
            const nextMessage = userMessages[userMessages.length - 1 - nextIndex]

            if (nextMessage !== undefined) {
                setComposerText(typeof nextMessage === 'string' ? nextMessage : '')
                setHistoryIndex(nextIndex)
                moveCursorToEnd()
            }

            return
        }

        if (event.key === 'ArrowDown') {
            if (historyIndex === -1) return

            event.preventDefault()

            const nextIndex = historyIndex - 1

            if (nextIndex < 0) {
                setComposerText(draftValue)
                setHistoryIndex(-1)
                moveCursorToEnd()
            } else {
                const nextMessage = userMessages[userMessages.length - 1 - nextIndex]
                setComposerText(typeof nextMessage === 'string' ? nextMessage : '')
                setHistoryIndex(nextIndex)
                moveCursorToEnd()
            }
        }
    }

    function handleAttachFilesClick() {
        if (disabledRef.current) return
        fileInputRef.current?.click()
    }

    function handleFileInputChange(event) {
        const selected = Array.from(event.target.files || [])
        if (selected.length) {
            addPendingFiles(selected)
        }
        event.target.value = ''
    }

    const sendDisabled = isStreaming
        ? isStopping
        : !isRecording && !hasTextToSend && !hasAudioToSend && !hasFilesToSend

    const audioDisabled = disabled || !!recordedAudioFile

    const centerMode = isRecording
        ? 'recording'
        : recordedAudioFile
            ? 'audio-preview'
            : 'text'

    return (
        <div
            style={{
                ...styles.wrapper,
                ...(isMobile ? styles.wrapperMobile : styles.wrapperDesktop),
            }}
        >
            <div
                style={{
                    ...styles.dragOverlay,
                    ...(isDraggingFiles ? styles.dragOverlayVisible : {}),
                }}
                aria-hidden={!isDraggingFiles}
            >
                <div style={styles.dragOverlayCard}>
                    <div style={styles.dragOverlayTitle}>
                        Suelta los archivos para adjuntarlos
                    </div>

                    <div style={styles.dragOverlaySubtitle}>
                        Se añadirán igual que si pulsaras el clip.
                    </div>
                </div>
            </div>

            <div style={styles.inputArea}>
                <PendingFilesBar
                    files={pendingFiles}
                    onRemoveFile={handleRemovePendingFile}
                />

                <div style={styles.inputBox}>
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        style={styles.hiddenInput}
                        onChange={handleFileInputChange}
                    />

                    <button
                        type="button"
                        style={styles.attachButton}
                        onClick={handleAttachFilesClick}
                        title="Añadir archivos"
                    >
                        <AttachIcon size={16} />
                    </button>

                    <div style={styles.centerArea}>
                        <RecordingComposer
                            mode={centerMode}
                            recordingPulse={recordingPulse}
                            recordingSeconds={recordingSeconds}
                            recordedAudioSeconds={recordedAudioSeconds}
                            onDeleteAudio={handleDeleteRecordedAudio}
                            formatRecordingTime={formatRecordingTime}
                        />

                        {centerMode === 'text' ? (
                            <TextComposer
                                ref={textareaRef}
                                value={inputValue}
                                onChange={handleInputChange}
                                onKeyDown={handleKeyDown}
                                onPaste={handlePaste}
                            />
                        ) : null}
                    </div>

                    <ChatInputActions
                        isRecording={isRecording}
                        isStreaming={isStreaming}
                        isStopping={isStopping}
                        recordedAudioFile={recordedAudioFile}
                        hasFilesToSend={hasFilesToSend}
                        hasTextToSend={hasTextToSend}
                        audioDisabled={audioDisabled}
                        sendDisabled={sendDisabled}
                        onAudioClick={handleAudioButtonClick}
                        onSendClick={
                            isStreaming
                                ? handleStopCurrentMessage
                                : handlePrimarySendAction
                        }
                    />
                </div>

                {hasPendingTool && !sendingDecision ? (
                    <div style={styles.toolHint}>
                        <span>
                            Ctrl/Cmd + Enter para aprobar · Ctrl/Cmd + Backspace para rechazar
                        </span>
                    </div>
                ) : null}

                <span style={styles.disclaimer}>
                    {isRecording
                        ? 'Grabando audio. Pulsa el botón rojo para detener o enviar para mandarlo.'
                        : recordedAudioFile
                            ? 'Audio listo para enviar o eliminar.'
                            : hasFilesToSend
                                ? 'Archivos listos para enviar.'
                                : 'BBAgent can make mistakes. Using OpenAI API'}
                </span>
            </div>
        </div>
    )
})

export default ChatInput
