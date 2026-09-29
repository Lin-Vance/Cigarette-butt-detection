<script setup lang="ts">
/**
 * 烟的一生 · 情绪共鸣剧场（市民端科普的互动环节）。
 *
 * 设计目标：把"烟头的一生"从一段静态图文，变成**用户自己选结局**的短剧场。
 *   四幕（点燃 / 抛掷 / 清扫 / 渗透）→ 关键抉择「如果当时……」→ 两条分支结局。
 *   · 选「随手一扔」→ 污染继续的灰暗结局，给出清理成本数据；
 *   · 选「走向吸烟区」→ 结局改变，给出积分与碳减排贡献，并可生成分享海报。
 *
 * 实现备注：
 *  - 图集放在 `public/media/story/`，按幕号命名，缺失时自动退化为渐变底，不会白屏；
 *  - 讲故事文本通过 `@speak` 交给**父组件的全局朗读器**，避免与页面其它朗读互相打断；
 *  - 分享海报用 canvas 现画并下载，不依赖任何后端。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'

type Phase = 'acts' | 'choice' | 'endA' | 'endB'

const props = withDefaults(
  defineProps<{
    /** 长者模式：放大字号、默认展开朗读按钮 */
    senior?: boolean
    /** 父组件正在朗读的条目 id，用于高亮 */
    speakingId?: string
    speechSupported?: boolean
    /** 海报上署的名字 */
    nickname?: string
  }>(),
  { senior: false, speakingId: '', speechSupported: false, nickname: '热心市民' }
)

const emit = defineEmits<{
  (e: 'earn', delta: number, label: string): void
  (e: 'speak', id: string, text: string): void
}>()

interface Act {
  /** 幕号 01..04 */
  no: string
  /** 幕名 */
  title: string
  /** 主文案（大字） */
  headline: string
  /** 旁白 */
  body: string
  /** 角标微数据 */
  stat: string
  /** 背景图 */
  img: string
  /** 主色（用于氛围） */
  tone: 'ash' | 'dust' | 'cold' | 'toxic'
}

const ACTS: Act[] = [
  {
    no: '01',
    title: '点燃',
    headline: '我燃烧着最后的生命……',
    body: '指尖一明一暗。我只有七八分钟，却被当成了这座城市里最不起眼的一次呼吸。滤嘴里藏着焦油、重金属和醋酸纤维素——它们不会跟着烟一起散掉。',
    stat: '一支烟燃烧约 7 分钟 · 滤嘴主体是醋酸纤维素',
    img: '/media/story/act-1.jpg',
    tone: 'ash'
  },
  {
    no: '02',
    title: '抛掷',
    headline: '我被随手抛下，重重摔在地上。',
    body: '一次抬手，我很轻。落地之后，我变成 12 微米级的塑料、焦油和重金属——比烟灰难清理得多，也不会像烟灰一样被风带走。',
    stat: '一次随手丢弃 · 数年环境负担',
    img: '/media/story/act-2.jpg',
    tone: 'dust'
  },
  {
    no: '03',
    title: '清扫',
    headline: '寒风中，我是最难清理的顽固。',
    body: '扫帚要贴着砖缝来回三遍，才能把我从地砖的纹路里刮出来。清晨五点，有人替所有随手的一秒钟弯腰。',
    stat: '清扫成本 ↑ · 二次污染风险',
    img: '/media/story/act-3.jpg',
    tone: 'cold'
  },
  {
    no: '04',
    title: '渗透',
    headline: '我的毒素，正在渗入这座城市的血液。',
    body: '一场雨把我冲进雨水口。我不溶解，只会碎成更小的颗粒，顺着管道住进水生生物的胃里——那里没有人为我登记，也没有人能把我捞干净。',
    stat: 'MICROPLASTIC / TOXIN PATH · 1 枚烟蒂可污染约 500 升水体',
    img: '/media/story/act-4.jpg',
    tone: 'toxic'
  }
]

const END_A_STATS = [
  { v: '20 倍', l: '河道打捞成本 ≈ 前端收集' },
  { v: '数年', l: '滤嘴自然降解时间' },
  { v: '500 L', l: '单枚烟蒂可污染水体' }
]

const END_B_STATS = [
  { v: '+20', l: '文明积分' },
  { v: '+1', l: '碳减排贡献' },
  { v: '40 步', l: '你多走过的距离' }
]

