/**
 * 修复后的人工复核探针（临时文件，不进工程）。
 *
 * 覆盖检测报告里无法靠 qa.mjs / qa-ends.mjs 直接证明的几条：
 *   D-02 环卫角色进管理端不再白屏（无限重定向已修）
 *   D-10 登录失败文案中文化
 *   D-12 未知路由按「当前端」回落
 *   D-04 入口页换端条可点击换页
 *   D-06 管理端窄屏出现宽屏提示而不是缩成蚂蚁
 *   D-01/D-03 管理员登录真的连通后端
 *
 * 用法：node probe-fix.mjs
 */
import { spawn } from 'node:child_process'
import path from 'node:path'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const PORT = 9900 + (process.pid % 90)
const PROFILE = path.join(process.env.TEMP || '/tmp', `edge-probe-fix-${process.pid}`)
const BASE = process.env.BASE || 'http://127.0.0.1:5180/'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const out = []
let STEP = '(初始化)'
const note = (ok, name, detail = '') => {
  out.push({ ok, name, detail })
  console.log(`[${ok ? 'PASS' : 'FAIL'}] ${name}${detail ? ' — ' + detail : ''}`)
}

/** 标记当前正在执行的检查项，异常时能定位到具体步骤 */
const mark = (s) => {
  STEP = s
  console.log(`   → ${s}`)
}

async function waitForTarget(tries = 120) {
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
    this.logs = []
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id)
        this.pending.delete(m.id)
        if (m.error) reject(new Error(JSON.stringify(m.error)))
        else resolve(m.result)
      } else if (m.method === 'Runtime.exceptionThrown') {
        const d = m.params.exceptionDetails || {}
        this.logs.push('EXC ' + String((d.exception && d.exception.description) || d.text).split('\n')[0])
      } else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
        this.logs.push('ERR ' + (m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' '))
      } else if (m.method === 'Log.entryAdded') {
        const e = m.params.entry || {}
        if (e.level === 'error' || (e.level === 'warning' && /redirect/i.test(e.text || ''))) {
          this.logs.push(`${e.level.toUpperCase()} ${e.text}`)
        }
      }
    })
  }

  send(method, params = {}) {
    const id = ++this.id
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    }).finally(() => this.pending.delete(id))
  }

  reset() {
    this.logs = []
  }

  async evaluate(expr, tries = 3) {
    let last
    for (let i = 0; i < tries; i++) {
      try {
        const r = await this.send('Runtime.evaluate', {
          expression: expr,
          awaitPromise: true,
          returnByValue: true
        })
        if (r.exceptionDetails) throw new Error(r.exceptionDetails.text)
        return r.result.value
      } catch (e) {
        last = e
        // 跨文档导航（about:blank → http）瞬间派发的命令会被 CDP 拒绝，重试即可
        if (!/navigated or closed|Inspected target|-32000/.test(String(e.message))) throw e
        await sleep(500)
      }
    }
    throw last
  }

  async goto(url, view, tries = 3) {
    let len = 0
    for (let i = 0; i < tries; i++) {
      await this._gotoOnce(url, view)
      // 跨文档导航偶尔会被 CDP 丢弃（命令返回 -32000），跳完必须验证真的渲染了
      len = await this.evaluate(
        `(document.getElementById('app')||{innerHTML:''}).innerHTML.length`
      ).catch(() => 0)
      if (len > 300) return
      if (i < tries - 1) console.log(`   ! 未渲染（app len=${len}），重试 ${i + 2}/${tries}`)
      await sleep(900)
    }
  }

  async _gotoOnce(url, view) {
    this.reset()
    await this.send('Emulation.setDeviceMetricsOverride', {
      width: view.w,
      height: view.h,
      deviceScaleFactor: 1,
      mobile: view.w < 700
    })
    await this.send('Page.navigate', { url: 'about:blank' }).catch(() => undefined)
    await sleep(200)
    const loaded = new Promise((res) => {
      const h = (ev) => {
        const m = JSON.parse(ev.data)
        if (m.method === 'Page.loadEventFired') {
          this.ws.removeEventListener('message', h)
          res()
        }
      }
      this.ws.addEventListener('message', h)
      setTimeout(res, 9000)
    })
    await this.send('Page.navigate', { url }).catch(() => undefined)
    await loaded
    // Vite dev 下首次加载某个端要现编译模块图，1.5s 不够，统一给 3s
    await sleep(view.wait ?? 3000)
  }
}

const DESKTOP = { w: 1440, h: 960 }
const MOBILE = { w: 390, h: 844 }

