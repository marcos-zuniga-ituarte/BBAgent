export default function BrandIcon({ size = 24, style, label }) {
    return (
        <img
            src="/brand-mark.svg"
            alt={label || ''}
            width={size}
            height={size}
            style={{ display: 'block', flexShrink: 0, ...style }}
        />
    )
}
