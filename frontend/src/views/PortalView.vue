<script setup lang="ts">
/**
 * 入口页（index.html）· 5 屏长滚动叙事。
 *
 * 视觉取向：延续第一屏那张黄昏步道实景（深墨底 + 朱砂轨迹 + 信号青标记），
 * 做成 Linear 式的长滚动叙事——大留白、柔性径向光晕、细边框卡、滚动驱动的逐段显影。
 *
 * 三处硬约束：
 *  1) 第一屏是原有 Hero 的**恢复**（此前被压成 208px 横幅），这里回到整屏。
 *  2) 「选择要进入的端」那种后台面板一律不要——端入口改为叙事的一部分（§04）。
 *  3) 零三方动画库：rAF 节流的 scroll + class 切换即可，
 *     且令牌只在本页生效，不与后台 / 其它端互相污染。
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useDemoStore } from '@/stores/demo'

const demo = useDemoStore()
const root = ref<HTMLElement | null>(null)

/** 手机 App 版：首页要能直接看到入口，并给出真机视口预览（iframe 宽 390，媒体查询自然生效） */
const phoneOn = ref(true)
function togglePhone() {
  phoneOn.value = !phoneOn.value
}

/* ------------------------------------------------------------------ 内容 */

/** 五个章节，顶栏导航与编号共用 */
const CHAPTERS = [
  { no: '01', id: 'c1', label: '主张' },
  { no: '02', id: 'c2', label: '断点' },
  { no: '03', id: 'c3', label: '机制' },
  { no: '04', id: 'c4', label: '证据' },
  { no: '05', id: 'c5', label: '边界' }
]

/** 第一屏的三段能力（原 Hero 的三个胶囊，保留） */
const CAPS = [
  { k: 'INPUT', v: '连续视频', note: '不是一张照片' },
  { k: 'REVIEW', v: '人工复核', note: 'AI 只给候选' },
  { k: 'OUTPUT', v: '治理闭环', note: '任务与回音' }
]

/** §02：断点对照 */
const CONTRAST = [
  {
    tag: '只看到结果',
    tone: 'dim',
    title: '地上一枚烟头',
    can: ['知道某处出现了烟头', '知道它大概在哪个位置'],
    cant: [
      '说不清是谁丢的',
      '说不清发生在几点几分',
      '说不清是随手一抛还是另有原因',
      '无从追溯是否重复发生'
    ]
  },
  {
    tag: '还原过程',
    tone: 'live',
    title: '一段连续动作',
    can: [
      '起止时刻精确到帧',
      '手部与烟头运动轨迹可回看',
      '落地位置有坐标标记',
      '同一位置可做重复发生统计'
    ],
    cant: ['不用于识别自然人身份', '不自动作出处罚决定']
  }
]

/** §03：五段闭环 */
const STAGES = [
  {
    no: '01',
    key: 'CAPTURE',
    title: '捕捉',
    what: '多路摄像头持续回传，按固定时间窗切片。',
    out: '视频片段 + 时间戳'
  },
  {
    no: '02',
    key: 'CHAIN',
    title: '串联',
    what: '把手部动作、烟头轨迹、落地位点串成同一条时间线。',
    out: '候选动作窗口'
  },
  {
    no: '03',
    key: 'REVIEW',
    title: '研判',
    what: '人工复核候选事件，可确认、可驳回、可标记证据不足。',
    out: '已确认事件 / 已驳回'
  },
  {
    no: '04',
    key: 'DISPATCH',
    title: '调度',
    what: '按区域与响应时长派单，环卫端接单后上传清理后照片。',
    out: '工单 + 处置记录'
  },
  {
    no: '05',
    key: 'CLOSE',
    title: '复盘',
    what: '同一位置重复发生、未闭环事件、平均响应时长进入统计。',
    out: '区域分析结论'
  }
]

/** §03 底部的五段实景通栏：五个阶段各自对应的现场 */
const SCENES = [
  '持烟识别',
  '吸烟亭',
  '烟头落地',
  '摄像头识别',
  '环卫协同处置'
]

/** §04 证据：同一次事件的三个关键帧（截图取自设计稿素材，演示用） */
const FRAMES = [
  {
    src: '/design-assets/6/pedestrian_smoke_camera_thumbnail.png',
    code: 'F-0288',
    ms: '2880 ms',
    alt: '持烟识别画面'
  },
  {
    src: '/design-assets/6/sidewalk_pedestrian_camera_thumbnail.png',
    code: 'F-0324',
    ms: '3240 ms',
    alt: '烟头释放画面'
  },
  {
    src: '/design-assets/6/pedestrian_crosswalk_camera_thumbnail.png',
    code: 'F-0372',
    ms: '3720 ms',
    alt: '落地判定画面'
  }
]

