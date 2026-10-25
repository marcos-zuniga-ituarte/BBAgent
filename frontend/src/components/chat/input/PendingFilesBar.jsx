import { useEffect, useRef } from 'react'
import { CloseIcon } from './ChatInputIcons.jsx'

function FileThumbIcon({ size = 16, strokeWidth = 1.8 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
                d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <path
                d="M14 3v5h5"
                stroke="currentColor"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    )
}

function isFileLike(value) {
    return !!(
        value &&
        typeof value === 'object' &&
        typeof value.size === 'number' &&
        typeof value.type === 'string' &&
        typeof value.slice === 'function'
    )
}

function getSourceFile(item) {
    if (!item) return null

    const candidates = [
        item,
        item.file,
        item.blob,
        item.raw,
        item.originFileObj,
        item.sourceFile,
    ]

    return candidates.find(isFileLike) || null
}

function getItemName(item, sourceFile) {
    return item?.name || sourceFile?.name || 'Archivo'
}

function getItemSize(item, sourceFile) {
    return item?.size ?? sourceFile?.size ?? 0
}

function getItemMimeType(item, sourceFile) {
    return String(item?.type || sourceFile?.type || '').toLowerCase()
}

function getExistingPreviewUrl(item) {
    const candidates = [
        item?.previewUrl,
        item?.preview,
        item?.thumbUrl,
        item?.thumbnailUrl,
        item?.url,
        item?.src,
    ]

    return (
        candidates.find(
            (value) => typeof value === 'string' && value.trim().length > 0,
        ) || ''
    )
}

function isImageItem(item, sourceFile = getSourceFile(item)) {
    if (getExistingPreviewUrl(item)) return true
    return getItemMimeType(item, sourceFile).startsWith('image/')
}

function buildItemKey(item, index) {
    const sourceFile = getSourceFile(item)
    const name = getItemName(item, sourceFile)
    const size = getItemSize(item, sourceFile)
    const lastModified =
        item?.lastModified ??
        item?.file?.lastModified ??
        item?.originFileObj?.lastModified ??
        sourceFile?.lastModified ??
        0

    return `${name}-${size}-${lastModified}-${index}`
}

function formatFileSize(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function FilePreview({ item, sourceFile, name }) {
    const imageRef = useRef(null)
    const existingUrl = getExistingPreviewUrl(item)

    useEffect(() => {
        if (existingUrl || !sourceFile) return
        const image = imageRef.current
        if (!image || typeof URL.createObjectURL !== 'function') return
        const url = URL.createObjectURL(sourceFile)
        image.src = url
        return () => {
            image.removeAttribute('src')
            URL.revokeObjectURL(url)
        }
    }, [sourceFile, existingUrl])

    return <img ref={imageRef} src={existingUrl || undefined} alt={name} style={styles.imagePreview} />
}

function PendingFilesBar({ files = [], onRemoveFile }) {
    if (!files.length) return null

    return (
        <div style={styles.filesContainer}>
            {files.map((item, index) => {
                const sourceFile = getSourceFile(item)
                const name = getItemName(item, sourceFile)
                const size = getItemSize(item, sourceFile)
                const key = buildItemKey(item, index)
                const isImage = isImageItem(item, sourceFile) && !!(sourceFile || getExistingPreviewUrl(item))

                return (
                    <div
                        key={key}
                        style={styles.fileChip}
                        title={name}
                    >
                        <div style={styles.fileContent}>
                            {isImage ? (
                                <div style={styles.imagePreviewFrame}>
                                    <FilePreview item={item} sourceFile={sourceFile} name={name} />
                                </div>
                            ) : (
                                <div style={styles.fileIconWrap}>
                                    <FileThumbIcon size={16} />
                                </div>
                            )}

                            <div style={styles.fileMeta}>
                                <span style={styles.fileChipName}>{name}</span>
                                <span style={styles.fileChipSize}>
                                    {formatFileSize(size)}
                                </span>
                            </div>
                        </div>

                        <button
                            type="button"
                            style={styles.fileChipRemove}
                            onClick={() => onRemoveFile?.(index)}
                            title="Eliminar archivo"
                        >
                            <CloseIcon size={12} />
                        </button>
                    </div>
                )
            })}
        </div>
    )
}

const styles = {
    filesContainer: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        marginBottom: '6px',
        padding: '0 6px',
        maxWidth: '100%',
    },

    fileChip: {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        minWidth: 0,
        maxWidth: '260px',
        padding: '6px 8px 6px 6px',
        borderRadius: '16px',
        border: '1px solid var(--border)',
        background: 'var(--bg)',
        boxShadow: '0 4px 14px rgba(0,0,0,0.10)',
    },

    fileContent: {
        minWidth: 0,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flex: 1,
    },

    fileIconWrap: {
        width: '36px',
        height: '36px',
        minWidth: '36px',
        borderRadius: '10px',
        border: '1px solid var(--border)',
        background: 'rgba(127,127,127,0.08)',
        color: 'var(--text)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        flexShrink: 0,
    },

    imagePreviewFrame: {
        width: '44px',
        height: '44px',
        minWidth: '44px',
        borderRadius: '12px',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        background: 'rgba(127,127,127,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
    },

    imagePreview: {
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        objectPosition: 'center',
        display: 'block',
    },

    fileMeta: {
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
        overflow: 'hidden',
    },

    fileChipName: {
        fontSize: '12px',
        lineHeight: '16px',
        color: 'var(--text)',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        minWidth: 0,
        maxWidth: '150px',
    },

    fileChipSize: {
        fontSize: '11px',
        lineHeight: '14px',
        color: 'var(--text)',
        opacity: 0.58,
        whiteSpace: 'nowrap',
    },

    fileChipRemove: {
        width: '24px',
        height: '24px',
        minWidth: '24px',
        borderRadius: '999px',
        border: 'none',
        background: 'transparent',
        color: 'var(--text)',
        cursor: 'pointer',
        opacity: 0.65,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 0,
        flexShrink: 0,
    },
}

export default PendingFilesBar