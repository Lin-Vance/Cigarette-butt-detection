/**
 * 多端页面验收（正式界面按角色进入，不暴露调试用跨端切换条）。
 *
 * 检查：
 *  1. 五个页面各自能打开、渲染出内容、无控制台报错、无横向溢出
 *  2. 入口页的四张卡片是**真实页面跳转**（href = ./xxx.html），不是站内 hash 路由
 *  3. 点卡片真的会换页（location.pathname 变化）
 *  4. 正式页面不出现调试用跨端切换条
 *  5. 端内交互：环卫端「演示直入」→ 出现工单；管理端登录 → 顶栏含「执法协同」
 *
 * 用法：node scripts/qa-ends.mjs            （默认 http://127.0.0.1:5180）
 *       BASE=http://127.0.0.1:5182/ node scripts/qa-ends.mjs
 */
import { spawn } from 'node:child_process'
import path from 'node:path'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const PORT = 9700 + (process.pid % 200)
const PROFILE = path.join(process.env.TEMP || '/tmp', `edge-qa-ends-${process.pid}`)
const BASE = process.env.BASE || 'http://127.0.0.1:5180/'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const results = []
const note = (ok, name, detail = '') => {
  results.push({ ok, name, detail })
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${name}${detail ? ' — ' + detail : ''}`)
}

async function waitForTarget(tries = 100) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`)
      const list = await r.json()
      const page = list.find((t) => t.type === 'page')
      if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch {
      /* 未就绪 */
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
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id)
        this.pending.delete(m.id)
        if (m.error) reject(new Error(JSON.stringify(m.error)))
        else resolve(m.result)
      } else if (m.method) {
        if (m.method === 'Runtime.exceptionThrown') {
          const d = m.params.exceptionDetails || {}
          this.logs.push('EXC ' + String((d.exception && d.exception.description) || d.text).split('\n')[0])
        } else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
          this.logs.push('ERR ' + (m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' '))
        }
        if (this.listeners.has(m.method)) this.listeners.get(m.method)(m.params)
      }
    })
  }

  send(method, params = {}) {
    const id = ++this.id
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
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
    const { result } = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    })
    return result.value
  }

  /** 触发会引发整页跳转的操作，不等待返回值（执行上下文会被销毁） */
  fire(expression) {
    return this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: false }).catch(
      () => undefined
    )
  }

  async open(url, wait = 1500) {
    this.logs = []
    const loaded = this.onceTimeout('Page.loadEventFired', 8000)
    await this.send('Page.navigate', { url: 'about:blank' })
    await sleep(120)
    await this.send('Page.navigate', { url })
    await loaded
    await sleep(wait)
  }
}

/** 五个页面：文件 / 名称 / 期望渲染出的根节点 */
/**
 * 每项：文件、标签、根节点签名、是否**应**出现调试用跨端切换组件。
 *
 * 现状（2026-09-28 用户要求）：**全部为 0**。
 * 入口页底部那条 `.yz-ends` 调试切换条已移除——从它点进登录页会走到与正式入口
 * 不一致的页面，用户明确要求删掉。现在换端只走入口页 §05 的端入口卡片（CTA），
 * 以及正式端页顶栏 / 手机端底部导航。
 */
export const PAGES = [
  ['index.html', '入口页（5 屏长滚动）', '.lp', false],
  ['auth.html', '登录 / 注册', '.au-auth', false],
  ['citizen.html', '市民用户端', '.citizen-login', false],
  ['worker.html', '环卫工人端', '.end-shell', false],
  ['admin.html', '管理员端', '.login-form', false]
]

const OVERFLOW = `(() => {
  const vw = document.documentElement.clientWidth
  const inScroller = (el) => {
    let p = el.parentElement
    while (p && p !== document.body) {
      if (/(auto|scroll)/.test(getComputedStyle(p).overflowX)) return true
      p = p.parentElement
    }
    return false
  }
  const bad = []
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect()
    if (r.width === 0 || r.height === 0) return
    if (r.right > vw + 1 || r.left < -1) {
      if (inScroller(el)) return
      const cn = typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\\s+/).join('.') : ''
      bad.push(el.tagName.toLowerCase() + cn)
    }
  })
  return JSON.stringify({ vw, sw: document.documentElement.scrollWidth, bad: bad.slice(0, 5) })
})()`