/** §05：边界 */
const BOUNDARIES = [
  {
    k: '不做的事',
    v: '不自动认定责任、不自动作出处罚；AI 输出一律是「候选」，不是结论。'
  },
  {
    k: '不公开的东西',
    v: '不公开上报人实名；含可识别人物的素材仅供授权研判，不在公开端展示。'
  },
  {
    k: '数据是演示的',
    v: '页面内事件、指标、点位、工单均为演示数据；行为识别管道尚未接入真实视频流。'
  }
]

/* ------------------------------------------------------------------ 滚动驱动 */

const barSolid = ref(false)
const activeCh = ref(0)
const progress = ref(0)

let secs: HTMLElement[] = []
let reveals: HTMLElement[] = []
let ticking = false

function measure() {
  const box = root.value
  if (!box) return
  secs = Array.from(box.querySelectorAll<HTMLElement>('[data-ch]'))
  reveals = Array.from(box.querySelectorAll<HTMLElement>('[data-reveal]'))
  compute()
}

function compute() {
  const box = root.value
  if (!box) return
  const top = box.scrollTop
  const vh = box.clientHeight

  barSolid.value = top > 48
  progress.value = Math.min(1, top / Math.max(1, box.scrollHeight - vh))

  // 当前章节：以视口 42% 处为判定线
  const line = top + vh * 0.42
  let idx = 0
  for (let i = 0; i < secs.length; i++) {
    if (secs[i].offsetTop <= line) idx = i
  }
  activeCh.value = idx

  // 逐段显影：进入视口 88% 处即显示，且不回退（避免来回闪烁）
  for (const el of reveals) {
    if (el.offsetTop < top + vh * 0.88) el.classList.add('in')
  }
}

function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    compute()
    ticking = false
  })
}

function gotoChapter(i: number) {
  const box = root.value
  if (!box || !secs[i]) return
  box.scrollTo({ top: secs[i].offsetTop - 1, behavior: 'smooth' })
}

/* ------------------------------------------------------------------ 演示数值 */

const stats = computed(() => [
  { label: '在线设备', value: demo.metrics.onlineDevices, unit: '路', note: demo.scale.label },
  { label: '今日候选事件', value: demo.metrics.todayViolations, unit: '起', note: '含未复核' },
  { label: '待处置', value: demo.metrics.processingEvents, unit: '起', note: '未闭环' },
  {
    label: '工单闭环率',
    value: `${demo.metrics.workorderCompletionRate}`,
    unit: '%',
    note: `平均响应 ${demo.metrics.avgResponseMin} 分`
  }
])

/* ------------------------------------------------------------------ 生命周期 */

let ro: ResizeObserver | undefined

onMounted(() => {
  demo.init()
  measure()
  const box = root.value
  box?.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', measure)
  ro = new ResizeObserver(measure)
  if (box) ro.observe(box)
  // 首屏立刻显影，不等滚动事件
  requestAnimationFrame(() => {
    root.value?.querySelector('.ch--hero')?.classList.add('in')
  })
})

onUnmounted(() => {
  root.value?.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', measure)
  ro?.disconnect()
})
</script>

