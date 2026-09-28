/** RBAC 专项探针：环卫角色登录后直接深链管理页，验证是否被守卫挡回。 */
import { spawn } from 'node:child_process'
import path from 'node:path'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const PORT = 9850 + (process.pid % 100)
const PROFILE = path.join(process.env.TEMP || '/tmp', `edge-rbac-${process.pid}`)
const BASE = process.env.BASE || 'http://127.0.0.1:5182/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const child = spawn(EDGE, ['--headless=new', '--disable-gpu', '--disable-extensions', '--no-first-run',
  `--user-data-dir=${PROFILE}`, `--remote-debugging-port=${PORT}`, 'about:blank'], { stdio: 'ignore' })

let id = 0
const pending = new Map()
async function target() {
  for (let i = 0; i < 100; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
      const p = list.find((t) => t.type === 'page')
      if (p?.webSocketDebuggerUrl) return p.webSocketDebuggerUrl
    } catch {}
    await sleep(250)
  }
  throw new Error('CDP 未就绪')
}
const send = (ws, method, params = {}) => new Promise((res, rej) => {
  const i = ++id
  pending.set(i, { res, rej })
  ws.send(JSON.stringify({ id: i, method, params }))
})
const evaluate = async (ws, expression) => {
  const r = await send(ws, 'Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  return r.result?.value
}

try {
  const ws = new WebSocket(await target())
  await new Promise((r) => (ws.onopen = r))
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data)
    if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result) }
  })
  await send(ws, 'Page.enable'); await send(ws, 'Runtime.enable')

  // 1) 环卫角色登录
  await send(ws, 'Page.navigate', { url: BASE + 'auth.html#/auth?role=worker' })
  await sleep(2500)
  await evaluate(ws, `localStorage.clear()`)
  await send(ws, 'Page.navigate', { url: BASE + 'auth.html#/auth?role=worker' })
  await sleep(2500)
  const click = await evaluate(ws, `(() => {
    const ins = [...document.querySelectorAll('input')]
    const acc = ins.find(i => /工号|worker/.test(i.placeholder||'')) || ins[0]
    const pw = ins.find(i => i.type === 'password')
    const set = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })) }
    set(acc, 'worker01'); set(pw, '123456')
    const b = document.querySelector('.au-submit')
    b.click()
    return 'clicked'
  })()`).catch((e) => 'eval-error-' + e.message.slice(0, 60))
  console.log('登录点击:', click)
  await sleep(3000)
  // 跳转后重新读 URL
  const after = await evaluate(ws, `JSON.stringify({ path: location.pathname.split('/').pop(), hash: location.hash, token: (localStorage.getItem('yz.auth')||'').slice(0,40) })`)
  console.log('登录后:', after)

  // 2) 越权深链
  await send(ws, 'Page.navigate', { url: BASE + 'admin.html#/platform/users' })
  await sleep(2800)
  const g = await evaluate(ws, `JSON.stringify({ path: location.pathname.split('/').pop(), hash: location.hash, pages: (document.querySelectorAll('.ad-page, .ov').length) })`)
  console.log('环卫角色访问 admin.html#/platform/users →', g)

  // 3) manager 角色登录后访问 law-cases（并集兜底）
  await send(ws, 'Page.navigate', { url: BASE + 'auth.html#/auth?role=admin' })
  await sleep(2500)
  await evaluate(ws, `localStorage.clear()`)
  await send(ws, 'Page.navigate', { url: BASE + 'auth.html#/auth?role=admin' })
  await sleep(2500)
  await evaluate(ws, `(() => {
    const ins = [...document.querySelectorAll('input')]
    const acc = ins.find(i => /admin|账号/.test(i.placeholder||'')) || ins[0]
    const pw = ins.find(i => i.type === 'password')
    const set = (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })) }
    set(acc, 'manager'); set(pw, '123456')
    document.querySelector('.au-submit').click()
  })()`).catch(() => 'nav')
  await sleep(3000)
  await send(ws, 'Page.navigate', { url: BASE + 'admin.html#/platform/law-cases' })
  await sleep(2800)
  const lc = await evaluate(ws, `JSON.stringify({ hash: location.hash, rows: document.querySelectorAll('table tr, .table .tr').length })`)
  console.log('manager 访问 law-cases →', lc)
  child.kill()
} catch (e) {
  console.log('异常:', e.message)
  child.kill()
}
