const state = {
  colors: [],
  selectedIds: [],
  latestResult: null,
  backgroundImage: null,
}

const $ = (selector) => document.querySelector(selector)
const colorGroupsEl = $("#colorGroups")
const selectedRailEl = $("#selectedRail")
const selectedCountEl = $("#selectedCount")
const mixedHexEl = $("#mixedHex")
const generateBtn = $("#generateBtn")
const randomBtn = $("#randomBtn")
const clearBtn = $("#clearBtn")
const imageToggle = $("#imageToggle")
const resultNameEl = $("#resultName")
const resultSubtitleEl = $("#resultSubtitle")
const tagRowEl = $("#tagRow")
const loadingBadge = $("#loadingBadge")
const canvas = $("#resultCanvas")
const ctx = canvas.getContext("2d")
const saveBtn = $("#saveBtn")
const copyBtn = $("#copyBtn")
const regenBtn = $("#regenBtn")
const noticeEl = $("#notice")

function setNotice(message, tone = "") {
  noticeEl.textContent = message || ""
  noticeEl.classList.toggle("error", tone === "error")
  noticeEl.classList.toggle("success", tone === "success")
}

function normalizeHex(hex) {
  return hex.toUpperCase()
}

function hexToRgb(hex) {
  const clean = hex.replace("#", "")
  return [
    parseInt(clean.slice(0, 2), 16),
    parseInt(clean.slice(2, 4), 16),
    parseInt(clean.slice(4, 6), 16),
  ]
}

function rgbToHex(rgb) {
  return `#${rgb.map((value) => Math.round(value).toString(16).padStart(2, "0")).join("")}`.toUpperCase()
}

function mixSelectedColors() {
  const selected = getSelectedColors()
  if (!selected.length) return null
  const rgb = [0, 0, 0]
  selected.forEach((color) => {
    const channels = hexToRgb(color.hex)
    rgb[0] += channels[0]
    rgb[1] += channels[1]
    rgb[2] += channels[2]
  })
  return rgbToHex(rgb.map((channel) => channel / selected.length))
}

function getSelectedColors() {
  const byId = new Map(state.colors.map((color) => [color.id, color]))
  return state.selectedIds.map((id) => byId.get(id)).filter(Boolean)
}

function groupColors(colors) {
  return colors.reduce((groups, color) => {
    if (!groups.has(color.group)) groups.set(color.group, [])
    groups.get(color.group).push(color)
    return groups
  }, new Map())
}

function renderColorGroups() {
  const groups = groupColors(state.colors)
  colorGroupsEl.innerHTML = ""

  for (const [group, colors] of groups) {
    const section = document.createElement("section")
    section.className = "color-group"

    const title = document.createElement("h3")
    title.className = "group-title"
    title.innerHTML = `<span>${group}</span><span>${colors.length}</span>`
    section.append(title)

    const grid = document.createElement("div")
    grid.className = "swatch-grid"
    for (const color of colors) {
      const button = document.createElement("button")
      button.type = "button"
      button.className = "swatch-button"
      button.style.setProperty("--swatch", color.hex)
      button.dataset.id = String(color.id)
      button.title = `${color.name} ${color.hex}`
      button.innerHTML = `<span>${color.name}</span>`
      button.addEventListener("click", () => toggleColor(color.id))
      grid.append(button)
    }
    section.append(grid)
    colorGroupsEl.append(section)
  }
  syncSelectionUI()
}

function syncSelectionUI() {
  const selected = getSelectedColors()
  const mixed = mixSelectedColors()
  selectedCountEl.textContent = `${selected.length} / 30`
  mixedHexEl.textContent = mixed || "#------"
  generateBtn.disabled = selected.length < 7 || selected.length > 30

  document.querySelectorAll(".swatch-button").forEach((button) => {
    const id = Number(button.dataset.id)
    const isSelected = state.selectedIds.includes(id)
    button.classList.toggle("selected", isSelected)
    button.classList.toggle("limit", state.selectedIds.length >= 30 && !isSelected)
  })

  if (!selected.length) {
    selectedRailEl.className = "selected-empty"
    selectedRailEl.textContent = "先选 7 个颜色"
    return
  }

  selectedRailEl.className = "selected-swatches"
  selectedRailEl.innerHTML = ""
  selected.forEach((color) => {
    const swatch = document.createElement("button")
    swatch.type = "button"
    swatch.className = "selected-swatch"
    swatch.style.setProperty("--swatch", color.hex)
    swatch.title = `移除 ${color.name}`
    swatch.addEventListener("click", () => toggleColor(color.id))
    selectedRailEl.append(swatch)
  })
}