<template>
  <div ref="root" class="lp" :class="{ solid: barSolid }">
    <!-- 顶部柔光：Linear 式的单束径向光，纯 CSS -->
    <div class="lp-glow" aria-hidden="true" />

    <!-- ---------------- 顶栏 ---------------- -->
    <header class="lp-bar">
      <a class="lp-brand" href="./index.html" aria-label="烟踪智治首页">
        <!-- 深底上用透明底图形徽标 + 白字：整张横版 logo 自带白底，
             直接反白会把白底一起反成实心白块 -->
        <img src="/logo-mark.png" alt="" />
        <b>烟踪智治</b>
      </a>

      <nav class="lp-nav" aria-label="页面章节">
        <button
          v-for="(c, i) in CHAPTERS"
          :key="c.id"
          type="button"
          :class="{ on: activeCh === i }"
          @click="gotoChapter(i)"
        >
          <i>{{ c.no }}</i>{{ c.label }}
        </button>
      </nav>

      <div class="lp-acts">
        <a class="lp-app" href="./citizen.html#/citizen?autologin=citizen&amp;app=1">市民 App</a>
        <a class="lp-ghost" href="./auth.html">登录</a>
        <a class="lp-solid" href="./auth.html">注册</a>
      </div>
    </header>

    <!-- 顶部细进度条 -->
    <div class="lp-progress" aria-hidden="true">
      <i :style="{ transform: `scaleX(${progress})` }" />
    </div>

    <!-- ---------------- §01 主张 ---------------- -->
    <section class="ch ch--hero" data-ch="c1">
      <img
        class="hero-img"
        src="/media/street-hero.png"
        alt="黄昏人行道：一名环卫工人正在清扫，地面留有烟头"
      />
      <div class="hero-veil" aria-hidden="true" />

      <div class="hero-inner">
        <p class="kicker">CIVIC FORENSICS · 烟踪智治</p>
        <h1>我们识别的不是烟头，<br />是动作</h1>
        <p class="lead">
          从连续视频中发现疑似抛掷过程，经人工复核转化为清理任务与治理线索。
          每一步都留下可回看的证据，而不是一句结论。
        </p>

        <div class="caps">
          <div v-for="c in CAPS" :key="c.k" class="cap">
            <span>{{ c.k }}</span>
            <strong>{{ c.v }}</strong>
            <em>{{ c.note }}</em>
          </div>
        </div>

        <div class="hero-cta">
          <a class="btn btn--solid" href="./citizen.html#/citizen?autologin=citizen&amp;app=1">打开市民端 App <i>→</i></a>
          <a class="btn btn--ghost hero-login" href="./auth.html">登录 / 注册</a>
        </div>
        <p class="hero-note">演示原型 · 全部为演示数据 · 共 5 屏，向下滚动</p>
      </div>

      <button class="hero-scroll" type="button" @click="gotoChapter(1)" aria-label="继续向下">
        <span /><i>SCROLL</i>
      </button>
    </section>

    <!-- ---------------- §02 断点 ---------------- -->
    <section class="ch ch--plain" data-ch="c2" data-reveal>
      <header class="sec-head">
        <p class="sec-no">02 / 断点</p>
        <h2>地上的一个烟头，<br />说不清任何事</h2>
        <p class="sec-lead">
          治理卡住的地方往往不是「没发现」，而是发现了却无法回溯过程：
          没有起止时刻、没有轨迹、没有落点依据，最后只剩一张无法说明来龙去脉的照片。
        </p>
      </header>

      <div class="contrast">
        <article v-for="c in CONTRAST" :key="c.tag" class="cs" :class="`cs--${c.tone}`">
          <p class="cs-tag">{{ c.tag }}</p>
          <h3>{{ c.title }}</h3>
          <div class="cs-lists">
            <div>
              <p class="cs-h">能说明</p>
              <ul>
                <li v-for="x in c.can" :key="x">{{ x }}</li>
              </ul>
            </div>
            <div>
              <p class="cs-h">{{ c.tone === 'live' ? '仍然不做' : '说明不了' }}</p>
              <ul>
                <li v-for="x in c.cant" :key="x">{{ x }}</li>
              </ul>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- ---------------- §03 机制 ---------------- -->
    <section class="ch ch--plain" data-ch="c3" data-reveal>
      <header class="sec-head">
        <p class="sec-no">03 / 机制</p>
        <h2>五段闭环，<br />一段都不会跳过</h2>
        <p class="sec-lead">
          从视频窗切片到区域复盘，每一段都有明确的产出物与责任人。
          任何一段缺失，事件就停在「未闭环」，而不是被悄悄结掉。
        </p>
      </header>

      <ol class="stages">
        <li v-for="s in STAGES" :key="s.key" class="stage">
          <div class="st-no">
            <span class="st-num">{{ s.no }}</span>
            <span class="st-rail" aria-hidden="true" />
          </div>
          <div class="st-body">
            <p class="st-key">{{ s.key }}</p>
            <h3>{{ s.title }}</h3>
            <p class="st-what">{{ s.what }}</p>
            <p class="st-out"><span>产出</span>{{ s.out }}</p>
          </div>
        </li>
      </ol>

      <div class="stats">
        <div v-for="s in stats" :key="s.label" class="stat">
          <p>{{ s.label }}</p>
          <strong>{{ s.value }}<i>{{ s.unit }}</i></strong>
          <span>{{ s.note }}</span>
        </div>
      </div>
      <p class="stats-note">数值随「平台配置 → 演示数据量级」切换，与当前档位一致。</p>

      <!-- 五段实景通栏：上面这五个阶段，各自对应的现场长这样 -->
      <figure class="strip">
        <img
          src="/media/scenes-strip.png"
          alt="五类现场实景：持烟识别、吸烟亭、烟头落地、摄像头识别、环卫协同处置"
        />
        <figcaption>
          <span v-for="s in SCENES" :key="s">{{ s }}</span>
        </figcaption>
      </figure>
    </section>

    <!-- ---------------- §04 证据 ---------------- -->
    <section class="ch ch--plain" data-ch="c4" data-reveal>
      <header class="sec-head">
        <p class="sec-no">04 / 证据</p>
        <h2>一段过程，<br />拆成能回看的帧</h2>
        <p class="sec-lead">
          候选事件不是一句结论，而是一组带时间码的画面。复核人员打开的就是下面这样一张原始画面：
          红框标出动作窗口，绿框标出落点，左上角是发生时刻——缺哪一项，哪一项就留空，
          不补、不猜。
        </p>
      </header>

      <div class="evidence">
        <figure class="ev-main">
          <img
            src="/design-assets/2/event_detection_evidence_photo.png"
            alt="监控画面：红框标出烟头动作，绿框标出烟头落点，左上角为发生时刻（演示素材）"
          />
          <figcaption>
            <span><i class="ev-dot ev-dot--action" />红框 · 动作窗口</span>
            <span><i class="ev-dot ev-dot--drop" />绿框 · 落点</span>
            <span><i class="ev-dot ev-dot--time" />左上 · 时间码</span>
          </figcaption>
        </figure>

        <div class="ev-side">
          <p class="ev-h">同一段视频里的三个关键帧</p>
          <div class="ev-frames">
            <figure v-for="f in FRAMES" :key="f.code">
              <img :src="f.src" :alt="f.alt" />
              <figcaption>
                <b>{{ f.code }}</b>
                <em>{{ f.ms }}</em>
                <span>{{ f.alt }}</span>
              </figcaption>
            </figure>
          </div>

          <ul class="ev-list">
            <li><b>起止时刻</b>精确到帧，不依赖人工回忆</li>
            <li><b>轨迹与落点</b>逐帧可回看，不做文字描述代替</li>
            <li><b>缺失即缺失</b>遮挡区间标为「证据缺失」，不自动补齐</li>
          </ul>

          <p class="ev-note">
            画面为演示素材，取自项目设计稿；识别管道尚未接入真实视频流。
          </p>
        </div>
      </div>
    </section>

    <!-- ---------------- §05 边界 ---------------- -->
    <section class="ch ch--last" data-ch="c5" data-reveal>
      <header class="sec-head">
        <p class="sec-no">05 / 边界</p>
        <h2>先说清楚<br />不做什么</h2>
      </header>

      <div class="bounds">
        <div v-for="b in BOUNDARIES" :key="b.k" class="bound">
          <p>{{ b.k }}</p>
          <span>{{ b.v }}</span>
        </div>
      </div>

      <!-- 手机 App 版入口：手机是市民端的主形态，这里把入口与真机预览放到首页 -->
      <section class="app-entry" data-testid="app-entry">
        <div class="app-copy">
          <span class="app-kicker">MOBILE APP · 市民端手机版</span>
          <h3>把「监督」装进口袋</h3>
          <p>
            手机版是市民端的主形态：底部五个入口，中间一颗放大的
            <b>监督拍照</b> 按钮，抬起手机就能拍，拍完当场拿到 AI 检测报告。
          </p>
          <ul class="app-points">
            <li><i>01</i><span><b>中间直接拍照</b>调起系统相机，拍完立刻做模型复检</span></li>
            <li><i>02</i><span><b>当场出报告</b>检出目标、置信度与证据链口径一次说清</span></li>
            <li><i>03</i><span><b>可以提异议</b>不同意 AI 判断就写理由，反馈直达管理端</span></li>
          </ul>
          <div class="app-acts">
            <a class="btn btn--solid" href="./citizen.html#/citizen?autologin=citizen&amp;app=1">打开市民端 App <i>→</i></a>
            <button class="btn btn--ghost" type="button" @click="togglePhone">
              {{ phoneOn ? '收起预览' : '切换预览' }}
            </button>
          </div>
        </div>
        <div class="app-phone" :class="{ live: phoneOn }">
          <div class="phone-frame">
            <iframe
              v-if="phoneOn"
              src="./citizen.html#/citizen-login"
              title="市民端手机版预览"
              loading="lazy"
            ></iframe>
            <div v-else class="phone-idle">点「切换预览」载入手机版界面</div>
          </div>
          <small>真机视口 390 宽 · 预览高度 640 · 底部那颗放大的「监督拍照」就是 App 主入口</small>
        </div>
      </section>

      <div class="cta-box">
        <div>
          <p class="cta-h">从任意一个端开始</p>
          <p class="cta-p">
            市民上报线索、环卫接单处置、管理员研判调度——三个端共享同一份事件状态，
            一处变更其余两端立即可见。
          </p>
        </div>
        <div class="cta-acts">
          <a class="btn btn--solid" href="./auth.html">登录 / 注册 <i>→</i></a>
          <a class="btn btn--ghost" href="./citizen.html">进入市民端</a>
          <a class="btn btn--ghost" href="./worker.html">进入环卫端</a>
          <a class="btn btn--ghost" href="./admin.html">进入管理端</a>
        </div>
      </div>

      <footer class="foot">
        <img src="/logo-mark.png" alt="烟踪智治" />
        <small>烟踪智治 · 公共场所扔烟头行为证据复核与治理闭环原型 · © 2026</small>
      </footer>
    </section>
  </div>