const open = ref(false)
const phase = ref<Phase>('acts')
const act = ref(0)
const failedImg = ref<Record<string, boolean>>({})
const poster = ref('')
const posterBusy = ref(false)

const current = computed(() => ACTS[act.value])
const isLastAct = computed(() => act.value >= ACTS.length - 1)

/** 该幕的朗读文本 */
function actSpeech(a: Act): string {
  return `${a.no}，${a.title}。${a.headline}${a.body}`
}
function speakAct(a: Act) {
  emit('speak', `story-${a.no}`, actSpeech(a))
}
function speakLine(id: string, text: string) {
  emit('speak', id, text)
}

function startStory() {
  open.value = true
  phase.value = 'acts'
  act.value = 0
}

function nextAct() {
  if (isLastAct.value) {
    phase.value = 'choice'
    return
  }
  act.value += 1
}

function gotoAct(i: number) {
  phase.value = 'acts'
  act.value = Math.max(0, Math.min(ACTS.length - 1, i))
}

function choose(bad: boolean) {
  if (bad) {
    phase.value = 'endA'
    return
  }
  if (phase.value === 'endB') return
  phase.value = 'endB'
  // 正向结局才给积分（只给一次）
  emit('earn', 20, '互动剧情「烟的一生」：选择走向吸烟区')
}

function restart() {
  phase.value = 'choice'
}

function close() {
  open.value = false
}

function onImgError(url: string) {
  failedImg.value = { ...failedImg.value, [url]: true }
}

/* ---------------- 分享海报（canvas 现画，不依赖后端） ---------------- */
const POSTER_W = 720
const POSTER_H = 1000

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const out: string[] = []
  let line = ''
  for (const ch of text) {
    if (ctx.measureText(line + ch).width > maxWidth) {
      out.push(line)
      line = ch
    } else {
      line += ch
    }
  }
  if (line) out.push(line)
  return out
}

function loadImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => resolve(null)
    img.src = src
  })
}

async function makePoster(): Promise<string> {
  const canvas = document.createElement('canvas')
  canvas.width = POSTER_W
  canvas.height = POSTER_H
  const ctx = canvas.getContext('2d')
  if (!ctx) return ''

  // 1) 底图（干净城市）＋ 暗压层，保证文字可读
  const bg = await loadImage('/media/story/end-hope.jpg')
  if (bg) {
    const scale = Math.max(POSTER_W / bg.width, POSTER_H / bg.height)
    const w = bg.width * scale
    const h = bg.height * scale
    ctx.drawImage(bg, (POSTER_W - w) / 2, (POSTER_H - h) / 2, w, h)
  } else {
    const g = ctx.createLinearGradient(0, 0, 0, POSTER_H)
    g.addColorStop(0, '#0d2136')
    g.addColorStop(1, '#123f34')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, POSTER_W, POSTER_H)
  }
  const veil = ctx.createLinearGradient(0, 0, 0, POSTER_H)
  veil.addColorStop(0, 'rgba(6,18,32,0.62)')
  veil.addColorStop(0.55, 'rgba(6,18,32,0.72)')
  veil.addColorStop(1, 'rgba(4,14,26,0.92)')
  ctx.fillStyle = veil
  ctx.fillRect(0, 0, POSTER_W, POSTER_H)

  // 2) 顶部品牌行
  ctx.fillStyle = 'rgba(255,255,255,0.82)'
  ctx.font = '600 22px "Microsoft YaHei", system-ui, sans-serif'
  ctx.fillText('烟踪智治 · 文明科普', 56, 86)
  ctx.fillStyle = 'rgba(120,230,200,0.9)'
  ctx.font = '600 18px Consolas, monospace'
  ctx.fillText('EMOTION THEATER / 情绪共鸣剧场', 56, 118)

  // 3) 主标语（手写感靠字号与行距，不依赖字体文件）
  ctx.fillStyle = '#eafff6'
  ctx.font = '700 54px "Microsoft YaHei", system-ui, sans-serif'
  const lines = wrapText(ctx, '谢谢你，让这座城市多了一分干净。', POSTER_W - 112)
  lines.forEach((l, i) => ctx.fillText(l, 56, 250 + i * 70))

  // 4) 副说明
  ctx.fillStyle = 'rgba(226,240,236,0.82)'
  ctx.font = '400 22px "Microsoft YaHei", system-ui, sans-serif'
  const sub = wrapText(
    ctx,
    '你多走了 40 步，我落进阻燃收集口，没有再进入雨水。同一枚烟头，可以有两种结局。',
    POSTER_W - 112
  )
  sub.forEach((l, i) => ctx.fillText(l, 56, 250 + lines.length * 70 + 22 + i * 34))

  // 5) 数据卡
  const cardY = POSTER_H - 330
  ctx.fillStyle = 'rgba(255,255,255,0.10)'
  roundRect(ctx, 56, cardY, POSTER_W - 112, 120, 20)
  ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.22)'
  ctx.lineWidth = 1.5
  roundRect(ctx, 56, cardY, POSTER_W - 112, 120, 20)
  ctx.stroke()
  const cells = END_B_STATS
  const cellW = (POSTER_W - 112) / cells.length
  cells.forEach((c, i) => {
    const cx = 56 + cellW * i + cellW / 2
    ctx.textAlign = 'center'
    ctx.fillStyle = '#8ff0d0'
    ctx.font = '700 34px Consolas, "Microsoft YaHei", monospace'
    ctx.fillText(c.v, cx, cardY + 56)
    ctx.fillStyle = 'rgba(226,240,236,0.78)'
    ctx.font = '400 17px "Microsoft YaHei", system-ui, sans-serif'
    ctx.fillText(c.l, cx, cardY + 88)
    ctx.textAlign = 'left'
  })

  // 6) 署名 + 落款
  ctx.fillStyle = '#ffffff'
  ctx.font = '600 24px "Microsoft YaHei", system-ui, sans-serif'
  ctx.fillText(`${props.nickname} · 完成互动剧情`, 56, POSTER_H - 150)
  ctx.fillStyle = 'rgba(190,215,225,0.72)'
  ctx.font = '400 19px "Microsoft YaHei", system-ui, sans-serif'
  ctx.fillText('图示与数据为演示内容，不代表真实点位、案件或治理结果。', 56, POSTER_H - 112)
  ctx.fillStyle = 'rgba(143,240,208,0.9)'
  ctx.font = '700 22px "Microsoft YaHei", system-ui, sans-serif'
  ctx.fillText('文明选择，让改变发生', 56, POSTER_H - 62)

  return canvas.toDataURL('image/png')
}

