<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import EndShell from '@/layouts/EndShell.vue'
import GaodeTileMap from '@/components/GaodeTileMap.vue'
import SmokeStory from '@/components/citizen/SmokeStory.vue'
import AiReportCard from '@/components/citizen/AiReportCard.vue'
import type { AiReportBlock, AiState } from '@/components/citizen/AiReportCard.vue'
import { useCitizenStore } from '@/stores/citizen'
import { useSpeech, SPEECH_RATES, type SpeechSegment } from '@/composables/useSpeech'
import { http, toFailure } from '@/api/client'

type Tab = 'home' | 'map' | 'report' | 'records' | 'tasks' | 'science' | 'profile'
type Audience = 'teen' | 'youth' | 'senior'

const citizen = useCitizenStore()

const activeTab = ref<Tab>('home')
const selectedPoint = ref(1)
const reportStep = ref(1)
const fileName = ref('')
const mediaPreview = ref('')
const mediaInspection = ref<{ status: 'idle' | 'checking' | 'candidate' | 'scene' | 'rejected'; title: string; detail: string; confidence?: number }>({ status: 'idle', title: '等待添加素材', detail: '上传后将先检查格式、画面质量与内容相关性。' })
const reportType = ref('行为视频线索')
const location = ref('浉河区 · 人民路演示点位')
const safeConfirmed = ref(false)
const reportError = ref('')
const taskDone = ref(false)
const submitting = ref(false)
const submittedNo = ref('')

/* ================= 轮播图 ================= */
const slides = [
  {
    img: '/media/banner-park.png',
    tag: '城市行动',
    title: '无烟城市 你我共建',
    sub: '学习文明知识 · 反馈公共空间问题'
  },
  {
    img: '/media/banner-shoot.png',
    tag: '安全上报',
    title: '记录环境问题，提交治理线索',
    sub: '不跟拍、不拦截 · 不公开传播他人画面'
  },
  {
    img: '/media/banner-dawn.png',
    tag: '环卫协同',
    title: '每一次清理都被看见',
    sub: '工单闭环 · 响应时长公开可查'
  }
]
const slideIndex = ref(0)
let autoTimer: ReturnType<typeof setInterval> | null = null
const hovering = ref(false)

function goSlide(i: number) {
  slideIndex.value = (i + slides.length) % slides.length
}
function startAuto() {
  stopAuto()
  autoTimer = setInterval(() => {
    if (!hovering.value) goSlide(slideIndex.value + 1)
  }, 4500)
}
function stopAuto() {
  if (autoTimer) clearInterval(autoTimer)
  autoTimer = null
}
let touchX = 0
function touchStart(e: TouchEvent) {
  touchX = e.touches[0].clientX
}
function touchEnd(e: TouchEvent) {
  const dx = e.changedTouches[0].clientX - touchX
  if (Math.abs(dx) > 40) goSlide(slideIndex.value + (dx < 0 ? 1 : -1))
}

