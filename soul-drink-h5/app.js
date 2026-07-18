const runtimeParams = new URLSearchParams(window.location.search);
const API_BASE = runtimeParams.get("apiBase") || window.SOUL_DRINK_API_BASE || "/api/v1/promotion/soul-drink";
const ASSET_BASE = window.SOUL_DRINK_ASSET_BASE || "https://assets.feelyourself.cn/miniprogram/assets/v1/pkgAssessment/images/drink-ti/";
const STORAGE_KEY = "feel_yourself_soul_drink_state_v1";
const AUDIO_PREF_KEY = "feel_yourself_soul_drink_audio_v1";
const QR_CODE_SRC = "feel-yourself-qr.png";
const AUTO_NEXT_DELAY_MS = 260;
const AUDIO_CDN_BASE = "https://assets.feelyourself.cn/miniprogram/assets/v1/pkgAssessment/images/drink-ti/audio/";
const AUDIO_ASSETS = {
  tap: `${AUDIO_CDN_BASE}candidates/glass_005.ogg`,
  option: `${AUDIO_CDN_BASE}candidates/glass_005.ogg`,
  bgm: {
    mp3: `${AUDIO_CDN_BASE}first-light-particles-bgm.mp3`,
  },
  iconOn: `${AUDIO_CDN_BASE}audio-on-wood-note.png`,
  iconMuted: `${AUDIO_CDN_BASE}audio-muted-wood-note.png`,
};
const AUDIO_VOLUME = {
  tap: 0.3,
  option: 0.3,
  bgm: 0.08,
};
const POSTER_TAGLINE = "欢迎来到FeelYourself，试着感受和理解你自己吧！";

