/**
 * 用 CDP 精确控制视口截图（Edge headless 的 --window-size 有 500px 最小窗口限制，
 * 无法直接模拟 390px 手机视口，所以走 DevTools 协议）。
 *
 * 用法：
 *   node scripts/shot.mjs --w 1440 --h 960 --prefix d --ys auto
 *   node scripts/shot.mjs --w 390 --h 844 --prefix m --ys auto
 *   node scripts/shot.mjs --w 1440 --h 4000 --prefix full --ys 0 --full
 */
import { spawn } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
/** 端口随进程变化，避免连到上一个残留实例的调试端口 */
const PORT = 9333 + (process.pid % 400)
/** 每次用独立 profile：Edge 会在 user-data-dir 相同时复用到已运行实例，
 *  导致 CDP 连上旧窗口、截图里出现上一次的页面。 */
const PROFILE = path.join(process.env.TEMP || '/tmp', `edge-cdp-shot-${process.pid}`)

function arg(name, dflt) {
  const i = process.argv.indexOf('--' + name)
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : dflt
}

const url = arg('url', 'http://127.0.0.1:5190/')
const width = Number(arg('w', 1440))
const height = Number(arg('h', 960))
const outDir = path.resolve(arg('out', 'C:/Users/20262/Desktop/烟头行为监测/shots/landing'))
const prefix = arg('prefix', 'shot')
const ysArg = arg('ys', '0')
const fullPage = process.argv.includes('--full')

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function waitForTarget(tries = 80) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`)
      const list = await r.json()
      const page = list.find((t) => t.type === 'page')
      if (page && page.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch {
      /* 端口还没起来 */
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
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id)
        this.pending.delete(m.id)
        if (m.error) reject(new Error(JSON.stringify(m.error)))
        else resolve(m.result)
      } else if (m.method && this.listeners.has(m.method)) {
        this.listeners.get(m.method)(m.params)
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

  once(method) {
    return new Promise((resolve) => this.listeners.set(method, resolve))
  }

  on(method, fn) {
    this.listeners.set(method, fn)
  }

  async evaluate(expression) {
    const { result } = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    })
    return result.value
  }
}

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
    'about:blank',
  ],
  { stdio: 'ignore' },
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
  const problems = []
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  cdp.on('Runtime.exceptionThrown', (p) => {
    const d = p.exceptionDetails || {}
    const desc = d.exception && d.exception.description ? d.exception.description : d.text
    problems.push('EXC ' + desc)
  })
  cdp.on('Runtime.consoleAPICalled', (p) => {
    if (p.type !== 'error' && p.type !== 'warning') return
    const text = (p.args || []).map((a) => a.value || a.description || '').join(' ')
    problems.push(p.type.toUpperCase() + ' ' + text)
  })
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 700,
  })

  const loaded = cdp.once('Page.loadEventFired')
  await cdp.send('Page.navigate', { url })
  await loaded
  await sleep(1800)

  let targets
  if (ysArg === 'auto') {
    const raw = await cdp.evaluate(
      `JSON.stringify((() => {
        const sc = document.querySelector('.lp')
        const top = sc ? sc.getBoundingClientRect().top : 0
        return [...document.querySelectorAll('[data-ch],[data-chapter]')]
          .map(e => Math.round(e.getBoundingClientRect().top - top + (sc ? sc.scrollTop : window.scrollY)))
      })())`,
    )
    targets = JSON.parse(raw).map((y, i) => (i === 0 ? 0 : Math.max(0, y - 32)))
  } else {
    targets = ysArg.split(',').map(Number)
  }

  await mkdir(outDir, { recursive: true })

  const script = arg('js', '')

  for (let i = 0; i < targets.length; i++) {
    // 入口页是 .lp 内层滚动容器，window.scrollTo 对它无效
    await cdp.evaluate(
      `(() => { const sc = document.querySelector('.lp'); window.scrollTo(0, ${targets[i]}); if (sc) sc.scrollTop = ${targets[i]}; })()`,
    )
    await sleep(900)
    if (script) {
      const value = await cdp.evaluate(script)
      if (value !== undefined && value !== null) console.log('js:', JSON.stringify(value))
      await sleep(Number(arg('wait', 3600)))
    }
    const params = { format: 'png' }
    if (fullPage) params.captureBeyondViewport = true
    const { data } = await cdp.send('Page.captureScreenshot', params)
    const file = path.join(outDir, `${prefix}-${String(i).padStart(2, '0')}.png`)
    await writeFile(file, Buffer.from(data, 'base64'))
    console.log('saved', path.basename(file), 'y=' + targets[i])
  }

  const report = await cdp.evaluate(`JSON.stringify({
    vw: document.documentElement.clientWidth,
    sw: document.documentElement.scrollWidth,
    sh: document.documentElement.scrollHeight,
    anchors: [...document.querySelectorAll('[data-ch],[data-chapter]')].map(e => (e.dataset.ch || e.dataset.chapter) + ':' + Math.round(e.getBoundingClientRect().top + window.scrollY))
  })`)
  console.log('=== viewport', width + 'x' + height, '===')
  console.log(report)

  const bad = await cdp.evaluate(`(() => {
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
    return JSON.stringify(out.slice(0, 20))
  })()`)
  console.log('overflow:', bad)

  if (problems.length) {
    console.log('--- console (' + problems.length + ') ---')
    problems.slice(0, 8).forEach((p) => console.log(p.slice(0, 600)))
  }

  const probe = arg('probe', '')
  if (probe) {
    await cdp.evaluate('window.scrollTo(0, 0)')
    await sleep(500)
    const [px, py] = probe.split(',').map(Number)
    const info = await cdp.evaluate(`(() => {
      const el = document.elementFromPoint(${px}, ${py})
      if (!el) return 'null'
      const cs = getComputedStyle(el)
      return JSON.stringify({
        tag: el.tagName,
        cls: String(el.className).slice(0, 60),
        bg: cs.backgroundColor,
        pos: cs.position,
        z: cs.zIndex,
        html: el.outerHTML.slice(0, 140)
      })
    })()`)
    console.log('probe@' + probe + ':', info)
  }

  ws.close()
} catch (err) {
  console.error('FAILED:', err.message)
  code = 1
} finally {
  edge.kill()
  process.exit(code)
}