function toggleColor(id) {
  if (state.selectedIds.includes(id)) {
    state.selectedIds = state.selectedIds.filter((item) => item !== id)
  } else if (state.selectedIds.length < 30) {
    state.selectedIds = [...state.selectedIds, id]
  }
  syncSelectionUI()
}

function randomPick() {
  const ids = state.colors.map((color) => color.id)
  const shuffled = ids.sort(() => Math.random() - 0.5)
  const count = 9 + Math.floor(Math.random() * 7)
  state.selectedIds = shuffled.slice(0, count)
  syncSelectionUI()
}

function clearSelection() {
  state.selectedIds = []
  syncSelectionUI()
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = "anonymous"
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = url
  })
}

function drawContainImage(image, fillHex) {
  drawFallbackBackground(fillHex)
  const scale = Math.min(canvas.width / image.width, canvas.height / image.height)
  const width = image.width * scale
  const height = image.height * scale
  const x = (canvas.width - width) / 2
  const y = (canvas.height - height) / 2
  ctx.drawImage(image, x, y, width, height)
}

function drawFallbackBackground(hex) {
  const [r, g, b] = hexToRgb(hex)
  const light = `rgb(${Math.min(255, r + 54)}, ${Math.min(255, g + 54)}, ${Math.min(255, b + 54)})`
  const dark = `rgb(${Math.max(0, r - 42)}, ${Math.max(0, g - 42)}, ${Math.max(0, b - 42)})`
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height)
  gradient.addColorStop(0, light)
  gradient.addColorStop(0.5, hex)
  gradient.addColorStop(1, dark)
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  for (let index = 0; index < 18; index += 1) {
    const radius = 120 + index * 18
    const x = (index * 227) % canvas.width
    const y = (index * 331) % canvas.height
    const radial = ctx.createRadialGradient(x, y, 0, x, y, radius)
    radial.addColorStop(0, `rgba(255,255,255,${0.18 - index * 0.004})`)
    radial.addColorStop(1, "rgba(255,255,255,0)")
    ctx.fillStyle = radial
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, Math.PI * 2)
    ctx.fill()
  }
}

async function renderCanvas(result) {
  const mixedHex = normalizeHex(result.mixed_color.hex)
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  let image = state.backgroundImage
  if (result.image_result?.background_image_url && !image) {
    try {
      image = await loadImage(result.image_result.background_image_url)
      state.backgroundImage = image
    } catch {
      image = null
    }
  }

  if (image) {
    drawContainImage(image, mixedHex)
  } else {
    drawFallbackBackground(mixedHex)
  }

  const overlay = ctx.createLinearGradient(0, 0, 0, canvas.height)
  overlay.addColorStop(0, "rgba(255,255,255,0.08)")
  overlay.addColorStop(0.5, "rgba(20,24,24,0.10)")
  overlay.addColorStop(1, "rgba(20,24,24,0.20)")
  ctx.fillStyle = overlay
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  ctx.save()
  ctx.shadowColor = "rgba(0,0,0,0.22)"
  ctx.shadowBlur = 18
  ctx.fillStyle = "rgba(255,255,255,0.9)"
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  ctx.font = "112px 'Noto Serif SC', 'Microsoft YaHei', serif"
  ctx.fillText(result.naming_result.color_name, canvas.width / 2, canvas.height / 2)
  ctx.restore()
}

function updateResultText(result) {
  resultNameEl.textContent = result.naming_result.color_name
  resultSubtitleEl.textContent = result.naming_result.subtitle
  tagRowEl.innerHTML = ""
  result.naming_result.tags.forEach((tag) => {
    const tagEl = document.createElement("span")
    tagEl.className = "tag"
    tagEl.textContent = tag
    tagRowEl.append(tagEl)
  })
  mixedHexEl.textContent = result.mixed_color.hex
}