function assetUrl(path) {
  if (!ASSET_BASE || /^(https?:|data:|blob:)/.test(path)) return path;
  return new URL(path.replace(/^\.\//, ""), ASSET_BASE.endsWith("/") ? ASSET_BASE : `${ASSET_BASE}/`).href;
}

const questions = [
  {
    id: 1,
    tag: "可能性联想",
    text: "你给朋友挑礼物时，更容易选？",
    options: [
      { key: "A", text: "一看到就会觉得“这也太像 TA 了”的东西。", score: { N: 2 } },
      { key: "B", text: "有点特别，背后还能讲出点意义或故事的东西。", score: { N: 1 } },
      { key: "C", text: "平时能经常用到，而且用起来顺手的东西。", score: { S: 1 } },
      { key: "D", text: "先想 TA 最近缺什么，直接挑最实用的东西。", score: { S: 2 } },
    ],
  },
  {
    id: 2,
    tag: "可能性联想",
    text: "遇到一个新领域，你刚开始更容易先做什么？",
    options: [
      { key: "A", text: "先弄懂它大概的框架和核心思路，再顺着感兴趣的方向边做边学。", score: { N: 1 } },
      { key: "B", text: "先找一个基础教程或具体例子跟着做一遍，做着做着再慢慢弄懂。", score: { S: 1 } },
    ],
  },
  {
    id: 3,
    tag: "可能性联想",
    text: "看完一部电影后，别人问你“这电影怎么样”，你更容易先说？",
    options: [
      { key: "A", text: "它大概想表达什么、让我想到了什么，以及整体给人的感觉。", score: { N: 1 } },
      { key: "B", text: "哪些情节、画面、台词或角色行为让我印象很深。", score: { S: 1 } },
    ],
  },
  {
    id: 4,
    tag: "可能性联想",
    text: "当一匹马走进酒吧，它会对调酒师说什么？",
    options: [
      { key: "A", text: "马不会说话，所以这个问题本身不成立。", score: { S: 1 } },
      { key: "B", text: "给我来杯伏特加。", score: { N: 1 } },
    ],
  },
  {
    id: 5,
    tag: "可能性联想",
    text: "和朋友出门前一天，你躺在床上会想什么？",
    options: [
      { key: "A", text: "好期待明天，想象明天会发生什么。", score: { N: 1 } },
      { key: "B", text: "到点了，该睡了。", score: { S: 1 } },
    ],
  },
  {
    id: 6,
    tag: "情绪关系",
    text: "好朋友跟你说“我最近真的好累”，你更自然的反应是？",
    options: [
      { key: "A", text: "先引导 TA 把感受说出来，接住 TA 的情绪。", score: { F: 1 } },
      { key: "B", text: "为 TA 分析一下问题在哪，看看能不能解决问题。", score: { T: 1 } },
    ],
  },
  {
    id: 7,
    tag: "情绪关系",
    text: "群聊里有人说了一个你不太认同的观点，你更可能？",
    options: [
      { key: "A", text: "如果问题明显，会想把逻辑或事实讲清楚。", score: { T: 1 } },
      { key: "B", text: "先看看当时的气氛，判断现在说合不合适。", score: { F: 1 } },
    ],
  },
  {
    id: 8,
    tag: "情绪关系",
    text: "如果朋友让你评价一件 TA 认真做的作品，你更倾向于？",
    options: [
      { key: "A", text: "认真分析并且明确指出哪里好、哪里可以改，这样对 TA 更有帮助。", score: { T: 1 } },
      { key: "B", text: "先保护 TA 的表达热情，再委婉说可以调整的地方；有些意见可能会让对方失落的话，你会选择不说。", score: { F: 1 } },
    ],
  },
  {
    id: 9,
    tag: "情绪关系",
    text: "和关系挺好的同事合作时，对方遭遇重大打击，情绪状态很差，导致进度慢了，你更容易先做什么？",
    options: [
      { key: "A", text: "先关心一下 TA 的状态，了解最近到底是什么在困扰 TA。", score: { F: 1 } },
      { key: "B", text: "看看自己能不能先帮 TA 分担一点，把进度先接上。", score: { T: 1 } },
    ],
  },
  {
    id: 10,
    tag: "情绪关系",
    text: "如果一个方案大家都挺喜欢，但你发现它实际执行起来有明显漏洞，你更可能？",
    options: [
      { key: "A", text: "先认可大家的热情，再用比较温和的方式提出担心。", score: { F: 1 } },
      { key: "B", text: "直接把漏洞说清楚，不然现在开心，后面会更麻烦。", score: { T: 1 } },
    ],
  },
  {
    id: 11,
    tag: "行动节奏",
    text: "周末突然空出一整天，你更舒服的状态是？",
    options: [
      { key: "A", text: "心里有几个想做的事，大概知道今天怎么过。", score: { J: 1 } },
      { key: "B", text: "先不急着安排，看醒来后的状态慢慢决定。", score: { P: 1 } },
    ],
  },
  {
    id: 12,
    tag: "行动节奏",
    text: "和朋友约好见面，但还没定接下来去哪，你更喜欢？",
    options: [
      { key: "A", text: "见了面再边走边看，看到有意思的地方就去。", score: { P: 2 } },
      { key: "B", text: "先随便想几个地方，到时候看心情选一个。", score: { P: 1 } },
      { key: "C", text: "见面前先定个大概去处，后面再根据情况调整。", score: { J: 1 } },
      { key: "D", text: "必须在见面前做好各种计划，不然会不舒服。", score: { J: 2 } },
    ],
  },
  {
    id: 13,
    tag: "行动节奏",
    text: "一天里事情很多，你更舒服的处理方式是？",
    options: [
      { key: "A", text: "先理出轻重缓急，按大致顺序一件件推进。", score: { J: 1 } },
      { key: "B", text: "先选一件当下适合做的开始，后面的顺序边做边调整。", score: { P: 1 } },
    ],
  },
  {
    id: 14,
    tag: "行动节奏",
    text: "你做饭、做手工或做一个小项目时，更像？",
    options: [
      { key: "A", text: "先动手试起来，过程中遇到问题再解决。", score: { P: 1 } },
      { key: "B", text: "先把步骤和材料大致弄清楚，心里有底再开始。", score: { J: 1 } },
    ],
  },
  {
    id: 15,
    tag: "行动节奏",
    text: "重新开始一件搁置很久的事时，你更自然的方式是？",
    options: [
      { key: "A", text: "先找一个明确的起点或小目标，让自己重新接上节奏。", score: { J: 1 } },
      { key: "B", text: "先打开看看或随手做一点，做到哪儿再决定怎么继续。", score: { P: 1 } },
    ],
  },
];

const drinkResults = {
  STJ: {
    drink: "无糖乌龙茶",
    resultCard: "result-cards/stj-unsweetened-oolong-tea.jpg",
  },
  STP: {
    drink: "青柠电解质水",
    resultCard: "result-cards/stp-lime-electrolyte-water.jpg",
  },
  SFJ: {
    drink: "热奶茶",
    resultCard: "result-cards/sfj-hot-milk-tea.jpg",
  },
  SFP: {
    drink: "蜜桃气泡水",
    resultCard: "result-cards/sfp-peach-sparkling-water.jpg",
  },
  NTJ: {
    drink: "冷萃黑咖啡",
    resultCard: "result-cards/ntj-cold-brew-black-coffee.jpg",
  },
  NTP: {
    drink: "特调鸡尾酒",
    resultCard: "result-cards/ntp-special-cocktail.jpg",
  },
  NFJ: {
    drink: "蜂蜜柚子茶",
    resultCard: "result-cards/nfj-honey-grapefruit-tea.jpg",
  },
  NFP: {
    drink: "缤纷水果茶",
    resultCard: "result-cards/nfp-colorful-fruit-tea.jpg",
  },
};

const resultCardToType = Object.fromEntries(
  Object.entries(drinkResults).map(([type, result]) => [result.resultCard.split("/").pop(), type])
);

const state = {
  currentIndex: 0,
  answers: Array(questions.length).fill(null),
  isAnswerCardOpen: false,
  result: null,
  visitorToken: null,
  syncStatus: "idle",
};

let autoNextTimer = null;
const audioState = {
  context: null,
  masterGain: null,
  bgGain: null,
  clickGain: null,
  bgNodes: [],
  bgTimer: null,
  bgm: null,
  effects: {},
  bgFadeTimer: null,
  bgStarted: false,
  enabled: localStorage.getItem(AUDIO_PREF_KEY) !== "off",
};

const els = {
  appShell: document.querySelector(".app-shell"),
  startView: document.querySelector("#startView"),
  quizView: document.querySelector("#quizView"),
  resultView: document.querySelector("#resultView"),
  backBtn: document.querySelector("#backBtn"),
  restartTopBtn: document.querySelector("#restartTopBtn"),
  audioToggle: document.querySelector("#audioToggle"),
  startBtn: document.querySelector("#startBtn"),
  dimensionTag: document.querySelector("#dimensionTag"),
  questionCounter: document.querySelector("#questionCounter"),
  questionIndex: document.querySelector("#questionIndex"),
  questionText: document.querySelector("#questionText"),
  optionList: document.querySelector("#optionList"),
  answerCardToggle: document.querySelector("#answerCardToggle"),
  answerCardToggleIcon: document.querySelector("#answerCardToggleIcon"),
  answerCardPanel: document.querySelector("#answerCardPanel"),
  answerCardGrid: document.querySelector("#answerCardGrid"),
  progressFill: document.querySelector("#progressFill"),
  runnerIcon: document.querySelector("#runnerIcon"),
  progressText: document.querySelector("#progressText"),
  prevBtn: document.querySelector("#prevBtn"),
  nextBtn: document.querySelector("#nextBtn"),
  nextBtnText: document.querySelector("#nextBtnText"),
  resultCardImage: document.querySelector("#resultCardImage"),
  resultFloatingActions: document.querySelector("#resultFloatingActions"),
  posterBtn: document.querySelector("#posterBtn"),
  restartBtn: document.querySelector("#restartBtn"),
  posterModal: document.querySelector("#posterModal"),
  posterCloseBtn: document.querySelector("#posterCloseBtn"),
  posterPreviewImage: document.querySelector("#posterPreviewImage"),
  posterLoading: document.querySelector("#posterLoading"),
  restartModal: document.querySelector("#restartModal"),
  restartCancelBtn: document.querySelector("#restartCancelBtn"),
  restartConfirmBtn: document.querySelector("#restartConfirmBtn"),
  toast: document.querySelector("#toast"),
};

function createAudio(src, { loop = false, volume = 1 } = {}) {
  const audio = new Audio(src);
  audio.preload = "auto";
  audio.loop = loop;
  audio.volume = volume;
  audio.playsInline = true;
  return audio;
}

function pickPlayableAudioSource(sources) {
  const probe = document.createElement("audio");
  if (sources.ogg && probe.canPlayType("audio/ogg; codecs=vorbis")) return sources.ogg;
  if (sources.mp3 && probe.canPlayType("audio/mpeg")) return sources.mp3;
  return sources.ogg || sources.mp3;
}

function getEffectAudio(kind) {
  const key = kind === "option" ? "option" : "tap";
  if (!audioState.effects[key]) {
    audioState.effects[key] = createAudio(AUDIO_ASSETS[key], { volume: AUDIO_VOLUME[key] });
  }
  return audioState.effects[key];
}

function getBackgroundAudio() {
  if (!audioState.bgm) {
    audioState.bgm = createAudio(pickPlayableAudioSource(AUDIO_ASSETS.bgm), { loop: true, volume: 0 });
  }
  return audioState.bgm;
}

function fadeBackgroundVolume(targetVolume) {
  const bgm = getBackgroundAudio();
  window.clearInterval(audioState.bgFadeTimer);

  const startVolume = bgm.volume;
  const startedAt = performance.now();
  const duration = 600;

  audioState.bgFadeTimer = window.setInterval(() => {
    const progress = Math.min(1, (performance.now() - startedAt) / duration);
    bgm.volume = startVolume + (targetVolume - startVolume) * progress;
    if (progress >= 1) {
      window.clearInterval(audioState.bgFadeTimer);
      audioState.bgFadeTimer = null;
    }
  }, 50);
}

async function unlockAudio() {
  if (!audioState.enabled) return;
  startBackgroundMusic();
}

function playClickSound(kind = "tap") {
  if (!audioState.enabled) return;

  const effect = getEffectAudio(kind);
  try {
    effect.currentTime = 0;
    effect.volume = kind === "option" ? AUDIO_VOLUME.option : AUDIO_VOLUME.tap;
    const playRequest = effect.play();
    if (playRequest) playRequest.catch(() => {});
  } catch (error) {
    // Audio feedback should never block the quiz flow.
  }
}

function startBackgroundMusic() {
  if (audioState.bgStarted || !audioState.enabled) return;

  const bgm = getBackgroundAudio();
  bgm.volume = 0;
  const playRequest = bgm.play();
  audioState.bgStarted = true;

  if (playRequest) {
    playRequest
      .then(() => fadeBackgroundVolume(AUDIO_VOLUME.bgm))
      .catch(() => {
        audioState.bgStarted = false;
      });
    return;
  }

  fadeBackgroundVolume(AUDIO_VOLUME.bgm);
}

function stopBackgroundMusic() {
  const bgm = audioState.bgm;
  if (!bgm) return;

  window.clearInterval(audioState.bgFadeTimer);
  audioState.bgFadeTimer = null;
  bgm.pause();
  bgm.volume = 0;
  audioState.bgStarted = false;
}

function updateAudioToggle() {
  if (!els.audioToggle) return;
  els.audioToggle.classList.toggle("is-muted", !audioState.enabled);
  els.audioToggle.setAttribute("aria-label", audioState.enabled ? "关闭音效" : "开启音效");
  els.audioToggle.title = audioState.enabled ? "关闭音效" : "开启音效";
  const icon = els.audioToggle.querySelector("img");
  if (icon) {
    icon.src = audioState.enabled ? AUDIO_ASSETS.iconOn : AUDIO_ASSETS.iconMuted;
  }
}

function setAudioEnabled(enabled) {
  audioState.enabled = enabled;
  localStorage.setItem(AUDIO_PREF_KEY, enabled ? "on" : "off");
  updateAudioToggle();
  if (enabled) {
    unlockAudio();
    window.setTimeout(() => playClickSound("tap"), 40);
  } else {
    stopBackgroundMusic();
  }
}
function showView(name) {
  els.appShell.classList.toggle("cover-mode", name === "start");
  els.appShell.classList.toggle("result-card-mode", name === "result");
  els.startView.hidden = name !== "start";
  els.quizView.hidden = name !== "quiz";
  els.resultView.hidden = name !== "result";
  els.backBtn.hidden = name !== "quiz";
  els.restartTopBtn.hidden = true;
  els.resultFloatingActions.hidden = name !== "result";
  els.appShell.scrollTo(0, 0);
  window.scrollTo(0, 0);
}

async function startQuiz({ reset = false } = {}) {
  if (reset) {
    resetQuizState();
    persistLocalState();
    await restartRemoteSession();
  }
  showView("quiz");
  renderQuestion();
}

function renderQuestion() {
  const question = questions[state.currentIndex];
  const answer = state.answers[state.currentIndex];

  els.dimensionTag.textContent = question.tag;
  els.questionCounter.textContent = `${String(state.currentIndex + 1).padStart(2, "0")} / ${questions.length}`;
  els.questionIndex.textContent = `第 ${question.id} 题`;
  els.questionText.textContent = question.text;

  els.optionList.innerHTML = question.options
    .map((option) => {
      const selected = answer === option.key;
      return `
        <button class="option-row ${selected ? "selected" : ""}" type="button" data-option="${option.key}" aria-pressed="${selected}">
          <span class="option-dot" aria-hidden="true"></span>
          <span class="option-copy">
            <span class="option-text">${option.text}</span>
          </span>
          <img class="sparkle-img option-sparkle" src="${assetUrl("sparkle.png")}" width="182" height="220" alt="" aria-hidden="true" />
        </button>
      `;
    })
    .join("");

  els.prevBtn.disabled = state.currentIndex === 0;
  els.nextBtn.disabled = !answer;
  els.nextBtnText.textContent = state.currentIndex === questions.length - 1 ? "查看结果" : "下一题";
  renderProgress();
  renderAnswerCard();
}

function renderProgress() {
  const answeredCount = state.answers.filter(Boolean).length;
  const progress = (answeredCount / questions.length) * 100;
  els.progressFill.style.width = `${progress}%`;
  els.runnerIcon.style.left = `${Math.min(98, Math.max(0, progress))}%`;
  els.progressText.textContent = `${answeredCount}/${questions.length}`;
}

function renderAnswerCard() {
  els.answerCardToggle.setAttribute("aria-expanded", String(state.isAnswerCardOpen));
  els.answerCardToggle.setAttribute("aria-label", state.isAnswerCardOpen ? "收起答题卡" : "展开答题卡");
  els.answerCardPanel.hidden = !state.isAnswerCardOpen;
  els.answerCardGrid.innerHTML = questions
    .map((question, index) => {
      const answered = Boolean(state.answers[index]);
      const current = index === state.currentIndex;
      return `
        <button class="answer-card-item ${answered ? "answered" : ""} ${current ? "current" : ""}" type="button" data-index="${index}" aria-label="第 ${question.id} 题">
          ${question.id}
        </button>
      `;
    })
    .join("");
}

function selectAnswer(optionKey) {
  state.answers[state.currentIndex] = optionKey;
  renderQuestion();
  persistLocalState();
  syncProgress();
  scheduleAutoAdvance();
}

function scheduleAutoAdvance() {
  clearTimeout(autoNextTimer);
  autoNextTimer = setTimeout(() => {
    if (state.currentIndex < questions.length - 1) {
      goToQuestion(state.currentIndex + 1);
      return;
    }

    nextQuestion();
  }, AUTO_NEXT_DELAY_MS);
}

function goToQuestion(index) {
  clearTimeout(autoNextTimer);
  state.currentIndex = Math.min(Math.max(index, 0), questions.length - 1);
  renderQuestion();
  persistLocalState();
  syncProgress();
}

function nextQuestion() {
  if (!state.answers[state.currentIndex]) {
    showToast("先凭直觉选一个答案");
    return;
  }

  if (state.currentIndex < questions.length - 1) {
    goToQuestion(state.currentIndex + 1);
    return;
  }

  const missingIndex = state.answers.findIndex((answer) => !answer);
  if (missingIndex >= 0) {
    state.isAnswerCardOpen = true;
    goToQuestion(missingIndex);
    showToast(`第 ${missingIndex + 1} 题还没选`);
    return;
  }

  renderResult();
}

function prevQuestion() {
  if (state.currentIndex > 0) {
    goToQuestion(state.currentIndex - 1);
  }
}

function calculateScores() {
  const scores = { S: 0, N: 0, T: 0, F: 0, J: 0, P: 0 };

  questions.forEach((question, index) => {
    const answerKey = state.answers[index];
    const option = question.options.find((item) => item.key === answerKey);
    if (!option) return;

    Object.entries(option.score).forEach(([key, value]) => {
      scores[key] += value;
    });
  });

  const type = `${scores.S > scores.N ? "S" : "N"}${scores.T > scores.F ? "T" : "F"}${scores.J > scores.P ? "J" : "P"}`;
  return { scores, type };
}

async function renderResult() {
  const calculated = calculateScores();
  const result = drinkResults[calculated.type];
  state.result = { ...calculated, ...result };

  els.resultCardImage.src = assetUrl(result.resultCard);
  els.resultCardImage.alt = `Drink-TI结果：${result.drink}`;
  showView("result");
  persistLocalState();
  await completeRemoteSession();
}

function restartQuiz() {
  openRestartModal();
}

function handleStartClick(event) {
  const button = event.currentTarget;
  button.classList.add("is-pressing");
  window.setTimeout(() => {
    button.classList.remove("is-pressing");
    startQuiz();
  }, 150);
}

function handleBack() {
  clearTimeout(autoNextTimer);
  state.currentIndex = 0;
  state.isAnswerCardOpen = false;
  persistLocalState();
  showView("start");
}

function resetQuizState() {
  state.currentIndex = 0;
  state.answers = Array(questions.length).fill(null);
  state.isAnswerCardOpen = false;
  state.result = null;
}

function loadLocalState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

function persistLocalState() {
  const payload = {
    visitorToken: state.visitorToken,
    currentIndex: state.currentIndex,
    answers: state.answers,
    result: state.result,
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function hydrateFromPayload(payload) {
  if (!payload) return;

  if (payload.visitorToken) {
    state.visitorToken = payload.visitorToken;
  }

  if (Array.isArray(payload.answers)) {
    state.answers = Array.from({ length: questions.length }, (_, index) => payload.answers[index] || null);
  }

  if (Number.isInteger(payload.currentIndex)) {
    state.currentIndex = Math.min(Math.max(payload.currentIndex, 0), questions.length - 1);
  }

  if (payload.result_type || payload.resultType) {
    const resultType = payload.result_type || payload.resultType;
    const result = drinkResults[resultType];
    if (result) {
      state.result = {
        scores: payload.scores || null,
        type: resultType,
        ...result,
      };
    }
  } else if (payload.result?.type && drinkResults[payload.result.type]) {
    state.result = payload.result;
  }
}

function ensureVisitorToken() {
  if (state.visitorToken) return;
  if (window.crypto?.randomUUID) {
    state.visitorToken = window.crypto.randomUUID();
    return;
  }
  state.visitorToken = `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function apiRequest(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

async function initRemoteSession() {
  try {
    const remote = await apiRequest("/session", { visitor_token: state.visitorToken });
    hydrateFromPayload(remote);
    persistLocalState();
    return remote;
  } catch (error) {
    state.syncStatus = "offline";
    return null;
  }
}

let progressSyncTimer = null;

function syncProgress() {
  clearTimeout(progressSyncTimer);
  progressSyncTimer = setTimeout(async () => {
    if (!state.visitorToken) return;

    try {
      await apiRequest("/progress", {
        visitor_token: state.visitorToken,
        answers: state.answers,
        current_index: state.currentIndex,
      });
      state.syncStatus = "synced";
    } catch (error) {
      state.syncStatus = "offline";
    }
  }, 280);
}

async function completeRemoteSession() {
  if (!state.visitorToken || state.answers.some((answer) => !answer)) return;

  try {
    await apiRequest("/complete", {
      visitor_token: state.visitorToken,
      answers: state.answers,
    });
    state.syncStatus = "synced";
  } catch (error) {
    state.syncStatus = "offline";
  }
}

async function restartRemoteSession() {
  if (!state.visitorToken) return;

  try {
    await apiRequest("/restart", { visitor_token: state.visitorToken });
    state.syncStatus = "synced";
  } catch (error) {
    state.syncStatus = "offline";
  }
}

function showStoredResult() {
  if (!state.result?.type || !drinkResults[state.result.type]) return false;
  const result = drinkResults[state.result.type];
  state.result = { ...state.result, ...result };
  els.resultCardImage.src = assetUrl(result.resultCard);
  els.resultCardImage.alt = `Drink-TI结果：${result.drink}`;
  showView("result");
  return true;
}

async function initApp() {
  hydrateFromPayload(loadLocalState());
  ensureVisitorToken();
  persistLocalState();
  const remote = await initRemoteSession();
  if (state.result?.type && showStoredResult()) {
    return;
  }

  if (remote?.status === "COMPLETED" && showStoredResult()) {
    return;
  }

  showView("start");
}

function openPosterModal() {
  if (!state.result?.type) {
    showToast("先完成测试，再生成海报");
    return;
  }

  els.posterPreviewImage.src = "";
  els.posterLoading.textContent = "正在生成海报...";
  els.posterLoading.classList.remove("done");
  els.posterModal.hidden = false;
  generatePosterImage();
}

function closePosterModal() {
  els.posterModal.hidden = true;
}

function openRestartModal() {
  els.restartModal.hidden = false;
}

function closeRestartModal() {
  els.restartModal.hidden = true;
}

async function confirmRestart() {
  closeRestartModal();
  await startQuiz({ reset: true });
  showToast("已开始新的测试");
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}

function drawCenteredText(ctx, text, x, y, maxWidth, lineHeight) {
  const chars = Array.from(text);
  const lines = [];
  let line = "";

  chars.forEach((char) => {
    const testLine = line + char;
    if (ctx.measureText(testLine).width > maxWidth && line) {
      lines.push(line);
      line = char;
      return;
    }
    line = testLine;
  });
  if (line) lines.push(line);

  lines.forEach((item, index) => {
    ctx.fillText(item, x, y + index * lineHeight);
  });
}

async function generatePosterImage() {
  try {
    const result = drinkResults[state.result.type];
    const [cardImage, qrImage] = await Promise.all([
      loadImage(assetUrl(result.resultCard)),
      loadImage(assetUrl(QR_CODE_SRC)),
    ]);

    const width = 852;
    const cardHeight = Math.round((cardImage.naturalHeight / cardImage.naturalWidth) * width);
    const footerHeight = 276;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = cardHeight + footerHeight;

    const ctx = canvas.getContext("2d");
    const pageGradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    pageGradient.addColorStop(0, "#fff8ec");
    pageGradient.addColorStop(0.42, "#fff4df");
    pageGradient.addColorStop(1, "#ffe4bb");
    ctx.fillStyle = pageGradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.drawImage(cardImage, 0, 0, width, cardHeight);

    const footerY = cardHeight;
    const gradient = ctx.createLinearGradient(0, footerY, 0, canvas.height);
    gradient.addColorStop(0, "#fff4df");
    gradient.addColorStop(1, "#ffe6be");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, footerY, width, footerHeight);

    ctx.fillStyle = "rgba(255, 255, 255, 0.76)";
    roundRect(ctx, 54, footerY + 36, width - 108, footerHeight - 72, 42);
    ctx.fill();

    const qrSize = 172;
    const qrX = 88;
    const qrY = footerY + 54;
    ctx.fillStyle = "#ffffff";
    roundRect(ctx, qrX - 12, qrY - 12, qrSize + 24, qrSize + 24, 26);
    ctx.fill();
    ctx.drawImage(qrImage, qrX, qrY, qrSize, qrSize);

    ctx.textAlign = "left";
    ctx.fillStyle = "#704831";
    ctx.font = '900 34px "STKaiti", "KaiTi", "PingFang SC", "Microsoft YaHei", sans-serif';
    drawCenteredText(ctx, POSTER_TAGLINE, 306, footerY + 104, 430, 52);

    els.posterPreviewImage.src = canvas.toDataURL("image/png");
    els.posterLoading.classList.add("done");
  } catch (error) {
    els.posterLoading.textContent = "海报生成失败，请确认二维码和结果图已加载。";
    showToast("海报生成失败");
  }
}

let toastTimer = null;

function showToast(message) {
  clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.classList.add("show");
  toastTimer = setTimeout(() => {
    els.toast.classList.remove("show");
  }, 2200);
}

els.startBtn.addEventListener("click", handleStartClick);
els.backBtn.addEventListener("click", handleBack);
els.restartTopBtn.addEventListener("click", restartQuiz);
els.prevBtn.addEventListener("click", prevQuestion);
els.nextBtn.addEventListener("click", nextQuestion);
els.posterBtn.addEventListener("click", openPosterModal);
els.restartBtn.addEventListener("click", restartQuiz);
els.audioToggle?.addEventListener("click", () => setAudioEnabled(!audioState.enabled));
els.posterCloseBtn.addEventListener("click", closePosterModal);
els.restartCancelBtn.addEventListener("click", closeRestartModal);
els.restartConfirmBtn.addEventListener("click", confirmRestart);

els.posterModal.addEventListener("click", (event) => {
  if (event.target.dataset.closeModal === "poster") closePosterModal();
});

els.restartModal.addEventListener("click", (event) => {
  if (event.target.dataset.closeModal === "restart") closeRestartModal();
});

els.optionList.addEventListener("click", (event) => {
  const button = event.target.closest(".option-row");
  if (!button) return;
  selectAnswer(button.dataset.option);
});

els.answerCardToggle.addEventListener("click", () => {
  state.isAnswerCardOpen = !state.isAnswerCardOpen;
  renderAnswerCard();
});

els.answerCardGrid.addEventListener("click", (event) => {
  const button = event.target.closest(".answer-card-item");
  if (!button) return;
  goToQuestion(Number(button.dataset.index));
});

document.addEventListener(
  "pointerdown",
  (event) => {
    const button = event.target.closest("button");
    unlockAudio().then(() => {
      if (!button || button.disabled) return;
      playClickSound(button.classList.contains("option-row") ? "option" : "tap");
    });
  },
  true
);

["contextmenu", "dragstart"].forEach((eventName) => {
  els.resultCardImage.addEventListener(eventName, (event) => {
    event.preventDefault();
  });
});

updateAudioToggle();
initApp();