</template>

<style scoped>
/* ============================================================
   令牌：仅本页生效，与后台 / 各端互不影响
   ============================================================ */
.lp {
  --ink: #080d15;
  --ink-2: #0d1522;
  --line: rgba(255, 255, 255, 0.09);
  --line-2: rgba(255, 255, 255, 0.16);
  --text: #eef3f8;
  --muted: rgba(238, 243, 248, 0.56);
  --muted-2: rgba(238, 243, 248, 0.36);
  --ember: #ff6847;
  --cyan: #45cfe0;
  --moss: #3ecf8e;

  position: relative;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--ink);
  color: var(--text);
  font-family: "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
}

/* 顶部柔光 */
.lp-glow {
  position: fixed;
  left: 50%;
  top: -30vh;
  width: 120vw;
  height: 80vh;
  transform: translateX(-50%);
  background: radial-gradient(
    42% 46% at 50% 50%,
    rgba(69, 207, 224, 0.16),
    rgba(255, 104, 71, 0.07) 46%,
    transparent 72%
  );
  pointer-events: none;
  z-index: 0;
}

/* ============================================================
   顶栏
   ============================================================ */
.lp-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 22px;
  height: 66px;
  padding: 0 clamp(18px, 4vw, 44px);
  border-bottom: 1px solid transparent;
  transition: background 0.24s, border-color 0.24s;
}
.lp.solid .lp-bar {
  border-bottom-color: var(--line);
  background: rgba(8, 13, 21, 0.76);
  backdrop-filter: blur(14px);
}

