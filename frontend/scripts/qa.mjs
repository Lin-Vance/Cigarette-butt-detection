/**
 * 全站质检脚本（CDP 驱动，单浏览器会话内跑完全部用例）
 *
 * 检查项：
 *   1. 每条路由是否渲染出预期根节点（防止悄悄 fallback 回首页或落在占位页）
 *   2. 运行时异常 / console.error
 *   3. 资源请求 4xx-5xx（含图片 404）
 *   4. 文档级横向溢出（跳过可滚动祖先内的元素）
 *   5. 关键交互：首页锚点滚动、治理平台入口跳转、市民端 tab 与上报表单、管理员登录
 *
 * 用法：
 *   node scripts/qa.mjs                 # 默认 http://127.0.0.1:5180/
 *   BASE=http://127.0.0.1:5181/ node scripts/qa.mjs
 */
import { spawn } from 'node:child_process'
import path from 'node:path'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const PORT = 9500 + (process.pid % 400)
const PROFILE = path.join(process.env.TEMP || '/tmp', `edge-qa-${process.pid}`)
const BASE = process.env.BASE || 'http://127.0.0.1:5180/'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function waitForTarget(tries = 100) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`)
      const list = await r.json()
      const page = list.find((t) => t.type === 'page')
      if (page && page.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch {
      /* 端口未就绪 */
    }
    await sleep(250)
  }
  throw new Error('CDP 端口未就绪')
}

class CDP {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    this.listeners = new Map()
    this.logs = []
    this.netBad = []
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id)
        this.pending.delete(m.id)
        if (m.error) reject(new Error(JSON.stringify(m.error)))
        else resolve(m.result)
      } else if (m.method) {
        if (this.listeners.has(m.method)) this.listeners.get(m.method)(m.params)
        this._collect(m)
      }
    })
  }

  _collect(m) {
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params.exceptionDetails || {}
      const desc = (d.exception && d.exception.description) || d.text || 'exception'
      this.logs.push('EXC ' + String(desc).split('\n')[0])
    } else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      const text = (m.params.args || [])
        .map((a) => a.value ?? a.description ?? '')
        .join(' ')
      this.logs.push('ERR ' + text)
    } else if (m.method === 'Network.responseReceived') {
      const r = m.params.response || {}
      if (r.status >= 400 && !/favicon/.test(r.url)) {
        this.netBad.push(r.status + ' ' + String(r.url).replace(BASE, '').slice(0, 110))
      }
    }
  }

  send(method, params = {}) {
    const id = ++this.id
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }

  once(method) {
    return new Promise((resolve) => this.listeners.set(method, resolve))
  }

  onceTimeout(method, ms) {
    return new Promise((resolve) => {
      const t = setTimeout(() => {
        this.listeners.delete(method)
        resolve(null)
      }, ms)
      this.listeners.set(method, (p) => {
        clearTimeout(t)
        resolve(p)
      })
    })
  }

  async evaluate(expression) {
    const { result, exceptionDetails } = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    })
    if (exceptionDetails) {
      throw new Error('eval: ' + (exceptionDetails.text || 'error'))
    }
    return result.value
  }

  reset() {
    this.logs = []
    this.netBad = []
  }
}

/* ------------------------------------------------------------------ */

const results = []
const note = (status, name, extra = '') => results.push({ status, name, extra })

const DESKTOP = { w: 1440, h: 960 }

/** 路由用例：hash / 名称 / 期望出现的根节点标识 */
const ROUTES = [
  // 注意：签名要用**挂载后不会变**的类名。根节点会在 onMounted 里追加状态类
  // （如 `.au` → `.au ready`），用 `class="au"` 这样的精确串会误判为未渲染。
  ['', '入口页 index.html（5 屏长滚动）', 'lp-glow'],
  ['auth', '登录 / 注册', 'au-bloom'],
  ['/worker.html', '环卫工人端 worker.html', 'class="end-shell"'],
  ['citizen-login', '市民登录', 'citizen-login'],
  ['citizen?autologin=citizen', '市民用户端', 'citizen-app'],
  ['login', '管理员登录', 'au-auth'],
  ['platform/overview?autologin=1', '后台 01 总览', 'class="overview"'],
  ['platform/governance?autologin=1', '后台 02 治理态势', 'class="ad-page"'],
  ['platform/device-status?autologin=1', '后台 03 设备地图', 'class="ad-page"'],
  ['platform/workboard?autologin=1', '后台 04 区域任务分布', 'class="ad-page"'],
  ['platform/alerts?autologin=1', '后台 05 告警列表', 'class="ad-page"'],
  ['platform/report?autologin=1', '后台 06 事件报表', 'class="ad-page"'],
  ['platform/dispatch-pool?autologin=1', '后台 07 任务池', 'class="ad-page"'],
  ['platform/dispatch-records?autologin=1', '后台 08 调度记录', 'class="ad-page"'],
  ['platform/gis?autologin=1', '后台 09 全域 GIS', 'class="ad-page"'],
  ['platform/device-archive?autologin=1', '后台 10 设备档案', 'class="ad-page"'],
  ['platform/sanitation?autologin=1', '后台 11 环卫资源', 'class="ad-page"'],
  ['platform/ai-model?autologin=1', '后台 12 模型与数据集', 'class="ad-page"'],
  ['platform/ai-config?autologin=1', '后台 13 AI 识别配置', 'class="ad-page"'],
  ['platform/analysis?autologin=1', '后台 14 数据分析', 'class="ad-page"'],
  ['platform/users?autologin=1', '后台 15 用户账号', 'class="ad-page"'],
  ['platform/law-cases?autologin=1', '后台 19 执法线索核查', 'class="ad-page"'],
  ['platform/law-trail?autologin=1', '后台 20 处置留痕', 'class="ad-page"'],
  ['platform/platform-config?autologin=1', '后台 16 平台配置', 'class="ad-page"'],
  ['platform/audit?autologin=1', '后台 17 审计日志', 'class="ad-page"']
]

const MOBILE_ROUTES = [
  ['', '入口页 @390'],
  ['auth', '登录 / 注册 @390'],
  ['/worker.html', '环卫工人端 @390'],
  ['citizen-login', '市民登录 @390'],
  ['citizen?autologin=citizen', '市民用户端 @390'],
  ['login', '管理员登录 @390']
]

const edge = spawn(
  EDGE,
  [
    '--headless=new',
    '--disable-gpu',
    '--disable-extensions',
    '--disable-component-extensions-with-background-pages',
    '--no-first-run',
    '--no-default-browser-check',
    '--hide-scrollbars',
    `--user-data-dir=${PROFILE}`,
    `--remote-debugging-port=${PORT}`,
    'about:blank'
  ],
  { stdio: 'ignore' }
)

let code = 0
try {
  const wsUrl = await waitForTarget()
  const ws = new WebSocket(wsUrl)
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true })
    ws.addEventListener('error', reject, { once: true })
  })
  const cdp = new CDP(ws)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Network.enable')

  /** 导航到指定位置。
   *  - hash 路由：goto('platform/alerts?autologin=1')
   *  - 多页入口：goto('/worker.html')（以 / 开头视为相对站点根的路径） */
  async function goto(hash, view) {
    cdp.reset()
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: view.w,
      height: view.h,
      deviceScaleFactor: 1,
      mobile: view.w < 700
    })
    let target
    if (hash.startsWith('/')) target = BASE.replace(/\/$/, '') + hash
    else if (hash === 'auth') target = `${BASE}auth.html#/auth`
    else if (hash === 'login') target = `${BASE}auth.html#/auth?role=admin`
    else if (hash.startsWith('citizen')) target = `${BASE}citizen.html#/${hash}`
    else if (hash.startsWith('platform/')) target = `${BASE}admin.html#/${hash}`
    else target = `${BASE}index.html#/${hash}`
    await cdp.send('Page.navigate', { url: 'about:blank' })
    await sleep(120)
    const loaded = cdp.onceTimeout('Page.loadEventFired', 6000)
    await cdp.send('Page.navigate', { url: target })
    await loaded
    await sleep(view.wait ?? 1400)
    return { logs: cdp.logs.slice(), netBad: cdp.netBad.slice() }
  }

  const OVERFLOW_CHECK = `(() => {
    const vw = document.documentElement.clientWidth
    const inScroller = (el) => {
      let p = el.parentElement
      while (p && p !== document.body) {
        if (/(auto|scroll)/.test(getComputedStyle(p).overflowX)) return true
        p = p.parentElement
      }
      return false
    }
    const out = []
    document.querySelectorAll('body *').forEach(el => {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) return
      if (r.right > vw + 1 || r.left < -1) {
        if (inScroller(el)) return
        const cn = typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\\s+/).join('.') : ''
        out.push(el.tagName.toLowerCase() + cn + '=' + Math.round(r.left) + ',' + Math.round(r.right))
      }
    })
    return JSON.stringify({
      vw,
      sw: document.documentElement.scrollWidth,
      sh: document.documentElement.scrollHeight,
      bad: out.slice(0, 8)
    })
  })()`

  /* ---------------- 1. 路由渲染 / 控制台 / 资源 ---------------- */

  console.log('=== 路由巡检 (desktop ' + DESKTOP.w + 'x' + DESKTOP.h + ') ===')
  for (const [hash, name, sig] of ROUTES) {
    const { logs, netBad } = await goto(hash, DESKTOP)
    const state = await cdp.evaluate(`(() => {
      const app = document.getElementById('app')
      const html = app ? app.innerHTML : ''
      return JSON.stringify({
        len: html.length,
        sig: html.includes(${JSON.stringify(sig)}),
        placeholder: /待迁移|PagePlaceholder|placeholder-note/.test(html),
        title: document.title
      })
    })()`)
    const s = JSON.parse(state)
    const problems = []
    if (!s.sig) problems.push('未渲染出预期根节点 ' + sig)
    if (s.len < 400) problems.push('内容过少 len=' + s.len)
    if (s.placeholder) problems.push('命中了占位页')
    if (logs.length) problems.push('控制台 ' + logs.length + ' 条: ' + logs[0].slice(0, 120))
    if (netBad.length) problems.push('资源失败 ' + netBad[0])
    if (problems.length) note('FAIL', name, problems.join(' / '))
    else note('OK', name, s.title.replace(' · 烟踪智治', ''))
  }

  /* ---------------- 2. 移动端视口 ---------------- */

  console.log('=== 移动端巡检 (390x844) ===')
  for (const [hash, name] of MOBILE_ROUTES) {
    const { logs, netBad } = await goto(hash, { w: 390, h: 844 })
    const raw = await cdp.evaluate(OVERFLOW_CHECK)
    const o = JSON.parse(raw)
    const problems = []
    if (o.sw > o.vw + 1) problems.push(`横向溢出 ${o.vw}/${o.sw}` + (o.bad.length ? ' → ' + o.bad[0] : ''))
    if (logs.length) problems.push('控制台: ' + logs[0].slice(0, 120))
    if (netBad.length) problems.push('资源失败 ' + netBad[0])
    if (problems.length) note('FAIL', name, problems.join(' / '))
    else note('OK', name, `${o.sw}px / 高 ${o.sh}px`)
  }

  /** 清掉演示登录态：?autologin=1 会写 localStorage 并持久化，
   *  不清会导致登录页被守卫直接重定向到后台，用例会误判失败 */
  async function clearAuth(view) {
    await goto('', view)
    await cdp.evaluate(`localStorage.clear()`)
    await sleep(200)
  }

  /* ---------------- 3. 入口页：5 屏长滚动叙事 ---------------- */

  console.log('=== 入口页长滚动 ===')
  await goto('', DESKTOP)
  const lpRes = await cdp.evaluate(`(async () => {
    const root = document.querySelector('.lp')
    if (!root) return JSON.stringify({ err: 'no .lp（入口页未渲染）' })
    const secs = [...root.querySelectorAll('[data-ch]')]
    const btns = [...root.querySelectorAll('.lp-nav button')]
    const hits = []
    for (let i = 0; i < btns.length; i++) {
      btns[i].click()
      await new Promise(r => setTimeout(r, 1000))
      const s = secs[i]
      if (!s) { hits.push('miss' + i); continue }
      const diff = Math.round(s.offsetTop - root.scrollTop)
      // 最后一屏若已滚到页面底部，就算命中（再往下没有可滚空间了）
      const atBottom = root.scrollTop + root.clientHeight >= root.scrollHeight - 4
      hits.push(Math.abs(diff) < 12 || (atBottom && diff > 0) ? 'ok' : 'off' + diff)
    }
    // §04 原「分端」三卡已改为证据链屏，端入口改由 §05 的 .cta-acts 承载
    const ends = [...root.querySelectorAll('.cta-acts a')].map(a => a.getAttribute('href'))
    const acts = [...root.querySelectorAll('.lp-acts a')].map(a => a.getAttribute('href'))
    return JSON.stringify({
      chapters: secs.length,
      nav: btns.length,
      badHits: hits.filter(h => h !== 'ok'),
      ends,
      acts,
      progress: !!root.querySelector('.lp-progress i'),
      heroImgs: root.querySelectorAll('.hero-img, .hero-veil').length,
      caps: root.querySelectorAll('.cap').length
    })
  })()`)
  const lp = JSON.parse(lpRes)
  if (lp.err) note('FAIL', '入口页 5 屏长滚动', lp.err)
  else {
    const probs = []
    if (lp.chapters !== 5) probs.push('章节数 ' + lp.chapters + '（应为 5）')
    if (lp.nav !== lp.chapters) probs.push('顶栏项数与章节不符 ' + lp.nav)
    if (lp.badHits.length) probs.push('顶栏跳转未命中 ' + lp.badHits.join(','))
    if (lp.caps !== 3) probs.push('首屏三胶囊 ' + lp.caps + '（应为 3）')
    if (!lp.progress) probs.push('缺滚动进度条')
    if (lp.heroImgs !== 2) probs.push('首屏背景层缺失')
    if (probs.length) note('FAIL', '入口页 5 屏长滚动', probs.join(' / '))
    else note('OK', '入口页 5 屏长滚动', `5 屏 · 顶栏 5 项全部命中 · 首屏三胶囊齐 · 进度条正常`)
  }

  // 端入口与登录注册入口必须是**真实页面链接**（不是站内 hash 路由）
  if (!lp.err) {
    const probs = []
    const wantEnds = ['./citizen.html', './worker.html', './admin.html']
    for (const h of wantEnds) if (!lp.ends || !lp.ends.includes(h)) probs.push('缺端入口 ' + h)
    if (!lp.acts || lp.acts.filter((h) => h === './auth.html').length < 2 || !lp.acts.includes('./citizen.html#/citizen?app=1'))
      probs.push('首屏入口不完整：' + (lp.acts || []).join(','))
    if (probs.length) note('FAIL', '入口页真实跳转链接', probs.join(' / '))
    else note('OK', '入口页真实跳转链接', `CTA 区端入口 3 个 + 登录/注册 ${lp.acts.length} 个，全部为 .html 页面链接`)
  }

  // 换端入口只保留「入口页 CTA 卡片 + 顶栏登录/注册」。
  // 底部那条 .yz-ends 调试切换条已按用户要求移除（点它进登录页与正式入口不一致），
  // 这里做**反向断言**，防止以后被误加回来。
  {
    const ends = JSON.parse(
      await cdp.evaluate(
        `JSON.stringify({
          bar: document.querySelectorAll('.yz-ends, .es-cross').length,
          cta: [...document.querySelectorAll('.cta-acts a')].map(a => a.getAttribute('href'))
        })`
      )
    )
    const need = ['./citizen.html', './worker.html', './admin.html']
    const missing = need.filter((h) => !ends.cta.includes(h))
    if (ends.bar !== 0) {
      note('FAIL', '换端入口（入口页 CTA）', `底部调试切换条应已移除，实际仍有 ${ends.bar} 个`)
    } else if (missing.length) {
      note('FAIL', '换端入口（入口页 CTA）', 'CTA 缺 ' + missing.join(','))
    } else {
      note('OK', '换端入口（入口页 CTA）', `底部调试条已移除 · CTA 三端入口齐全：${ends.cta.join(' ')}`)
    }
  }


  /* ---------------- 4. 市民端交互 ---------------- */

  console.log('=== 市民端交互 ===')
  await goto('citizen?autologin=citizen', DESKTOP)
  const tabRes = await cdp.evaluate(`(async () => {
    const btns = [...document.querySelectorAll('.es-nav button')]
    const out = []
    for (const b of btns) {
      b.click()
      await new Promise(r => setTimeout(r, 500))
      const page = document.querySelector('.portal-page')
      out.push(b.textContent.trim() + '=' + (page ? page.className.replace(/portal-page\\s*/, '') : 'NONE'))
    }
    return JSON.stringify(out)
  })()`)
  const tabs = JSON.parse(tabRes)
  if (!tabs.length || tabs.some((t) => t.endsWith('=NONE'))) note('FAIL', '市民端 tab 切换', tabs.join(' '))
  else note('OK', '市民端 tab 切换', tabs.join(' '))

  await goto('citizen?autologin=citizen', DESKTOP)
  const repRes = await cdp.evaluate(`(async () => {
    const q = document.querySelector('[data-testid="report-entry"]')
    if (!q) return JSON.stringify({ err: '找不到上报入口 [data-testid=report-entry]' })
    q.click()
    await new Promise(r => setTimeout(r, 800))
    const input = document.querySelector('.upload-zone input[type=file]')
    if (!input) return JSON.stringify({ err: '找不到上传控件' })
    const dt = new DataTransfer()
    dt.items.add(new File([new Uint8Array([0, 0, 0, 24, 102, 116, 121, 112])], 'demo-clip.mp4', { type: 'video/mp4' }))
    input.files = dt.files
    input.dispatchEvent(new Event('change', { bubbles: true }))
    await new Promise(r => setTimeout(r, 400))
    const picked = (document.querySelector('.upload-zone b') || {}).textContent || ''
    // 先试一次「未勾选安全确认」的拦截分支
    document.querySelector('.report-submit').click()
    await new Promise(r => setTimeout(r, 400))
    const guarded = (document.querySelector('.report-error') || {}).textContent || ''
    const cb = document.querySelector('.safety-check input[type=checkbox]')
    if (!cb) return JSON.stringify({ err: '找不到安全确认勾选' })
    cb.checked = true
    cb.dispatchEvent(new Event('change', { bubbles: true }))
    await new Promise(r => setTimeout(r, 400))
    document.querySelector('.report-submit').click()
    await new Promise(r => setTimeout(r, 900))
    return JSON.stringify({
      picked,
      guarded,
      success: !!document.querySelector('.submit-success')
    })
  })()`)
  const rep = JSON.parse(repRes)
  if (rep.err) note('FAIL', '市民端上报表单', rep.err)
  else if (!rep.guarded) note('FAIL', '市民端上报表单', '未勾选安全确认时没有被拦下')
  else if (!rep.success) note('FAIL', '市民端上报表单', '提交后未见成功态 picked=' + rep.picked)
  else note('OK', '市民端上报表单', '素材=' + rep.picked.trim() + ' · 拦截提示「' + rep.guarded.trim() + '」')

  // 轮播图：指示点存在且点击可切换
  await goto('citizen?autologin=citizen', DESKTOP)
  const carRes = await cdp.evaluate(`(async () => {
    const dots = [...document.querySelectorAll('.carousel-dots button')]
    if (dots.length < 3) return JSON.stringify({ err: '轮播指示点不足：' + dots.length })
    dots[1].click()
    await new Promise(r => setTimeout(r, 700))
    const track = document.querySelector('.carousel-track')
    return JSON.stringify({ dots: dots.length, transform: track ? track.style.transform : 'NONE' })
  })()`)
  const car = JSON.parse(carRes)
  if (car.err) note('FAIL', '市民端轮播图', car.err)
  else if (!car.transform.includes('-100')) note('FAIL', '市民端轮播图', '点击指示点后未切换到第 2 张：' + car.transform)
  else note('OK', '市民端轮播图', '指示点 ' + car.dots + ' 个 · 切换生效 ' + car.transform)

  // 文明打卡积分
  const checkInRes = await cdp.evaluate(`(async () => {
    const before = (document.querySelector('.task-ring strong') || {}).textContent || ''
    const btn = document.querySelector('[data-testid="checkin-home"]')
    if (!btn) return JSON.stringify({ err: '找不到打卡按钮' })
    btn.click()
    await new Promise(r => setTimeout(r, 500))
    const after = (document.querySelector('.task-ring strong') || {}).textContent || ''
    const done = (document.querySelector('[data-testid="checkin-home"]') || {}).textContent || ''
    return JSON.stringify({ before, after, done })
  })()`)
  const ci = JSON.parse(checkInRes)
  if (ci.err) note('FAIL', '市民端文明打卡', ci.err)
  else if (!ci.done.includes('已打卡')) note('FAIL', '市民端文明打卡', '点击后未进入已打卡状态：' + ci.done)
  else note('OK', '市民端文明打卡', '积分 ' + ci.before + ' → ' + ci.after)

  // 科普三人群统筹：切到长者模式应出现朗读按钮与大字版类名
  const sciRes = await cdp.evaluate(`(async () => {
    const tabs = [...document.querySelectorAll('.es-nav button')]
    const sci = tabs.find(b => (b.textContent || '').includes('科普'))
    if (!sci) return JSON.stringify({ err: '找不到科普 tab' })
    sci.click()
    await new Promise(r => setTimeout(r, 600))
    const senior = [...document.querySelectorAll('.audience-bar button')].find(b => (b.textContent || '').includes('长者'))
    if (!senior) return JSON.stringify({ err: '找不到长者切换' })
    senior.click()
    await new Promise(r => setTimeout(r, 500))
    const page = document.querySelector('.science-page')
    const speak = document.querySelectorAll('.speak-btn').length
    return JSON.stringify({ cls: page ? page.className : 'NONE', speak })
  })()`)
  const sci = JSON.parse(sciRes)
  if (sci.err) note('FAIL', '科普人群统筹（长者模式）', sci.err)
  else if (!sci.cls.includes('aud-senior') || sci.speak < 1) note('FAIL', '科普人群统筹（长者模式）', 'cls=' + sci.cls + ' 朗读按钮=' + sci.speak)
  else note('OK', '科普人群统筹（长者模式）', 'aud-senior 生效 · 朗读按钮 ' + sci.speak + ' 个')

  /* ---------------- 5. 管理员登录 ---------------- */

  console.log('=== 管理员登录 ===')
  await clearAuth(DESKTOP)
  await goto('platform/overview?autologin=1', DESKTOP)
  const login = JSON.parse(await cdp.evaluate(`JSON.stringify({
    path: location.pathname,
    hash: location.hash,
    ok: !!document.querySelector('.admin-shell')
  })`))
  if (!login.ok) note('FAIL', '管理员登录', '演示登录后未进入管理端：' + login.path + login.hash)
  else note('OK', '管理员登录', login.path + login.hash)

  /* ---------------- 6. 后台深度交互 ---------------- */

  console.log('=== 后台深度交互 ===')

  // 6.1 AI 识别配置：阈值滑块与数值框联动 + 白名单增删
  await goto('platform/ai-config?autologin=1', DESKTOP)
  const aiRes = await cdp.evaluate(`(async () => {
    const range = document.querySelector('input[type=range].ad-ctrl, input[type=range]')
    const num = document.querySelector('input.ad-ctrl.num[type=number]')
    if (!range || !num) return JSON.stringify({ err: '找不到阈值滑块/数值框' })
    const before = num.value
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
    const target = String(Math.min(Number(range.max || 100), Number(range.value) + 5))
    setter.call(range, target)
    range.dispatchEvent(new Event('input', { bubbles: true }))
    range.dispatchEvent(new Event('change', { bubbles: true }))
    await new Promise(r => setTimeout(r, 400))
    const linked = num.value
    const tags = document.querySelectorAll('.ad-tag, .tag, .p-tag').length
    const box = [...document.querySelectorAll('input.ad-ctrl')].find(i => /设备编号/.test(i.placeholder || ''))
    let added = null
    if (box) {
      setter.call(box, 'CAM-777')
      box.dispatchEvent(new Event('input', { bubbles: true }))
      await new Promise(r => setTimeout(r, 250))
      const btn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '添加设备')
      if (btn) { btn.click(); await new Promise(r => setTimeout(r, 450)) }
      added = /CAM-777/.test(document.body.innerText)
    }
    return JSON.stringify({ before, slider: target, linked, tags, added })
  })()`)
  const ai = JSON.parse(aiRes)
  if (ai.err) note('FAIL', 'AI 配置：阈值联动', ai.err)
  else if (String(ai.before) === String(ai.linked)) note('FAIL', 'AI 配置：阈值联动', `滑块改到 ${ai.slider} 但数值框仍是 ${ai.linked}`)
  else if (ai.added === false) note('FAIL', 'AI 配置：白名单新增', '添加 CAM-777 后页面上找不到该编号')
  else note('OK', 'AI 配置：阈值联动 + 白名单', `滑块 ${ai.slider} → 数值框 ${ai.linked}${ai.added ? ' · 白名单 +CAM-777' : ''}`)

  // 6.2 全域 GIS：图层开关是否真的控制点位
  await goto('platform/gis?autologin=1', DESKTOP)
  const gisRes = await cdp.evaluate(`(async () => {
    // 图层开关要**按标签定位**：GisView 现在有 7 个开关（行政区分区/设备/事件/热力/任务点/烟蒂设施/兴趣点），
    // 用 boxes[0] 会点到"行政区分区"，而它本来就不改变点位数 → 用例会假红。
    const all = [...document.querySelectorAll('.layer-bar input[type=checkbox]')]
    if (!all.length) return JSON.stringify({ err: '找不到图层开关' })
    const labelOf = (box) => (box.closest('label')?.innerText || '').trim()
    const box = all.find((b) => /设备点位/.test(labelOf(b))) || all[0]
    const count = () => document.querySelectorAll('.gd-pin').length
    const on = count()
    box.click()
    await new Promise(r => setTimeout(r, 600))
    const off = count()
    box.click()
    await new Promise(r => setTimeout(r, 600))
    return JSON.stringify({ switches: all.length, on, off, back: count() })
  })()`)
  const gis = JSON.parse(gisRes)
  if (gis.err) note('FAIL', 'GIS：图层开关', gis.err)
  else if (gis.on === gis.off) note('FAIL', 'GIS：图层开关', `关掉图层后点位数量没变（${gis.on}）`)
  else note('OK', 'GIS：图层开关', `${gis.switches} 个开关 · 点位 ${gis.on} → ${gis.off} → ${gis.back}`)

  // 6.3 用户账号：权限抽屉开合
  await goto('platform/users?autologin=1', DESKTOP)
  const drawRes = await cdp.evaluate(`(async () => {
    const btn = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '分配权限')
    if (!btn) return JSON.stringify({ err: '找不到「分配权限」按钮' })
    btn.click()
    await new Promise(r => setTimeout(r, 500))
    const box = document.querySelector('.drawer')
    const checks = box ? box.querySelectorAll('input[type=checkbox]').length : 0
    const opened = !!box
    const save = box ? [...box.querySelectorAll('button')].find(b => /保存|确定/.test(b.textContent)) : null
    if (save) { save.click(); await new Promise(r => setTimeout(r, 500)) }
    return JSON.stringify({ opened, checks, closed: !document.querySelector('.drawer') })
  })()`)
  const dr = JSON.parse(drawRes)
  if (dr.err) note('FAIL', '用户账号：权限抽屉', dr.err)
  else if (!dr.opened || !dr.checks) note('FAIL', '用户账号：权限抽屉', `打开=${dr.opened} 权限项=${dr.checks}`)
  else note('OK', '用户账号：权限抽屉', `权限项 ${dr.checks} 个 · 保存后关闭=${dr.closed}`)

  // 6.4 告警列表：筛选 + 翻页
  await goto('platform/alerts?autologin=1', DESKTOP)
  const pgRes = await cdp.evaluate(`(async () => {
    const firstRow = () => (document.querySelector('.table .tr:not(.th)') || {}).innerText || ''
    const before = firstRow().slice(0, 40)
    const next = document.querySelector('.pager button[aria-label=下一页]')
    if (!next || next.disabled) return JSON.stringify({ err: '找不到可用的下一页按钮' })
    next.click()
    await new Promise(r => setTimeout(r, 600))
    const after = firstRow().slice(0, 40)
    const onPage = (document.querySelector('.pager button.pg.on') || {}).textContent || ''
    return JSON.stringify({ changed: before !== after, before, after, onPage: onPage.trim() })
  })()`)
  const pg = JSON.parse(pgRes)
  if (pg.err) note('FAIL', '告警列表：翻页', pg.err)
  else if (!pg.changed) note('FAIL', '告警列表：翻页', '翻页后首行内容没变')
  else note('OK', '告警列表：翻页', `第 ${pg.onPage} 页 · 首行已变化`)

  // 6.5 执法协同：认领 → 不予处理必须填原因 → 写入留痕
  await goto('platform/law-cases?autologin=1', DESKTOP)
  const lawRes = await cdp.evaluate(`(async () => {
    const claim = [...document.querySelectorAll('.ad-link')].find(b => b.textContent.trim() === '认领核查')
    if (!claim) return JSON.stringify({ err: '没有可认领的线索' })
    claim.click()
    await new Promise(r => setTimeout(r, 800))
    const rej = [...document.querySelectorAll('.ad-link')].find(b => b.textContent.trim() === '不予处理')
    if (!rej) return JSON.stringify({ err: '认领后未出现处置动作' })
    rej.click()
    await new Promise(r => setTimeout(r, 500))

    // 不填原因直接提交 → 抽屉应保持打开
    document.querySelector('.d-foot .ad-btn--primary').click()
    await new Promise(r => setTimeout(r, 700))
    const blocked = !!document.querySelector('.drawer')

    // 填了原因再提交 → 抽屉关闭
    const ta = document.querySelector('.d-field textarea')
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set
    setter.call(ta, '现场核查未发现遗留烟蒂')
    ta.dispatchEvent(new Event('input', { bubbles: true }))
    await new Promise(r => setTimeout(r, 200))
    document.querySelector('.d-foot .ad-btn--primary').click()
    await new Promise(r => setTimeout(r, 900))
    return JSON.stringify({ blocked, closed: !document.querySelector('.drawer') })
  })()`)
  const law = JSON.parse(lawRes)
  if (law.err) note('FAIL', '执法协同：处置动作', law.err)
  else if (!law.blocked) note('FAIL', '执法协同：处置动作', '未填原因竟然提交成功')
  else if (!law.closed) note('FAIL', '执法协同：处置动作', '填了原因抽屉却没关')
  else note('OK', '执法协同：认领 + 不予处理需填原因', '空原因被拦下，填后提交成功')

  await goto('platform/law-trail?autologin=1', DESKTOP)
  const trailRes = await cdp.evaluate(`JSON.stringify({
    rows: document.querySelectorAll('.table .tr:not(.th)').length,
    first: ((document.querySelector('.table .tr:not(.th)') || {}).innerText || '').replace(/\\s+/g, ' ').slice(0, 60)
  })`)
  const trail = JSON.parse(trailRes)
  if (!trail.rows) note('FAIL', '执法协同：处置留痕', '留痕表为空')
  else note('OK', '执法协同：处置留痕', `${trail.rows} 条 · ${trail.first}`)

  // 6.6 平台配置：演示数据量级切换是否全局生效
  const digest = async () => {
    await goto('platform/overview?autologin=1', DESKTOP)
    return cdp.evaluate(`(() => {
      const el = document.querySelector('.admin-content')
      return el ? el.innerText.replace(/\\s+/g, ' ').slice(0, 500) : ''
    })()`)
  }
  await goto('platform/platform-config?autologin=1', DESKTOP)
  const scaleRes = await cdp.evaluate(`(async () => {
    const btns = [...document.querySelectorAll('.scale-btn')]
    if (btns.length < 2) return JSON.stringify({ err: '找不到量级切换按钮' })
    const before = (document.querySelector('.scale-btn.on') || {}).textContent || ''
    btns[1].click()
    await new Promise(r => setTimeout(r, 700))
    return JSON.stringify({ before: before.trim(), after: (document.querySelector('.scale-btn.on') || {}).textContent })
  })()`)
  const sc = JSON.parse(scaleRes)
  if (sc.err) note('FAIL', '平台配置：量级切换', sc.err)
  else {
    const d1 = await digest()
    await goto('platform/platform-config?autologin=1', DESKTOP)
    await cdp.evaluate(`document.querySelectorAll('.scale-btn')[0].click()`)
    await sleep(700)
    const d2 = await digest()
    if (d1 === d2) note('FAIL', '平台配置：量级切换', '切成试点量级后总览页数字没有变化')
    else note('OK', '平台配置：量级切换', `${sc.before} → ${sc.after}，总览页数值同步变化`)
  }

  ws.close()
} catch (err) {
  console.error('QA 脚本异常:', err.message)
  code = 1
} finally {
  edge.kill()
}

/* ---------------- 汇总 ---------------- */

const fails = results.filter((r) => r.status === 'FAIL')
console.log('\n=================== 质检汇总 ===================')
for (const r of results) {
  console.log(`${r.status.padEnd(4)} ${r.name.padEnd(22, '　')} ${r.extra}`)
}
console.log('===============================================')
console.log(`通过 ${results.length - fails.length} / ${results.length}，失败 ${fails.length}`)
process.exit(fails.length ? 1 : code)