async function generateCard() {
  const selected = getSelectedColors()
  if (selected.length < 7) return

  loadingBadge.hidden = false
  generateBtn.disabled = true
  saveBtn.disabled = true
  copyBtn.disabled = true
  regenBtn.disabled = true
  setNotice(imageToggle.checked ? "正在调和颜色、命名并生成背景。" : "正在调和颜色并命名。")
  state.backgroundImage = null

  try {
    const response = await fetch("/api/generate-card-data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        color_ids: state.selectedIds,
        generate_image: imageToggle.checked,
      }),
    })
    if (!response.ok) throw new Error(await response.text())
    const result = await response.json()
    state.latestResult = result
    updateResultText(result)
    await renderCanvas(result)
    saveBtn.disabled = false
    copyBtn.disabled = false
    regenBtn.disabled = false

    const imageSource = result.image_result.source
    const namingSource = result.naming_result.source
    const imageSucceeded = imageSource === "hepai-images"
    if (imageToggle.checked && !imageSucceeded) {
      const error = result.image_result.error ? `：${result.image_result.error}` : ""
      setNotice(`AI 背景生成失败${error} 当前显示 Canvas 渐变兜底。`, "error")
    } else if (namingSource !== "hepai") {
      setNotice("命名使用了本地兜底，结果卡已生成。", "error")
    } else if (!imageToggle.checked) {
      setNotice("生成完成。当前未开启 AI 背景，使用 Canvas 渐变兜底。")
    } else {
      setNotice("AI 背景已通过 HEPAI Images API 生成，可以保存图片。", "success")
    }
  } catch (error) {
    setNotice(`生成失败：${error.message}`)
  } finally {
    loadingBadge.hidden = true
    syncSelectionUI()
  }
}

async function regenerateBackground() {
  if (!state.latestResult) return
  loadingBadge.hidden = false
  regenBtn.disabled = true
  setNotice("正在重新生成背景。")
  state.backgroundImage = null

  const { mixed_color: mixed, naming_result: naming } = state.latestResult
  try {
    const response = await fetch("/api/regenerate-background", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mixed_hex: mixed.hex,
        color_name: naming.color_name,
        subtitle: naming.subtitle,
        tags: naming.tags,
        scene_hint: naming.scene_hint,
      }),
    })
    if (!response.ok) throw new Error(await response.text())
    state.latestResult.image_result = await response.json()
    await renderCanvas(state.latestResult)
    const imageSucceeded = state.latestResult.image_result.source === "hepai-images"
    if (imageSucceeded) {
      setNotice("背景已通过 HEPAI Images API 更新。", "success")
    } else {
      const error = state.latestResult.image_result.error ? `：${state.latestResult.image_result.error}` : ""
      setNotice(`背景生成失败${error} 继续使用渐变兜底。`, "error")
    }
  } catch (error) {
    setNotice(`重生背景失败：${error.message}`)
  } finally {
    loadingBadge.hidden = true
    regenBtn.disabled = false
  }
}

function saveCanvas() {
  const link = document.createElement("a")
  link.download = `emotion-color-card-${Date.now()}.png`
  link.href = canvas.toDataURL("image/png")
  link.click()
}

async function copyMixedHex() {
  if (!state.latestResult) return
  await navigator.clipboard.writeText(state.latestResult.mixed_color.hex)
  setNotice(`已复制 ${state.latestResult.mixed_color.hex}`)
}

async function bootstrap() {
  const response = await fetch("/api/colors")
  const payload = await response.json()
  state.colors = payload.colors
  renderColorGroups()
  drawFallbackBackground("#D8BFA8")
  setNotice("默认关闭 AI 背景，打开后会调用 HEPAI Images API 生成无字背景图。")
}

randomBtn.addEventListener("click", randomPick)
clearBtn.addEventListener("click", clearSelection)
generateBtn.addEventListener("click", generateCard)
saveBtn.addEventListener("click", saveCanvas)
copyBtn.addEventListener("click", copyMixedHex)
regenBtn.addEventListener("click", regenerateBackground)

bootstrap().catch((error) => {
  setNotice(`初始化失败：${error.message}`)
})