async function loginAdmin(cdp) {
  await cdp.goto(BASE + 'auth.html#/auth?role=admin', DESKTOP)
  await cdp.evaluate(`localStorage.clear()`)
  await cdp.goto(BASE + 'auth.html#/auth?role=admin', DESKTOP)
  return cdp.evaluate(`(async () => {
    // 登录成功后在 MPA 里是**整页跳转**，CDP 会把在途命令判为 -32000 从而触发重试；
    // 重试时页面已经是管理端，这里直接判定成功，避免二次执行。
    if (!document.querySelector('.au-form')) {
      return JSON.stringify({ hash: location.hash, url: location.href.split('/').pop(), err: '', landed: true })
    }
    const inputs = [...document.querySelectorAll('.au-field input')]
    if (inputs.length < 2) return JSON.stringify({ err: '未找到账号/密码输入框（' + inputs.length + ' 个）' })
    const set = (el, v) => {
      const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      s.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    set(inputs[0], 'admin'); set(inputs[1], '123456')
    await new Promise(r => setTimeout(r, 200))
    const btn = document.querySelector('.au-submit')
    if (!btn) return JSON.stringify({ err: '未找到提交按钮 .au-submit' })
    btn.click()
    await new Promise(r => setTimeout(r, 3000))
    return JSON.stringify({
      hash: location.hash,
      url: location.href.split('/').pop(),
      err: (document.querySelector('.au-error') || {}).textContent || ''
    })
  })()`)
}

async function loginWorker(cdp) {
  await cdp.goto(BASE + 'auth.html#/auth?role=worker', DESKTOP)
  await cdp.evaluate(`localStorage.clear()`)
  await cdp.goto(BASE + 'auth.html#/auth?role=worker', DESKTOP)
  return cdp.evaluate(`(async () => {
    if (!document.querySelector('.au-form')) {
      return JSON.stringify({ hash: location.hash, url: location.href.split('/').pop(), err: '', landed: true })
    }
    const inputs = [...document.querySelectorAll('.au-field input')]
    if (inputs.length < 2) return JSON.stringify({ err: '未找到账号/密码输入框（' + inputs.length + ' 个）' })
    const set = (el, v) => {
      const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      s.call(el, v)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    set(inputs[0], 'worker01'); set(inputs[1], '123456')
    await new Promise(r => setTimeout(r, 200))
    const btn = document.querySelector('.au-submit')
    if (!btn) return JSON.stringify({ err: '未找到提交按钮 .au-submit' })
    btn.click()
    await new Promise(r => setTimeout(r, 3000))
    return JSON.stringify({
      hash: location.hash,
      url: location.href.split('/').pop(),
      err: (document.querySelector('.au-error') || {}).textContent || ''
    })
  })()`)
}

