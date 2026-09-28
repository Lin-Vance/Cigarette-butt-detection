/**
 * 边界场景探针（QA 临时脚本，放在 shots 目录下，不进工程）
 * 用 CDP 驱动 Edge headless，验证鉴权 / 路由 / 容错等边界行为。
 */
import { spawn } from 'node:child_process'
import path from 'node:path'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const PORT = 9700 + (process.pid % 200)
const PROFILE = path.join(process.env.TEMP || '/tmp', `edge-probe-${process.pid}`)
const BASE = process.env.BASE || 'http://127.0.0.1:5182/'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function waitTarget(tries = 100) {
  for (let i = 0; i < tries; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
      const p = list.find((t) => t.type === 'page')
      if (p?.webSocketDebuggerUrl) return p.webSocketDebuggerUrl
    } catch {}
    await sleep(250)
  }
  throw new Error('CDP 端口未就绪')
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.logs = []
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id)
        this.pending.delete(m.id)
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result)
      } else if (m.method === 'Runtime.consoleAPICalled') {
        if (m.params.type === 'error') this.logs.push((m.params.args || []).map((a) => a.value ?? a.description ?? '').join(' '))
      } else if (m.method === 'Runtime.exceptionThrown') {
        this.logs.push('EXC: ' + (m.params.exceptionDetails?.exception?.description || ''))
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
  async evaluate(expr) {
    const r = await this.send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) return '<<JS-ERROR>> ' + (r.exceptionDetails.exception?.description || '').slice(0, 200)
    return r.result?.value
  }
}

const results = []
const note = (ok, name, detail = '') => {
  results.push({ ok, name, detail })
  console.log(`${ok ? '[PASS]' : '[FAIL]'} ${name}${detail ? ' — ' + detail : ''}`)
}

const child = spawn(EDGE, [
  '--headless=new', '--disable-gpu', '--disable-extensions', '--no-first-run',
  '--no-default-browser-check', '--hide-scrollbars', `--user-data-dir=${PROFILE}`,
  `--remote-debugging-port=${PORT}`, 'about:blank'
], { stdio: 'ignore' })

