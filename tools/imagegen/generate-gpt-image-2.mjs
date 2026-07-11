import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { basename, dirname, extname, isAbsolute, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const toolDir = dirname(fileURLToPath(import.meta.url))
const projectRoot = resolve(toolDir, '..', '..')

function parseDotEnv(text) {
  const values = {}
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    const index = line.indexOf('=')
    if (index < 0) continue

    const key = line.slice(0, index).trim()
    let value = line.slice(index + 1).trim()
    if (!key) continue

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    values[key] = value
  }
  return values
}

async function loadEnv() {
  const candidates = [
    resolve(process.cwd(), '.env'),
    resolve(projectRoot, '.env'),
    resolve(projectRoot, 'AImental_backend', '.env'),
  ]

  for (const envPath of [...new Set(candidates)]) {
    try {
      const values = parseDotEnv(await readFile(envPath, 'utf8'))
      for (const [key, value] of Object.entries(values)) {
        if (process.env[key] == null || process.env[key] === '') {
          process.env[key] = value
        }
      }
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error
    }
  }
}

function readOption(args, name, fallback) {
  const prefix = `--${name}=`
  const inline = args.find((arg) => arg.startsWith(prefix))
  if (inline) return inline.slice(prefix.length)

  const index = args.indexOf(`--${name}`)
  if (index >= 0 && args[index + 1] && !args[index + 1].startsWith('--')) {
    return args[index + 1]
  }

  return fallback
}

function readOptions(args, name) {
  const values = []
  const prefix = `--${name}=`
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i]
    if (arg.startsWith(prefix)) {
      values.push(arg.slice(prefix.length))
      continue
    }
    if (arg === `--${name}` && args[i + 1] && !args[i + 1].startsWith('--')) {
      values.push(args[i + 1])
      i += 1
    }
  }
  return values
}

function hasFlag(args, name) {
  return args.includes(`--${name}`)
}

function positionalPrompt(args) {
  const values = []
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i]
    if (arg.startsWith('--')) {
      if (!arg.includes('=') && args[i + 1] && !args[i + 1].startsWith('--')) i += 1
      continue
    }
    values.push(arg)
  }
  return values.join(' ').trim()
}

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, '-')
}

function redactSecrets(text) {
  return text.replace(/sk-[A-Za-z0-9_-]+/g, 'sk-REDACTED')
}

function normalizeImagesApiRoot(value) {
  const trimmed = String(value || '').trim().replace(/\/+$/, '')
  return trimmed.replace(/\/v1$/i, '')
}

function imageGenerationUrl(baseUrl) {
  return /\/apiv2$/i.test(baseUrl)
    ? `${baseUrl}/images/generations`
    : `${baseUrl}/v1/images/generations`
}

function imageEditUrl(baseUrl) {
  return /\/apiv2$/i.test(baseUrl)
    ? `${baseUrl}/images/edits`
    : `${baseUrl}/v1/images/edits`
}

function printHelp() {
  console.log(`Usage:
  node tools/imagegen/generate-gpt-image-2.mjs --prompt "your image prompt"
  node tools/imagegen/generate-gpt-image-2.mjs "your image prompt"

Options:
  --prompt       Image prompt. Positional text also works.
  --out          Output path. Defaults to output/imagegen/<timestamp>.png.
  --raw-out      Save raw Images API JSON response for debugging.
  --size         Image size. Defaults to 1024x1024.
  --quality      low, medium, high, or auto. Defaults to low.
  --format       png, jpeg, or webp. Defaults to png.
  --model        Model id. Defaults to gpt-image-2.
  --base-url     API site root. Defaults to OPENAI_BASE_URL or https://api.openai.com.
  --image        Input/reference image path. Repeat for edits.
  --help         Show this help.
`)
}

await loadEnv()

const args = process.argv.slice(2)
if (hasFlag(args, 'help')) {
  printHelp()
  process.exit(0)
}

