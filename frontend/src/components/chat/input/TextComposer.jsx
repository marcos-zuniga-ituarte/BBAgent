import { forwardRef } from 'react'
import { styles } from './chatInputStyles.js'

const TextComposer = forwardRef(function TextComposer(
    { value, onChange, onKeyDown, onPaste },
    ref,
) {
    return (
        <textarea
            ref={ref}
            className="chat-input-textarea"
            placeholder="Pregunta lo que quieras"
            style={styles.input}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
            rows={1}
        />
    )
})

export default TextComposer