.lp-brand {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  flex: none;
  color: inherit;
  text-decoration: none;
}
.lp-brand img {
  height: 30px;
  width: auto;
  /* 透明底徽标：深底上提亮一点，让绿色圆环与蓝色天际线都看得清 */
  filter: brightness(1.18) saturate(1.05);
}
.lp-brand b {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.lp-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.lp-nav::-webkit-scrollbar {
  display: none;
}
.lp-nav button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.16s, background 0.16s;
}
.lp-nav button i {
  font-family: Consolas, monospace;
  font-size: 10px;
  font-style: normal;
  opacity: 0.5;
}
.lp-nav button:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.05);
}
.lp-nav button.on {
  color: var(--text);
  background: rgba(255, 255, 255, 0.08);
}
.lp-nav button.on i {
  color: var(--cyan);
  opacity: 1;
}

.lp-acts {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  flex: none;
}
.lp-ghost,
.lp-solid,
.lp-app {
  padding: 8px 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.16s, border-color 0.16s, transform 0.16s;
}
.lp-app {
  border: 1px solid rgba(69, 207, 224, 0.42);
  color: #7deaf2;
  background: rgba(69, 207, 224, 0.1);
}
.lp-app:hover {
  border-color: rgba(125, 234, 242, 0.8);
  background: rgba(69, 207, 224, 0.17);
}
.lp-ghost {
  border: 1px solid var(--line-2);
  color: var(--text);
}
.lp-ghost:hover {
  border-color: rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.06);
}
.lp-solid {
  border: 1px solid transparent;
  background: var(--text);
  color: var(--ink);
}
.lp-solid:hover {
  transform: translateY(-1px);
}

/* 顶部进度条 */
.lp-progress {
  position: sticky;
  top: 66px;
  z-index: 21;
  height: 1px;
  margin-top: -1px;
}
.lp-progress i {
  display: block;
  height: 100%;
  transform-origin: 0 50%;
  background: linear-gradient(90deg, var(--cyan), var(--ember));
}

/* ============================================================
   通用章节容器 + 显影
   ============================================================ */
.ch {
  position: relative;
  z-index: 1;
  padding: clamp(76px, 11vh, 132px) clamp(20px, 6vw, 84px);
  opacity: 0;
  transform: translateY(26px);
  transition: opacity 0.7s cubic-bezier(0.22, 0.61, 0.36, 1),
    transform 0.7s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.ch.in {
  opacity: 1;
  transform: none;
}
/* 首屏不参与显影（第一眼就该看到） */
.ch--hero {
  opacity: 1;
  transform: none;
}

.ch--plain,
.ch--last {
  max-width: 1200px;
  margin: 0 auto;
}
/* 最后一屏也撑满一屏：否则滚到它时页面已到底，
   顶部永远差一截，「翻到第 5 屏」的手感会不完整 */
.ch--last {
  min-height: 100vh;
  padding-bottom: clamp(60px, 10vh, 110px);
}

/* 章节头 */
.sec-head {
  max-width: 780px;
}
.sec-no {
  font-family: Consolas, monospace;
  font-size: 12px;
  letter-spacing: 0.2em;
  color: var(--cyan);
}
.sec-head h2 {
  margin-top: 18px;
  font-size: clamp(30px, 4.2vw, 54px);
  line-height: 1.12;
  letter-spacing: -0.02em;
  font-weight: 700;
}
.sec-lead {
  margin-top: 22px;
  max-width: 640px;
  color: var(--muted);
  font-size: clamp(14px, 1.2vw, 16px);
  line-height: 1.95;
}

/* ============================================================
   §01 Hero（整屏）
   ============================================================ */
.ch--hero {
  display: flex;
  align-items: center;
  min-height: 100vh;
  margin-top: -67px; /* 让顶栏浮在图上 */
  padding: 0;
  overflow: hidden;
}
.hero-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 62% 50%;
}
.hero-veil {
  position: absolute;
  inset: 0;
  background: linear-gradient(
      100deg,
      rgba(6, 10, 17, 0.96) 0%,
      rgba(6, 10, 17, 0.86) 32%,
      rgba(6, 10, 17, 0.44) 58%,
      rgba(6, 10, 17, 0.5) 100%
    ),
    linear-gradient(180deg, rgba(6, 10, 17, 0.72) 0%, transparent 22%, rgba(6, 10, 17, 0.86) 100%);
}
.hero-inner {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: clamp(120px, 20vh, 180px) clamp(20px, 6vw, 84px) clamp(80px, 12vh, 120px);
}
.kicker {
  font-family: Consolas, monospace;
  font-size: 12px;
  letter-spacing: 0.24em;
  color: var(--ember);
}
.hero-inner h1 {
  margin-top: 22px;
  max-width: 15ch;
  font-size: clamp(40px, 6.4vw, 88px);
  line-height: 1.06;
  letter-spacing: -0.035em;
  font-weight: 800;
}
.lead {
  margin-top: 26px;
  max-width: 560px;
  color: var(--muted);
  font-size: clamp(14px, 1.3vw, 17px);
  line-height: 1.95;
}