const requestedBaseUrl = readOption(args, 'base-url', process.env.OPENAI_BASE_URL || 'https://api.openai.com')
const baseUrl = normalizeImagesApiRoot(requestedBaseUrl)
const isHepai = /\/apiv2$/i.test(baseUrl)
const apiKey = (
  isHepai
    ? process.env.HEPAI_API_KEY || process.env.OPENAI_API_KEY
    : process.env.OPENAI_API_KEY
)?.trim()
if (!apiKey) {
  console.error(`Missing ${isHepai ? 'HEPAI_API_KEY or OPENAI_API_KEY' : 'OPENAI_API_KEY'}. Configure it in a local .env file first.`)
  process.exit(1)
}

const model = readOption(args, 'model', 'gpt-image-2')
const size = readOption(args, 'size', '1024x1024')
const quality = readOption(args, 'quality', 'low')
const outputFormat = readOption(args, 'format', 'png')
const imagePaths = readOptions(args, 'image').map((item) => isAbsolute(item) ? item : resolve(projectRoot, item))
const prompt = readOption(args, 'prompt', positionalPrompt(args)) ||
  'A cozy manga artist desk at night, clean workspace, sketch pages, warm desk lamp, detailed illustration style, no text, no watermark.'

const defaultOutPath = resolve(projectRoot, 'output', 'imagegen', `${timestamp()}.${outputFormat}`)
const outOption = readOption(args, 'out', defaultOutPath)
const outPath = isAbsolute(outOption) ? outOption : resolve(projectRoot, outOption)
const rawOutOption = readOption(args, 'raw-out', '')
const rawOutPath = rawOutOption ? (isAbsolute(rawOutOption) ? rawOutOption : resolve(projectRoot, rawOutOption)) : ''

const body = {
  model,
  prompt,
  n: 1,
  size,
  quality,
  output_format: outputFormat,
  moderation: 'auto',
}

let response
if (imagePaths.length) {
  const formData = new FormData()
  for (const [key, value] of Object.entries(body)) {
    if (value != null) formData.append(key, String(value))
  }

  for (const [index, imagePath] of imagePaths.entries()) {
    const bytes = await readFile(imagePath)
    const ext = extname(imagePath).toLowerCase()
    const type = ext === '.jpg' || ext === '.jpeg'
      ? 'image/jpeg'
      : ext === '.webp'
        ? 'image/webp'
        : 'image/png'
    formData.append(index === 0 ? 'image' : 'image[]', new Blob([bytes], { type }), basename(imagePath))
  }

  response = await fetch(imageEditUrl(baseUrl), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
    body: formData,
  })
} else {
  response = await fetch(imageGenerationUrl(baseUrl), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}

if (!response.ok) {
  const text = await response.text()
  throw new Error(redactSecrets(`Image ${imagePaths.length ? 'edit' : 'generation'} failed: HTTP ${response.status}\n${text}`))
}

const responseText = await response.text()
if (rawOutPath) {
  await mkdir(dirname(rawOutPath), { recursive: true })
  await writeFile(rawOutPath, responseText)
}

const payload = JSON.parse(responseText)
const item = payload?.data?.[0]
if (!item?.b64_json && !item?.url) {
  throw new Error(`No image found in API response:\n${JSON.stringify(payload, null, 2)}`)
}

await mkdir(dirname(outPath), { recursive: true })

if (item.b64_json) {
  await writeFile(outPath, Buffer.from(item.b64_json, 'base64'))
} else {
  const imageResponse = await fetch(item.url)
  if (!imageResponse.ok) {
    throw new Error(`Failed to download generated image: HTTP ${imageResponse.status}`)
  }
  await writeFile(outPath, Buffer.from(await imageResponse.arrayBuffer()))
}

console.log(JSON.stringify({
  ok: true,
  path: outPath,
  revisedPrompt: item.revised_prompt ?? null,
  actual: {
    model: payload.model ?? model,
    size: payload.size ?? size,
    quality: payload.quality ?? quality,
    output_format: payload.output_format ?? outputFormat,
  },
}, null, 2))
