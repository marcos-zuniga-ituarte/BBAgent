import { MicIcon, SendIcon, StopIcon } from './ChatInputIcons.jsx'
import { styles } from './chatInputStyles.js'

function ChatInputActions({
                              isRecording,
                              isStreaming,
                              isStopping,
                              recordedAudioFile,
                              hasFilesToSend,
                              hasTextToSend,
                              audioDisabled,
                              sendDisabled,
                              onAudioClick,
                              onSendClick,
                          }) {
    return (
        <>
            <button
                type="button"
                style={{
                    ...styles.audioButton,
                    ...(isRecording ? styles.audioButtonRecording : {}),
                    ...(audioDisabled ? styles.iconButtonDisabled : {}),
                }}
                onClick={onAudioClick}
                disabled={isRecording ? false : audioDisabled}
                title={
                    isRecording
                        ? 'Detener grabación'
                        : recordedAudioFile
                            ? 'Envía o elimina el audio actual'
                            : 'Grabar audio'
                }
            >
                {isRecording ? <StopIcon size={14} /> : <MicIcon size={16} />}
            </button>

            <button
                type="button"
                style={{
                    ...styles.sendButton,
                    ...(isStreaming ? styles.sendButtonStreaming : {}),
                    ...(isStopping ? styles.sendButtonStopping : {}),
                    ...(sendDisabled ? styles.sendButtonDisabled : {}),
                }}
                onClick={onSendClick}
                disabled={sendDisabled}
                title={
                    isStreaming
                        ? isStopping
                            ? 'Deteniendo...'
                            : 'Detener'
                        : isRecording
                            ? 'Detener y enviar audio'
                            : recordedAudioFile
                                ? 'Enviar audio'
                                : hasFilesToSend && !hasTextToSend
                                    ? 'Enviar archivos'
                                    : 'Enviar'
                }
            >
                {isStreaming ? (
                    isStopping ? '…' : <StopIcon size={12} />
                ) : (
                    <SendIcon size={15} />
                )}
            </button>
        </>
    )
}

export default ChatInputActions