async function generatePoster() {
  if (posterBusy.value) return
  posterBusy.value = true
  try {
    poster.value = await makePoster()
  } finally {
    posterBusy.value = false
  }
}

function downloadPoster() {
  if (!poster.value) return
  const a = document.createElement('a')
  a.href = poster.value
  a.download = `烟踪智治-烟的一生-${Date.now()}.png`
  a.click()
}

watch(open, (v) => {
  if (!v) poster.value = ''
  document.documentElement.style.overflow = v ? 'hidden' : ''
})

onBeforeUnmount(() => {
  poster.value = ''
  document.documentElement.style.overflow = ''
})
</script>

<template>
  <section class="story" :class="[`tone-${current.tone}`, { senior, open }]">
    <!-- ============ 封面（未展开） ============ -->
    <div v-if="!open" class="story-cover">
      <!-- 注意：这里必须用 :src 动态绑定。写静态 src="/media/..." 会被 Vite 当成
           需要解析的模块资源，图片缺失时直接让整个组件编译失败、进而整站白屏。 -->
      <img class="sc-bg" :src="ACTS[0].img" alt="" @error="onImgError(ACTS[0].img)" />
      <div class="sc-veil"></div>
      <div class="sc-copy">
        <span class="life-badge">互动剧情 · 情绪共鸣剧场</span>
        <h2>烟的一生</h2>
        <p>从点燃到落地，只差一个选择。这一枚烟头的结局，由你决定。</p>
        <div class="sc-meta">
          <span>4 幕剧情</span><i></i><span>2 条分支结局</span><i></i><span>可生成分享海报</span>
        </div>
        <button type="button" data-testid="story-open" @click="startStory">开始体验</button>
      </div>
    </div>

    <!-- ============ 剧场（已展开） ============ -->
    <div v-else class="story-stage">
      <header class="st-bar">
        <div>
          <b>情绪共鸣剧场</b>
          <small>{{ phase === 'acts' ? `第 ${act + 1} / ${ACTS.length} 幕` : phase === 'choice' ? '关键抉择' : '结局' }}</small>
        </div>
        <div class="st-bar-acts">
          <button
            v-if="speechSupported"
            type="button"
            class="st-speak"
            @click="phase === 'acts' ? speakAct(current) : speakLine(`story-${phase}`, phase === 'choice' ? '如果当时……你可以重新选择这枚烟头的结局。随手一扔，污染继续；走向吸烟区，结局改变。' : phase === 'endA' ? '结局没有改变。我进了排水管，最后停在河湾的淤泥里。清理它要花掉二十倍于前端收集的成本，而且没人会知道是我。' : '谢谢你，让这座城市多了一分干净。你多走了四十步，我落进阻燃收集口，没有再进入雨水。')"
          >🔊 朗读这一幕</button>
          <button type="button" class="st-close" aria-label="关闭剧场" @click="close">✕</button>
        </div>
      </header>

      <!-- ---- 四幕 ---- -->
      <template v-if="phase === 'acts'">
        <div class="st-frame" :key="current.no">
          <img
            class="st-bg"
            :src="current.img"
            :alt="current.title"
            :class="{ missing: failedImg[current.img] }"
            @error="onImgError(current.img)"
          />
          <div class="st-veil"></div>
          <div class="st-text">
            <span class="st-no">{{ current.no }} / {{ current.title }}</span>
            <h3>{{ current.headline }}</h3>
            <p>{{ current.body }}</p>
            <em>{{ current.stat }}</em>
          </div>

          <!-- 右侧幕进度轨 -->
          <ol class="st-rail">
            <li v-for="(a, i) in ACTS" :key="a.no" :class="{ on: i === act, done: i < act }">
              <button type="button" :aria-label="`跳到第 ${i + 1} 幕：${a.title}`" @click="gotoAct(i)">
                <i></i><span>{{ a.no }}</span>
              </button>
            </li>
          </ol>
        </div>

        <div class="st-foot">
          <div class="st-dots">
            <i v-for="(a, i) in ACTS" :key="a.no" :class="{ on: i === act }"></i>
          </div>
          <div class="st-foot-acts">
            <button v-if="act > 0" type="button" class="ghost" @click="gotoAct(act - 1)">上一幕</button>
            <button type="button" data-testid="story-next" @click="nextAct">
              {{ isLastAct ? '进入关键抉择 →' : '向下滚动 · 继续故事 →' }}
            </button>
          </div>
        </div>
      </template>

      <!-- ---- 关键抉择 ---- -->
      <div v-else-if="phase === 'choice'" class="st-choice">
        <span class="st-choice-kicker">如果当时……</span>
        <h3>你可以重新选择这枚烟头的结局</h3>
        <p>同一只手、同一条街、同一个雨夜。区别只在于下一个动作。</p>
        <div class="st-choice-acts">
          <button type="button" class="bad" data-testid="story-choice-bad" @click="choose(true)">
            <span>🚬</span>
            <b>随手一扔</b>
            <small>污染继续</small>
          </button>
          <button type="button" class="good" data-testid="story-choice-good" @click="choose(false)">
            <span>🌀</span>
            <b>走向吸烟区</b>
            <small>结局改变</small>
          </button>
        </div>
      </div>

      <!-- ---- 结局 A：污染继续 ---- -->
      <div v-else-if="phase === 'endA'" class="st-end bad">
        <div class="st-end-head">
          <span class="tag-bad">结局 · 污染继续</span>
          <h3>结局没有改变。</h3>
          <p>
            我进了排水管，最后停在河湾的淤泥里。清理我要花掉约 20 倍于前端收集的成本——而且没有人会知道是我。
          </p>
        </div>
        <ul class="st-stats">
          <li v-for="s in END_A_STATS" :key="s.l"><b>{{ s.v }}</b><small>{{ s.l }}</small></li>
        </ul>
        <div class="st-end-acts">
          <button type="button" data-testid="story-restart" @click="restart">重新选择一次</button>
          <button type="button" class="ghost" @click="close">先离开剧场</button>
        </div>
      </div>

      <!-- ---- 结局 B：结局改变 ---- -->
      <div v-else class="st-end good">
        <div class="st-end-head">
          <span class="tag-good">结局 · 改变</span>
          <h3>谢谢你，让这座城市多了一分干净。</h3>
          <p>
            你多走了 40 步。我落进阻燃收集口，被集中处理，没有再进入雨水。
            同一枚烟头，原本可以有两种结局。
          </p>
        </div>
        <ul class="st-stats">
          <li v-for="s in END_B_STATS" :key="s.l"><b>{{ s.v }}</b><small>{{ s.l }}</small></li>
        </ul>
        <div class="st-end-acts">
          <button type="button" data-testid="story-poster" :disabled="posterBusy" @click="generatePoster">
            {{ posterBusy ? '正在生成…' : '生成分享海报' }}
          </button>
          <button type="button" class="ghost" @click="restart">重新体验</button>
        </div>

        <div v-if="poster" class="st-poster">
          <img :src="poster" alt="烟的一生 · 分享海报预览" />
          <div class="st-poster-acts">
            <button type="button" @click="downloadPoster">保存到本地</button>
            <button type="button" class="ghost" @click="poster = ''">收起预览</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.story {
  position: relative;
  margin-top: 18px;
  border: 1px solid #d7e6ee;
  border-radius: 18px;
  overflow: hidden;
  background: #0e1a26;
  color: #eaf3f8;
}