/* 三胶囊（原 Hero 保留） */
.caps {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 38px;
}
.cap {
  min-width: 142px;
  padding: 12px 16px;
  border: 1px solid var(--line-2);
  border-radius: 12px;
  background: rgba(10, 16, 26, 0.56);
  backdrop-filter: blur(5px);
}
.cap span {
  display: block;
  font-family: Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--cyan);
}
.cap strong {
  display: block;
  margin-top: 5px;
  font-size: 15px;
  font-weight: 700;
}
.cap em {
  display: block;
  margin-top: 3px;
  color: var(--muted-2);
  font-size: 11px;
  font-style: normal;
}

.hero-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 40px;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 13px 24px;
  border-radius: 11px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: transform 0.16s, background 0.16s, border-color 0.16s;
}
.btn i {
  font-style: normal;
  transition: transform 0.16s;
}
.btn:hover i {
  transform: translateX(4px);
}
.btn--solid {
  border: 1px solid transparent;
  background: var(--text);
  color: var(--ink);
}
.btn--solid:hover {
  transform: translateY(-1px);
}
.btn--ghost {
  border: 1px solid var(--line-2);
  /* 必须显式透明：<button> 有 UA 默认底色（浅灰），
     而 .btn--ghost 的文字是白色 → 用 <button> 时会变成"白底白字"看不见。 */
  background: transparent;
  color: var(--text);
}
.btn--ghost:hover {
  border-color: rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.06);
}
.hero-login {
  border-color: rgba(255, 255, 255, 0.55);
  background: rgba(5, 11, 18, 0.72);
  color: #fff;
}
.hero-note {
  margin-top: 30px;
  color: var(--muted-2);
  font-size: 12px;
}

.hero-scroll {
  position: absolute;
  left: 50%;
  bottom: 26px;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
}
.hero-scroll span {
  width: 1px;
  height: 34px;
  background: linear-gradient(180deg, transparent, var(--text));
  animation: fall 1.9s ease-in-out infinite;
}
.hero-scroll i {
  font-family: Consolas, monospace;
  font-size: 10px;
  font-style: normal;
  letter-spacing: 0.2em;
  color: var(--muted-2);
}
@keyframes fall {
  0% {
    opacity: 0;
    transform: scaleY(0.35);
  }
  40% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: scaleY(1);
  }
}

/* ============================================================
   §02 断点对照
   ============================================================ */
.contrast {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 52px;
}
.cs {
  padding: 26px 24px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.012));
}
.cs--live {
  border-color: rgba(69, 207, 224, 0.34);
  box-shadow: 0 22px 60px -30px rgba(69, 207, 224, 0.5);
}
.cs-tag {
  display: inline-block;
  padding: 4px 10px;
  border: 1px solid var(--line-2);
  border-radius: 999px;
  font-family: Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--muted);
}
.cs--live .cs-tag {
  border-color: rgba(69, 207, 224, 0.36);
  color: var(--cyan);
}
.cs h3 {
  margin-top: 16px;
  font-size: clamp(20px, 2.2vw, 26px);
  font-weight: 700;
  letter-spacing: -0.01em;
}
.cs-lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-top: 22px;
}
.cs-h {
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
  color: var(--muted-2);
  font-size: 11px;
  letter-spacing: 0.1em;
}
.cs ul {
  margin-top: 12px;
  list-style: none;
}
.cs li {
  position: relative;
  padding-left: 14px;
  color: var(--muted);
  font-size: 13px;
  line-height: 2;
}
.cs li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 11px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--muted-2);
}
.cs--live li {
  color: rgba(238, 243, 248, 0.78);
}
.cs--live li::before {
  background: var(--cyan);
}

/* ============================================================
   §03 五段机制
   ============================================================ */
