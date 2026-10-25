export function formatRecordingTime(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export function getSupportedMimeType() {
    if (typeof MediaRecorder === 'undefined') return ''

    const candidates = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg',
        'audio/mp4',
    ]

    return (
        candidates.find((type) => {
            try {
                return MediaRecorder.isTypeSupported(type)
            } catch {
                return false
            }
        }) || ''
    )
}

export function buildRecordedAudioFile(chunks, finalMimeType) {
    if (!chunks.length) return null

    const extension = finalMimeType.includes('ogg')
        ? 'ogg'
        : finalMimeType.includes('mp4')
            ? 'm4a'
            : 'webm'

    const blob = new Blob(chunks, { type: finalMimeType })

    return new File([blob], `recording-${Date.now()}.${extension}`, {
        type: finalMimeType,
    })
}