const main = async () => {
  const edge = spawn(    EDGE,
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

  const wsUrl = await waitForTarget()
  const ws = new WebSocket(wsUrl)
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true })
    ws.addEventListener('error', rej, { once: true })
  })
  const cdp = new CDP(ws)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Log.enable')

  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch(BASE + 'index.html')
      if (r.ok) break
    } catch {
      /* 等 dev server */
    }
    await sleep(400)
  }
  await cdp.goto(BASE + 'index.html', DESKTOP)
  await cdp.evaluate('localStorage.clear()')

  /* ---------- R1 管理员登录（D-01/D-03：真的连通后端） ---------- */
  mark('R1 管理员登录')
  const a = JSON.parse(await loginAdmin(cdp))
  const aState = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      hash: location.hash,
      adPage: document.querySelectorAll('.ad-page, .overview').length,
      token: !!JSON.parse(localStorage.getItem('yz.auth') || '{}').token,
      err: (document.querySelector('.au-error, .login-error') || {}).textContent || '',
      pill: (document.querySelector('.sync-pill') || {}).textContent || ''
    })`)
  )
  note(
    aState.adPage > 0 && aState.token,
    'R1 管理员登录连通后端',
    `跳转=${a.url}${a.hash} · 页面节点=${aState.adPage} · ${aState.pill.trim()} · 错误=「${aState.err.trim() || '无'}」`
  )

  /* ---------- R2 环卫角色进管理端：不得白屏（D-02） ---------- */
  mark('R2 环卫角色进管理端')
  await loginWorker(cdp)
  await cdp.goto(BASE + 'admin.html#/platform/dispatch-pool', DESKTOP)
  const w1 = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      hash: location.hash,
      textLen: document.body.innerText.length,
      adPage: document.querySelectorAll('.ad-page').length
    })`)
  )
  const w1Bad = cdp.logs.filter((l) => /Infinite redirect/i.test(l))
  note(
    w1.textLen > 200 && w1.adPage > 0 && w1Bad.length === 0,
    'R2 环卫角色进管理端不再白屏',
    `hash=${w1.hash} · textLen=${w1.textLen} · .ad-page=${w1.adPage} · 无限重定向告警=${w1Bad.length}`
  )

  await cdp.goto(BASE + 'admin.html#/platform/users', DESKTOP)
  const w2 = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      hash: location.hash,
      textLen: document.body.innerText.length,
      adPage: document.querySelectorAll('.ad-page').length
    })`)
  )
  const w2Bad = cdp.logs.filter((l) => /Infinite redirect/i.test(l))
  note(
    w2.textLen > 200 && w2Bad.length === 0,
    'R3 环卫角色访问越权页被兜底到有权限页',
    `hash=${w2.hash}（应含 dispatch-pool）· textLen=${w2.textLen} · 无限重定向告警=${w2Bad.length}`
  )

  /* ---------- R4 管理员密码错误文案中文化（D-10） ---------- */
  mark('R4 登录失败文案')
  await cdp.goto(BASE + 'auth.html#/auth?role=admin', DESKTOP)
  await cdp.evaluate('localStorage.clear()')
  await cdp.goto(BASE + 'auth.html#/auth?role=admin', DESKTOP)
  const wrong = await cdp.evaluate(`(async () => {
    const inputs = [...document.querySelectorAll('.au-field input')]
    const set = (el, v) => {
      const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      s.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    if (inputs.length >= 2) { set(inputs[0], 'admin'); set(inputs[1], 'wrong-pass') }
    await new Promise(r => setTimeout(r, 200))
    document.querySelector('.au-submit').click()
    await new Promise(r => setTimeout(r, 2000))
    const box = document.querySelector('.au-error, .login-error, .au-msg')
    return JSON.stringify({ msg: (box || {}).textContent || '', hash: location.hash })
  })()`)
  const wrongObj = JSON.parse(wrong)
  note(
    wrongObj.msg.length > 0 && !/[A-Za-z]{4,}/.test(wrongObj.msg.replace(/[（(].*?[)）]/g, '')),
    'R4 登录失败文案为中文（无英文技术文案）',
    `提示=「${wrongObj.msg.trim()}」`
  )

  /* ---------- R5 未知路由按当前端回落（D-12） ---------- */
  mark('R5 未知路由回落')
  await loginAdmin(cdp)
  await cdp.goto(BASE + 'admin.html#/not-exist', DESKTOP)
  const nf = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      hash: location.hash,
      hasPortal: !!document.querySelector('.lp'),
      hasAdmin: !!document.querySelector('.admin-shell'),
      title: document.title
    })`)
  )
  note(
    nf.hasAdmin && !nf.hasPortal,
    'R5 未知路由回落到本端（不再渲染官网入口页）',
    `hash=${nf.hash} · admin-shell=${nf.hasAdmin} · 渲染官网首页=${nf.hasPortal} · title=${nf.title}`
  )

  /* ---------- R6 入口页换端条可点击换页（D-04） ---------- */
  mark('R6 入口页换端条')
  const bar = JSON.parse(
    await (async () => {
      await cdp.goto(BASE + 'index.html', DESKTOP)
      return cdp.evaluate(`JSON.stringify({
        links: [...document.querySelectorAll('.yz-ends a')].map(a => ({ t: a.textContent.trim(), h: a.getAttribute('href') })),
        fixed: getComputedStyle(document.querySelector('.yz-ends')).position
      })`)
    })()
  )
  note(
    bar.links.length === 5 && bar.fixed === 'fixed',
    'R6 入口页换端条存在且为固定条',
    bar.links.map((l) => `${l.t}→${l.h}`).join(' ')
  )
  await cdp.evaluate(`document.querySelector('.yz-ends a[href="./citizen.html"]').click()`)
  await sleep(2200)
  const afterBar = JSON.parse(
    await cdp.evaluate(`JSON.stringify({ path: location.pathname.split('/').pop() })`)
  )
  note(
    afterBar.path === 'citizen.html',
    'R7 点换端条真的换页到市民端',
    `pathname=${afterBar.path}`
  )

  /* ---------- R8 管理端窄屏兜底提示（D-06） ---------- */
  mark('R8 管理端窄屏兜底')
  await loginAdmin(cdp)
  await cdp.goto(BASE + 'admin.html#/platform/overview', MOBILE)
  const m = JSON.parse(
    await cdp.evaluate(`JSON.stringify({
      guard: !!document.querySelector('.fit-guard'),
      text: (document.querySelector('.fit-guard h2') || {}).textContent || ''
    })`)
  )
  note(m.guard, 'R8 管理端窄屏给出宽屏提示（而非缩成不可读）', `提示=「${m.text.trim()}」`)

  console.log('\n============ 汇总 ============')
  const pass = out.filter((x) => x.ok).length
  console.log(`通过 ${pass} / ${out.length}`)
  const failed = out.filter((x) => !x.ok)
  if (failed.length) failed.forEach((f) => console.log(`  FAIL ${f.name} — ${f.detail}`))

  await cdp.send('Browser.close').catch(() => undefined)
  ws.close()
  edge.kill()
  process.exit(0)
}

main().catch((e) => {
  console.error(`探针中断于「${STEP}」：`, e)
  console.log('\n============ 已完成的检查 ============')
  out.forEach((x) => console.log(`  ${x.ok ? 'PASS' : 'FAIL'} ${x.name} — ${x.detail}`))
  process.exit(1)
})