.stages {
  margin-top: 52px;
  list-style: none;
}
.stage {
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
  gap: 20px;
  padding: 26px 0;
  border-top: 1px solid var(--line);
}
.stage:last-child {
  border-bottom: 1px solid var(--line);
}
.st-no {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.st-num {
  font-family: Consolas, monospace;
  font-size: 30px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.2);
  transition: color 0.3s;
}
.stage:hover .st-num {
  color: var(--ember);
}
.st-rail {
  flex: 1;
  width: 1px;
  background: linear-gradient(180deg, var(--line-2), transparent);
}
.st-body {
  max-width: 720px;
}
.st-key {
  font-family: Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.2em;
  color: var(--cyan);
}
.st-body h3 {
  margin-top: 8px;
  font-size: clamp(19px, 1.9vw, 24px);
  font-weight: 700;
}
.st-what {
  margin-top: 10px;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.9;
}
.st-out {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  color: var(--text);
  font-size: 12.5px;
}
.st-out span {
  padding: 3px 8px;
  border: 1px solid var(--line-2);
  border-radius: 6px;
  color: var(--muted);
  font-size: 10px;
  letter-spacing: 0.12em;
}

/* 统计条 */
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin-top: 52px;
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
  background: var(--line);
}
.stat {
  padding: 22px 22px 20px;
  background: var(--ink-2);
}
.stat p {
  color: var(--muted-2);
  font-size: 12px;
}
.stat strong {
  display: block;
  margin-top: 10px;
  font-family: Consolas, monospace;
  font-size: clamp(24px, 2.6vw, 34px);
  font-weight: 700;
  letter-spacing: -0.02em;
}
.stat strong i {
  margin-left: 3px;
  font-size: 13px;
  font-style: normal;
  color: var(--muted);
}
.stat span {
  display: block;
  margin-top: 6px;
  color: var(--muted-2);
  font-size: 11px;
}
.stats-note {
  margin-top: 14px;
  color: var(--muted-2);
  font-size: 11.5px;
}

/* ============================================================
   §03 五段实景通栏
   ============================================================ */
.strip {
  margin-top: 34px;
  border: 1px solid var(--line);
  border-radius: 16px;
  overflow: hidden;
}
.strip img {
  display: block;
  width: 100%;
  height: auto;
}
.strip figcaption {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  padding: 14px 18px;
  border-top: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
}
.strip figcaption span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-size: 11.5px;
}
.strip figcaption span::before {
  content: "";
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--moss);
}

/* ============================================================
   §04 证据
   ============================================================ */
.evidence {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(0, 0.88fr);
  gap: 18px;
  margin-top: 52px;
}
.ev-main {
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
}
.ev-main img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 10px;
}
.ev-main figcaption {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  padding: 14px 6px 4px;
}
.ev-main figcaption span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-size: 11.5px;
}
.ev-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  flex: none;
}
.ev-dot--action {
  background: #ff4d4f;
}
.ev-dot--drop {
  background: #52c41a;
}
.ev-dot--time {
  background: var(--muted-2);
}

.ev-side {
  display: flex;
  flex-direction: column;
  padding: 22px 22px 20px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.012));
}
.ev-h {
  font-family: Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--cyan);
}
.ev-frames {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
}
.ev-frames figure {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.24);
}
.ev-frames img {
  display: block;
  width: 100%;
  height: 54px;
  object-fit: cover;
}
.ev-frames figcaption {
  padding: 8px 9px 9px;
}
.ev-frames b {
  display: block;
  font-family: Consolas, monospace;
  font-size: 11px;
  color: var(--text);
}
.ev-frames em {
  display: block;
  margin-top: 2px;
  font-family: Consolas, monospace;
  font-size: 10px;
  font-style: normal;
  color: var(--cyan);
}
.ev-frames span {
  display: block;
  margin-top: 5px;
  color: var(--muted-2);
  font-size: 10.5px;
  line-height: 1.5;
}
.ev-list {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
  list-style: none;
}
.ev-list li {
  position: relative;
  padding-left: 15px;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.95;
}
.ev-list li + li {
  margin-top: 8px;
}
.ev-list li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 10px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--muted-2);
}
.ev-list b {
  color: var(--text);
  font-weight: 600;
}
.ev-note {
  margin-top: auto;
  padding-top: 18px;
  color: var(--muted-2);
  font-size: 11px;
  line-height: 1.7;
}

/* ============================================================
   §05 边界 + 收束
   ============================================================ */
.bounds {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 44px;
}
.bound {
  padding: 24px 22px;
  border: 1px solid var(--line);
  border-left: 2px solid var(--ember);
  border-radius: 4px 14px 14px 4px;
  background: rgba(255, 255, 255, 0.025);
}
.bound p {
  font-family: Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--ember);
}
.bound span {
  display: block;
  margin-top: 12px;
  color: rgba(238, 243, 248, 0.72);
  font-size: 13.5px;
  line-height: 1.95;
}

