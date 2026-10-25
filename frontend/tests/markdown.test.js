import test from 'node:test'
import assert from 'node:assert/strict'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ReactMarkdown from 'react-markdown'
import { markdownRehypePlugins } from '../src/utils/markdownPlugins.js'

test('removes unsafe HTML while keeping Markdown and safe HTML', () => {
    const content = '**Texto** <em>HTML permitido</em> <script>alert(1)</script><img src="x" onerror="alert(1)"><a href="javascript:alert(1)">enlace</a><iframe src="https://example.com"></iframe>'
    const html = renderToStaticMarkup(createElement(ReactMarkdown, { rehypePlugins: markdownRehypePlugins }, content))
    assert.match(html, /<strong>Texto<\/strong>/)
    assert.match(html, /<em>HTML permitido<\/em>/)
    assert.doesNotMatch(html, /<script|<iframe|onerror|javascript:|alert\(1\)/)
})
