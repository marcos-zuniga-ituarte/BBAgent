import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'
import ignore from 'ignore'

const root = fileURLToPath(new URL('../../', import.meta.url))
const read = name => fs.readFileSync(path.join(root, name), 'utf8').replace(/^\uFEFF/, '')
const rules = ['', 'backend', 'frontend'].map(prefix => ({
    prefix: prefix ? prefix + '/' : '',
    matcher: ignore().add(read(path.posix.join(prefix, '.gitignore'))),
}))
const ignored = name => rules.some(({ prefix, matcher }) => name.startsWith(prefix) && name.length > prefix.length && matcher.ignores(name.slice(prefix.length)))
const problems = []
const protectedPaths = [
    '.env', 'backend/.env', 'frontend/.env.local', 'backend/custom.env',
    'backend/.venv/pyvenv.cfg', 'frontend/node_modules/example/index.js',
    'backend/data/bd/local.db', 'backend/local.db-wal', 'backend/local.sqlite3-shm',
    'private.pem', 'service-account-demo.json', '.local-only/notes.txt',
    'docs/screenshots/raw/screenshot.png',
]
for (const name of protectedPaths) {
    if (!ignored(name)) problems.push(`${name}: missing ignore protection`)
}
for (const name of ['backend/.env.example', 'frontend/.env.example', 'docs/screenshots/chat-overview.png']) {
    if (ignored(name)) problems.push(`${name}: public example or approved screenshot is excluded`)
}

const candidates = []
function walk(directory = '') {
    for (const entry of fs.readdirSync(path.join(root, directory), { withFileTypes: true })) {
        const name = path.posix.join(directory, entry.name)
        if (name === '.git' || ignored(name + (entry.isDirectory() ? '/' : ''))) continue
        if (entry.isSymbolicLink()) {
            problems.push(`${name}: review symlink before publishing`)
        } else if (entry.isDirectory()) {
            walk(name)
        } else if (entry.isFile()) {
            candidates.push(name)
        }
    }
}
walk()

// Compare with local credentials without printing their values or uploading them.
const localSecrets = []
for (const name of ['backend/.env', 'frontend/.env.local']) {
    if (!fs.existsSync(path.join(root, name))) continue
    for (const line of read(name).split(/\r?\n/)) {
        const match = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/)
        if (!match || !/(?:API_KEY|SECRET|PASSWORD|ACCESS_TOKEN|PRIVATE_KEY)/.test(match[1])) continue
        const value = match[2].replace(/^(['"])(.*)\1$/, '$2')
        if (value.length >= 12 && !/^(replace-|test-|example|tu_clave)/i.test(value)) localSecrets.push(value)
    }
}

const patterns = [
    ['API key or access token', /\b(?:sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})/],
    ['private key', /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/],
    ['credential in a URL', /https?:\/\/[^\s/@:]+:[^\s/@]+@/],
]
function scan(name, buffer) {
    if (buffer.length > 10 * 1024 * 1024) problems.push(`${name}: file larger than 10 MB needs review`)
    for (const value of localSecrets) {
        if (buffer.includes(Buffer.from(value))) problems.push(`${name}: contains a credential from local configuration`)
    }
    if (buffer.includes(0)) return
    const text = buffer.toString('utf8')
    for (const [label, pattern] of patterns) {
        // These exact fake credentials are used to test URL rejection.
        const scanned = name.includes('/test') && label === 'credential in a URL'
            ? text.replace(/https:\/\/user:(?:secret|password)@example\.com/g, 'https://example.com')
            : text
        if (pattern.test(scanned)) problems.push(`${name}: possible ${label}`)
    }
}
for (const name of candidates) scan(name, fs.readFileSync(path.join(root, name)))

// Once Git exists, also inspect the index: .gitignore does not protect force-added files.
const git = spawnSync('git', ['rev-parse', '--show-toplevel'], { cwd: root, encoding: 'utf8', windowsHide: true })
if (git.status === 0 && path.resolve(git.stdout.trim()) === path.resolve(root)) {
    const result = spawnSync('git', ['ls-files', '--cached', '-z'], { cwd: root, encoding: 'utf8', windowsHide: true })
    if (result.status !== 0) problems.push('Cannot read Git index')
    for (const name of result.stdout.split('\0').filter(Boolean)) {
        if (ignored(name)) problems.push(`${name}: ignored file is already in the Git index`)
        const staged = spawnSync('git', ['show', `:${name}`], { cwd: root, maxBuffer: 20 * 1024 * 1024, windowsHide: true })
        if (staged.status !== 0) problems.push(`${name}: cannot inspect Git index contents`)
        else scan(name, staged.stdout)
    }
}

if (problems.length) {
    console.error([...new Set(problems)].join('\n'))
    process.exitCode = 1
} else {
    console.log(`OK: ${candidates.length} public files scanned; ignore protections verified; no matching secrets detected.`)
    console.log('Screenshots require visual review. This check does not guarantee that every possible secret is detected.')
}