.cta-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-top: 34px;
  padding: 30px 28px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(69, 207, 224, 0.07), rgba(255, 255, 255, 0.012));
}
.cta-h {
  font-family: Consolas, monospace;
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--cyan);
}
.cta-p {
  max-width: 620px;
  margin-top: 12px;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.95;
}
/* ---------------- 手机 App 版入口 ---------------- */
.app-entry {
  display: grid;
  grid-template-columns: 1fr 390px;
  gap: 44px;
  align-items: center;
  margin-top: 56px;
  padding: 34px 36px;
  border: 1px solid var(--line-2);
  border-radius: 22px;
  background: linear-gradient(140deg, rgba(69, 207, 224, 0.08), rgba(255, 255, 255, 0.02));
}
.app-kicker { color: var(--cyan); font: 10.5px Consolas, monospace; letter-spacing: 0.2em; }
.app-copy h3 { margin: 12px 0 10px; font-size: 27px; }
.app-copy > p { max-width: 560px; margin: 0; color: var(--muted); font-size: 14px; line-height: 1.9; }
.app-copy > p b { color: var(--text); }
.app-points { display: grid; gap: 10px; margin: 20px 0 24px; padding: 0; list-style: none; }
.app-points li { display: flex; gap: 11px; align-items: flex-start; }
.app-points i {
  flex: none;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(69, 207, 224, 0.14);
  color: var(--cyan);
  font: 700 10px Consolas, monospace;
  font-style: normal;
}
.app-points span { color: var(--muted); font-size: 13px; line-height: 1.7; }
.app-points span b { color: var(--text); }
.app-acts { display: flex; gap: 10px; flex-wrap: wrap; }
.app-phone { display: grid; gap: 12px; justify-items: center; }
.phone-frame {
  position: relative;
  width: 390px;
  height: 640px;
  padding: 12px;
  border: 1px solid var(--line-2);
  border-radius: 40px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.02));
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.45), inset 0 0 0 2px rgba(255, 255, 255, 0.04);
}
.phone-frame::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 18px;
  z-index: 2;
  width: 86px;
  height: 6px;
  transform: translateX(-50%);
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.16);
}
.phone-frame iframe { display: block; width: 100%; height: 100%; border: 0; border-radius: 30px; background: #fff; }
.phone-idle {
  display: grid;
  place-items: center;
  height: 100%;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--muted-2);
  font-size: 12px;
}
.app-phone small { max-width: 390px; color: var(--muted-2); font-size: 11px; line-height: 1.6; text-align: center; }

.cta-acts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.foot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  margin-top: 64px;
  padding-top: 30px;
  border-top: 1px solid var(--line);
}
.foot img {
  height: 34px;
  width: auto;
  opacity: 0.72;
  filter: brightness(1.15);
}
.foot small {
  color: var(--muted-2);
  font-size: 11.5px;
  text-align: center;
}

/* ============================================================
   响应式
   ============================================================ */
@media (max-width: 1024px) {
  .contrast,
  .evidence,
  .bounds,
  .app-entry {
    grid-template-columns: 1fr;
  }
  .app-entry { gap: 28px; }
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .phone-frame { width: 100%; max-width: 390px; }
}

@media (max-width: 760px) {
  .lp-nav {
    display: none;
  }
  .lp-bar {
    height: 60px;
    gap: 12px;
  }
  .lp-progress {
    top: 60px;
  }
  .lp-brand img {
    height: 28px;
  }
  .lp-ghost,
  .lp-solid,
  .lp-app {
    padding: 7px 13px;
    font-size: 12.5px;
  }
  .ch--hero {
    margin-top: -61px;
  }
  .hero-img {
    object-position: 70% 50%;
  }
  .hero-veil {
    background: linear-gradient(
      180deg,
      rgba(6, 10, 17, 0.82) 0%,
      rgba(6, 10, 17, 0.9) 55%,
      rgba(6, 10, 17, 0.96) 100%
    );
  }
  .hero-inner {
    padding-top: 116px;
  }
  .hero-inner h1 {
    font-size: clamp(32px, 9vw, 44px);
  }
  .caps {
    gap: 8px;
  }
  .cap {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
    padding: 10px 12px;
  }
  .hero-cta .btn {
    flex: 1 1 100%;
    justify-content: center;
  }
  .cs-lists {
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .stats {
    grid-template-columns: 1fr;
  }
  .cta-box {
    flex-direction: column;
    align-items: stretch;
  }
  .cta-acts .btn {
    flex: 1 1 100%;
    justify-content: center;
  }
  /* 窄屏下三张帧缩略只剩帧号与时刻，描述文字省掉（列宽不够） */
  .ev-frames span {
    display: none;
  }
  .ev-main figcaption {
    gap: 6px 12px;
  }
}

/* 1366×768 等常见笔记本首屏：主标题、说明、入口按钮完整落在可视区内。 */
@media (min-width: 761px) and (max-height: 820px) {
  .hero-inner { padding-top: 92px; padding-bottom: 38px; }
  .hero-inner h1 { margin-top: 14px; font-size: clamp(44px, 5.2vw, 70px); }
  .lead { margin-top: 14px; line-height: 1.72; }
  .caps { margin-top: 20px; }
  .hero-cta { margin-top: 22px; }
  .hero-note { margin-top: 14px; }
}

/* 尊重「减少动态效果」 */
@media (prefers-reduced-motion: reduce) {
  .ch {
    opacity: 1;
    transform: none;
    transition: none;
  }
  .hero-scroll span {
    animation: none;
  }
}
</style>
