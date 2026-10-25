import { AudioReadyIcon, CloseIcon } from './ChatInputIcons.jsx'
import { styles } from './chatInputStyles.js'

function RecordingComposer({
                               mode,
                               recordingPulse,
                               recordingSeconds,
                               recordedAudioSeconds,
                               onDeleteAudio,
                               formatRecordingTime,
                           }) {
    if (mode === 'recording') {
        return (
            <div style={styles.recordingView}>
                <div style={styles.recordingLeft}>
                    <span style={styles.recordingDot} />
                    <span style={styles.recordingLabel}>Grabando…</span>
                </div>

                <div style={styles.recordingBars}>
                    {[0, 1, 2, 3, 4].map((index) => {
                        const frames = [0.45, 0.7, 1, 0.75, 0.5, 0.82]
                        const scale = frames[(recordingPulse + index) % frames.length]

                        return (
                            <span
                                key={index}
                                style={{
                                    ...styles.recordingBar,
                                    transform: `scaleY(${scale})`,
                                    opacity: 0.55 + scale * 0.45,
                                }}
                            />
                        )
                    })}
                </div>

                <span style={styles.recordingTime}>
                    {formatRecordingTime(recordingSeconds)}
                </span>
            </div>
        )
    }

    if (mode === 'audio-preview') {
        return (
            <div style={styles.audioPreview}>
                <div style={styles.audioPreviewInfo}>
                    <span style={styles.audioPreviewIcon}>
                        <AudioReadyIcon size={16} />
                    </span>

                    <span style={styles.audioPreviewText}>
                        Audio listo · {formatRecordingTime(recordedAudioSeconds)}
                    </span>
                </div>

                <button
                    type="button"
                    style={styles.deleteAudioButton}
                    onClick={onDeleteAudio}
                    title="Eliminar audio"
                >
                    <CloseIcon size={14} />
                </button>
            </div>
        )
    }

    return null
}

export default RecordingComposer