import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'

// Parse HTML first, then strip unsafe tags, attributes and URL protocols.
export const markdownRehypePlugins = [rehypeRaw, rehypeSanitize]