/* ================= 文明积分 ================= */
const points = ref(citizen.profile?.contribution ?? 36)
const ledger = ref<{ label: string; delta: number; time: string }[]>([
  { label: '情景问答 · 照片能定责吗', delta: 5, time: '09-26' },
  { label: '学习「小小烟头的环境影响」', delta: 3, time: '09-25' },
  { label: '文明打卡 · 连续第 2 天', delta: 5, time: '09-25' }
])
function today() {
  const d = new Date()
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function earn(delta: number, label: string) {
  points.value += delta
  ledger.value.unshift({ label, delta, time: today() })
}
/** 周排行（同事匿名化，仅演示） */
const weeklyRank = [
  { name: '市民 02**', score: 96, me: false },
  { name: '市民 05**', score: 88, me: false },
  { name: '市民 08**', score: 79, me: false },
  { name: citizen.profile?.displayName ?? '我', score: 71, me: true },
  { name: '市民 03**', score: 64, me: false },
  { name: '市民 06**', score: 58, me: false },
  { name: '市民 09**', score: 47, me: false },
  { name: '市民 01**', score: 35, me: false }
]
const myRank = computed(() => weeklyRank.findIndex((r) => r.me) + 1)

function doCheckIn() {
  if (taskDone.value) return
  taskDone.value = true
  earn(5, '文明打卡 · 到合规吸烟区现场打卡')
}

/** 首页「文明小贴士」——补齐右栏留白，同时把科普入口前置 */
const TIPS = [
  {
    no: '01',
    t: '烟头不是「可降解垃圾」',
    d: '滤嘴主要成分是醋酸纤维素，自然降解需数年，随意丢弃会长期留在土壤与水体中。'
  },
  {
    no: '02',
    t: '掐灭比扔掉更重要',
    d: '未熄灭的烟头中心温度可达 700℃，绿化带、纸箱、枯叶都极易被引燃。'
  },
  {
    no: '03',
    t: '上报不需要拍到脸',
    d: '平台只用画面判断现场状态与清理需求，不要求识别个人身份，也禁止跟拍拦截。'
  }
]

/** 本周治理速览（演示数据） */
const WEEKLY = [
  { v: '128', u: '件', l: '本周完成清理' },
  { v: '18', u: '分钟', l: '平均响应时长' },
  { v: '96%', u: '', l: '按时闭环率' },
  { v: '6', u: '处', l: '新增烟蒂设施' }
]

/* ================= 附近点位（GCJ-02 演示坐标） ================= */
const YOU: [number, number] = [114.091, 32.1468]
const mapPoints = [
  {
    id: 1, name: '城市书房烟蒂投放设施', area: '浉河区',
    address: '北京大街与中山路交叉口东北角', distance: 420,
    open: true, todayTask: true, kind: '烟蒂设施',
    lng: 114.0926, lat: 32.1486
  },
  {
    id: 2, name: '步行街示范吸烟点', area: '浉河区',
    address: '胜利路步行街南口西侧', distance: 1200,
    open: true, todayTask: false, kind: '演示吸烟点',
    lng: 114.0948, lat: 32.1449
  },
  {
    id: 3, name: '交通枢纽示范点位', area: '平桥区',
    address: '南京大道东站广场北侧', distance: 2400,
    open: false, todayTask: false, kind: '演示吸烟点',
    lng: 114.0832, lat: 32.1512
  },
  {
    id: 4, name: '社区公园烟蒂投放设施', area: '羊山新区',
    address: '新五大道与新六大街交叉口东南角', distance: 3100,
    open: true, todayTask: false, kind: '烟蒂设施',
    lng: 114.0975, lat: 32.1396
  }
]
const currentPoint = computed(
  () => mapPoints.find((p) => p.id === selectedPoint.value) ?? mapPoints[0]
)
const nearbyPoints = computed(() =>
  [...mapPoints].sort((a, b) => a.distance - b.distance).slice(0, 3)
)
const mapMarkers = computed(() => [
  { lng: YOU[0], lat: YOU[1], label: '你', kind: 'self' as const },
  ...mapPoints.map((p) => ({
    lng: p.lng, lat: p.lat,
    label: p.kind.includes('设施') ? '烟蒂设施' : '吸烟点',
    kind: (p.kind.includes('设施') ? 'facility' : 'spot') as 'facility' | 'spot'
  }))
])

/* ================= 科普（三人群统筹） ================= */
type Category = '烟头危害' | '火灾安全' | '文明吸烟' | '城市环保'
interface SciArticle {
  id: number
  title: string
  desc: string
  seniorDesc?: string
  dataPoint?: string
  category: Category
  minutes: number
  points: number
  cover?: string
  quiz?: { options: string[]; answer: number; explain: string }
  order: Record<Audience, number>
}

const ARTICLES: SciArticle[] = [
  {
    id: 1, title: '烟头的一生：从点燃到入河', category: '城市环保',
    desc: '一根烟蒂从被点燃、被丢弃，到随雨水进入下水道和水体，会经历什么？',
    seniorDesc: '烟头丢在地上，雨水一冲就进了下水道，最后流到河里，鱼虾都会受害。',
    minutes: 6, points: 3, cover: '/media/sci-life.png',
    order: { teen: 2, youth: 5, senior: 5 }
  },
  {
    id: 2, title: '小小烟头的环境影响', category: '烟头危害',
    desc: '从土壤、水体到公共空间，了解每一枚烟头的治理意义。',
    seniorDesc: '烟头里有毒东西会渗进土里、流到水里，不是“小事一桩”。',
    dataPoint: '1 枚烟蒂可污染约 500 升水体',
    minutes: 4, points: 3, cover: '/media/sci-soil.png',
    order: { teen: 4, youth: 3, senior: 2 }
  },
  {
    id: 3, title: '一颗烟头可能引发一场火灾', category: '火灾安全',
    desc: '未熄灭的烟头中心温度可达 700℃，遇到枯叶、纸箱、绿化带极易引燃。',
    seniorDesc: '烟头没掐灭，中心温度有七八百摄氏度，碰到干树叶、纸箱就会着火。',
    dataPoint: '烟头中心温度约 700℃',
    minutes: 3, points: 3, cover: '/media/sci-fire.png',
    order: { teen: 3, youth: 4, senior: 1 }
  },
  {
    id: 4, title: '合规吸烟点怎么用？', category: '文明吸烟',
    desc: '吸烟请至合规吸烟点，烟蒂投入阻燃收集设施，不在楼道、绿化带吸烟。',
    seniorDesc: '想抽烟请到吸烟亭，抽完把烟头掐灭放进收集桶，别扔在绿化带里。',
    minutes: 3, points: 3,
    order: { teen: 6, youth: 6, senior: 4 }
  },
  {
    id: 5, title: '单张烟头照片能证明是谁扔的吗？', category: '烟头危害',
    desc: '动作判断需要连续视频证据，照片只能记录现场状态。',
    seniorDesc: '一张照片说不清是谁扔的，要看连续的视频，还要人工确认。',
    minutes: 2, points: 5,
    quiz: {
      options: ['能，照片拍得很清楚', '不能，照片说明不了动作过程'],
      answer: 1,
      explain: '不能。照片只能说明现场状态，无法证明完整抛掷动作；判定需要连续视频证据并经过人工复核。'
    },
    order: { teen: 1, youth: 1, senior: 6 }
  },
  {
    id: 6, title: '二手烟与公共健康', category: '烟头危害',
    desc: '二手烟暴露没有安全水平，老人、儿童与孕妇是敏感人群。',
    seniorDesc: '二手烟对老人、小孩、孕妇伤害最大，公共场所请克制。',
    dataPoint: '二手烟含 69 种已知致癌物',
    minutes: 4, points: 3,
    order: { teen: 7, youth: 7, senior: 3 }
  },
  {
    id: 7, title: '安全参与：不跟拍、不传播', category: '文明吸烟',
    desc: '不要为了取证跟拍、拦截陌生人；素材不上传到公开平台，平台会替你把关。',
    seniorDesc: '看见有人扔烟头，别去拦、别去追，拍个远景交给平台就行。',
    minutes: 3, points: 3,
    order: { teen: 5, youth: 2, senior: 7 }
  },
  {
    id: 8, title: '烟蒂与城市水环境（数据解读）', category: '城市环保',
    desc: '从雨污分流角度看烟蒂入河路径，理解前端收集设施为什么划算。',
    dataPoint: '打捞 1kg 河道烟蒂成本 ≈ 前端收集的 20 倍',
    minutes: 5, points: 3,
    order: { teen: 8, youth: 8, senior: 8 }
  }
]

const NEWS_BY_AUDIENCE: Record<Audience, { title: string; cover: string; meta: string; desc: string }[]> = {
  teen: [
    { title: '校园消防课：一枚烟头为什么能点燃落叶', cover: '/media/sci-fire.png', meta: '3分钟 · 校园安全', desc: '用温度实验和互动问答认识未熄灭烟头的火灾风险。' },
    { title: '环保社团观察：烟蒂会沿雨水口去哪里', cover: '/media/sci-life.png', meta: '4分钟 · 观察实践', desc: '跟着城市水循环路线，记录小垃圾对河流环境的影响。' }
  ],
  youth: [
    { title: '城市更新观察：46处公共设施完成升级', cover: '/media/news-upgrade.png', meta: '2分钟 · 城市治理', desc: '从选址、使用率和维护成本理解公共空间设施如何运营。' },
    { title: '安全参与公共治理：线索、隐私与证据边界', cover: '/media/news-block.png', meta: '5分钟 · 权益指南', desc: '不追拍、不传播，在保护个人安全和隐私的前提下理性反馈。' }
  ],
  senior: [
    { title: '家门口的吸烟点怎么找、怎么用', cover: '/media/news-upgrade-alt.jpg', meta: '大字版 · 生活服务', desc: '看清标识、确认开放状态，烟头熄灭后投入阻燃收集设施。' },
    { title: '楼道和绿化带防火：记住这三个提醒', cover: '/media/sci-fire-alt.jpg', meta: '大字版 · 消防提醒', desc: '烟头要完全熄灭，纸箱杂物及时清理，发现冒烟立即远离并求助。' }
  ]
}

const audience = ref<Audience>('teen')
const AUDIENCES: { key: Audience; label: string; hint: string }[] = [
  { key: 'teen', label: '中学生', hint: '互动问答先行，校园场景讲解' },
  { key: 'youth', label: '青年', hint: '数据与权益并重，理性参与' },
  { key: 'senior', label: '长者', hint: '大字版 · 可语音朗读' }
]
const sciSearch = ref('')
const sciCategory = ref<'全部' | Category>('全部')
const SCI_CATEGORIES: ('全部' | Category)[] = ['全部', '烟头危害', '火灾安全', '文明吸烟', '城市环保']

const filteredArticles = computed(() => {
  const kw = sciSearch.value.trim()
  return ARTICLES.filter((a) => {
    if (sciCategory.value !== '全部' && a.category !== sciCategory.value) return false
    if (kw && !`${a.title}${a.desc}`.includes(kw)) return false
    return true
  }).sort((a, b) => a.order[audience.value] - b.order[audience.value])
})

/** 已完成学习 / 答题的文章 */
const readIds = ref<number[]>([])
const quizPicked = ref<Record<number, number>>({})
const lifeExpanded = ref(false)

const LIFE_STAGES = [
  { t: '点燃', d: '吸烟过程中，滤嘴吸附尼古丁与焦油。' },
  { t: '丢弃', d: '被随手丢弃的烟头进入人行道、绿化带或雨水口。' },
  { t: '冲刷', d: '雨水把烟蒂冲入下水道，塑料滤嘴难以降解。' },
  { t: '入河', d: '最终进入水体，释放有害物质，影响水生生物。' }
]

function readArticle(a: SciArticle) {
  if (readIds.value.includes(a.id)) return
  readIds.value.push(a.id)
  earn(a.points, `学习「${a.title}」`)
}
function pickQuiz(a: SciArticle, idx: number) {
  if (!a.quiz || quizPicked.value[a.id] !== undefined) return
  quizPicked.value = { ...quizPicked.value, [a.id]: idx }
  if (idx === a.quiz.answer) earn(a.points, `情景问答「${a.title}」`)
}
function finishLife() {
  readArticle(ARTICLES[0])
  lifeExpanded.value = true
}

/* ================= 语音朗读（长者模式的核心特色） ================= */
/**
 * 朗读做成**一个全局播报器**（见 composables/useSpeech.ts）：
 * 整页连读 / 单条朗读 / 暂停 / 继续 / 停止 / 语速切换，并高亮当前正在朗读的那一条。
 * 入口有三处：科普页顶部的常驻朗读条、每篇文章的「朗读」按钮、每张新闻卡片的「朗读」按钮。
 */
const speech = useSpeech()
// 解构出来，模板里才能直接自动解包（模板只自动解包顶层 ref）
const {
  supported: speechSupported,
  message: speechMessage,
  currentId: speakingId,
  speaking: isSpeaking,
  paused: speechPaused,
  rate: speechRate,
  stop: stopSpeech,
  togglePause: toggleSpeechPause,
  setRate: setSpeechRate,
  cycleRate: cycleSpeechRate
} = speech
const RATE_LABEL: Record<number, string> = { 0.7: '很慢', 0.85: '慢', 0.95: '正常', 1.1: '稍快' }

/** 当前屏幕可见的科普内容，按视觉顺序组成朗读清单 */
function pageSegments(): SpeechSegment[] {
  const out: SpeechSegment[] = []
  if (!sciSearch.value && sciCategory.value === '全部') {
    NEWS_BY_AUDIENCE[audience.value].forEach((n, i) =>
      out.push({ id: `news-${audience.value}-${i}`, text: `${n.title}。${n.desc}` })
    )
  }
  filteredArticles.value.forEach((a) =>
    out.push({ id: `article-${a.id}`, text: articleSpeech(a) })
  )
  return out
}

function articleSpeech(a: SciArticle): string {
  const body = audience.value === 'senior' && a.seniorDesc ? a.seniorDesc : a.desc
  return `${a.title}。${body}`
}

function readPageAloud() {
  if (!speech.supported) return
  speech.speakList(pageSegments())
}
function readArticleAloud(a: SciArticle) {
  speech.speakOne(`article-${a.id}`, articleSpeech(a))
}
function readNewsAloud(n: { title: string; desc: string }, i: number) {
  speech.speakOne(`news-${audience.value}-${i}`, `${n.title}。${n.desc}`)
}
/** 供子组件（互动剧情）调用：把一段文字交给同一个全局朗读器 */
function speakSegment(id: string, text: string) {
  speech.speakOne(id, text)
}

/* ================= AI 报告（上传即检，当场出结论） ================= */
/**
 * 市民选择素材后立刻调后端 `/public/ai/inspect`，当场拿到**结构化 AI 报告**：
 * 检出目标与置信度、三阶段推断标注、证据链状态、免责说明。
 * 报告快照会随上报一起落库 → 管理端复核时能看到当时的模型结论（"检测为真反馈给管理员端"）。
 *
 * 两个必须处理的现实问题：
 *  1. 首次调用可能触发模型加载（CPU 约 40~60 秒），所以给 150 秒超时 + 进度提示，
 *     而不是像以前那样 3.5 秒超时就悄悄退回本地预检、用户根本看不到真实结论；
 *  2. 模型不可用时**仍允许提交**，并在卡片上说明已改用本地预检——不能把用户堵死。
 */
const aiState = ref<AiState>('idle')
const aiReport = ref<AiReportBlock | null>(null)
const aiError = ref('')
const aiElapsed = ref(0)
let aiTicker: ReturnType<typeof setInterval> | undefined
let aiToken = 0

function startAiTicker() {
  stopAiTicker()
  const t0 = Date.now()
  aiElapsed.value = 0
  aiTicker = setInterval(() => {
    aiElapsed.value = (Date.now() - t0) / 1000
  }, 100)
}
function stopAiTicker() {
  if (aiTicker) clearInterval(aiTicker)
  aiTicker = undefined
}

async function runAiInspect(file: File) {
  aiToken += 1
  const token = aiToken
  aiReport.value = null
  aiError.value = ''
  aiState.value = 'running'
  startAiTicker()
  try {
    const form = new FormData()
    form.append('file', file)
    const { data } = await http.post<AiReportBlock>('/public/ai/inspect', form, { timeout: 150000 })
    if (token !== aiToken) return
    aiReport.value = data
    aiState.value = 'done'
    // 同步一下表单里的轻量预检文案，保持两处口径一致
    mediaInspection.value = {
      status: data.detected ? 'candidate' : 'scene',
      title: data.verdict_label,
      detail: data.summary,
      confidence: data.confidence
    }
  } catch (err) {
    if (token !== aiToken) return
    aiState.value = 'failed'
    aiError.value = toFailure(err).message
  } finally {
    if (token === aiToken) stopAiTicker()
  }
}

function retryAiInspect() {
  const input = document.querySelector<HTMLInputElement>('.upload-zone input[type=file]')
  const file = input?.files?.[0]
  if (file && file.type.startsWith('image/')) {
    void runAiInspect(file)
    return
  }
  aiState.value = 'idle'
}

/* ---- 市民对 AI 判断的反馈（不同意 → 进入人工复核） ---- */
const feedbackDraft = ref<Record<string, string>>({})
const feedbackDone = ref<string[]>([])
const feedbackBusy = ref('')
const feedbackError = ref('')

function feedbackSubmitted(no: string, fromServer?: unknown) {
  return Boolean(fromServer) || feedbackDone.value.includes(no)
}

/** 模板里不做类型断言，统一走这个收口函数 */
function toAiReport(raw: unknown): AiReportBlock | null {
  return (raw as AiReportBlock) ?? null
}

/** 无后端时的演示报告：保证「治理进度」里也能看到 AI 报告的样子 */
const DEMO_AI_REPORT: AiReportBlock = {
  engine: 'best.pt · Ultralytics YOLO（cigarette / hand / person）',
  demo: true,
  detected: true,
  confidence: 87.3,
  count: 1,
  detections: [{ label: 'cigarette', label_zh: '烟头', confidence: 87.3 }],
  verdict: 'candidate',
  verdict_label: '疑似烟头目标',
  verdict_tone: 'ok',
  summary:
    '模型检出 1 个相关目标，最高置信度 87.3%。可作为候选线索进入人工复核；单张图片只能说明现场状态，不能证明完整抛掷动作。',
  stages: [
    { key: 'holding', label: '持烟 · 点燃', state: 'hit', note: '检出烟头目标' },
    { key: 'throw', label: '抛掷动作', state: 'unknown', note: '静态图片无法判定动作过程' },
    { key: 'landing', label: '落地 · 现场状态', state: 'hit', note: '可见落地痕迹' }
  ],
  evidence: {
    frames: 1,
    chain: '不完整',
    note: '本次素材为单张图片：可记录现场状态，不足以证明完整抛掷动作。'
  },
  risk_notes: ['不要为了取证跟拍、拦截或靠近陌生人。', '素材仅用于治理研判，不会公开传播他人画面。'],
  notice: '模型结果仅生成候选线索，不会自动认定违规或触发处罚；判定需授权人员人工复核。'
}

async function sendAiFeedback(no: string, agree: boolean) {
  const reason = (feedbackDraft.value[no] ?? '').trim()
  if (!agree && reason.length < 4) {
    feedbackError.value = '不同意模型判断时，请写上不少于 4 个字的理由'
    return
  }
  feedbackError.value = ''
  feedbackBusy.value = no
  try {
    if (citizen.apiMode) {
      await http.post(`/citizen/reports/${no}/ai-feedback`, { agree, reason })
      void citizen.loadReports()
    }
    feedbackDone.value = [...feedbackDone.value, no]
    feedbackDraft.value = { ...feedbackDraft.value, [no]: '' }
  } catch (err) {
    feedbackError.value = toFailure(err).message
  } finally {
    feedbackBusy.value = ''
  }
}

/* ================= 通用 ================= */
const tabs: { key: Tab; label: string; icon: string }[] = [
  { key: 'home', label: '首页', icon: '⌂' },
  { key: 'map', label: '吸烟区地图', icon: '⌖' },
  { key: 'tasks', label: '任务', icon: '▤' },
  { key: 'science', label: '科普', icon: '◇' },
  { key: 'profile', label: '我们', icon: '○' }
]

function switchTab(tab: Tab) {
  activeTab.value = tab
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  await processFile(file)
  // 清空 input，保证同一张照片连续选两次也能再次触发 change
  input.value = ''
}

/**
 * 素材入库前的统一处理：类型/大小校验 → 本地即时预检 → 图片再走真实模型当场出 AI 报告。
 * 表单的「上传素材」与 App 底部中间的「监督拍照」都走这一条，避免两套口径。
 */
async function processFile(file: File) {
  reportError.value = ''
  const isVideo = file.type.startsWith('video/')
  const isImage = file.type.startsWith('image/')
  if (!isVideo && !isImage) {
    fileName.value = ''
    aiState.value = 'idle'
    aiReport.value = null
    mediaInspection.value = { status: 'rejected', title: '文件类型不支持', detail: '请上传 JPG、PNG、WEBP 图片或常见 MP4 视频。' }
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    fileName.value = ''
    aiState.value = 'idle'
    aiReport.value = null
    mediaInspection.value = { status: 'rejected', title: '文件过大', detail: '单个素材不能超过 20MB，请压缩后重新上传。' }
    return
  }
  fileName.value = file.name
  if (mediaPreview.value) URL.revokeObjectURL(mediaPreview.value)
  mediaPreview.value = URL.createObjectURL(file)
  mediaInspection.value = { status: 'checking', title: '正在进行智能预检…', detail: '检查文件完整性、画面清晰度及烟头场景相关性。' }
  await new Promise((resolve) => window.setTimeout(resolve, 300))

  const lower = file.name.toLowerCase()
  const unrelated = /(logo|avatar|证件|合同|发票|截图|screenshot|cat|dog|food|receipt|document)/i.test(lower)
  const related = /(烟|烟头|烟蒂|cigarette|smoke|butt|litter)/i.test(lower)
  if (isImage) {
    // 图片：交给真正的模型，当场出 AI 报告（不再 3.5 秒超时后悄悄退回本地预检）
    await runAiInspect(file)
    return
  }
  // 视频：模型不做即时检测，标注为「待抽帧分析」，先走本地安全预检
  aiState.value = 'skipped'
  aiReport.value = null
  if (unrelated) {
    mediaInspection.value = { status: 'rejected', title: '素材与上报场景不符', detail: '未识别到烟头、烟蒂设施或公共空间环境，请检查是否选错文件。' }
  } else if (isVideo || related) {
    mediaInspection.value = { status: 'candidate', title: '发现疑似相关线索', detail: '检测到烟头/抛掷场景候选区域，仍需授权人员人工复核，系统不会自动定责。', confidence: 83.6 }
  } else {
    mediaInspection.value = { status: 'scene', title: '画面有效，未确认违规动作', detail: '单张照片只能作为现场环境线索，无法证明完整抛掷动作；可提交用于清理与热点治理。', confidence: 61.2 }
  }
}

/* ================= 手机 App 版：底部导航 + 中间「监督拍照」 ================= */
/** App 底栏五项，中间一项是突出的相机按钮（对齐参考稿：中间最大、最显眼） */
const APP_TABS: { key: Tab | 'capture'; label: string; icon: string }[] = [
  { key: 'home', label: '首页', icon: '⌂' },
  { key: 'map', label: '点位', icon: '⌖' },
  { key: 'capture', label: '监督拍照', icon: '' },
  { key: 'science', label: '科普', icon: '◇' },
  { key: 'profile', label: '我的', icon: '○' }
]

const appCaptureRef = ref<HTMLInputElement | null>(null)

/** 中间相机按钮：优先直接调起系统相机（capture），桌面端则退化为选择文件 */
function tapCapture() {
  appCaptureRef.value?.click()
}

async function onAppCapture(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  // 先进上报页：用户能看到 AI 报告与提交表单，而不是停留在首页不知所措
  reportType.value = '现场卫生照片'
  switchTab('report')
  if (file) {
    await processFile(file)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function appTabActive(key: Tab | 'capture') {
  if (key === 'capture') return activeTab.value === 'report'
  return activeTab.value === key
}

/** 底栏点击：中间项走拍照，其余走切页 */
function tapTab(key: Tab | 'capture') {
  if (key === 'capture') {
    tapCapture()
    return
  }
  switchTab(key)
}

/* ================= 演示导航：按路网形态仿真一条路线 ================= */
/**
 * 需求是「无非就是想仿真环境当中的、模拟一条路线出来」，所以这里：
 *  1. 用折线**仿真一条符合路网习惯的路线**（先拐上主路 → 沿主路 → 再折向目的地），
 *     而不是两点之间的直线；
 *  2. 在瓦片地图上把路线画出来，已走部分高亮、未走部分虚线，断点处有行进点；
 *  3. 给出分步指引（出发 / 路口转向 / 到达），转向文案由**几何叉积**推出来，不是写死的；
 *  4. 演示按 12 秒走完全程（真实步行时间同时显示，避免误导）。
 */
const NAV_DEMO_SECONDS = 12
const WALK_SPEED_MPS = 1.25

const navOn = ref(false)
const navPaused = ref(false)
const navProgress = ref(0)
const navRoute = ref<[number, number][]>([])
let navTimer: ReturnType<typeof setInterval> | undefined
/** 地图页那块地图：导航时要用它放大并居中到路线 */
const navMapRef = ref<{ setView: (c: [number, number], z: number) => void } | null>(null)

function buildRoute(from: [number, number], to: [number, number]): [number, number][] {
  const [x1, y1] = from
  const [x2, y2] = to
  const dx = x2 - x1
  const dy = y2 - y1
  return [
    [x1, y1],
    [x1 + dx * 0.04, y1 - dy * 0.22],
    [x1 + dx * 0.38, y1 - dy * 0.16],
    [x1 + dx * 0.44, y1 + dy * 0.44],
    [x1 + dx * 0.86, y1 + dy * 0.52],
    [x2, y2]
  ]
}

/** 转向提示：用叉积判断左/右（屏幕 y 向下，且纬度增大对应屏幕向上，故取反） */
function turnLabel(a: [number, number], b: [number, number], c: [number, number]): string {
  const geo = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
  if (Math.abs(geo) < 1e-9) return '继续直行'
  return geo > 0 ? '前方路口右转' : '前方路口左转'
}

const navLegs = computed(() => {
  const pts = navRoute.value
  const legs: number[] = []
  let total = 0
  for (let i = 1; i < pts.length; i++) {
    const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
    total += d
    legs.push(total)
  }
  return { legs, total }
})

const navSteps = computed(() => {
  const pts = navRoute.value
  const n = pts.length
  if (n < 2) return []
  const out: string[] = []
  for (let i = 0; i < n - 1; i++) {
    if (i === 0) out.push('从当前位置出发，沿当前道路前进')
    else if (i === n - 2) out.push(`到达 ${currentPoint.value.name}`)
    else out.push(`${turnLabel(pts[i - 1], pts[i], pts[i + 1])}，继续前进`)
  }
  return out
})

const navStepIndex = computed(() => {
  const { legs, total } = navLegs.value
  if (!total) return 0
  const walked = navProgress.value * total
  for (let i = 0; i < legs.length; i++) if (walked <= legs[i]) return i
  return Math.max(0, legs.length - 1)
})

const navRemainM = computed(() =>
  Math.max(0, Math.round(currentPoint.value.distance * (1 - navProgress.value)))
)
const navEtaMin = computed(() => Math.max(0, Math.ceil(navRemainM.value / WALK_SPEED_MPS / 60)))
const navRealMin = computed(() => Math.max(1, Math.ceil(currentPoint.value.distance / WALK_SPEED_MPS / 60)))

function tickNav() {
  if (navPaused.value) return
  navProgress.value = Math.min(1, navProgress.value + 1 / NAV_DEMO_SECONDS / 10)
  if (navProgress.value >= 1) stopNavTimer()
}
function startNavTimer() {
  stopNavTimer()
  navTimer = setInterval(tickNav, 100)
}
function stopNavTimer() {
  if (navTimer) clearInterval(navTimer)
  navTimer = undefined
}

function startNav() {
  const target: [number, number] = [currentPoint.value.lng, currentPoint.value.lat]
  navRoute.value = buildRoute(YOU, target)
  navProgress.value = 0
  navPaused.value = false
  navOn.value = true
  // 校区尺度上两点只差两百多米：z15 下路线只有几十像素、基本看不见，
  // 所以导航一开始就把地图放大到 z17 并居中到起终点中间。
  navMapRef.value?.setView([(YOU[0] + target[0]) / 2, (YOU[1] + target[1]) / 2], 17)
  startNavTimer()
}
function toggleNavPause() {
  navPaused.value = !navPaused.value
}
function stopNav() {
  stopNavTimer()
  navOn.value = false
  navPaused.value = false
  navProgress.value = 0
  navRoute.value = []
  navMapRef.value?.setView(YOU, 15)
}

async function submitReport() {
  reportError.value = ''
  if (!fileName.value) {
    reportError.value = '请先选择一段已获得合法使用权的视频或现场照片'
    return
  }
  if (mediaInspection.value.status === 'checking') {
    reportError.value = '素材仍在智能预检中，请稍候'
    return
  }
  if (mediaInspection.value.status === 'rejected') {
    reportError.value = '当前素材未通过相关性检查，请重新选择正确的现场素材'
    return
  }
  if (!safeConfirmed.value) {
    reportError.value = '请确认素材不是通过跟拍、拦截等危险方式取得'
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    const res = await citizen.submitReport({
      kind: reportType.value.includes('视频') ? 'video' : 'photo',
      media_name: fileName.value,
      location: location.value,
      description: '',
      safe_confirmed: true,
      // 把当场拿到的 AI 报告快照一起提交：管理端复核时能看到当时的模型结论
      ai_report: aiReport.value ?? undefined
    })
    if (!res.ok) {
      reportError.value = res.message
      return
    }
    submittedNo.value = res.report?.report_no || ''
    reportStep.value = 2
    if (citizen.apiMode) void citizen.loadReports()
  } finally {
    submitting.value = false
  }
}

function fmtDateTime(ts: string) {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}月${p(d.getDate())}日 ${p(d.getHours())}:${p(d.getMinutes())}`
}
function fmtTime(ts: string) {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ''
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}`
}

onMounted(() => {
  if (citizen.apiMode) void citizen.loadReports()
  startAuto()
})
onBeforeUnmount(() => {
  stopAuto()
  stopAiTicker()
  if (mediaPreview.value) URL.revokeObjectURL(mediaPreview.value)
})

function logout() {
  citizen.logout()
  window.location.href = './auth.html#/auth?role=citizen'
}
</script>

<template>
  <EndShell
    class="citizen-app"
    end="citizen"
    title="市民用户端"
    subtitle="烟踪智治 · 安全上报与治理进度"
    :user="citizen.profile?.displayName ?? ''"
    width="100%"
  >
    <template #nav>
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="ad-btn"
        :class="{ 'ad-btn--primary': activeTab === tab.key }"
        type="button"
        @click="switchTab(tab.key)"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </template>
    <template #actions>
      <button class="ad-btn" type="button" @click="logout">退出</button>
    </template>

    <section class="portal-shell">
      <header class="mobile-header">
        <button class="city-select" type="button"><i></i><b>信阳市</b><span>⌄</span></button>
        <button class="search-entry" type="button" @click="switchTab('map')"><span>⌕</span>搜索吸烟区或烟蒂设施</button>
        <button class="notice-entry" type="button" aria-label="打开通知" @click="switchTab('records')">♢<em>2</em></button>
      </header>

      <div class="demo-banner"><span>DEMO</span> 当前为演示模式，不代表真实点位、案件或治理结果</div>

      <!-- ================= 首页 ================= -->
      <div v-if="activeTab === 'home'" class="portal-page home-page">
        <header class="citizen-brand-row">
          <span class="citizen-brand-mark">◎</span>
          <div><h1>烟踪智治</h1><p>共建无烟城市 · 文明打卡每一天</p></div>
        </header>

        <!-- 轮播图 -->
        <section
          class="home-carousel"
          @mouseenter="hovering = true"
          @mouseleave="hovering = false"
          @touchstart.passive="touchStart"
          @touchend.passive="touchEnd"
        >
          <div class="carousel-track" :style="{ transform: `translateX(-${slideIndex * 100}%)` }">
            <div v-for="(s, i) in slides" :key="i" class="carousel-slide">
              <img :src="s.img" :alt="s.title" draggable="false" />
              <div class="slide-shade"></div>
              <div class="slide-copy">
                <span class="slide-tag">{{ s.tag }}</span>
                <h2>{{ s.title }}</h2>
                <p>{{ s.sub }}</p>
              </div>
            </div>
          </div>
          <button class="carousel-arrow left" type="button" aria-label="上一张" @click="goSlide(slideIndex - 1)">‹</button>
          <button class="carousel-arrow right" type="button" aria-label="下一张" @click="goSlide(slideIndex + 1)">›</button>
          <div class="carousel-dots">
            <button
              v-for="(s, i) in slides"
              :key="i"
              type="button"
              :class="{ on: i === slideIndex }"
              :aria-label="`第 ${i + 1} 张`"
              @click="goSlide(i)"
            ></button>
          </div>
        </section>

        <!-- 快捷入口（对齐参考稿：附近吸烟区/文明任务/随手拍/积分排行/科普） -->
        <section class="quick-grid">
          <button type="button" @click="switchTab('map')"><span class="quick-symbol blue">⌖</span><b>附近吸烟区</b></button>
          <button type="button" @click="switchTab('tasks')"><span class="quick-symbol green">✓</span><b>文明任务</b></button>
          <button type="button" data-testid="report-entry" @click="switchTab('report')"><span class="quick-symbol orange">▣</span><b>安全上报</b></button>
          <button type="button" @click="switchTab('records')"><span class="quick-symbol yellow">↻</span><b>治理进度</b></button>
          <button type="button" @click="switchTab('science')"><span class="quick-symbol teal">▤</span><b>科普</b></button>
        </section>

        <section class="my-latest latest-prominent">
          <div class="section-title"><span>我的最新线索</span><button type="button" @click="switchTab('records')">全部记录 →</button></div>
          <button class="latest-row" type="button" @click="switchTab('records')">
            <span class="status-icon">✓</span><div><b>XZ-DEMO-260917</b><small>浉河区 · 环境线索 · 09月17日</small></div><em>已完成清理</em><i>→</i>
          </button>
        </section>

        <section class="home-grid">
          <!-- 附近合规吸烟区（高德地图） -->
          <article class="nearby-card">
            <div class="section-title"><span>附近合规吸烟区</span><button type="button" @click="switchTab('map')">地图 ›</button></div>
            <GaodeTileMap
              class="nearby-map"
              :center="YOU"
              :zoom="15"
              :markers="mapMarkers"
              :route="navRoute"
              :route-progress="navProgress"
              height="190px"
              :interactive="true"
            />
            <div class="poi-list">
              <button
                v-for="p in nearbyPoints"
                :key="p.id"
                type="button"
                class="poi-row"
                :class="{ active: selectedPoint === p.id }"
                @click="selectedPoint = p.id"
              >
                <div class="poi-main">
                  <b>{{ p.name }}</b>
                  <small>{{ p.address }}</small>
                </div>
                <div class="poi-side">
                  <em>约{{ p.distance }}米</em>
                  <span class="poi-tags">
                    <i class="open" v-if="p.open">营业中</i>
                    <i class="closed" v-else>维护中</i>
                    <i class="task" v-if="p.todayTask">今日任务</i>
                  </span>
                </div>
              </button>
            </div>
            <div class="facility-guide">
              <span><i>灭</i><b>确认完全熄灭</b><small>投入设施前不留明火</small></span>
              <span><i>投</i><b>分类投入烟蒂口</b><small>不混入纸屑和塑料瓶</small></span>
              <span><i>护</i><b>异常及时反馈</b><small>满溢或损坏可安全上报</small></span>
            </div>
            <div class="nearby-insight">
              <header><div><b>周边设施运行概览</b><small>基于演示点位的状态汇总</small></div><em>更新于 17:30</em></header>
              <div class="insight-row"><span>开放可用</span><i><b style="width:75%"></b></i><strong>3 / 4</strong></div>
              <div class="insight-row"><span>今日已巡检</span><i><b style="width:58%"></b></i><strong>7 处</strong></div>
              <div class="insight-row"><span>设施整洁度</span><i><b style="width:86%"></b></i><strong>86%</strong></div>
              <p><span>文明提示</span>进入公共空间前请留意禁烟标识；吸烟点仅为演示数据，不作为现实吸烟指引。</p>
            </div>
          </article>

          <div class="home-side">
            <!-- 今日文明任务 -->
            <article class="task-card">
              <div class="section-title"><span>今日文明任务</span><small>学习记录 +5</small></div>
              <div class="task-body">
                <div class="task-copy">
                  <h2>公共空间文明打卡</h2>
                  <p>了解附近烟蒂投放设施，并完成一次文明知识确认。</p>
                  <button type="button" data-testid="checkin-home" :disabled="taskDone" @click="doCheckIn">
                    {{ taskDone ? '已打卡' : '立即打卡' }}
                  </button>
                </div>
                <img class="task-coins" src="/media/coins-alt.jpg" alt="文明学习记录" />
              </div>
            </article>

            <article class="knowledge-card">
              <div class="section-title"><span>一分钟了解</span><button type="button" @click="switchTab('science')">更多科普 ›</button></div>
              <ul>
                <li><i>01</i><div><b>照片不能证明完整动作</b><p>行为研判需要连续视频、时间码和人工复核。</p></div></li>
                <li><i>02</i><div><b>不要为了取证追拍</b><p>优先保护自身安全，环境问题仍可单独上报。</p></div></li>
                <li><i>03</i><div><b>AI只生成候选线索</b><p>系统不会依据模型结果自动认定责任或处罚。</p></div></li>
              </ul>
            </article>

            <article class="service-card">
              <div class="section-title"><span>今日治理动态</span><button type="button" @click="switchTab('records')">查看进度 ›</button></div>
              <div class="service-stats">
                <span><b>6</b><small>附近开放设施</small></span>
                <span><b>3</b><small>今日完成清理</small></span>
                <span><b>18<em>分钟</em></b><small>平均响应时长</small></span>
              </div>
              <ol class="service-feed">
                <li><i class="done">✓</i><div><b>人民路雨水口周边已清理</b><small>环卫班组 · 12分钟前完成</small></div></li>
                <li><i>巡</i><div><b>步行街示范点进入例行巡检</b><small>设施状态 · 正常开放</small></div></li>
                <li><i class="warn">!</i><div><b>社区公园收集设施等待维护</b><small>已登记 · 预计今日处理</small></div></li>
              </ol>
            </article>
          </div>
        </section>

      </div>

      <!-- ================= 吸烟区地图 ================= -->
      <div v-else-if="activeTab === 'map'" class="portal-page map-page">
        <header class="page-heading"><span>PUBLIC MAP / DEMO</span><h1>附近点位</h1><p>优先展示烟蒂投放设施。吸烟点数据只有经主管单位确认后才能正式发布。</p></header>
        <div class="map-layout">
          <div class="citizen-map">
            <div class="map-disclaimer">演示地图 · 非官方点位</div>
            <GaodeTileMap
              ref="navMapRef"
              :center="YOU"
              :zoom="15"
              :markers="mapMarkers"
              :route="navRoute"
              :route-progress="navProgress"
              height="480px"
              :interactive="true"
            />
            <!-- 演示导航面板：路线进度 + 分步指引（路线由 buildRoute 按路网形态仿真） -->
            <div v-if="navOn" class="nav-panel" data-testid="nav-panel">
              <header>
                <div>
                  <b>{{ navSteps[navStepIndex] }}</b>
                  <small>剩余 {{ navRemainM }} 米 · 步行约 {{ navEtaMin }} 分钟</small>
                </div>
                <span class="nav-demo">演示加速</span>
              </header>
              <div class="nav-bar"><i :style="{ width: `${Math.round(navProgress * 100)}%` }"></i></div>
              <ol class="nav-steps">
                <li
                  v-for="(s, i) in navSteps"
                  :key="i"
                  :class="{ on: i === navStepIndex, done: i < navStepIndex }"
                >
                  <i></i><span>{{ s }}</span>
                </li>
              </ol>
              <div class="nav-acts">
                <button type="button" @click="toggleNavPause">{{ navPaused ? '继续' : '暂停' }}</button>
                <button type="button" class="ghost" @click="stopNav">结束导航</button>
              </div>
              <p class="nav-note">
                演示用 12 秒走完全程（真实步行约 {{ navRealMin }} 分钟）。导航只提供方向参考，
                不作为现实吸烟许可。</p>
            </div>
          </div>
          <div class="point-list">
            <button
              v-for="p in [...mapPoints].sort((a, b) => a.distance - b.distance)"
              :key="p.id"
              type="button"
              :class="{ active: selectedPoint === p.id }"
              @click="selectedPoint = p.id"
            >
              <span>{{ String(p.id).padStart(2, '0') }}</span>
              <div>
                <b>{{ p.name }}</b>
                <small>{{ p.address }}</small>
              </div>
              <em>约{{ p.distance }}米</em>
            </button>
            <article class="selected-place">
              <small>当前选择</small>
              <h2>{{ currentPoint.name }}</h2>
              <p>{{ currentPoint.kind.includes('吸烟') ? '该点位仅为产品交互演示，不能作为现实吸烟指引。' : '配有阻燃烟蒂收集设施，正式状态等待主管单位审核。' }}</p>
              <div class="poi-tags big">
                <i class="open" v-if="currentPoint.open">营业中</i>
                <i class="closed" v-else>维护中</i>
                <i class="task" v-if="currentPoint.todayTask">今日任务</i>
              </div>
              <button v-if="!navOn" type="button" data-testid="nav-start" @click="startNav">开始导航（演示）</button>
              <button v-else type="button" class="nav-stop" @click="stopNav">结束导航</button>
            </article>
          </div>
        </div>
        <section class="map-support-grid">
          <article><i>查</i><div><b>点位状态核验</b><p>地图优先展示设施开放、维护和距离信息；正式点位需经主管单位确认。</p></div><span>4 个演示点位</span></article>
          <article><i>行</i><div><b>到达前先确认</b><p>开放时间和现场状态可能变化，导航只提供方向参考，不作为现实吸烟许可。</p></div><span>安全出行提示</span></article>
          <article><i>报</i><div><b>发现异常可反馈</b><p>设施满溢、破损或周边存在卫生问题时，可通过安全上报生成治理线索。</p></div><button type="button" @click="switchTab('report')">去反馈 →</button></article>
        </section>
      </div>

      <!-- ================= 安全上报 ================= -->
      <div v-else-if="activeTab === 'report'" class="portal-page report-page">
        <header class="page-heading"><span>SAFE REPORT</span><h1>安全提交线索</h1><p>不要为了取证跟拍、拦截或靠近陌生人。不能确认人物身份时，线索仍可用于清理和热点治理。</p></header>

        <div v-if="reportStep === 1" class="report-workspace">
          <section class="report-form">
            <div class="form-section"><span>01</span><div><h2>选择线索类型</h2><div class="choice-row"><button v-for="item in ['行为视频线索','现场卫生照片']" :key="item" type="button" :class="{ active: reportType === item }" @click="reportType = item">{{ item }}</button></div></div></div>
            <div class="form-section"><span>02</span><div><h2>添加素材并智能预检</h2><label class="upload-zone" :class="`inspect-${mediaInspection.status}`"><input type="file" :accept="reportType.includes('视频') ? 'video/*' : 'image/*'" @change="onFile" /><i>{{ mediaInspection.status === 'checking' ? '…' : fileName ? '✓' : '＋' }}</i><b>{{ fileName || (reportType.includes('视频') ? '录制或上传短视频' : '拍摄或上传现场照片') }}</b><small>支持格式检查、画面质量检查和场景相关性预检</small></label><div class="inline-inspection" :class="mediaInspection.status"><b>{{ mediaInspection.title }}</b><p>{{ mediaInspection.detail }}</p><em v-if="mediaInspection.confidence">候选置信度 {{ mediaInspection.confidence }}%</em></div><AiReportCard :report="aiReport" :state="aiState" :elapsed="aiElapsed" :error="aiError" @retry="retryAiInspect" /></div></div>
            <div class="form-section"><span>03</span><div><h2>确认地点</h2><input v-model="location" class="location-input" /><small class="field-note">当前位置为演示值，可以手动修改</small></div></div>
            <div class="form-section"><span>04</span><div><h2>安全与隐私确认</h2><label class="safety-check"><input v-model="safeConfirmed" type="checkbox" /><span>我确认素材不是通过跟拍、拦截、争执等危险方式取得，也不会在公开平台传播他人画面。</span></label></div></div>
            <p v-if="reportError" class="report-error" role="alert">{{ reportError }}</p>
            <button class="report-submit" type="button" :disabled="submitting" @click="submitReport">{{ submitting ? '提交中…' : '提交演示线索' }} <span>→</span></button>
          </section>
          <aside class="report-aside">
            <section class="report-boundary"><span>先保护自己，再提供线索</span><h2>平台会做什么？</h2><ol><li><b>1</b>检查素材格式与隐私风险</li><li><b>2</b>生成候选动作或现场线索</li><li><b>3</b>授权人员人工复核</li><li><b>4</b>转为清理、巡查或协同线索</li></ol><p>AI结果不会自动触发处罚。</p></section>
            <section class="aside-result" :class="mediaInspection.status"><header><span>AI 报告怎么读</span><i>口径说明</i></header><h3>候选线索，不是处罚结论</h3><p>模型只标出疑似目标与置信度，动作过程需要连续视频与人工复核。若你不同意这次判断，可在「治理进度」里提交反馈，会同步到管理端。</p><div class="result-scale"><span :style="{ width: `${mediaInspection.confidence || 0}%` }"></span></div></section>
            <section class="aside-tips"><h3>合格素材建议</h3><ul><li>画面包含现场环境和烟蒂位置</li><li>视频保持连续，不剪辑关键动作</li><li>不要追拍、拦截或公开传播他人画面</li><li>选错文件时系统会阻止提交并提醒更换</li></ul></section>
          </aside>
        </div>

        <section v-else class="submit-success">
          <div class="success-mark">✓</div><span>{{ submittedNo ? '提交成功 · 已生成上报编号' : '提交成功 · 本地演示' }}</span><h2>线索已进入隐私检查</h2><p v-if="submittedNo">你的上报编号为 <code>{{ submittedNo }}</code>。可在「治理进度」中查看受理与处置状态。</p><p v-else>你的演示编号为 <code>XZ-DEMO-270928</code>。当前为本地演示模式，不会真实上传文件或发送给任何单位。</p>
          <div class="success-actions"><button type="button" @click="switchTab('records')">查看处理进度</button><button type="button" @click="reportStep = 1; fileName = ''; safeConfirmed = false; submittedNo = ''">再提交一条</button></div>
        </section>
      </div>

      <!-- ================= 治理进度 ================= -->
      <div v-else-if="activeTab === 'records'" class="portal-page records-page">
        <header class="page-heading"><span>MY RECORDS</span><h1>治理进度</h1><p>这里只展示当前账户提交的线索。身份、原始素材和精确轨迹不会向其他普通用户公开。</p></header>

        <template v-if="citizen.apiMode">
          <section v-for="r in citizen.reports" :key="r.report_no" class="record-card" :class="{ featured: r.status === 'finished' }">
            <header>
              <div><span>{{ r.kind_label }}</span><code>{{ r.report_no }}</code></div>
              <b :class="{ reviewing: r.status !== 'finished' }">{{ r.status_label }}</b>
            </header>
            <div class="record-meta">
              <span><small>提交时间</small>{{ fmtDateTime(r.submitted_at) }}</span>
              <span><small>区域</small>{{ r.location }}</span>
              <span><small>去向</small>{{ r.event_id ? '已转为处置事件' : '等待分析' }}</span>
            </div>
            <ol v-if="r.timeline.length" class="progress-line">
              <li v-for="t in r.timeline" :key="t.key" class="done">
                <i>✓</i><b>{{ t.label }}</b><small>{{ fmtTime(t.ts) }}</small>
              </li>
            </ol>
            <div v-if="r.public_reply" class="result-note"><b>处理说明</b><p>{{ r.public_reply }}</p></div>
            <div v-if="r.reject_reason" class="result-note"><b>不予受理原因</b><p>{{ r.reject_reason }}</p></div>

            <!-- 提交时当场生成的 AI 报告快照：这里可回看，并可对模型判断提出异议 -->
            <AiReportCard v-if="r.ai_report" :report="toAiReport(r.ai_report)" state="done" compact />
            <div class="ai-feedback">
              <template v-if="feedbackSubmitted(r.report_no, r.ai_feedback)">
                <b>已提交 AI 反馈</b>
                <p>{{ r.ai_feedback?.agree ? '你认可了这一次模型判断。' : `你提出了异议：${r.ai_feedback?.reason || '（已转人工复核）'}` }}</p>
              </template>
              <template v-else>
                <b>对 AI 判断有异议？</b>
                <p>模型只做候选判定。如果这次判断不对，写下理由后会转人工复核，并同步到管理端。</p>
                <textarea
                  v-model="feedbackDraft[r.report_no]"
                  rows="2"
                  placeholder="例如：画面里只是路边的烟蒂设施，并没有抛掷动作"
                ></textarea>
                <div class="fb-acts">
                  <button type="button" :disabled="feedbackBusy === r.report_no" @click="sendAiFeedback(r.report_no, false)">
                    {{ feedbackBusy === r.report_no ? '提交中…' : '我不同意' }}
                  </button>
                  <button type="button" class="ghost" :disabled="feedbackBusy === r.report_no" @click="sendAiFeedback(r.report_no, true)">
                    判断合理
                  </button>
                </div>
                <p v-if="feedbackError" class="fb-err">{{ feedbackError }}</p>
              </template>
            </div>
          </section>
          <p v-if="!citizen.reports.length" class="field-note">
            {{ citizen.loadingReports ? '正在读取上报记录…' : '当前账户暂无上报记录。' }}
          </p>
        </template>

        <section v-if="!citizen.apiMode" class="record-card featured">
          <header><div><span>模拟事件</span><code>XZ-DEMO-260917</code></div><b>已完成清理</b></header>
          <div class="record-meta"><span><small>提交时间</small>09月17日 09:12</span><span><small>区域</small>浉河区 · 演示点位</span><span><small>去向</small>环境清理</span></div>
          <ol class="progress-line"><li class="done"><i>✓</i><b>已提交</b><small>09:12</small></li><li class="done"><i>✓</i><b>已研判</b><small>09:26</small></li><li class="done"><i>✓</i><b>已接单</b><small>09:33</small></li><li class="done"><i>✓</i><b>已清理</b><small>09:48</small></li></ol>
          <div class="result-note"><b>处理说明</b><p>该素材不足以确认个人身份，未进入执法流程；现场烟蒂已转交网格作业人员完成清理。</p></div>
          <AiReportCard :report="DEMO_AI_REPORT" state="done" compact />
          <div class="ai-feedback">
            <template v-if="feedbackSubmitted('XZ-DEMO-260917')">
              <b>已提交 AI 反馈</b>
              <p>你提出了异议，已转人工复核。</p>
            </template>
            <template v-else>
              <b>对 AI 判断有异议？</b>
              <p>模型只做候选判定。本次为本地演示模式，反馈只在前端记录，不会真实提交。</p>
              <textarea v-model="feedbackDraft['XZ-DEMO-260917']" rows="2" placeholder="例如：画面里只是路边的烟蒂设施，并没有抛掷动作"></textarea>
              <div class="fb-acts">
                <button type="button" @click="sendAiFeedback('XZ-DEMO-260917', false)">我不同意</button>
                <button type="button" class="ghost" @click="sendAiFeedback('XZ-DEMO-260917', true)">判断合理</button>
              </div>
              <p v-if="feedbackError" class="fb-err">{{ feedbackError }}</p>
            </template>
          </div>
        </section>
        <section v-if="!citizen.apiMode" class="record-card"><header><div><span>模拟事件</span><code>XZ-DEMO-260903</code></div><b class="reviewing">人工复核中</b></header><div class="record-meta"><span><small>提交时间</small>09月03日 17:40</span><span><small>区域</small>羊山新区 · 演示点位</span><span><small>去向</small>等待研判</span></div></section>
      </div>

      <!-- ================= 任务中心（积分 + 排行） ================= -->
      <div v-else-if="activeTab === 'tasks'" class="portal-page tasks-page">
        <header class="simple-page-head"><h1>任务中心</h1><p>完成文明学习与公共空间打卡，积累个人文明贡献。</p></header>

        <section class="task-summary">
          <div class="task-ring"><strong>{{ points }}</strong><small>我的文明积分</small></div>
          <div class="task-summary-copy">
            <b>本周排名 第 {{ myRank }} 名</b>
            <span>{{ taskDone ? '今日打卡已完成，继续保持' : '今日还未打卡，去附近吸烟区完成打卡' }}</span>
            <button type="button" data-testid="checkin-summary" :disabled="taskDone" @click="doCheckIn">{{ taskDone ? '已打卡' : '立即打卡' }}</button>
          </div>
          <img class="task-summary-img" src="/media/coins.png" alt="文明积分" />
        </section>

        <div class="tasks-columns">
          <section class="task-list-card">
            <h2>每日任务</h2>
            <article>
              <span class="task-check" :class="{ done: taskDone }">{{ taskDone ? '✓' : '!' }}</span>
              <div><b>文明打卡 · 到合规吸烟区</b><p>现场打卡，传递文明吸烟习惯</p></div>
              <em>+5</em>
              <button type="button" data-testid="checkin-row" :disabled="taskDone" @click="doCheckIn">{{ taskDone ? '已打卡' : '立即打卡' }}</button>
            </article>
            <article>
              <span class="task-check" :class="{ done: readIds.includes(5) }">{{ readIds.includes(5) ? '✓' : '!' }}</span>
              <div><b>情景问答 · 照片能定责吗</b><p>了解照片、视频与行为证据的区别</p></div>
              <em>+5</em>
              <button type="button" @click="switchTab('science')">去完成</button>
            </article>
            <article>
              <span class="task-check" :class="{ done: readIds.length >= 2 }">{{ readIds.length >= 2 ? '✓' : '!' }}</span>
              <div><b>学习两篇科普文章</b><p>当前已完成 {{ readIds.length }} / 2</p></div>
              <em>+3/篇</em>
              <button type="button" @click="switchTab('science')">去学习</button>
            </article>
            <article>
              <span class="task-check" :class="{ done: fileName !== '' }">{{ fileName ? '✓' : '!' }}</span>
              <div><b>认识一次安全上报流程</b><p>了解素材授权、隐私检查和人工复核</p></div>
              <em>+2</em>
              <button type="button" @click="switchTab('report')">去了解</button>
            </article>
            <article>
              <span class="task-check">!</span>
              <div><b>检查附近设施开放状态</b><p>查看最近点位，出行前确认维护状态</p></div>
              <em>+2</em>
              <button type="button" @click="switchTab('map')">去查看</button>
            </article>
          </section>

          <section class="rank-card">
            <h2>本周积分排行</h2>
            <ol class="rank-list">
              <li v-for="(r, i) in weeklyRank" :key="r.name" :class="{ me: r.me, top: i < 3 }">
                <span class="rank-no">{{ i + 1 }}</span>
                <span class="rank-name">{{ r.name }}</span>
                <em>{{ r.score }} 分</em>
              </li>
            </ol>
            <p class="rank-note">排行榜与积分仅用于演示学习反馈，不对应现金、处罚结果或现实权益。</p>
          </section>
        </div>

        <section class="ledger-card">
          <h2>积分明细</h2>
          <ul>
            <li v-for="(l, i) in ledger.slice(0, 6)" :key="i">
              <span>{{ l.label }}</span><em>+{{ l.delta }}</em><small>{{ l.time }}</small>
            </li>
          </ul>
        </section>
      </div>

      <!-- ================= 科普（三人群统筹） ================= -->
      <div v-else-if="activeTab === 'science'" class="portal-page science-page" :class="`aud-${audience}`">
        <header class="simple-page-head">
          <h1>文明科普</h1>
          <p>同一批知识，按不同人群的阅读习惯统筹编排。</p>
        </header>

        <!-- 人群切换 -->
        <div class="audience-bar" role="tablist" aria-label="选择适合人群">
          <button
            v-for="a in AUDIENCES"
            :key="a.key"
            type="button"
            role="tab"
            :aria-selected="audience === a.key"
            :class="{ on: audience === a.key }"
            @click="audience = a.key"
          >
            <b>{{ a.label }}</b>
            <small>{{ a.hint }}</small>
          </button>
        </div>

        <!-- 长者模式：常驻朗读条（整页连读 / 暂停-继续 / 停止 / 语速） -->
        <section v-if="audience === 'senior'" class="speak-bar">
          <div class="sb-lead">
            <i :class="{ live: isSpeaking && !speechPaused }">🔊</i>
            <div>
              <b>语音朗读</b>
              <small>
                {{ speechSupported
                  ? (isSpeaking
                      ? (speechPaused ? '已暂停 · 点「继续」接着听' : '正在朗读，可随时暂停或改语速')
                      : '点右侧「朗读本页」可把当前列表从头念一遍')
                  : speechMessage }}
              </small>
            </div>
          </div>
          <div class="sb-acts">
            <button type="button" :disabled="!speechSupported" @click="readPageAloud">朗读本页</button>
            <button type="button" :disabled="!isSpeaking" @click="toggleSpeechPause">
              {{ speechPaused ? '继续' : '暂停' }}
            </button>
            <button type="button" :disabled="!isSpeaking" @click="stopSpeech">停止</button>
            <button type="button" class="sb-rate" :disabled="!speechSupported" @click="cycleSpeechRate">
              语速 {{ RATE_LABEL[speechRate] ?? speechRate + '×' }}
            </button>
          </div>
        </section>

        <!-- 搜索 -->
        <label class="sci-search">
          <span>⌕</span>
          <input v-model="sciSearch" type="search" placeholder="搜索烟头危害、火灾安全、城市环保" />
        </label>

        <!-- 近期新闻 -->
        <section v-if="!sciSearch && sciCategory === '全部'" class="news-section">
          <h2 class="block-title">近期新闻</h2>
          <div class="news-grid">
            <article
              v-for="(n, i) in NEWS_BY_AUDIENCE[audience]"
              :key="`${audience}-${i}`"
              :class="{ 'is-reading': speakingId === `news-${audience}-${i}` }"
            >
              <img :src="n.cover" :alt="n.title" />
              <div>
                <h3>{{ n.title }}</h3>
                <p>{{ n.desc }}</p>
                <div class="card-foot">
                  <small>{{ n.meta }}</small>
                  <button
                    v-if="audience === 'senior'"
                    type="button"
                    class="speak-btn mini"
                    :disabled="!speechSupported"
                    @click="readNewsAloud(n, i)"
                  >🔊 朗读</button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <!-- 互动剧情：烟的一生（用户自行选择结局，见 components/citizen/SmokeStory.vue） -->
        <SmokeStory
          :senior="audience === 'senior'"
          :speaking-id="speakingId"
          :speech-supported="speechSupported"
          :nickname="citizen.profile?.displayName ?? '热心市民'"
          @earn="earn"
          @speak="speakSegment"
        />

        <!-- 分类 -->
        <div class="sci-categories">
          <button
            v-for="c in SCI_CATEGORIES"
            :key="c"
            type="button"
            :class="{ on: sciCategory === c }"
            @click="sciCategory = c"
          >{{ c }}</button>
        </div>

        <!-- 文章列表 -->
        <div class="sci-list">
          <article
            v-for="a in filteredArticles"
            :key="a.id"
            class="sci-article"
            :class="{ 'is-reading': speakingId === `article-${a.id}` }"
          >
            <img v-if="a.cover" class="sci-cover" :src="a.cover" :alt="a.title" />
            <div v-else class="sci-cover tile" :class="`cat-${a.category}`">{{ a.category.slice(0, 2) }}</div>
            <div class="sci-body">
              <h3>{{ a.title }}</h3>
              <p>{{ audience === 'senior' && a.seniorDesc ? a.seniorDesc : a.desc }}</p>
              <div v-if="audience === 'youth' && a.dataPoint" class="data-chip">数据 · {{ a.dataPoint }}</div>

              <!-- 互动问答 -->
              <div v-if="a.quiz" class="quiz-box">
                <template v-if="quizPicked[a.id] === undefined">
                  <button v-for="(opt, oi) in a.quiz.options" :key="oi" type="button" @click="pickQuiz(a, oi)">{{ opt }}</button>
                </template>
                <p v-else :class="quizPicked[a.id] === a.quiz?.answer ? 'quiz-right' : 'quiz-wrong'">
                  {{ quizPicked[a.id] === a.quiz?.answer ? '✓ 回答正确 ' : '✗ 再想想 ' }}{{ a.quiz.explain }}
                </p>
              </div>

              <div class="sci-meta">
                <span class="sci-cat">{{ a.category }}</span>
                <small>{{ a.minutes }}分钟 · 学习+{{ a.points }}积分</small>
                <button
                  v-if="audience === 'senior'"
                  type="button"
                  class="speak-btn"
                  :disabled="!speechSupported"
                  :title="speechSupported ? '朗读这篇（再点一次重新朗读）' : speechMessage"
                  @click="readArticleAloud(a)"
                >🔊 朗读</button>
                <button type="button" class="read-btn" :disabled="readIds.includes(a.id)" @click="readArticle(a)">
                  {{ readIds.includes(a.id) ? '已学习 ✓' : '学习本文' }}
                </button>
              </div>
            </div>
          </article>
          <p v-if="!filteredArticles.length" class="field-note">没有匹配的内容，换个关键词试试。</p>
        </div>
      </div>

      <!-- ================= 我们 ================= -->
      <div v-else class="portal-page profile-page">
        <header class="profile-hero"><div class="profile-avatar">{{ citizen.profile?.displayName.slice(-2) }}</div><div><span>已登录账户</span><h1>{{ citizen.profile?.displayName }}</h1><p>{{ citizen.profile?.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') }} · {{ citizen.profile?.district }}</p></div></header>
        <section class="profile-stats">
          <div><strong>{{ points }}</strong><span>文明积分</span></div>
          <div><strong>2</strong><span>有效线索</span></div>
          <div><strong>{{ readIds.length + 3 }}</strong><span>完成学习</span></div>
        </section>
        <section class="profile-menu">
          <button type="button" @click="switchTab('tasks')"><span>我的积分与排行</span><i>→</i></button>
          <button type="button"><span>隐私与素材授权</span><i>→</i></button>
          <button type="button"><span>我的通知</span><em>2</em><i>→</i></button>
          <button type="button"><span>线索提交规则</span><i>→</i></button>
          <button type="button"><span>无障碍与减少动效</span><i>→</i></button>
        </section>
        <div class="account-boundary"><b>账户说明</b><p>后台授权角色可以依据职责查看举报人账户信息，但任何角色都不能查看你的明文密码。演示版本未接入真实实名认证。</p></div>
        <button class="logout-button" type="button" @click="logout">退出当前账户</button>
      </div>

      <!-- 手机 App 版底部导航：中间「监督拍照」最大最突出（对齐参考稿的信息层级） -->
      <nav class="mobile-nav app-tabbar" aria-label="市民端底部导航">
        <template v-for="t in APP_TABS" :key="t.key">
          <button
            v-if="t.key === 'capture'"
            type="button"
            class="app-capture"
            :class="{ on: appTabActive('capture') }"
            data-testid="app-capture"
            :aria-label="t.label"
            @click="tapCapture"
          >
            <i class="cam">
              <svg
                viewBox="0 0 24 24"
                width="26"
                height="26"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M4 8.5h3l1.4-2h7.2L17 8.5h3v9.5H4z" />
                <circle cx="12" cy="13.2" r="3.4" />
              </svg>
            </i>
            <span>{{ t.label }}</span>
          </button>
          <button
            v-else
            type="button"
            :class="{ on: appTabActive(t.key) }"
            :data-testid="`app-tab-${t.key}`"
            @click="tapTab(t.key)"
          >
            <i>{{ t.icon }}</i>
            <span>{{ t.label }}</span>
          </button>
        </template>
      </nav>
      <input
        ref="appCaptureRef"
        class="app-capture-input"
        type="file"
        accept="image/*"
        capture="environment"
        @change="onAppCapture"
      />
    </section>
  </EndShell>
</template>

<style scoped>
/* ============ 基础 ============ */
.citizen-app { --ink:#0b1320;--paper:#f4f6f9;--paper2:#ffffff;--line:#e7ebf1;--ember:#ff6847;--cyan:#38c8d4;--moss:#3e9b72;--gold:#f0a92e;--blue:#2f7cf6; display:flex;flex-direction:column;width:100%;height:100vh;overflow:hidden;color:var(--ink);background:var(--paper);font-family:"Noto Sans SC","Microsoft YaHei",system-ui,sans-serif; }
.portal-shell { min-height:100%;overflow:visible; }
.mobile-header,.mobile-nav { display:none; }
.demo-banner { position:relative;z-index:1;display:flex;gap:10px;align-items:center;min-height:34px;margin:0 20px;padding:6px 22px;color:#74451d;background:#fff0c9;font-size:12px; }
.demo-banner span { padding:2px 5px;color:#fff;background:#936213;font:9px Consolas,monospace; }
.portal-page { width:100%;max-width:none;margin:0 auto;padding:24px 20px; }
.citizen-app :deep(.es-main) { padding-left:0;padding-right:0; }
.citizen-brand-row { display:flex;gap:12px;align-items:center;margin-bottom:14px; }
.citizen-brand-mark { display:grid;place-items:center;width:40px;height:40px;border-radius:12px;color:#fff;font-size:20px;background:linear-gradient(135deg,#20b26b,#177e68); }
.citizen-brand-row h1 { margin:0;color:#17283e;font-size:21px;letter-spacing:.02em; }
.citizen-brand-row p { margin:3px 0 0;color:#8a94a3;font-size:11px; }
.section-title { display:flex;align-items:center;justify-content:space-between;margin-bottom:12px; }
.section-title > span { position:relative;padding-left:12px;color:#1c2d44;font-size:15px;font-weight:700; }
.section-title > span::before { content:'';position:absolute;left:0;top:50%;width:4px;height:16px;transform:translateY(-50%);border-radius:2px;background:linear-gradient(180deg,#2f7cf6,#38c8d4); }
.section-title button,.section-title small { border:0;background:transparent;color:#2f7cf6;font-size:12px;cursor:pointer; }
.block-title { position:relative;margin:22px 0 12px;padding-left:12px;color:#1c2d44;font-size:15px;font-weight:700; }
.block-title::before { content:'';position:absolute;left:0;top:50%;width:4px;height:16px;transform:translateY(-50%);border-radius:2px;background:linear-gradient(180deg,#2f7cf6,#38c8d4); }

/* ============ 轮播图 ============ */
.home-carousel { position:relative;height:clamp(190px,26vw,300px);overflow:hidden;border-radius:17px;box-shadow:0 8px 22px rgba(37,99,157,.13); }
.carousel-track { display:flex;height:100%;transition:transform .55s cubic-bezier(.33,.9,.35,1); }
.carousel-slide { position:relative;flex:0 0 100%;height:100%; }
.carousel-slide img { width:100%;height:100%;object-fit:cover;object-position:center 62%; }
.slide-shade { position:absolute;inset:0;background:linear-gradient(92deg,rgba(8,38,66,.72) 0%,rgba(10,55,92,.42) 42%,rgba(12,80,120,0) 74%); }
.slide-copy { position:absolute;left:clamp(18px,4vw,42px);top:50%;transform:translateY(-50%);max-width:60%;color:#fff; }
.slide-tag { display:inline-block;padding:4px 11px;border-radius:999px;background:var(--ember);font-size:11px;letter-spacing:.05em; }
.slide-copy h2 { margin:12px 0 8px;font-size:clamp(20px,2.6vw,30px);line-height:1.25;letter-spacing:.01em;text-shadow:0 2px 10px rgba(0,20,40,.35); }
.slide-copy p { margin:0;color:rgba(255,255,255,.92);font-size:clamp(11px,1.2vw,13px); }
.carousel-arrow { position:absolute;top:50%;transform:translateY(-50%);z-index:3;width:32px;height:32px;border:0;border-radius:50%;background:rgba(255,255,255,.92);color:#22364d;font-size:19px;line-height:1;box-shadow:0 2px 8px rgba(20,50,80,.2);cursor:pointer; }
.carousel-arrow.left { left:12px; }
.carousel-arrow.right { right:12px; }
.carousel-dots { position:absolute;left:50%;bottom:12px;transform:translateX(-50%);z-index:3;display:flex;gap:7px; }
.carousel-dots button { width:7px;height:7px;padding:0;border:0;border-radius:999px;background:rgba(255,255,255,.55);cursor:pointer;transition:width .25s,background .25s; }
.carousel-dots button.on { width:18px;background:#fff; }

/* ============ 快捷入口 ============ */
.quick-grid { display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:16px;padding:16px 10px 12px;border:1px solid var(--line);border-radius:17px;background:var(--paper2);box-shadow:0 7px 22px rgba(39,72,111,.055); }
.quick-grid > button { display:flex;min-height:76px;flex-direction:column;align-items:center;justify-content:center;gap:8px;border:0;border-radius:13px;background:transparent;cursor:pointer;transition:background .16s,transform .16s; }
.quick-grid > button:hover { background:#f1f7fd;transform:translateY(-1px); }
.quick-symbol { display:grid;place-items:center;width:48px;height:48px;border-radius:15px;color:#fff;font-size:21px; }
.quick-symbol.blue { background:linear-gradient(135deg,#2f7cf6,#38a2f6); }
.quick-symbol.green { background:linear-gradient(135deg,#27b56d,#4ecf8a); }
.quick-symbol.orange { background:linear-gradient(135deg,#ff8a3c,#ffab5e); }
.quick-symbol.yellow { background:linear-gradient(135deg,#f0a92e,#f7c65b); }
.quick-symbol.teal { background:linear-gradient(135deg,#17b8c4,#4fd4dd); }
.quick-grid b { color:#22344b;font-size:13px;font-weight:600; }
.my-latest { margin-top:16px;padding:15px 16px;border:1px solid var(--line);border-radius:17px;background:#fff;box-shadow:0 7px 22px rgba(39,72,111,.055); }
.latest-row { display:flex;align-items:center;gap:12px;width:100%;padding:12px 14px;border:1px solid #d9e9df;border-radius:13px;background:linear-gradient(105deg,#f2fbf6,#f7fbff);text-align:left;cursor:pointer; }
.status-icon { display:grid;place-items:center;flex:0 0 34px;width:34px;height:34px;border-radius:10px;color:#fff;background:linear-gradient(135deg,#27b56d,#4ecf8a);font-weight:800; }
.latest-row > div { flex:1;min-width:0; }
.latest-row b { display:block;color:#22344b;font:700 13px Consolas,monospace; }
.latest-row small { display:block;margin-top:3px;color:#8a94a3;font-size:11px; }
.latest-row em { padding:4px 10px;border-radius:999px;color:#1d8a52;background:#e0f5e9;font-size:11px;font-style:normal;font-weight:700; }
.latest-row > i { color:#5f7894;font-style:normal; }

/* ============ 首页双卡 ============ */
.home-grid { display:grid;grid-template-columns:1.15fr .85fr;gap:16px;margin-top:16px;align-items:stretch; }
.home-side { display:grid;gap:16px;grid-template-rows:auto auto 1fr;min-width:0; }
.nearby-card,.task-card,.knowledge-card,.service-card { border:1px solid var(--line);border-radius:17px;background:var(--paper2);box-shadow:0 7px 22px rgba(39,72,111,.055);padding:16px; }
.nearby-card { display:flex;flex-direction:column; }
.nearby-map { margin-bottom:10px; }
.poi-list { display:grid;gap:8px; }
.poi-row { display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border:1px solid transparent;border-radius:12px;background:#f7fafc;text-align:left;cursor:pointer;transition:border-color .15s,background .15s; }
.poi-row.active,.poi-row:hover { border-color:#bcd6f5;background:#eef5ff; }
.poi-main { min-width:0; }
.poi-main b { display:block;color:#22344b;font-size:13px; }
.poi-main small { display:block;margin-top:2px;color:#8a94a3;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.poi-side { flex:none;text-align:right; }
.poi-side em { color:#f08c1e;font-size:12px;font-weight:700;font-style:normal; }
.poi-tags { display:inline-flex;gap:5px;margin-top:4px; }
.poi-tags i { padding:2px 7px;border-radius:999px;font-size:10px;font-style:normal; }
.poi-tags i.open { color:#1d8a52;background:#dff3e8; }
.poi-tags i.closed { color:#98a2ae;background:#eef1f4; }
.poi-tags i.task { color:#d9641e;background:#ffe9d9; }
.facility-guide { display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:11px; }
.facility-guide span { display:grid;grid-template-columns:30px 1fr;gap:1px 8px;padding:10px;border-radius:11px;background:#f4f8fc; }
.facility-guide i { grid-row:1/3;display:grid;place-items:center;width:30px;height:30px;border-radius:9px;color:#16845b;background:#e5f6ee;font-size:11px;font-style:normal;font-weight:800; }
.facility-guide b { color:#32445a;font-size:11px; }
.facility-guide small { color:#929eac;font-size:9.5px; }
.nearby-insight { margin-top:auto;padding-top:16px; }
.nearby-insight header { display:flex;align-items:center;justify-content:space-between;padding:12px 13px;border-radius:11px;background:linear-gradient(110deg,#edf7ff,#eefaf5); }
.nearby-insight header b,.nearby-insight header small { display:block; }
.nearby-insight header b { color:#2d435b;font-size:12px; }
.nearby-insight header small { margin-top:3px;color:#8d9aa9;font-size:9px; }
.nearby-insight header em { color:#3286c8;font-size:9px;font-style:normal; }
.insight-row { display:grid;grid-template-columns:76px 1fr 42px;align-items:center;gap:9px;margin-top:11px;color:#718096;font-size:10px; }
.insight-row > i { height:7px;overflow:hidden;border-radius:7px;background:#e7edf3; }
.insight-row > i b { display:block;height:100%;border-radius:7px;background:linear-gradient(90deg,#2988f0,#35bd8b); }
.insight-row strong { color:#40546b;text-align:right;font-size:10px; }
.nearby-insight > p { margin-top:12px;padding:10px 12px;border-left:3px solid #31b594;background:#f5faf8;color:#8190a0;font-size:9.5px;line-height:1.65; }
.nearby-insight > p span { margin-right:7px;color:#198564;font-weight:800; }
.service-card { display:flex;flex-direction:column;gap:13px; }
.service-stats { display:grid;grid-template-columns:repeat(3,1fr);gap:8px; }
.service-stats span { padding:10px 8px;border-radius:11px;background:linear-gradient(145deg,#f2f8ff,#f5fbf8);text-align:center; }
.service-stats b { display:block;color:#177ed1;font-size:20px;line-height:1.1; }
.service-stats b em { margin-left:2px;font-size:9px;font-style:normal;font-weight:600; }
.service-stats small { display:block;margin-top:5px;color:#8593a5;font-size:9px; }
.service-feed { display:grid;gap:8px;margin:auto 0 0;padding:0;list-style:none; }
.service-feed li { display:flex;align-items:center;gap:9px;padding-top:8px;border-top:1px dashed #dce8f1; }
.service-feed i { display:grid;place-items:center;width:25px;height:25px;border-radius:8px;background:#eaf3ff;color:#247be8;font-size:10px;font-style:normal;font-weight:800; }
.service-feed i.done { color:#188a60;background:#e5f7ef; }
.service-feed i.warn { color:#d98a18;background:#fff3dd; }
.service-feed div { min-width:0; }
.service-feed b,.service-feed small { display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.service-feed b { color:#31435a;font-size:10.5px; }
.service-feed small { margin-top:2px;color:#96a1af;font-size:9px; }
.poi-tags.big i { font-size:11px; }
.task-body { display:flex;align-items:center;gap:12px; }
.task-copy { flex:1;min-width:0; }
.task-copy h2 { margin:0;color:#22344b;font-size:17px; }
.task-copy p { margin:6px 0 12px;color:#7d8999;font-size:12px;line-height:1.6; }
.task-copy button { padding:8px 22px;border:0;border-radius:999px;color:#fff;background:linear-gradient(100deg,#ff8a3c,#ffab5e);font-size:13px;cursor:pointer; }
.task-copy button:disabled { background:#c9d2db;cursor:default; }
.task-coins { flex:none;width:96px;height:96px;object-fit:cover;border-radius:14px; }
.knowledge-card { min-height:0; }
.knowledge-card ul { display:grid;gap:0;margin:0;padding:0;list-style:none; }
.knowledge-card li { display:flex;gap:11px;padding:11px 0;border-bottom:1px dashed var(--line); }
.knowledge-card li:last-child { border-bottom:0; }
.knowledge-card li > i { display:grid;place-items:center;flex:0 0 30px;width:30px;height:30px;border-radius:9px;color:#fff;background:linear-gradient(135deg,#216eff,#4baedb);font:700 10px Consolas,monospace; }
.knowledge-card li div { min-width:0; }
.knowledge-card li b { color:#22344b;font-size:13px; }
.knowledge-card li p { margin:3px 0 0;color:#7d8999;font-size:11.5px;line-height:1.55; }

/* ============ 地图页 ============ */
.page-heading { margin-bottom:18px; }
.page-heading span { color:var(--ember);font:11px Consolas,monospace;letter-spacing:.14em; }
.page-heading h1 { margin:8px 0;color:#17283e;font-size:clamp(24px,2.6vw,34px); }
.page-heading p { max-width:640px;margin:0;color:#7d8999;font-size:13px;line-height:1.7; }
.map-layout { display:grid;grid-template-columns:minmax(0,1.35fr) minmax(360px,.85fr);gap:16px;align-items:stretch; }
.citizen-map { position:relative;min-width:0;height:480px;overflow:hidden;border-radius:15px; }
.map-disclaimer { position:absolute;z-index:2;left:12px;top:12px;padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.92);color:#936213;font-size:11px;box-shadow:0 2px 8px rgba(20,50,80,.12); }

/* ---- 演示导航面板：贴在地图右侧，竖排 ----
   放底部会把 480px 高的地图遮掉一大半，路线就看不见了；
   竖排贴右边能同时容纳"路线 + 分步指引"。 */
.nav-panel { position:absolute;right:12px;top:12px;bottom:12px;z-index:6;display:flex;flex-direction:column;width:272px;padding:14px 16px;border-radius:16px;background:rgba(255,255,255,.96);box-shadow:0 14px 32px rgba(20,50,80,.24);backdrop-filter:blur(10px); }
.nav-panel header { display:flex;align-items:flex-start;justify-content:space-between;gap:10px; }
.nav-panel header b { display:block;color:#17283e;font-size:14px; }
.nav-panel header small { display:block;margin-top:4px;color:#7d8999;font-size:11.5px; }
.nav-demo { flex:none;padding:3px 9px;border-radius:999px;background:#e7f0ff;color:#216eff;font-size:10px;font-weight:700; }
.nav-bar { height:5px;margin:11px 0 12px;overflow:hidden;border-radius:5px;background:#e6edf4; }
.nav-bar i { display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#0f8bff,#2bc2a0);transition:width .12s linear; }
.nav-steps { flex:1;min-height:0;display:grid;align-content:start;gap:6px;margin:0 0 12px;padding:0;list-style:none;overflow:auto; }
.nav-steps li { display:flex;gap:8px;align-items:center;padding:6px 9px;border-radius:9px;background:#f6f9fc;color:#7d8999;font-size:11.5px; }
.nav-steps li i { flex:none;width:7px;height:7px;border-radius:50%;background:#c3ccd6; }
.nav-steps li.done { color:#5b6b7d; }
.nav-steps li.done i { background:#2bab7c; }
.nav-steps li.on { background:#e7f0ff;color:#216eff;font-weight:700; }
.nav-steps li.on i { background:#216eff; }
.nav-acts { display:flex;gap:8px;flex:none; }
.nav-acts button { flex:1;padding:8px 14px;border:0;border-radius:999px;background:linear-gradient(100deg,#216eff,#4baedb);color:#fff;font-size:12.5px;cursor:pointer; }
.nav-acts button.ghost { background:#eef2f6;color:#5b6b7d; }
.nav-note { flex:none;margin:10px 0 0;color:#9aa6b3;font-size:10.5px;line-height:1.6; }
.selected-place > button.nav-stop { background:linear-gradient(100deg,#f0803c,#f0a92e); }
.point-list { display:flex;min-width:0;height:480px;flex-direction:column;gap:8px; }
.point-list > button { display:flex;align-items:center;gap:10px;padding:11px 12px;border:1px solid var(--line);border-radius:12px;background:#fff;text-align:left;cursor:pointer; }
.point-list > button.active { border-color:#2f7cf6;background:#eef5ff; }
.point-list > button > span { color:#2f7cf6;font:700 12px Consolas,monospace; }
.point-list > button div { flex:1;min-width:0; }
.point-list > button b { display:block;color:#22344b;font-size:13px; }
.point-list > button small { display:block;margin-top:2px;color:#8a94a3;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
.selected-place { padding:16px !important; }
.selected-place h2 { margin:7px 0 6px !important;font-size:18px !important; }
.selected-place p { margin:0 0 10px !important;line-height:1.55 !important; }
.selected-place > button { margin-top:12px !important; }
.point-list > button em { flex:none;color:#f08c1e;font-size:11px;font-style:normal;font-weight:700; }
.selected-place { display:flex;flex:1;min-height:0;margin-top:6px;padding:16px;border:1px solid var(--line);border-radius:14px;background:#fff;flex-direction:column;justify-content:center; }
.selected-place small { color:#8a94a3;font-size:11px; }
.selected-place h2 { margin:6px 0;color:#1c2d44;font-size:18px; }
.selected-place p { margin:0 0 10px;color:#7d8999;font-size:12px;line-height:1.6; }
.selected-place > button { margin-top:10px;width:100%;padding:9px 0;border:0;border-radius:10px;color:#fff;background:linear-gradient(100deg,#216eff,#4baedb);font-size:13px;cursor:pointer; }
.map-support-grid { display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px; }
.map-support-grid article { display:grid;grid-template-columns:38px 1fr;gap:10px;padding:16px;border:1px solid var(--line);border-radius:15px;background:#fff;box-shadow:0 7px 22px rgba(39,72,111,.05); }
.map-support-grid article > i { grid-row:1/3;display:grid;place-items:center;width:38px;height:38px;border-radius:11px;color:#fff;background:linear-gradient(145deg,#287df3,#2bc2a0);font-style:normal;font-weight:800; }
.map-support-grid b { color:#263a52;font-size:13px; }
.map-support-grid p { margin-top:5px;color:#8290a1;font-size:10.5px;line-height:1.6; }
.map-support-grid article > span,.map-support-grid article > button { grid-column:2;margin-top:5px;justify-self:start;padding:5px 9px;border:0;border-radius:8px;background:#edf6ff;color:#247be8;font-size:10px; }

/* ============ 上报 / 记录（沿用既有版式） ============ */
.report-workspace { display:grid;grid-template-columns:1.5fr .8fr;gap:18px;align-items:start; }
.report-form { padding:22px;border:1px solid var(--line);border-radius:17px;background:var(--paper2);box-shadow:0 7px 22px rgba(39,72,111,.055); }
.form-section { display:flex;gap:16px;padding:16px 0;border-bottom:1px dashed var(--line); }
.form-section > span { color:#c3ccd6;font:700 18px Consolas,monospace; }
.form-section h2 { margin:0 0 10px;color:#1c2d44;font-size:15px; }
.choice-row { display:flex;gap:10px; }
.choice-row button { padding:8px 18px;border:1px solid var(--line);border-radius:999px;background:#fff;font-size:13px;cursor:pointer; }
.choice-row button.active { border-color:#2f7cf6;color:#2f7cf6;background:#eef5ff; }
.upload-zone { display:grid;place-items:center;gap:6px;min-height:120px;border:1.5px dashed #c9d6e4;border-radius:13px;background:#f8fbfd;cursor:pointer; }
.upload-zone input { display:none; }
.upload-zone i { color:#2f7cf6;font-size:26px;font-style:normal; }
.upload-zone b { color:#22344b;font-size:13px; }
.upload-zone small { color:#98a2ae;font-size:11px; }
.upload-zone.inspect-candidate { border-color:#5ac69a;background:#f0fbf6; }
.upload-zone.inspect-scene { border-color:#6fa7eb;background:#f2f7ff; }
.upload-zone.inspect-rejected { border-color:#ef9b92;background:#fff5f3; }
.inline-inspection { margin-top:10px;padding:11px 13px;border-radius:10px;background:#f3f7fb; }
.inline-inspection b { color:#42536a;font-size:11.5px; }
.inline-inspection p { margin:4px 0 0;color:#7d8999;font-size:10.5px;line-height:1.55; }
.inline-inspection em { display:block;margin-top:5px;color:#257fbc;font-size:10px;font-style:normal;font-weight:700; }
.inline-inspection.candidate { background:#edf9f3; }.inline-inspection.candidate b { color:#19845f; }
.inline-inspection.rejected { background:#fff0ee; }.inline-inspection.rejected b { color:#d45145; }
.location-input { width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;font-size:13px; }
.field-note { display:block;margin-top:6px;color:#98a2ae;font-size:11px; }
.safety-check { display:flex;gap:10px;align-items:flex-start;font-size:12.5px;line-height:1.7;color:#4a5768; }
.safety-check input { margin-top:3px;accent-color:var(--blue); }
.report-error { margin:14px 0 0;padding:10px 12px;border-radius:10px;color:#c0392b;background:#fdeceb;font-size:12.5px; }
.report-submit { position:relative;margin-top:18px;width:100%;padding:13px 0;border:0;border-radius:12px;color:#fff;background:linear-gradient(100deg,#216eff,#4baedb);font-size:14px;cursor:pointer;box-shadow:0 8px 24px rgba(33,110,255,.18); }
.report-aside { display:grid;gap:14px;align-content:start; }
.report-boundary { padding:22px;border-radius:17px;color:#e8eef5;background:linear-gradient(160deg,#12283f,#1b3a56); }
.report-boundary > span { color:var(--cyan);font:10px Consolas,monospace;letter-spacing:.14em; }
.report-boundary h2 { margin:10px 0 16px;font-size:18px; }
.report-boundary ol { display:grid;gap:12px;margin:0;padding:0;list-style:none; }
.report-boundary li { display:flex;gap:10px;align-items:center;font-size:12.5px;color:rgba(232,238,245,.85); }
.report-boundary li b { display:grid;place-items:center;width:22px;height:22px;border-radius:50%;color:#12283f;background:var(--cyan);font-size:11px; }
.report-boundary p { margin:16px 0 0;padding-top:14px;border-top:1px solid rgba(255,255,255,.14);color:rgba(232,238,245,.6);font-size:11.5px; }
.aside-result,.aside-tips { padding:18px;border:1px solid var(--line);border-radius:15px;background:#fff;box-shadow:0 7px 22px rgba(39,72,111,.04); }
.aside-result header { display:flex;justify-content:space-between;align-items:center; }
.aside-result header span { color:#8794a5;font-size:10px;letter-spacing:.1em; }
.aside-result header i { padding:3px 8px;border-radius:999px;color:#2f7cf6;background:#eaf2ff;font-size:9px;font-style:normal; }
.aside-result h3,.aside-tips h3 { margin:11px 0 6px;color:#293d55;font-size:14px; }
.aside-result p { margin:0;color:#7d8999;font-size:10.5px;line-height:1.65; }
.aside-result.rejected header i { color:#d45145;background:#fff0ee; }
.aside-result.candidate header i { color:#17845f;background:#e6f7ef; }
.result-scale { height:6px;margin-top:12px;overflow:hidden;border-radius:8px;background:#e8eef4; }
.result-scale span { display:block;height:100%;border-radius:8px;background:linear-gradient(90deg,#2f7cf6,#35bf8f);transition:width .4s; }
.aside-tips ul { display:grid;gap:8px;margin:10px 0 0;padding:0;list-style:none; }
.aside-tips li { position:relative;padding-left:17px;color:#68778a;font-size:10.5px;line-height:1.5; }
.aside-tips li::before { content:'✓';position:absolute;left:0;color:#2eaa79;font-weight:800; }
.submit-success { display:grid;place-items:center;gap:8px;max-width:520px;margin:40px auto;padding:44px 34px;border:1px solid var(--line);border-radius:20px;background:var(--paper2);text-align:center;box-shadow:0 7px 22px rgba(39,72,111,.055); }
.success-mark { display:grid;place-items:center;width:62px;height:62px;border-radius:50%;color:#fff;font-size:28px;background:linear-gradient(135deg,#27b56d,#4ecf8a); }
.submit-success span { margin-top:6px;color:#1d8a52;font-size:12px; }
.submit-success h2 { margin:2px 0;color:#1c2d44;font-size:21px; }
.submit-success p { margin:0;color:#7d8999;font-size:13px;line-height:1.7; }
.submit-success code { padding:2px 7px;border-radius:6px;background:#eef3f8;color:#216eff;font-family:Consolas,monospace; }
.success-actions { display:flex;gap:10px;margin-top:14px; }
.success-actions button { padding:9px 20px;border:0;border-radius:999px;font-size:13px;cursor:pointer; }
.success-actions button:first-child { color:#fff;background:linear-gradient(100deg,#216eff,#4baedb); }
.success-actions button:last-child { border:1px solid var(--line);color:#4a5768;background:#fff; }
.record-card { margin-bottom:14px;padding:18px 20px;border:1px solid var(--line);border-radius:17px;background:var(--paper2);box-shadow:0 7px 22px rgba(39,72,111,.055); }
.record-card.featured { border-color:#b7e3d2;background:linear-gradient(180deg,#f2fbf6,#fff); }
.record-card header { display:flex;justify-content:space-between;align-items:center; }
.record-card header span { margin-right:8px;padding:3px 9px;border-radius:999px;color:#216eff;background:#e7f0ff;font-size:11px; }
.record-card header code { color:#22344b;font-family:Consolas,monospace;font-size:13px; }
.record-card header b { color:#1d8a52;font-size:13px; }
.record-card header b.reviewing { color:#d98a1e; }
.record-meta { display:flex;gap:26px;margin:12px 0;flex-wrap:wrap; }
.record-meta small { display:block;margin-bottom:3px;color:#98a2ae;font-size:10.5px; }
.record-meta span { color:#37465a;font-size:12.5px; }
.progress-line { display:flex;gap:6px;margin:6px 0 0;padding:0;list-style:none;flex-wrap:wrap; }
.progress-line li { display:flex;gap:6px;align-items:center;padding:6px 12px;border-radius:999px;background:#eafaf1;font-size:12px; }
.progress-line li i { color:#1d8a52;font-style:normal; }
.progress-line li small { color:#6fa287; }
.result-note { margin-top:12px;padding:12px 14px;border-radius:12px;background:#f4f8fc; }
.result-note b { color:#37465a;font-size:12px; }
.result-note p { margin:5px 0 0;color:#62718a;font-size:12px;line-height:1.7; }

/* 对 AI 判断提出异议（市民反馈 → 同步管理端） */
.ai-feedback { margin-top:12px;padding:14px 16px;border:1px dashed #c9d6e4;border-radius:13px;background:#f8fbfd; }
.ai-feedback b { color:#37465a;font-size:12.5px; }
.ai-feedback p { margin:6px 0 0;color:#7d8999;font-size:11.5px;line-height:1.7; }
.ai-feedback textarea { width:100%;margin-top:9px;padding:9px 11px;border:1px solid #dbe6ef;border-radius:10px;font-size:12px;font-family:inherit;resize:vertical;box-sizing:border-box; }
.ai-feedback textarea:focus { outline:none;border-color:#2f7cf6;box-shadow:0 0 0 3px rgba(47,124,246,.12); }
.fb-acts { display:flex;gap:8px;margin-top:9px; }
.fb-acts button { padding:7px 18px;border:0;border-radius:999px;background:#e7f0ff;color:#216eff;font-size:12.5px;cursor:pointer; }
.fb-acts button.ghost { background:#eef2f6;color:#5b6b7d; }
.fb-acts button:disabled { opacity:.6;cursor:default; }
.fb-err { margin-top:8px;color:#c0392b;font-size:11.5px; }

/* ============ 任务中心 ============ */
.simple-page-head { padding:4px 2px 14px; }
.simple-page-head h1 { margin:0;color:#1c2d44;font-size:27px; }
.simple-page-head p { margin:7px 0 0;color:#7d8999;font-size:13px;line-height:1.6; }
.task-summary { position:relative;display:flex;gap:22px;align-items:center;overflow:hidden;padding:20px;border:1px solid var(--line);border-radius:17px;background:var(--paper2);box-shadow:0 7px 22px rgba(39,72,111,.055); }
.task-ring { display:grid;place-items:center;flex:0 0 104px;width:104px;height:104px;border:9px solid #fff3df;border-top-color:var(--gold);border-radius:50%;background:#fffdf7;text-align:center; }
.task-ring strong { color:#d98a1e;font:700 26px Consolas,monospace; }
.task-ring small { max-width:70px;color:#98a2ae;font-size:10px;line-height:1.3; }
.task-summary-copy { flex:1;min-width:0; }
.task-summary-copy b { color:#22344b;font-size:16px; }
.task-summary-copy span { display:block;margin:5px 0 12px;color:#7d8999;font-size:12px; }
.task-summary-copy button { padding:8px 22px;border:0;border-radius:999px;color:#fff;background:linear-gradient(100deg,#f0a92e,#f7c65b);font-size:13px;cursor:pointer; }
.task-summary-copy button:disabled { background:#c9d2db;cursor:default; }
.task-summary-img { flex:none;width:110px;height:110px;object-fit:cover;border-radius:14px; }
.tasks-columns { display:grid;grid-template-columns:1.25fr .75fr;gap:16px;margin-top:16px; }
.task-list-card,.rank-card,.ledger-card { border:1px solid var(--line);border-radius:17px;background:var(--paper2);box-shadow:0 7px 22px rgba(39,72,111,.055);padding:18px; }
.task-list-card h2,.rank-card h2,.ledger-card h2 { margin:0 0 14px;color:#1c2d44;font-size:15px; }
.task-list-card article { display:flex;align-items:center;gap:12px;padding:13px 0;border-bottom:1px dashed var(--line); }
.task-list-card article:last-child { border-bottom:0; }
.task-check { display:grid;place-items:center;flex:0 0 34px;width:34px;height:34px;border-radius:10px;color:#fff;font-weight:700;background:#d3dbe3; }
.task-check.done { background:linear-gradient(135deg,#27b56d,#4ecf8a); }
.task-list-card article > div { flex:1;min-width:0; }
.task-list-card article b { color:#22344b;font-size:13.5px; }
.task-list-card article p { margin:2px 0 0;color:#8a94a3;font-size:11.5px; }
.task-list-card article em { color:#f08c1e;font-size:13px;font-style:normal;font-weight:700; }
.task-list-card article button { padding:6px 16px;border:0;border-radius:999px;color:#216eff;background:#e7f0ff;font-size:12px;cursor:pointer; }
.task-list-card article button:disabled { color:#98a2ae;background:#eef1f4;cursor:default; }
.task-list-card article:nth-of-type(4) .task-check { background:#72a9ee; }
.task-list-card article:nth-of-type(5) .task-check { background:#55bba0; }
.rank-list { display:grid;gap:6px;margin:0;padding:0;list-style:none; }
.rank-list li { display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;background:#f7fafc; }
.rank-list li.me { background:#fff6e6;outline:1.5px solid #f7c65b; }
.rank-list li.top .rank-no { background:linear-gradient(135deg,#f0a92e,#f7c65b);color:#fff; }
.rank-no { display:grid;place-items:center;width:22px;height:22px;border-radius:50%;color:#7d8999;background:#e4eaf0;font-size:11px;font-weight:700; }
.rank-name { flex:1;color:#37465a;font-size:13px; }
.rank-list li.me .rank-name { color:#b06f00;font-weight:700; }
.rank-list li em { color:#d98a1e;font-size:12.5px;font-style:normal;font-weight:700; }
.rank-note { margin:12px 0 0;color:#98a2ae;font-size:11px;line-height:1.6; }
.ledger-card { margin-top:16px; }
.ledger-card ul { display:grid;gap:0;margin:0;padding:0;list-style:none; }
.ledger-card li { display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px dashed var(--line); }
.ledger-card li:last-child { border-bottom:0; }
.ledger-card li span { flex:1;color:#37465a;font-size:12.5px; }
.ledger-card li em { color:#1d8a52;font-weight:700;font-style:normal; }
.ledger-card li small { color:#98a2ae;font-size:11px; }

/* ============ 科普（三人群统筹） ============ */
.audience-bar { display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px; }
.audience-bar button { display:grid;gap:3px;padding:12px 14px;border:1.5px solid var(--line);border-radius:14px;background:#fff;text-align:left;cursor:pointer;transition:border-color .15s,background .15s; }
.audience-bar button.on { border-color:#2f7cf6;background:#eef5ff; }
.audience-bar b { color:#22344b;font-size:14px; }
.audience-bar button.on b { color:#216eff; }
.audience-bar small { color:#98a2ae;font-size:11px; }
.sci-search { display:flex;gap:10px;align-items:center;margin-bottom:16px;padding:11px 16px;border:1px solid var(--line);border-radius:999px;background:#fff; }
.sci-search span { color:#98a2ae;font-size:15px; }
.sci-search input { flex:1;border:0;outline:0;font-size:13px;background:transparent;color:#22344b; }
.news-grid { display:grid;grid-template-columns:1fr 1fr;gap:14px; }
.news-grid article { overflow:hidden;border:1px solid var(--line);border-radius:14px;background:#fff;box-shadow:0 7px 22px rgba(39,72,111,.055); }
.news-grid img { width:100%;height:120px;object-fit:cover; }
.news-grid article > div { padding:12px 14px 14px; }
.news-grid h3 { margin:0;color:#22344b;font-size:13.5px;line-height:1.4; }
.news-grid p { margin:5px 0 8px;color:#7d8999;font-size:11.5px;line-height:1.55; }
.news-grid small { color:#a3adba;font-size:10.5px; }
.life-card { display:grid;grid-template-columns:220px 1fr;gap:16px;margin-top:18px;padding:16px;border:1px solid #bfe3e8;border-radius:17px;background:linear-gradient(120deg,#f2fbfc,#fff); }
.life-cover { width:100%;height:150px;object-fit:cover;border-radius:12px; }
.life-copy { align-self:center; }
.life-badge { display:inline-block;padding:3px 10px;border-radius:999px;color:#0f8a96;background:#d9f4f7;font-size:11px; }
.life-copy h2 { margin:9px 0 6px;color:#1c2d44;font-size:19px; }
.life-copy p { margin:0 0 12px;color:#7d8999;font-size:12.5px; }
.life-copy button { padding:8px 22px;border:0;border-radius:999px;color:#fff;background:linear-gradient(100deg,#17b8c4,#4fd4dd);font-size:13px;cursor:pointer; }
.life-stages { grid-column:1/-1;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:6px 0 0;padding:14px 0 0;border-top:1px dashed #bfe3e8;list-style:none; }
.life-stages li { display:flex;gap:9px; }
.life-stages i { display:grid;place-items:center;flex:0 0 26px;width:26px;height:26px;border-radius:50%;color:#fff;font-size:12px;font-style:normal;background:linear-gradient(135deg,#17b8c4,#4fd4dd); }
.life-stages b { color:#22344b;font-size:13px; }
.life-stages p { margin:3px 0 0;color:#7d8999;font-size:11.5px;line-height:1.55; }
.sci-categories { display:flex;gap:8px;margin:18px 0 12px;flex-wrap:wrap; }
.sci-categories button { padding:7px 16px;border:1px solid var(--line);border-radius:999px;background:#fff;color:#4a5768;font-size:12.5px;cursor:pointer; }
.sci-categories button.on { border-color:#2f7cf6;color:#216eff;background:#eef5ff;font-weight:700; }
.sci-list { display:grid;gap:12px; }
.sci-article { display:grid;grid-template-columns:150px 1fr;gap:14px;padding:14px;border:1px solid var(--line);border-radius:15px;background:#fff;box-shadow:0 7px 22px rgba(39,72,111,.05); }
.sci-cover { width:150px;height:104px;object-fit:cover;border-radius:11px; }
.sci-cover.tile { display:grid;place-items:center;color:#fff;font-size:15px;font-weight:700; }
.sci-cover.tile.cat-烟头危害 { background:linear-gradient(135deg,#5b8def,#7fb0f5); }
.sci-cover.tile.cat-火灾安全 { background:linear-gradient(135deg,#ef7d54,#f5a37f); }
.sci-cover.tile.cat-文明吸烟 { background:linear-gradient(135deg,#3aa982,#63c7a3); }
.sci-cover.tile.cat-城市环保 { background:linear-gradient(135deg,#2aa7b8,#58c8d6); }
.sci-body h3 { margin:0;color:#22344b;font-size:14.5px; }
.sci-body > p { margin:5px 0 8px;color:#7d8999;font-size:12px;line-height:1.6; }
.data-chip { display:inline-block;margin-bottom:8px;padding:4px 10px;border-radius:8px;color:#0f8a96;background:#d9f4f7;font-size:11px; }
.quiz-box { display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap; }
.quiz-box > button { padding:7px 14px;border:1px solid #c9d6e4;border-radius:999px;background:#f8fbfd;font-size:12px;cursor:pointer; }
.quiz-box > button:hover { border-color:#2f7cf6;color:#216eff; }
.quiz-box p { margin:0;padding:9px 12px;border-radius:10px;font-size:12px;line-height:1.6; }
.quiz-box p.quiz-right { color:#1d8a52;background:#eafaf1; }
.quiz-box p.quiz-wrong { color:#c0392b;background:#fdeceb; }
.sci-meta { display:flex;align-items:center;gap:10px;flex-wrap:wrap; }
.sci-cat { padding:2px 9px;border-radius:999px;color:#216eff;background:#e7f0ff;font-size:10.5px; }
.sci-meta small { color:#a3adba;font-size:11px; }
.read-btn { margin-left:auto;padding:6px 16px;border:0;border-radius:999px;color:#fff;background:linear-gradient(100deg,#216eff,#4baedb);font-size:12px;cursor:pointer; }
.read-btn:disabled { background:#c9d2db;cursor:default; }
.speak-btn { padding:6px 12px;border:1px solid #c9d6e4;border-radius:999px;background:#fff;font-size:12px;cursor:pointer; }
.speak-btn:disabled { opacity:.45;cursor:default; }

/* ---- 长者模式：常驻语音朗读条 ---- */
.speak-bar { position:sticky;top:0;z-index:6;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:0 0 14px;padding:12px 16px;border:1.5px solid #cfe0ea;border-radius:15px;background:linear-gradient(120deg,#f2f9ff,#fff);box-shadow:0 6px 18px rgba(39,72,111,.07); }
.sb-lead { display:flex;align-items:center;gap:11px;min-width:0; }
.sb-lead > i { display:grid;place-items:center;flex:none;width:40px;height:40px;border-radius:12px;font-size:18px;font-style:normal;background:#e7f0ff; }
.sb-lead > i.live { background:#d8f2e6;animation:sbPulse 1.3s ease-in-out infinite; }
@keyframes sbPulse { 0%,100% { transform:scale(1) } 50% { transform:scale(1.12) } }
.sb-lead b { display:block;color:#1c2d44;font-size:15px; }
.sb-lead small { display:block;margin-top:2px;color:#7d8999;font-size:11.5px;line-height:1.5; }
.sb-acts { display:flex;align-items:center;gap:8px;flex-wrap:wrap; }
.sb-acts button { padding:8px 15px;border:1px solid #c9d6e4;border-radius:999px;background:#fff;color:#2a4a6b;font-size:13px;cursor:pointer; }
.sb-acts button:disabled { opacity:.45;cursor:default; }
.sb-acts button:not(:disabled):hover { border-color:#2f7cf6;color:#216eff; }
.sb-rate { border-color:#c3dcff !important;background:#eef5ff !important;color:#216eff !important;font-weight:700; }

/* 正在朗读的那一条 */
.sci-article.is-reading,
.news-grid article.is-reading { border-color:#5aa9f0;background:#f5faff;box-shadow:0 0 0 3px rgba(47,124,246,.12); }
.card-foot { display:flex;align-items:center;justify-content:space-between;gap:8px; }
.speak-btn.mini { padding:4px 10px;font-size:11px; flex:none; }
/* 长者模式：大字 + 高对比 */
.aud-senior .sci-article { grid-template-columns:170px 1fr; }
.aud-senior .sci-body h3 { font-size:19px; }
.aud-senior .sci-body > p { font-size:16px;color:#37465a; }
.aud-senior .sci-meta small { font-size:13px; }
.aud-senior .news-grid h3 { font-size:17px; }
.aud-senior .news-grid p { font-size:14px; }
.aud-senior .life-copy h2 { font-size:23px; }
.aud-senior .life-copy p { font-size:15px; }
.aud-senior .life-stages p { font-size:14px; }
.aud-senior .life-stages b { font-size:15px; }
.aud-senior .audience-bar b { font-size:16px; }
.aud-senior .audience-bar small { font-size:12px; }
.aud-senior .quiz-box > button { font-size:15px;padding:10px 18px; }
.aud-senior .quiz-box p { font-size:14px; }
.aud-senior .read-btn,.aud-senior .speak-btn { font-size:14px;padding:9px 18px; }
.aud-senior .sb-acts button { font-size:15px;padding:10px 18px; }
.aud-senior .sb-lead b { font-size:17px; }
.aud-senior .sb-lead small { font-size:13px; }
.aud-senior .speak-btn.mini { font-size:12.5px;padding:6px 12px; }

/* ============ 我的 ============ */
.profile-hero { display:flex;gap:16px;align-items:center;padding:22px;border:1px solid var(--line);border-radius:17px;background:linear-gradient(120deg,#f0f7ff,#fff);box-shadow:0 7px 22px rgba(39,72,111,.055); }
.profile-avatar { display:grid;place-items:center;flex:0 0 62px;width:62px;height:62px;border-radius:50%;color:#fff;font-size:19px;font-weight:700;background:linear-gradient(135deg,#2f7cf6,#38c8d4); }
.profile-hero span { color:#8a94a3;font-size:11px; }
.profile-hero h1 { margin:3px 0;color:#1c2d44;font-size:21px; }
.profile-hero p { margin:0;color:#7d8999;font-size:12px; }
.profile-stats { display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px; }
.profile-stats > div { display:grid;place-items:center;gap:3px;padding:16px;border:1px solid var(--line);border-radius:14px;background:#fff; }
.profile-stats strong { color:#216eff;font:700 24px Consolas,monospace; }
.profile-stats span { color:#8a94a3;font-size:11px; }
.profile-menu { display:grid;gap:8px;margin-top:14px; }
.profile-menu button { display:flex;align-items:center;padding:15px 18px;border:1px solid var(--line);border-radius:13px;background:#fff;font-size:13.5px;cursor:pointer; }
.profile-menu button span { flex:1;color:#37465a;text-align:left; }
.profile-menu button em { margin-right:8px;padding:1px 8px;border-radius:999px;color:#fff;background:#f05a4e;font-size:11px;font-style:normal; }
.profile-menu button i { color:#a3adba;font-style:normal; }
.account-boundary { margin-top:14px;padding:15px 17px;border:1px dashed #c9d6e4;border-radius:13px;background:#f8fbfd; }
.account-boundary b { color:#37465a;font-size:12.5px; }
.account-boundary p { margin:6px 0 0;color:#7d8999;font-size:12px;line-height:1.7; }
.logout-button { margin-top:16px;width:100%;padding:13px 0;border:1px solid #f3c2bd;border-radius:13px;color:#d84a3f;background:#fdf1ef;font-size:14px;cursor:pointer; }

/* ============ 窄屏 ============ */
@media (max-width: 860px) {
  .citizen-app { background:#f3f6fa; }
  .citizen-app :deep(.es-bar) { display:none; }
  .citizen-app :deep(.es-main) { padding:0 0 calc(76px + env(safe-area-inset-bottom));scrollbar-gutter:auto;overscroll-behavior-y:contain; }
  .citizen-app :deep(.es-inner) { display:block;min-height:100%; }
  .portal-shell { min-height:100%;padding-top:60px; }
  .mobile-header { position:fixed;z-index:30;top:0;left:0;right:0;display:grid;grid-template-columns:auto minmax(0,1fr) 38px;gap:9px;align-items:center;height:60px;padding:8px 13px;border-bottom:1px solid #e4ebf3;background:rgba(255,255,255,.96);box-shadow:0 3px 14px rgba(39,72,111,.07);backdrop-filter:blur(14px); }
  .city-select,.search-entry,.notice-entry { border:0;background:transparent; }
  .city-select { display:flex;align-items:center;gap:6px;padding:0;color:#20344d;white-space:nowrap; }
  .city-select i { width:9px;height:9px;border-radius:50%;background:#20b26b;box-shadow:0 0 0 4px #e4f7ed; }
  .city-select b { font-size:14px; }
  .city-select span { color:#8d9aaa;font-size:11px; }
  .search-entry { display:flex;align-items:center;gap:7px;min-width:0;height:38px;padding:0 13px;border-radius:12px;color:#8795a6;background:#f1f5f8;font-size:11px;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
  .search-entry span { color:#2f7cf6;font-size:17px; }
  .notice-entry { position:relative;display:grid;place-items:center;width:38px;height:38px;border-radius:12px;color:#27405b;background:#f5f8fb;font-size:20px; }
  .notice-entry em { position:absolute;right:1px;top:0;display:grid;place-items:center;width:16px;height:16px;border:2px solid #fff;border-radius:50%;color:#fff;background:#ff6257;font-size:8px;font-style:normal; }
  .mobile-nav { position:fixed;z-index:40;left:0;right:0;bottom:0;display:grid;grid-template-columns:repeat(5,1fr);min-height:64px;padding:5px 8px calc(5px + env(safe-area-inset-bottom));border-top:1px solid #dfe8f1;background:rgba(255,255,255,.97);box-shadow:0 -8px 24px rgba(30,63,96,.09);backdrop-filter:blur(16px); }
  .mobile-nav button { position:relative;display:flex;min-width:0;min-height:54px;flex-direction:column;align-items:center;justify-content:center;gap:3px;border:0;border-radius:13px;color:#8b98a8;background:transparent;font-size:10px; }
  .mobile-nav button i { display:grid;place-items:center;width:27px;height:27px;border-radius:9px;font-size:16px;font-style:normal;transition:.18s ease; }
  .mobile-nav button.on { color:#167e68;font-weight:700; }
  .mobile-nav button.on i { color:#fff;background:linear-gradient(135deg,#188c75,#2ca9bd);box-shadow:0 5px 12px rgba(29,143,127,.2);transform:translateY(-1px); }
  /* ---- App 版底栏：五格，中间一格是突出的「监督拍照」相机按钮 ---- */
  .mobile-nav.app-tabbar { align-items:end;overflow:visible;padding-top:0; }
  .mobile-nav.app-tabbar > button { position:relative; }
  .mobile-nav .app-capture { gap:1px;padding-top:0; }
  .mobile-nav .app-capture i.cam { display:grid;place-items:center;width:54px;height:54px;margin-top:-30px;border-radius:50%;color:#fff;background:linear-gradient(145deg,#188c75,#2ca9bd);box-shadow:0 10px 22px rgba(24,140,117,.42),0 0 0 4px rgba(255,255,255,.92);transition:transform .16s ease,box-shadow .16s ease; }
  .mobile-nav .app-capture span { margin-top:3px;color:#167e68;font-size:10px;font-weight:700; }
  .mobile-nav .app-capture.on i.cam { box-shadow:0 10px 24px rgba(24,140,117,.55),0 0 0 4px #e8f7f1; }
  .mobile-nav .app-capture:active i.cam { transform:scale(.93); }
  .mobile-nav .app-capture::after { content:'';position:absolute;left:50%;bottom:-2px;width:0;height:0; }
  .app-capture-input { position:absolute;left:-9999px;width:1px;height:1px;opacity:0;pointer-events:none; }
  .demo-banner { min-height:30px;margin:8px 12px 0;padding:5px 10px;border-radius:9px;font-size:9.5px;line-height:1.45; }
  .portal-page { padding:14px 12px 18px; }
  .citizen-brand-row { margin:2px 2px 12px; }
  .citizen-brand-mark { width:36px;height:36px;border-radius:11px;font-size:17px; }
  .citizen-brand-row h1 { font-size:18px; }
  .home-carousel { height:188px;border-radius:15px; }
  .slide-copy { left:18px;max-width:76%; }
  .slide-copy h2 { font-size:20px; }
  .quick-grid { gap:2px;margin-top:12px;padding:10px 3px 8px;border-radius:15px; }
  .quick-grid > button { min-height:68px;gap:5px;padding:3px 1px; }
  .quick-symbol { width:38px;height:38px;border-radius:12px;font-size:17px; }
  .quick-grid b { font-size:9.5px;line-height:1.25; }
  .my-latest,.nearby-card,.task-card,.knowledge-card,.service-card,.task-list-card,.rank-card,.ledger-card { border-radius:15px;box-shadow:0 5px 18px rgba(39,72,111,.045); }
  .home-grid,.map-layout,.report-workspace,.tasks-columns,.map-support-grid { grid-template-columns:1fr; }
  .map-layout { gap:12px; }
  .citizen-map { height:300px;border-radius:14px; }
  .citizen-map :deep(.gd-map) { height:300px !important; }
  /* 窄屏：右侧竖排放不下，改成底部卡片式面板 */
  .nav-panel { left:12px;right:12px;top:auto;bottom:12px;width:auto;max-height:66%; }
  .nav-steps { max-height:none; }
  .point-list { height:auto; }
  .point-list > button { padding:12px 11px; }
  .selected-place { min-height:168px; }
  .map-support-grid { gap:10px;margin-top:12px; }
  .map-support-grid article { padding:13px; }
  .page-heading { margin:4px 2px 14px; }
  .page-heading h1 { margin:5px 0;font-size:24px; }
  .page-heading p { font-size:11.5px;line-height:1.55; }
  .report-form { padding:14px; }
  .form-section { gap:10px;padding:14px 0; }
  .report-aside { gap:10px; }
  .report-boundary,.aside-result,.aside-tips { padding:15px; }
  .task-summary { gap:14px;padding:15px; }
  .task-ring { flex-basis:82px;width:82px;height:82px;border-width:7px; }
  .task-ring strong { font-size:22px; }
  .news-grid { grid-template-columns:1fr; }
  .life-card { grid-template-columns:1fr; }
  .life-stages { grid-template-columns:1fr 1fr; }
  .sci-article { grid-template-columns:104px 1fr;gap:10px;padding:11px; }
  .sci-cover { width:104px;height:82px; }
  .aud-senior .sci-article { grid-template-columns:1fr; }
  .aud-senior .sci-cover { width:100%;height:130px; }
  .task-summary-img { display:none; }
  .audience-bar { grid-template-columns:1fr; }
  .home-side { grid-template-rows:auto auto; }
  .facility-guide { grid-template-columns:1fr; }
  .profile-hero { padding:17px; }
  .profile-stats { gap:7px; }
  .profile-stats > div { padding:12px 5px; }
}
@media (max-width: 560px) {
  .home-carousel { height:182px; }
  .slide-copy h2 { font-size:17px; }
  .slide-copy p { font-size:10.5px; }
  .carousel-arrow { display:none; }
  .portal-page { padding:13px 12px 18px; }
}
</style>
