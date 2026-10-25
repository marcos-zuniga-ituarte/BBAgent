import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveApiBaseUrl } from '../src/config.js'

test('uses the local API by default and normalizes trailing slashes', () => {
    assert.equal(resolveApiBaseUrl(undefined), 'http://localhost:8000')
    assert.equal(resolveApiBaseUrl(' https://api.example.com/v1/ '), 'https://api.example.com/v1')
})

test('rejects credentials, unsafe protocols and non-base URLs without exposing the value', () => {
    for (const value of ['invalid', 'javascript:alert(1)', 'https://user:secret@example.com', 'https://example.com?key=secret', 'https://example.com#fragment']) {
        assert.throws(() => resolveApiBaseUrl(value), error => !error.message.includes('secret'))
    }
})
