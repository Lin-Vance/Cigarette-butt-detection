/**
 * Service Worker —— 离线缓存（渐进增强，注册失败不影响站点使用）。
 *
 * 历史问题（缺陷 D-07）：这里曾是已删除的 landing 工程遗留，
 * `CACHE_NAME = 'yanzong-landing-v1'`、`CORE_ASSETS` 指向 `./favicon.svg`
 * 和 `./landing/civic-forensics-hero.png` —— 两个文件都已不存在，
 * `cache.addAll()` 必然 reject（而注册处 `.catch(() => {})` 把错误吞掉），
 * 于是 install 永远失败、离线缓存从未生效。
 *
 * 现在按**当前五页 MPA 结构**重写：五个 HTML 入口 + 品牌资产 + 换端条样式。
 * 策略保持 network-first：联网时永远拿最新内容，断网时才回落到缓存，
 * 避免演示机上出现"改了页面却看到旧版本"的经典 SW 缓存坑。
 */
const CACHE_NAME = 'yanzong-mpa-v2'
const CORE_ASSETS = [
  './index.html',
  './auth.html',
  './citizen.html',
  './worker.html',
  './admin.html',
  './favicon.png',
  './apple-touch-icon.png',
  './logo-horizontal.png',
  './logo-mark.png',
  './end-switcher.css',
  './manifest.webmanifest',
  './media/street-hero.png'
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      // 单个资源缺失不应让整个 SW 装不上：逐条降级重试。
      .catch(() =>
        caches.open(CACHE_NAME).then((cache) =>
          Promise.all(
            CORE_ASSETS.map((url) =>
              cache.add(url).catch(() => undefined)
            )
          )
        )
      )
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy))
        }
        return response
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match('./index.html')))
  )
})
