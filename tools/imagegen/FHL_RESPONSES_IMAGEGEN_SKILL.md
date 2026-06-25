---
name: fhl-images-imagegen
description: Generate and edit images for the manga project through the fhl.mom OpenAI-compatible Images API. Use when Codex is working in C:\Users\29537\OneDrive\Desktop\漫画 and the user asks to generate images from prompts or reference photos with the project-local Image-2 workflow.
---

# FHL Images API Imagegen

Use this workflow for the manga project. The correct fhl backend setup is the
Image-2 dedicated image generation group with upstream API shape set to
`Images API`, not `Responses API`.

```toml
[model_providers.fhl]
name = "fhl"
base_url = "https://www.fhl.mom"
wire_api = "images"
requires_openai_auth = true
```

Important:

- Use `POST /v1/images/generations` for text-to-image.
- Use `POST /v1/images/edits` for image-to-image or reference-photo edits.
- Do not use `POST /v1/responses` for image generation on fhl. The Responses
  shape can cause base64 image output to be billed as huge output-token usage.
- Use `gpt-image-2` as the image model.
- Keep API keys in `.env`; never print or repeat the full key in chat or logs.

## Project Paths

Default project root:

```text
C:\Users\29537\OneDrive\Desktop\漫画
```

Main CLI files:

```text
tools/imagegen/generate-gpt-image-2.mjs
tools/imagegen/run-gpt-image-2.ps1
tools/imagegen/README.md
```

Outputs:

```text
output/imagegen/
output/imagegen/raw/
```

## Required Env

The project root `.env` should contain:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://www.fhl.mom
IMAGE_STUDIO_IMAGE_MODEL=gpt-image-2
```

If the Image Studio frontend is used, mirror the public Vite values in
`tools/image-studio/image-studio/frontend/.env.local`:

```env
VITE_IMAGE_STUDIO_BASE_URL=https://www.fhl.mom
VITE_IMAGE_STUDIO_IMAGE_MODEL=gpt-image-2
```

The CLI accepts a site root such as `https://www.fhl.mom` and appends
`/v1/images/generations` or `/v1/images/edits` internally.

## Generate Images

From the project root, use the Images API script:

```powershell
npm run imagegen:images -- --prompt "A warm pixel-art manga couple scene, no text, no watermark" --out output/imagegen/example.png --raw-out output/imagegen/raw/example.json
```

With a reference image:

```powershell
.\tools\imagegen\run-gpt-image-2.ps1 --image "C:\path\to\photo.jpg" --prompt "Transform this photo into a cute pixel-art manga illustration, no text, no watermark" --out output\imagegen\edit.png --raw-out output\imagegen\raw\edit.json
```

Useful options:

```text
--prompt
--image       input/reference image path; repeat for multiple images
--out
--raw-out
--base-url    default from OPENAI_BASE_URL
--model       default gpt-image-2
--size        default 1024x1024
--quality     low, medium, high, or auto
--format      png, jpeg, or webp
```

## Deploy Or Repair

Use this sequence when another agent needs to set up or repair the manga
project image generation workflow.

1. Enter the project root:

```powershell
Set-Location 'C:\Users\29537\OneDrive\Desktop\漫画'
```

2. Ensure Node.js 18+ and npm are available:

```powershell
node --version
npm --version
```

3. Install root dependencies:

```powershell
npm install
```

4. If `tools/image-studio` is missing, clone Image Studio for reference and
frontend use:

```powershell
git clone --depth 1 https://github.com/RoseKhlifa/Image-Studio.git tools\image-studio
```

5. Ensure `package.json` has this script:

```json
{
  "scripts": {
    "imagegen:images": "node tools/imagegen/generate-gpt-image-2.mjs"
  }
}
```

6. Ensure `.env` contains the fhl settings from the Required Env section.

7. Validate locally without spending credits:

```powershell
node --check tools/imagegen/generate-gpt-image-2.mjs
npm run imagegen:images -- --help
```

8. Run one real fhl smoke generation only after the user confirms:

```powershell
npm run imagegen:images -- --prompt "A tiny cozy pixel-art cup of tea on a wooden desk, warm light, no text, no watermark" --size 1024x1024 --quality low --format png --out output/imagegen/fhl-images-smoke.png --raw-out output/imagegen/raw/fhl-images-smoke.json
```

9. Inspect the generated image before reporting success.

## Known Good Result

The fhl provider was verified with the Images API edit endpoint:

```text
endpoint: https://www.fhl.mom/v1/images/edits
model: gpt-image-2
requested size: 1536x1024
requested quality: low
actual returned size: 1672x940
actual returned quality: high
output format: png
```

Known-good output from the first successful Images API edit:

```text
output/imagegen/footspa-couple-images-api.png
output/imagegen/raw/footspa-couple-images-api.json
```

## Troubleshooting

- If backend billing shows `/v1/responses`, the wrong script/API shape was used.
  Stop and use `npm run imagegen:images`.
- If fhl returns 404 or route errors, check the fhl backend upstream is set to
  `Images API` and the API group is the Image-2 dedicated group.
- If fhl returns 401 or 403, the key is missing, invalid, expired, or the
  account/group has insufficient balance.
- If no image is found, inspect the raw JSON in `output/imagegen/raw/`.
- fhl may override requested `size` or `quality`; always read the final CLI
  `actual` block and report what the upstream actually returned.
