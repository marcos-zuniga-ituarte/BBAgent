import { useEffect, useState } from 'react'

const EMPTY_STEPS = []

function ChatStreamSteps({
                             streamSteps,
                             pendingTool,
                             sendingDecision,
                             onConfirmTool,
                             onRejectTool,
                         }) {
    const [isExpanded, setIsExpanded] = useState(false)
    const [renderedSteps, setRenderedSteps] = useState(
        Array.isArray(streamSteps) ? streamSteps : []
    )
    const safeSteps = Array.isArray(streamSteps) ? streamSteps : EMPTY_STEPS
    const [previousSteps, setPreviousSteps] = useState(safeSteps)
    if (previousSteps !== safeSteps) {
        setPreviousSteps(safeSteps)
        if (safeSteps.length > 0) setRenderedSteps(safeSteps)
    }
    const hasConfirmation = !!pendingTool
    const hasSteps = renderedSteps.length > 0
    const shouldStayVisible = safeSteps.length > 0 || hasConfirmation

    const isClosing = !shouldStayVisible && hasSteps

    useEffect(() => {
        if (!isClosing) return
        const timeout = setTimeout(() => {
            setRenderedSteps([])
            setIsExpanded(false)
        }, 280)
        return () => clearTimeout(timeout)
    }, [isClosing])

    const visibleSteps = renderedSteps

    function formatArguments(argumentsObj) {
        if (!argumentsObj || typeof argumentsObj !== 'object') {
            return ''
        }

        try {
            return JSON.stringify(argumentsObj, null, 2)
        } catch {
            return ''
        }
    }

    function getStepDisplay(step) {
        return {
            type:
                typeof step?.type === 'string' && step.type.length > 0
                    ? step.type
                    : '',
            text:
                typeof step?.text === 'string' && step.text.length > 0
                    ? step.text
                    : '',
            toolName:
                typeof step?.toolName === 'string' && step.toolName.length > 0
                    ? step.toolName
                    : '',
            arguments:
                step?.arguments && typeof step.arguments === 'object'
                    ? step.arguments
                    : null,
        }
    }

    function getHeaderStepDisplay() {
        if (pendingTool?.text) {
            return {
                type: '',
                text: pendingTool.text,
                toolName:
                    typeof pendingTool?.toolName === 'string' &&
                    pendingTool.toolName.length > 0
                        ? pendingTool.toolName
                        : '',
            }
        }

        if (renderedSteps.length > 0) {
            return getStepDisplay(renderedSteps[renderedSteps.length - 1])
        }

        return {
            type: '',
            text: 'Esperando confirmación...',
            toolName: '',
        }
    }

    const headerStep = getHeaderStepDisplay()

    if (!shouldStayVisible && renderedSteps.length === 0) {
        return null
    }

    return (
        <div
            style={{
                ...styles.wrapper,
                ...(isClosing ? styles.wrapperClosing : styles.wrapperOpen),
            }}
        >
            <div style={styles.header}>
                <div style={styles.headerLeft}>
                    {hasConfirmation ? (
                        <span style={styles.pendingDot}>●</span>
                    ) : (
                        <span className="stream-spinner" />
                    )}

                    <div style={styles.headerTextBlock}>
                        {headerStep.type ? (
                            <span style={styles.headerTextLine}>
                                {headerStep.type}
                            </span>
                        ) : null}


                        {headerStep.text ? (
                            <span style={styles.headerTextLine}>
                                {headerStep.text}
                            </span>
                        ) : null}

                        {headerStep.toolName ? (
                            <span style={styles.headerTextLine}>
                                {headerStep.toolName}
                            </span>
                        ) : null}
                    </div>
                </div>

                {hasSteps ? (
                    <button
                        type="button"
                        onClick={() => setIsExpanded((prev) => !prev)}
                        style={styles.historyToggleButton}
                    >
                        <span style={styles.chevron}>
                            {isExpanded ? '▾' : '▸'}
                        </span>
                        {isExpanded ? 'Ocultar pasos' : 'Ver pasos'}
                    </button>
                ) : null}
            </div>

            {pendingTool ? (
                <div style={styles.confirmationSection}>
                    <p style={styles.confirmationText}>
                        {pendingTool.text || '¿Deseas ejecutar esta tool?'}
                    </p>

                    <div style={styles.toolMeta}>
                        <div style={styles.toolNameRow}>
                            <span style={styles.toolLabel}>Tool</span>
                            <span style={styles.toolValue}>
                                {pendingTool.toolName || '(sin nombre)'}
                            </span>
                        </div>

                        <pre style={styles.commandBox}>
                            {formatArguments(pendingTool.arguments) || '{}'}
                        </pre>
                    </div>

                    <div style={styles.actions}>
                        <button
                            type="button"
                            onClick={onRejectTool}
                            disabled={sendingDecision}
                            style={{
                                ...styles.cancelButton,
                                ...(sendingDecision ? styles.buttonDisabled : null),
                            }}
                        >
                            Cancelar
                        </button>

                        <button
                            type="button"
                            onClick={onConfirmTool}
                            disabled={sendingDecision}
                            style={{
                                ...styles.confirmButton,
                                ...(sendingDecision ? styles.buttonDisabled : null),
                            }}
                        >
                            {sendingDecision ? 'Enviando...' : 'Ejecutar'}
                        </button>
                    </div>

                    <p style={styles.shortcutsHint}>
                        Ctrl/Cmd + Enter = aceptar · Ctrl/Cmd + Backspace = rechazar
                    </p>
                </div>
            ) : null}

            {hasSteps ? (
                <div
                    style={{
                        ...styles.stepsListWrap,
                        ...(isExpanded
                            ? styles.stepsListWrapOpen
                            : styles.stepsListWrapClosed),
                    }}
                >
                    <div style={styles.stepsList}>
                        {visibleSteps.map((step, index) => {
                            const isReallyLast =
                                index === visibleSteps.length - 1 && !hasConfirmation
                            const stepDisplay = getStepDisplay(step)
                            const hasArguments =
                                stepDisplay.arguments &&
                                Object.keys(stepDisplay.arguments).length > 0

                            return (
                                <div
                                    key={`${step?.type || 'step'}-${step?.toolName || ''}-${index}`}
                                    style={{
                                        ...styles.stepRow,
                                        ...(isClosing
                                            ? styles.stepRowClosing
                                            : styles.stepRowOpen),
                                    }}
                                >
                                    {isReallyLast ? (
                                        <span className="stream-spinner" />
                                    ) : (
                                        <span style={styles.check}>✓</span>
                                    )}

                                    <div style={styles.stepContent}>
                                        {stepDisplay.type ? (
                                            <span style={styles.stepTextLine}>
                                                {stepDisplay.type}
                                            </span>
                                        ) : null}

                                        {stepDisplay.text ? (
                                            <span style={styles.stepTextLine}>
                                                {stepDisplay.text}
                                            </span>
                                        ) : null}

                                        {stepDisplay.toolName ? (
                                            <span style={styles.stepTextLine}>
                                                {stepDisplay.toolName}
                                            </span>
                                        ) : null}

                                        {hasArguments ? (
                                            <pre style={styles.stepArgumentsBox}>
                                                {formatArguments(stepDisplay.arguments)}
                                            </pre>
                                        ) : null}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            ) : null}
        </div>
    )
}

const styles = {
    wrapper: {
        alignSelf: 'flex-start',
        maxWidth: '75%',
        //background: 'var(--bubble-assistant)',
        //border: '1px solid var(--border)',
        //borderRadius: '14px',
        color: 'var(--text)',
        overflow: 'hidden',
        transformOrigin: 'top left',
        willChange: 'opacity, transform, max-height, margin',
        transition:
            'opacity 280ms ease, transform 280ms ease, max-height 280ms ease, margin-top 280ms ease',
    },

    wrapperOpen: {
        opacity: 1,
        transform: 'translateY(0)',
        marginTop: '8px',
    },

    wrapperClosing: {
        opacity: 0,
        transform: 'translateY(-6px)',
        maxHeight: '0px',
        marginTop: '0px',
    },

    header: {
        padding: '10px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
    },

    headerLeft: {
        display: 'flex',
        alignItems: 'flex-start',
        gap: '8px',
        minWidth: 0,
        flex: 1,
    },

    headerTextBlock: {
        display: 'flex',
        flexDirection: 'column',
        gap: '0px',
        minWidth: 0,
        flex: 1,
    },

    headerTextLine: {
        fontSize: '13px',
        color: 'var(--text)',
        opacity: 0.72,
        lineHeight: 1.35,
        wordBreak: 'break-word',
        whiteSpace: 'normal',
    },

    historyToggleButton: {
        border: '1px solid var(--border)',
        background: 'transparent',
        color: 'var(--text)',
        opacity: 0.9,
        borderRadius: '999px',
        padding: '6px 10px',
        cursor: 'pointer',
        fontSize: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        flexShrink: 0,
    },

    chevron: {
        fontSize: '11px',
        lineHeight: 1,
    },

    pendingDot: {
        fontSize: '10px',
        lineHeight: 1,
        flexShrink: 0,
        marginTop: '4px',
    },

    confirmationSection: {
        padding: '0 12px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
    },

    confirmationText: {
        margin: 0,
        fontSize: '13px',
        lineHeight: 1.5,
        color: 'var(--text)',
        opacity: 0.72,
    },

    toolMeta: {
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
    },

    toolNameRow: {
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexWrap: 'wrap',
    },

    toolLabel: {
        fontSize: '12px',
        opacity: 0.75,
    },

    toolValue: {
        fontSize: '13px',
        fontWeight: 600,
    },

    commandBox: {
        margin: 0,
        padding: '12px',
        borderRadius: '12px',
        background: 'var(--code-bg)',
        color: 'var(--code-text)',
        border: '1px solid var(--code-border)',
        overflowX: 'auto',
        fontSize: '13px',
        lineHeight: 1.5,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily:
            'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
    },

    actions: {
        display: 'flex',
        justifyContent: 'flex-end',
        gap: '12px',
        flexWrap: 'wrap',
    },

    cancelButton: {
        border: '1px solid var(--border)',
        background: 'var(--button-bg)',
        color: 'var(--button-text)',
        borderRadius: '10px',
        padding: '10px 14px',
        cursor: 'pointer',
    },

    confirmButton: {
        border: '1px solid var(--border)',
        background: 'var(--bubble-user)',
        color: 'var(--text-user-message)',
        borderRadius: '10px',
        padding: '10px 14px',
        cursor: 'pointer',
    },

    buttonDisabled: {
        opacity: 0.7,
        cursor: 'not-allowed',
    },

    shortcutsHint: {
        margin: 0,
        fontSize: '12px',
        color: 'var(--text)',
        opacity: 0.6,
    },

    stepsListWrap: {
        overflow: 'hidden',
        transition: 'max-height 220ms ease, opacity 220ms ease',
        borderTop: '1px solid var(--border)',
    },

    stepsListWrapOpen: {
        maxHeight: '320px',
        opacity: 1,
    },

    stepsListWrapClosed: {
        maxHeight: '0px',
        opacity: 0,
        borderTop: 'none',
    },

    stepsList: {
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
    },

    stepRow: {
        display: 'flex',
        alignItems: 'flex-start',
        gap: '8px',
        fontSize: '13px',
        transition: 'opacity 180ms ease, transform 180ms ease',
    },

    stepRowOpen: {
        opacity: 1,
        transform: 'translateY(0)',
    },

    stepRowClosing: {
        opacity: 0,
        transform: 'translateY(-4px)',
    },

    stepContent: {
        display: 'flex',
        flexDirection: 'column',
        gap: '0px',
        minWidth: 0,
        flex: 1,
    },

    stepTextLine: {
        fontSize: '13px',
        color: 'var(--text)',
        opacity: 0.72,
        lineHeight: 1.35,
        wordBreak: 'break-word',
        whiteSpace: 'normal',
    },

    stepArgumentsBox: {
        margin: '6px 0 0 0',
        padding: '10px',
        borderRadius: '10px',
        background: 'var(--code-bg)',
        color: 'var(--code-text)',
        border: '1px solid var(--code-border)',
        overflowX: 'auto',
        fontSize: '12px',
        lineHeight: 1.45,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily:
            'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
    },

    check: {
        fontSize: '12px',
        marginTop: '2px',
    },
}

export default ChatStreamSteps