/**
 * 中文语音朗读（浏览器内置 TTS）。
 *
 * 为什么做成组合式函数：市民端至少三处要朗读 —— 科普文章、互动剧情「烟的一生」、
 * 新闻卡片 —— 而朗读必须是**一个全局播报器**（同时只播一条、可暂停/继续/停止/改语速、
 * 能高亮"正在读哪一条"）。散在各处写 `speechSynthesis` 会互相打断。
 *
 * 实现要点（都是踩过的坑）：
 *  1. `getVoices()` 首次调用常常返回空数组，要监听 `voiceschanged` 并主动预热；
 *  2. `cancel()` 之后部分浏览器仍会回调 `onend`，于是"下一段"会被推进两次 → 用 runToken 守卫；
 *  3. 改语速时正在播的段落不会自动变速，必须取消后从当前段重播；
 *  4. 组件卸载必须 `cancel()`，否则离开页面后声音还在继续；
 *  5. 不支持 TTS 时给可见提示，而不是按钮点了没反应。
 */
import { onBeforeUnmount, ref } from 'vue'

export interface SpeechSegment {
  /** 稳定标识，用于高亮「正在朗读」的那一条 */
  id: string
  /** 朗读文本 */
  text: string
}

/** 语速可选项（长者默认略慢，便于听清） */
export const SPEECH_RATES = [0.7, 0.85, 0.95, 1.1] as const

export function useSpeech(defaultRate = 0.85) {
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const currentId = ref('')
  const speaking = ref(false)
  const paused = ref(false)
  const rate = ref(defaultRate)
  const message = ref(supported ? '' : '当前浏览器不支持语音朗读，请改用 Edge / Chrome 打开。')

  /** 每次播放/取消都 +1，用来丢弃旧 utterance 的延迟回调 */
  let runToken = 0
  let segments: SpeechSegment[] = []
  let cursor = 0

  function allVoices(): SpeechSynthesisVoice[] {
    if (!supported) return []
    try {
      return window.speechSynthesis.getVoices() ?? []
    } catch {
      return []
    }
  }

  /** 优先挑中文女声，其次任意中文，最后交给浏览器按 lang 自己选 */
  function pickVoice(): SpeechSynthesisVoice | null {
    const voices = allVoices()
    if (!voices.length) return null
    const zh = voices.filter((v) => /^zh/i.test(v.lang) || /中文|Chinese|普通话/i.test(v.name))
    if (!zh.length) return null
    const preferred = zh.find((v) =>
      /xiaoxiao|xiaoyi|huihui|yaoyao|kangkang|lili|女|female/i.test(`${v.name} ${v.voiceURI}`)
    )
    return preferred ?? zh.find((v) => /zh[-_]CN/i.test(v.lang)) ?? zh[0]
  }

  if (supported) {
    // 预热一次，并监听后续注入（Edge/Chrome 的语音列表是异步就绪的）
    allVoices()
    try {
      window.speechSynthesis.addEventListener('voiceschanged', () => allVoices())
    } catch {
      /* 老浏览器不支持 addEventListener，忽略 */
    }
  }

  function resetState() {
    speaking.value = false
    paused.value = false
    currentId.value = ''
  }

  function stop() {
    if (!supported) return
    runToken += 1
    segments = []
    cursor = 0
    try {
      window.speechSynthesis.cancel()
    } catch {
      /* 忽略 */
    }
    resetState()
  }

  function speakCurrent(token: number) {
    if (!supported || token !== runToken) return
    if (cursor >= segments.length) {
      resetState()
      return
    }
    const seg = segments[cursor]
    currentId.value = seg.id
    speaking.value = true

    const utter = new SpeechSynthesisUtterance(seg.text)
    utter.lang = 'zh-CN'
    utter.rate = rate.value
    utter.pitch = 1
    const voice = pickVoice()
    if (voice) utter.voice = voice

    const advance = () => {
      // cancel() 之后旧回调可能还会来，用 token 丢弃
      if (token !== runToken) return
      cursor += 1
      speakCurrent(token)
    }
    utter.onend = advance
    utter.onerror = advance

    try {
      window.speechSynthesis.speak(utter)
    } catch {
      message.value = '语音引擎调用失败，请检查系统是否安装了中文语音包。'
      resetState()
    }
  }

  /** 从指定位置开始按顺序朗读 */
  function speakList(list: SpeechSegment[]) {
    if (!supported) return
    if (!list.length) return
    runToken += 1
    const token = runToken
    try {
      window.speechSynthesis.cancel()
    } catch {
      /* 忽略 */
    }
    segments = [...list]
    cursor = 0
    paused.value = false
    speakCurrent(token)
  }

  /** 朗读单条（重复点击同一条会重头播） */
  function speakOne(id: string, text: string) {
    speakList([{ id, text }])
  }

  function togglePause() {
    if (!supported || !speaking.value) return
    try {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume()
        paused.value = false
      } else {
        window.speechSynthesis.pause()
        paused.value = true
      }
    } catch {
      /* 忽略 */
    }
  }

  /** 改语速：正在播且没暂停时，取消并从当前段重播 */
  function setRate(next: number) {
    rate.value = next
    if (!supported) return
    if (speaking.value && !paused.value) {
      runToken += 1
      const token = runToken
      try {
        window.speechSynthesis.cancel()
      } catch {
        /* 忽略 */
      }
      // 让 cancel 生效后再续播
      window.setTimeout(() => speakCurrent(token), 60)
    }
  }

  function cycleRate() {
    const idx = SPEECH_RATES.indexOf(rate.value as (typeof SPEECH_RATES)[number])
    setRate(SPEECH_RATES[(idx + 1) % SPEECH_RATES.length])
  }

  onBeforeUnmount(stop)

  return {
    supported,
    message,
    currentId,
    speaking,
    paused,
    rate,
    stop,
    speakList,
    speakOne,
    togglePause,
    setRate,
    cycleRate
  }
}