let cdp
try {
  const wsUrl = await waitTarget()
  const ws = new WebSocket(wsUrl)
  await new Promise((res) => (ws.onopen = res))
  cdp = new CDP(ws)
  await cdp.send('Page.enable'); await cdp.send('Runtime.enable')

  const goto = async (hash, w = 1440, h = 960) => {
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false })
    await cdp.send('Page.navigate', { url: BASE + hash })
    await sleep(2200)
  }
  const hashOf = () => cdp.evaluate('location.hash')
  const pathOf = () => cdp.evaluate('location.pathname.split("/").pop()')

  /* ---- 1. 未登录深链：应被挡到登录页 ---- */
  await goto('admin.html#/platform/audit')
  let h = await hashOf()
  note(/login/.test(h), '未登录深链 #/platform/audit 被守卫拦到登录页', 'hash=' + h)

  /* ---- 2. 未知路由：应落到入口页 ---- */
  await goto('admin.html#/this-route-does-not-exist')
  h = await hashOf(); let p = await pathOf()
  note(p === 'index.html' || h === '#/', '未知路由回落到入口页（catch-all）', `path=${p} hash=${h}`)

  /* ---- 3. 管理员空表单提交 ---- */
  await goto('auth.html#/auth?role=admin')
  const empty = await cdp.evaluate(`(async () => {
    localStorage.clear()
    const ins = [...document.querySelectorAll('input')]
    const acc = ins.find(i => /admin|工号/.test(i.placeholder||'')) || ins[0]
    const pw = ins.find(i => i.type === 'password')
    if (!acc || !pw) return JSON.stringify({ err: '找不到输入框', ph: ins.map(i=>i.placeholder) })
    const set = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })) }
    set(acc, ''); set(pw, '')
    const btn = document.querySelector('.au-submit')
    if (!btn) return JSON.stringify({ err: '找不到登录按钮' })
    btn.click()
    await new Promise(r => setTimeout(r, 700))
    const msg = (document.querySelector('.au-error, .au-msg, [class*=error]')||{}).textContent||''
    return JSON.stringify({ msg: msg.trim().slice(0,80), disabled: btn.disabled })
  })()`)
  note(!String(empty).includes('"msg":""'), '管理员登录页空表单有校验提示', String(empty).slice(0, 200))

  /* ---- 4. 错误密码 ---- */
  const wrong = await cdp.evaluate(`(async () => {
    const ins = [...document.querySelectorAll('input')]
    const acc = ins.find(i => /admin|工号/.test(i.placeholder||'')) || ins[0]
    const pw = ins.find(i => i.type === 'password')
    const set = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })) }
    set(acc, 'admin'); set(pw, 'wrong-password')
    const btn = document.querySelector('.au-submit')
    btn.click()
    await new Promise(r => setTimeout(r, 1500))
    const msg = (document.querySelector('.au-error, .au-msg, [class*=error]')||{}).textContent||''
    return JSON.stringify({ msg: msg.trim().slice(0,80), hash: location.hash })
  })()`)
  note(/login|auth/.test(String(wrong)), '错误密码被拦下（未进后台）', String(wrong).slice(0, 200))

  /* ---- 5. 环卫角色登录 ---- */
  await goto('auth.html#/auth?role=worker')
  const rbac = await cdp.evaluate(`(async () => {
    localStorage.clear()
    const ins = [...document.querySelectorAll('input')]
    const acc = ins.find(i => /worker|工号/.test(i.placeholder||'')) || ins[0]
    const pw = ins.find(i => i.type === 'password')
    if (!acc || !pw) return JSON.stringify({ err: '找不到输入框', ph: ins.map(i=>i.placeholder) })
    const set = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })) }
    set(acc, 'worker01'); set(pw, '123456')
    const btn = document.querySelector('.au-submit')
    btn.click()
    await new Promise(r => setTimeout(r, 2500))
    return JSON.stringify({ hash: location.hash, path: location.pathname.split('/').pop() })
  })()`)
  note(String(rbac).includes('worker.html') || String(rbac).includes('/worker'), '环卫角色登录后进入环卫端', String(rbac).slice(0, 200))

  /* ---- 6. 越权：环卫角色直接改 hash 访问管理页 ---- */
  if (String(rbac).includes('worker.html')) {
    await cdp.evaluate(`location.href = './admin.html#/platform/users'`)
    await sleep(2500)
    h = await hashOf()
    note(!/users/.test(h), '环卫角色访问 #/platform/users 被挡回', 'hash=' + h)
  } else {
    note(false, '环卫角色访问 #/platform/users 被挡回', '前置登录未成功，跳过')
  }

  /* ---- 7. localStorage 损坏容错 ---- */
  await goto('admin.html#/platform/overview')
  await cdp.evaluate(`localStorage.setItem('yz.auth', '{ this is not json')`)
  await cdp.send('Page.navigate', { url: BASE + 'admin.html#/platform/overview' })
  await sleep(2200)
  const broken = await cdp.evaluate(`JSON.stringify({
    hasApp: !!document.querySelector('#app') && document.querySelector('#app').children.length > 0,
    raw: (localStorage.getItem('yz.auth')||'').slice(0,20),
    hash: location.hash
  })`)
  note(!String(broken).includes('"hasApp":false'), 'localStorage 损坏时未白屏（能自愈）', String(broken).slice(0, 180))

  /* ---- 8. 市民端未登录深链 ---- */
  await cdp.evaluate(`localStorage.clear()`)
  await goto('citizen.html#/citizen')
  h = await hashOf(); p = await pathOf()
  note(p === 'citizen.html' && /citizen-login/.test(h), '市民端未登录深链跳市民登录', `path=${p} hash=${h}`)

  /* ---- 9. 控制台是否有异常 ---- */
  const realErr = cdp.logs.filter((l) => !/favicon|Download the Vue Devtools|ResizeObserver/i.test(l))
  note(realErr.length === 0, '全流程无 JS 运行时异常', realErr.slice(0, 3).join(' | ').slice(0, 300) || '无')

} catch (e) {
  console.log('探针异常:', e.message)
} finally {
  try { child.kill() } catch {}
}

const pass = results.filter((r) => r.ok).length
console.log(`\n=================== 边界探针汇总 ===================\n通过 ${pass} / ${results.length}`)