const edge = spawn(
  EDGE,
  [
    '--headless=new',
    '--disable-gpu',
    '--disable-extensions',
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
  const ws = new WebSocket(await waitForTarget())
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true })
    ws.addEventListener('error', rej, { once: true })
  })
  const cdp = new CDP(ws)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false
  })

  /* ---------- 0. 等站点就绪 + 清掉上次的登录态 ---------- */
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(BASE + 'index.html')
      if (r.ok) break
    } catch {
      /* 还没起来 */
    }
    await sleep(400)
  }
  await cdp.open(BASE + 'index.html')
  await cdp.evaluate('localStorage.clear()')

  /* ---------- 1. 五个页面各自可用 ---------- */
  console.log('=== 五个页面 ===')
  for (const [file, label, sig, expectEnds] of PAGES) {
    await cdp.open(BASE + file)
    const raw = await cdp.evaluate(`JSON.stringify({
      path: location.pathname.split('/').pop() || 'index.html',
      hash: location.hash,
      len: (document.getElementById('app') || { innerHTML: '' }).innerHTML.length,
      title: document.title,
      ends: document.querySelectorAll('.yz-ends, .es-cross').length,
      main: !!document.querySelector(${JSON.stringify(sig)})
    })`)
    const s = JSON.parse(raw)
    const over = JSON.parse(await cdp.evaluate(OVERFLOW))
    const problems = []
    if (s.len < 400) problems.push('内容过少 ' + s.len)
    if (!s.main) problems.push('未渲染出预期根节点 ' + sig)
    // 调试用跨端切换组件：按用户要求已全部移除，出现即失败
    if (s.ends !== 0) problems.push(`仍暴露调试用跨端切换条（${s.ends} 个）`)
    if (over.sw > over.vw + 1) problems.push(`横向溢出 ${over.vw}/${over.sw} ${over.bad[0] ?? ''}`)
    if (cdp.logs.length) problems.push('控制台: ' + cdp.logs[0].slice(0, 110))
    note(problems.length === 0, `${label}（${file}）`, problems.join(' / ') || `${s.title} · hash=${s.hash || '—'}`)
  }

  /* ---------- 2. 入口页端入口是真跳转（§04 分端卡已改为证据链屏，入口改由 §05 CTA 区承载） ---------- */
  console.log('=== 端间跳转 ===')
  await cdp.open(BASE + 'index.html')
  const cards = JSON.parse(
    await cdp.evaluate(`JSON.stringify([...document.querySelectorAll('.cta-acts a')].map(a => ({
      name: a.textContent.trim(),
      href: a.getAttribute('href')
    })))`)
  )
  const expected = ['./citizen.html', './worker.html', './admin.html']
  const cardsOk = expected.every((h) => cards.some((c) => c.href === h))
  note(cardsOk, '入口页端入口指向真实页面', cards.map((c) => `${c.name}→${c.href}`).join(' '))

  // 点「进入环卫端」→ 应换页到 /worker.html
  await cdp.fire(`document.querySelector('.cta-acts a[href="./worker.html"]').click()`)
  await sleep(2200)
  const after = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      path: location.pathname.split('/').pop(),
      hasGate: !!document.querySelector('.end-shell'),
      ends: document.querySelectorAll('.yz-ends, .es-cross').length
    })`)
  )
  note(
    after.path === 'worker.html' && after.hasGate && after.ends === 0,
    '点卡片真的换页到环卫端',
    `pathname=${after.path} · 调试用跨端切换组件 ${after.ends} 个（应为 0）`
  )

  /* ---------- 2.5 登录 / 注册页真的能进端 ---------- */
  console.log('=== 登录 / 注册 ===')
  {
    await cdp.open(BASE + 'auth.html')
    const register = JSON.parse(
      await cdp.evaluate(`(async () => {
        const b = [...document.querySelectorAll('.au-seg button')].find(x => x.textContent.trim() === '注册')
        if (!b) return JSON.stringify({ err: '找不到注册页签' })
        b.click()
        await new Promise(r => setTimeout(r, 400))
        return JSON.stringify({
          on: !!document.querySelector('.au-seg button.on') && document.querySelector('.au-seg button.on').textContent.trim(),
          submit: (document.querySelector('.au-submit') || {}).textContent.trim() || '',
          ids: document.querySelectorAll('.au-id').length
        })
      })()`)
    )
    if (register.err) note(false, '登录/注册页：模式切换', register.err)
    else
      note(
        register.on === '注册' && register.ids === 3,
        '登录/注册页：登录↔注册切换 + 三种身份',
        `当前=${register.on} · 身份 ${register.ids} 种 · 按钮「${register.submit}」`
      )
  }

  {
    // 用管理身份登录 → 应真的跳到 admin.html
    await cdp.open(BASE + 'auth.html')
    await cdp.evaluate('localStorage.clear()')
    await cdp.open(BASE + 'auth.html')
    await cdp.fire(`(async () => {
      const b = [...document.querySelectorAll('.au-id')].find(x => x.textContent.includes('ADMIN'))
      b?.click()
      await new Promise(r => setTimeout(r, 400))
      document.querySelector('.au-submit')?.click()
      return 'fired'
    })()`)
    await sleep(3600)
    const r = JSON.parse(
      await cdp.evaluate(`JSON.stringify({
        path: location.pathname.split('/').pop(),
        hash: location.hash,
        login: !!document.querySelector('.input-shell')
      })`)
    )
    note(
      r.path === 'admin.html',
      '登录页：管理身份登录后跳管理端',
      `pathname=${r.path} · hash=${r.hash}${r.login ? '（落在登录页）' : ''}`
    )
  }

  /* ---------- 3. 端内交互 ---------- */
  console.log('=== 端内交互 ===')

  await cdp.open(BASE + 'worker.html')
  await cdp.fire(`[...document.querySelectorAll('button')].find(b => b.textContent.includes('演示直入'))?.click()`)
  await sleep(2800)
  const w = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      stats: document.querySelectorAll('.stats .stat').length,
      rows: document.querySelectorAll('.table .tr:not(.th)').length,
      tabCount: document.querySelectorAll('.es-nav button').length,
      err: (document.querySelector('.f-err') || {}).textContent || ''
    })`)
  )
  note(
    w.tabCount === 5 && w.rows > 0,
    '环卫端：登录后出现工单',
    `统计 ${w.stats} 项 · 分组/功能 ${w.tabCount} 个 · 工单行 ${w.rows} ${w.err}`
  )

  // 路线与班次：新增的现场辅助功能应包含建议点位、物资检查和启停操作
  const routeView = JSON.parse(
    await cdp.evaluate(`(async () => {
      const btn = [...document.querySelectorAll('.es-nav button')].find(b => (b.textContent || '').includes('路线与班次'))
      if (!btn) return JSON.stringify({ ok: false, err: '找不到路线与班次入口' })
      btn.click()
      await new Promise(r => setTimeout(r, 700))
      return JSON.stringify({
        ok: !!document.querySelector('.route-layout'),
        stops: document.querySelectorAll('.stop-list > li:not(.route-empty)').length,
        kits: document.querySelectorAll('.kit-card input[type="checkbox"]').length,
        actions: document.querySelectorAll('.route-head-actions button').length
      })
    })()`)
  )
  note(
    routeView.ok && routeView.stops > 0 && routeView.kits === 3 && routeView.actions >= 2,
    '环卫端：路线、班次与物资检查',
    `点位 ${routeView.stops} 个 · 物资 ${routeView.kits} 项 · 操作 ${routeView.actions} 个${routeView.err ? ' · ' + routeView.err : ''}`
  )

  // 绩效激励：切换后出现积分 / 排行 / 规则
  const perf = JSON.parse(
    await cdp.evaluate(`(async () => {
      const btn = [...document.querySelectorAll('.es-nav button')].find(b => (b.textContent || '').includes('绩效激励'))
      if (!btn) return JSON.stringify({ ok: false, err: '找不到绩效激励入口' })
      btn.click()
      await new Promise(r => setTimeout(r, 900))
      return JSON.stringify({
        ok: !!document.querySelector('.perf-hero'),
        points: (document.querySelector('.perf-me-main strong') || {}).textContent || '',
        rankRows: document.querySelectorAll('.perf-rank li').length,
        rules: document.querySelectorAll('.perf-rules li').length
      })
    })()`)
  )
  note(
    perf.ok && perf.rankRows >= 5 && perf.rules >= 4,
    '环卫端：绩效激励（积分/排行/规则）',
    `积分 ${perf.points} · 排行 ${perf.rankRows} 人 · 规则 ${perf.rules} 条${perf.err ? ' · ' + perf.err : ''}`
  )

  // 接单第一条待接单工单（先切回工单视图：上一条绩效用例切走了）
  const acc = JSON.parse(
    await cdp.evaluate(`(async () => {
      const nav = [...document.querySelectorAll('.es-nav button')].find(b => (b.textContent || '').includes('待接单'))
      if (nav) { nav.click(); await new Promise(r => setTimeout(r, 700)) }
      const btn = [...document.querySelectorAll('.table .ad-link')].find(b => b.textContent.trim() === '接单')
      if (!btn) return JSON.stringify({ ok: false })
      const row = btn.closest('.tr')
      const no = row.querySelector('.td').textContent.trim()
      btn.click()
      await new Promise(r => setTimeout(r, 1400))
      return JSON.stringify({ ok: true, no, status: (row.querySelector('.yz-tag') || {}).textContent || '' })
    })()`)
  )
  note(acc.ok, '环卫端：可接单', acc.no ? `已接 ${acc.no} · 状态 ${acc.status}` : '未找到待接单工单')

  // 管理端：先清登录态（环卫端刚以 worker01 登入并持久化，不清就进不了登录页）
  await cdp.open(BASE + 'index.html')
  await cdp.evaluate('localStorage.clear()')
  await cdp.open(BASE + 'admin.html')
  const adminNav = JSON.parse(
    await cdp.evaluate(`(async () => {
      const inputs = [...document.querySelectorAll('.field-input')]
      if (inputs.length < 2) return JSON.stringify({ err: '登录表单未就绪' })
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(inputs[0], 'admin')
      inputs[0].dispatchEvent(new Event('input', { bubbles: true }))
      setter.call(inputs[1], '123456')
      inputs[1].dispatchEvent(new Event('input', { bubbles: true }))
      await new Promise(r => setTimeout(r, 300))
      document.querySelector('form.login-form').dispatchEvent(
        new Event('submit', { bubbles: true, cancelable: true })
      )
      await new Promise(r => setTimeout(r, 2200))
      return JSON.stringify({
        hash: location.hash,
        nav: (document.querySelector('.main-nav') || {}).textContent || '',
        admin: !!document.querySelector('.admin-shell')
      })
    })()`)
  )
  note(
    adminNav.admin && /执法协同/.test(adminNav.nav || ''),
    '管理端顶栏含「执法协同」模块',
    adminNav.err || adminNav.hash
  )

  // 管理端首页轮播：左右按钮与圆点必须能真实切换图片
  await cdp.open(`${BASE}admin.html#/platform/overview`, 1800)
  const carousel = JSON.parse(
    await cdp.evaluate(`(async () => {
      const image = document.querySelector('.hero-art')
      const before = image?.getAttribute('src') || ''
      document.querySelector('.hero-arrow.right')?.click()
      await new Promise(r => setTimeout(r, 500))
      return JSON.stringify({
        before,
        after: document.querySelector('.hero-art')?.getAttribute('src') || '',
        dots: document.querySelectorAll('.hero-dots button').length
      })
    })()`)
  )
  note(
    carousel.before && carousel.after && carousel.before !== carousel.after && carousel.dots === 3,
    '管理端：首页轮播按钮可用',
    `${carousel.before} → ${carousel.after} · ${carousel.dots} 张`
  )

  // 区域工作台：增加足量任务行，消除底部大面积空白
  await cdp.open(`${BASE}admin.html#/platform/workboard`, 1800)
  const board = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      rows: document.querySelectorAll('.table .tr:not(.th)').length,
      overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
    })`)
  )
  note(board.rows >= 6 && !board.overflow, '管理端：区域工作台内容充实且无横向溢出', `任务行 ${board.rows}`)

  // 执法协同两个页面可用
  for (const [name, label] of [
    ['law-cases', '执法线索核查'],
    ['law-trail', '处置留痕']
  ]) {
    await cdp.open(`${BASE}#/platform/${name}?autologin=1`, 2200)
    const s = JSON.parse(
      await cdp.evaluate(`JSON.stringify({
        title: (document.querySelector('.ad-title') || {}).textContent || '',
        rows: document.querySelectorAll('.table .tr:not(.th)').length
      })`)
    )
    note(
      s.title.includes(label.slice(0, 4)) || s.rows > 0,
      `执法协同页：${label}`,
      s.title + ' · 表格行 ' + s.rows
    )
  }

  // 市民端：三类人群科普必须使用不同内容；退出统一回到 auth.html
  await cdp.open(BASE + 'index.html')
  await cdp.evaluate('localStorage.clear()')
  await cdp.open(BASE + 'citizen.html')
  const citizenCheck = JSON.parse(
    await cdp.evaluate(`(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      const inputs = [...document.querySelectorAll('input')]
      setter.call(inputs[0], '13800138000'); inputs[0].dispatchEvent(new Event('input', { bubbles: true }))
      setter.call(inputs[1], '123456'); inputs[1].dispatchEvent(new Event('input', { bubbles: true }))
      const agree = document.querySelector('.agreement input'); if (agree && !agree.checked) agree.click()
      document.querySelector('.submit-button')?.click()
      await new Promise(r => setTimeout(r, 1400))
      const latest = !!document.querySelector('.my-latest')
      const science = [...document.querySelectorAll('.es-nav button')].find(b => b.textContent.includes('科普'))
      science?.click(); await new Promise(r => setTimeout(r, 400))
      const groups = [...document.querySelectorAll('.audience-bar button')]
      const titles = []
      for (const group of groups) {
        group.click(); await new Promise(r => setTimeout(r, 120))
        titles.push([...document.querySelectorAll('.news-grid h3')].map(x => x.textContent.trim()).join('|'))
      }
      return JSON.stringify({ groups: groups.length, distinct: new Set(titles).size, latest })
    })()`)
  )
  note(
    citizenCheck.groups === 3 && citizenCheck.distinct === 3 && citizenCheck.latest,
    '市民端：分众科普与最新线索',
    `人群 ${citizenCheck.groups} 类 · 独立内容 ${citizenCheck.distinct} 组`
  )

  await cdp.fire(`[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '退出')?.click()`)
  await sleep(1300)
  const citizenLogout = JSON.parse(await cdp.evaluate(`JSON.stringify({ path: location.pathname.split('/').pop(), hash: location.hash })`))
  note(citizenLogout.path === 'auth.html' && citizenLogout.hash.includes('role=citizen'), '角色退出：市民端返回市民身份登录', `${citizenLogout.path}${citizenLogout.hash}`)

  await cdp.open(BASE + 'worker.html')
  await cdp.fire(`[...document.querySelectorAll('button')].find(b => b.textContent.includes('演示直入'))?.click()`)
  await sleep(1200)
  await cdp.fire(`[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '退出')?.click()`)
  await sleep(1300)
  const workerLogout = JSON.parse(await cdp.evaluate(`JSON.stringify({ path: location.pathname.split('/').pop(), hash: location.hash })`))
  note(workerLogout.path === 'auth.html' && workerLogout.hash.includes('role=worker'), '角色退出：环卫端返回环卫身份登录', `${workerLogout.path}${workerLogout.hash}`)

  await cdp.open(`${BASE}admin.html#/platform/overview?autologin=1`, 1500)
  await cdp.fire(`document.querySelector('.logout')?.click()`)
  await sleep(1300)
  const adminLogout = JSON.parse(await cdp.evaluate(`JSON.stringify({ path: location.pathname.split('/').pop(), hash: location.hash })`))
  note(adminLogout.path === 'auth.html' && adminLogout.hash.includes('role=admin'), '角色退出：管理端返回管理员身份登录', `${adminLogout.path}${adminLogout.hash}`)

  ws.close()
} catch (err) {
  console.error('验收脚本异常:', err.message)
  code = 1
} finally {
  edge.kill()
}

const fails = results.filter((r) => !r.ok)
console.log('\n=================== 多端验收 ===================')
console.log(`通过 ${results.length - fails.length} / ${results.length}`)
if (fails.length) fails.forEach((f) => console.log('  失败：' + f.name + ' ' + f.detail))
process.exit(fails.length ? 1 : code)
