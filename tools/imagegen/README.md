# GPT Image Toolkit

This toolkit calls the OpenAI-compatible Images API shape used by the fhl
Image-2 dedicated image generation group. For fhl, use Images API rather than
Responses API.

## Images API

The recommended command calls the OpenAI-compatible Images API endpoints:

```text
POST /v1/images/generations
POST /v1/images/edits
```

It uses `gpt-image-2` by default and reads `OPENAI_API_KEY` and
`OPENAI_BASE_URL` from the project root `.env` file.

Text-to-image:

```powershell
.\tools\imagegen\run-gpt-image-2.ps1 --prompt "A cozy manga artist desk at night, warm lamp, detailed illustration, no text" --out output\imagegen\example.png --raw-out output\imagegen\raw\example.json
```

With a local reference image:

```powershell
.\tools\imagegen\run-gpt-image-2.ps1 --image "C:\path\to\photo.jpg" --prompt "Create a new warm pixel-art manga scene from this photo, no text, no watermark." --out output\imagegen\edit.png --raw-out output\imagegen\raw\edit.json
```

Generated images are saved under:

```text
output/imagegen/
```

Raw JSON responses are saved under:

```text
output/imagegen/raw/
```

Useful options:

```powershell
.\tools\imagegen\run-gpt-image-2.ps1 --prompt "..." --size 1024x1024 --quality low --format png
```

Available options:

- `--prompt`: image prompt
- `--image`: input/reference image path; repeat for multiple images
- `--out`: custom output path
- `--raw-out`: custom raw response path
- `--base-url`: API site root, default from `OPENAI_BASE_URL`
- `--model`: image model, default `gpt-image-2`
- `--size`: image size, default `1024x1024`
- `--quality`: `low`, `medium`, `high`, or `auto`
- `--format`: `png`, `jpeg`, or `webp`

## Responses API

The repository still contains `run-responses.ps1` and
`generate-responses.mjs` only as disabled guard rails. They immediately fail.
Do not use Responses API for fhl image generation. fhl should be configured as
Images API; otherwise image base64 output may be billed as very large
Responses output tokens.

## Setup

Open the project root `.env` file and paste your key after the equals sign:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://www.fhl.mom
IMAGE_STUDIO_IMAGE_MODEL=gpt-image-2
```

Do not add spaces around the equals sign.

The CLI accepts a site root such as `https://www.fhl.mom` and appends
`/v1/images/generations` or `/v1/images/edits` internally.

## Run With Node Directly

```powershell
node .\tools\imagegen\generate-gpt-image-2.mjs --prompt "A cozy manga artist desk at night, warm lamp, detailed illustration, no text" --out output\imagegen\example.png --raw-out output\imagegen\raw\example.json
```

Edit or regenerate from local images:

```powershell
.\tools\imagegen\run-gpt-image-2.ps1 --image block.jpg --prompt "Regenerate this image as a cute pixel-art manga illustration, no text, no watermark."
```