/* ---------------- 封面 ---------------- */
.story-cover {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 260px;
  padding: 26px 30px;
}
.sc-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.sc-veil {
  position: absolute;
  inset: 0;
  background: linear-gradient(100deg, rgba(8, 20, 34, 0.88), rgba(8, 20, 34, 0.55) 60%, rgba(8, 20, 34, 0.3));
}
.sc-copy {
  position: relative;
  z-index: 2;
  max-width: 470px;
}
.sc-copy h2 {
  margin: 12px 0 8px;
  font-size: 28px;
  letter-spacing: 0.02em;
}
.sc-copy p {
  margin: 0 0 14px;
  color: rgba(226, 240, 246, 0.86);
  font-size: 13.5px;
  line-height: 1.75;
}
.sc-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: rgba(200, 220, 232, 0.8);
  font-size: 11.5px;
}
.sc-meta i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: rgba(200, 220, 232, 0.5);
}
.sc-copy button {
  padding: 10px 26px;
  border: 0;
  border-radius: 999px;
  color: #06231c;
  background: linear-gradient(100deg, #6ee7bf, #a8f0d4);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

/* ---------------- 剧场 ---------------- */
.story-stage {
  padding: 14px;
}
.story.open {
  position: fixed;
  z-index: 120;
  inset: 72px 3vw 18px;
  margin: 0;
  overflow: auto;
  border: 1px solid rgba(143, 240, 208, .3);
  border-radius: 20px;
  background: #07121d;
  box-shadow: 0 26px 90px rgba(1, 8, 16, .58), 0 0 0 9999px rgba(3, 10, 18, .68);
}
.story.open .story-stage {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-height: 100%;
}
.story.open .st-frame,
.story.open .st-text { min-height: min(52vh, 430px); }
.story.open .st-foot {
  position: sticky;
  z-index: 5;
  bottom: -14px;
  padding: 12px 8px 10px;
  background: linear-gradient(180deg, rgba(7,18,29,.84), #07121d 34%);
}
.st-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 6px 12px;
}
.st-bar b {
  font-size: 14px;
  letter-spacing: 0.04em;
}
.st-bar small {
  margin-left: 8px;
  color: rgba(190, 214, 226, 0.7);
  font-size: 11px;
}
.st-bar-acts {
  display: flex;
  align-items: center;
  gap: 8px;
}
.st-speak,
.st-close {
  border: 1px solid rgba(190, 214, 226, 0.3);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #dcecf4;
  font-size: 12px;
  cursor: pointer;
}
.st-speak { padding: 7px 13px; }
.st-close { width: 30px; height: 30px; }

.st-frame {
  position: relative;
  min-height: 340px;
  border-radius: 14px;
  overflow: hidden;
  animation: stIn 0.5s ease both;
}
@keyframes stIn {
  from { opacity: 0; transform: translateY(10px) scale(0.995); }
  to { opacity: 1; transform: none; }
}
.st-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.st-bg.missing { display: none; }
.tone-ash .st-frame { background: linear-gradient(160deg, #26333d, #0d161e); }
.tone-dust .st-frame { background: linear-gradient(160deg, #3a352f, #14110e); }
.tone-cold .st-frame { background: linear-gradient(160deg, #223140, #0b131b); }
.tone-toxic .st-frame { background: linear-gradient(160deg, #2a1f2e, #100a14); }
.st-veil {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(6, 16, 28, 0.42) 0%, rgba(6, 16, 28, 0.62) 45%, rgba(6, 16, 28, 0.92) 100%);
}
.st-text {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-height: 340px;
  padding: 22px 26px 24px;
  max-width: 74%;
}
.st-no {
  color: #8ff0d0;
  font: 600 11px Consolas, monospace;
  letter-spacing: 0.22em;
}
.st-text h3 {
  margin: 10px 0 10px;
  font-size: 25px;
  line-height: 1.35;
  letter-spacing: 0.01em;
}
.st-text p {
  margin: 0 0 12px;
  color: rgba(226, 240, 246, 0.84);
  font-size: 13px;
  line-height: 1.85;
}
.st-text em {
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 999px;
  color: rgba(190, 232, 220, 0.95);
  background: rgba(255, 255, 255, 0.1);
  font-size: 10.5px;
  font-style: normal;
}

/* 右侧幕进度轨 */
.st-rail {
  position: absolute;
  right: 16px;
  top: 50%;
  z-index: 3;
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  transform: translateY(-50%);
}
.st-rail button {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 0;
  background: transparent;
  color: rgba(210, 228, 238, 0.55);
  font: 600 10px Consolas, monospace;
  cursor: pointer;
}
.st-rail i {
  display: block;
  width: 9px;
  height: 9px;
  border: 1.5px solid rgba(210, 228, 238, 0.5);
  border-radius: 50%;
}
.st-rail li.done i { background: rgba(143, 240, 208, 0.7); border-color: transparent; }
.st-rail li.on i {
  background: #8ff0d0;
  border-color: transparent;
  box-shadow: 0 0 0 4px rgba(143, 240, 208, 0.22);
}
.st-rail li.on span { color: #8ff0d0; }

.st-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 6px 4px;
}
.st-dots { display: flex; gap: 6px; }
.st-dots i {
  width: 22px;
  height: 3px;
  border-radius: 2px;
  background: rgba(210, 228, 238, 0.25);
}
.st-dots i.on { background: #8ff0d0; }
.st-foot-acts { display: flex; gap: 8px; }
.st-foot-acts button,
.st-choice-acts button,
.st-end-acts button {
  border: 0;
  border-radius: 999px;
  font-size: 13px;
  cursor: pointer;
}
.st-foot-acts button {
  padding: 9px 20px;
  color: #06231c;
  background: linear-gradient(100deg, #6ee7bf, #a8f0d4);
  font-weight: 700;
}
.st-foot-acts button.ghost {
  color: #dcecf4;
  background: rgba(255, 255, 255, 0.1);
  font-weight: 400;
}

/* ---------------- 抉择 ---------------- */
.st-choice,
.st-end {
  padding: 22px;
  border-radius: 14px;
  animation: stIn 0.45s ease both;
}
.st-choice { background: linear-gradient(160deg, #14273a, #0b1622); text-align: center; }
.st-choice-kicker {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  color: #8ff0d0;
  background: rgba(143, 240, 208, 0.12);
  font: 600 11px Consolas, monospace;
  letter-spacing: 0.16em;
}
.st-choice h3 { margin: 14px 0 8px; font-size: 24px; }
.st-choice > p { margin: 0 0 20px; color: rgba(212, 230, 240, 0.76); font-size: 13px; }
.st-choice-acts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  max-width: 620px;
  margin: 0 auto;
}
.st-choice-acts button {
  display: grid;
  gap: 5px;
  padding: 18px 12px;
  border: 1.5px solid transparent;
  border-radius: 16px;
  text-align: center;
  transition: transform 0.16s, box-shadow 0.16s;
}
.st-choice-acts button:hover { transform: translateY(-2px); }
.st-choice-acts button span { font-size: 22px; }
.st-choice-acts button b { font-size: 15px; }
.st-choice-acts button small { font-size: 11px; opacity: 0.75; }
.st-choice-acts .bad { color: #f3e6e4; background: linear-gradient(160deg, #3a2226, #241317); border-color: rgba(240, 140, 130, 0.3); }
.st-choice-acts .bad:hover { box-shadow: 0 10px 26px rgba(200, 90, 80, 0.24); }
.st-choice-acts .good { color: #dffaf0; background: linear-gradient(160deg, #143c34, #0d2620); border-color: rgba(143, 240, 208, 0.42); }
.st-choice-acts .good:hover { box-shadow: 0 10px 26px rgba(110, 231, 191, 0.24); }

/* ---------------- 结局 ---------------- */
.st-end.bad { background: linear-gradient(160deg, #2a1b1f, #150c10); }
.st-end.good { background: linear-gradient(160deg, #10352d, #0a1c25); }
.st-end-head { max-width: 640px; }
.st-end-head h3 { margin: 12px 0 10px; font-size: 24px; line-height: 1.4; }
.st-end.good .st-end-head h3 { color: #b9fbe0; }
.st-end.bad .st-end-head h3 { color: #f6cfc8; }
.st-end-head p { margin: 0; color: rgba(216, 232, 240, 0.82); font-size: 13px; line-height: 1.9; }
.tag-bad,
.tag-good {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font: 600 11px Consolas, monospace;
  letter-spacing: 0.14em;
}
.tag-bad { color: #ffb9ad; background: rgba(255, 130, 110, 0.14); }
.tag-good { color: #8ff0d0; background: rgba(143, 240, 208, 0.14); }
.st-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 18px 0;
  padding: 0;
  list-style: none;
}
.st-stats li {
  display: grid;
  gap: 4px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.06);
}
.st-stats b { color: #8ff0d0; font: 700 20px Consolas, monospace; }
.st-end.bad .st-stats b { color: #ffb9ad; }
.st-stats small { color: rgba(216, 232, 240, 0.76); font-size: 11px; line-height: 1.5; }
.st-end-acts { display: flex; gap: 10px; flex-wrap: wrap; }
.st-end-acts button {
  padding: 10px 22px;
  color: #06231c;
  background: linear-gradient(100deg, #6ee7bf, #a8f0d4);
  font-weight: 700;
}
.st-end.bad .st-end-acts button { color: #2a1316; background: linear-gradient(100deg, #ffb9ad, #f0a08f); }
.st-end-acts button.ghost {
  color: #dcecf4;
  background: rgba(255, 255, 255, 0.1);
  font-weight: 400;
}
.st-end-acts button:disabled { opacity: 0.6; cursor: default; }

.st-poster {
  margin-top: 18px;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.22);
}
.st-poster img {
  display: block;
  width: 100%;
  max-width: 340px;
  margin: 0 auto 12px;
  border-radius: 12px;
}
.st-poster-acts { display: flex; gap: 8px; justify-content: center; }
.st-poster-acts button {
  padding: 8px 18px;
  border: 0;
  border-radius: 999px;
  color: #06231c;
  background: #8ff0d0;
  font-size: 12.5px;
  cursor: pointer;
}
.st-poster-acts button.ghost { color: #dcecf4; background: rgba(255, 255, 255, 0.12); }

/* 长者模式：全面放大，保证可读 */
.senior .sc-copy h2 { font-size: 34px; }
.senior .sc-copy p { font-size: 16px; }
.senior .sc-copy button { font-size: 17px; padding: 13px 32px; }
.senior .st-text h3 { font-size: 31px; }
.senior .st-text p { font-size: 16px; }
.senior .st-text em { font-size: 13px; }
.senior .st-choice h3 { font-size: 29px; }
.senior .st-choice > p { font-size: 16px; }
.senior .st-choice-acts button b { font-size: 18px; }
.senior .st-choice-acts button small { font-size: 13px; }
.senior .st-end-head h3 { font-size: 29px; }
.senior .st-end-head p { font-size: 16px; }
.senior .st-stats b { font-size: 24px; }
.senior .st-stats small { font-size: 13px; }
.senior .st-foot-acts button,
.senior .st-end-acts button { font-size: 16px; padding: 13px 26px; }

@media (max-width: 860px) {
  .story.open { inset: 8px 8px 76px; border-radius: 16px; }
  .story.open .story-stage { padding: 9px; }
  .story.open .st-frame,
  .story.open .st-text { min-height: min(49vh, 360px); }
  .story-cover { min-height: 220px; padding: 20px; }
  .sc-copy h2 { font-size: 23px; }
  .st-frame,
  .st-text { min-height: 300px; }
  .st-text { max-width: 100%; padding: 18px 16px 20px; }
  .st-text h3 { font-size: 20px; }
  .st-rail { right: 8px; gap: 9px; }
  .st-rail span { display: none; }
  .st-choice-acts { grid-template-columns: 1fr; }
  .st-stats { grid-template-columns: 1fr; }
  .st-foot { flex-direction: column; align-items: stretch; }
  .st-foot-acts { justify-content: stretch; }
  .st-foot-acts button { flex: 1; }
}
</style>
