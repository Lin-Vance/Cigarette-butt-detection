<script setup lang="ts">
/**
 * AI 报告卡：市民上传素材后**当场**展示模型结论。
 *
 * 为什么要单独做一个组件：同一份报告要在三处出现——
 *   ① 上报页「智能预检」步骤   ② 提交成功页   ③ 治理进度里的历史记录，
 * 而它的状态机（等待中 / 完成 / 失败 / 视频不支持）与视觉层级都比较重，
 * 内联进 CitizenAppView 会让那个文件继续膨胀。
 *
 * 展示口径（与后端 inference.py 一致，答辩时经得起追问）：
 *   · 只展示**检测结果**（检出目标、置信度、候选框），不给动作结论；
 *   · 明确写出「证据链不完整」与免责说明；
 *   · 未检出时也给出可提交的替代路径，而不是一句"不行"。
 */
import { computed } from 'vue'

export interface AiDetection {
  label: string
  label_zh?: string
  confidence: number
  box?: number[]
}

export interface AiStage {
  key: string
  label: string
  state: 'hit' | 'miss' | 'unknown' | string
  note: string
}

export interface AiReportBlock {
  engine: string
  demo: boolean
  detected: boolean
  confidence: number
  count: number
  detections: AiDetection[]
  verdict: string
  verdict_label: string
  verdict_tone: string
  summary: string
  stages: AiStage[]
  evidence: { frames: number; chain: string; note: string }
  risk_notes: string[]
  notice: string
  timings?: Record<string, unknown>
}

export type AiState = 'idle' | 'running' | 'done' | 'failed' | 'skipped'

const props = withDefaults(
  defineProps<{
    report: AiReportBlock | null
    state: AiState
    /** 已等待秒数（等待态展示） */
    elapsed?: number
    /** 失败原因 */
    error?: string
    /** 紧凑版：用在治理进度的历史记录里 */
    compact?: boolean
  }>(),
  { elapsed: 0, error: '', compact: false }
)

const emit = defineEmits<{ (e: 'retry'): void }>()

/** 等待态的四个阶段，按已等待时间推进（拿不到真实进度，就如实呈现"在做什么"） */
const STEPS = ['上传素材', '载入模型', '目标检测', '生成报告']
const stepIndex = computed(() => {
  const t = props.elapsed
  if (t < 0.6) return 0
  if (t < 1.6) return 1
  if (t < 4) return 2
  return 3
})

/** 首次加载模型会很慢：超过 8 秒就把原因说清楚，别让用户以为卡死 */
const slowHint = computed(() => (props.elapsed > 8 ? '模型首次加载约需 40~60 秒（仅第一次），请稍候' : ''))

const tone = computed(() => props.report?.verdict_tone ?? 'muted')

const confidenceText = computed(() => {
  const c = props.report?.confidence ?? 0
  return c > 0 ? `${c}%` : '未检出'
})

const stageStateText = (s: string) => (s === 'hit' ? '命中' : s === 'miss' ? '未检出' : '需视频')
</script>

<template>
  <section class="ai-card" :class="[`st-${state}`, `tone-${tone}`, { compact }]">
    <!-- ============ 等待中 ============ -->
    <template v-if="state === 'running'">
      <header class="ac-head">
        <span class="ac-badge running"><i></i>模型复检中</span>
        <em>{{ elapsed.toFixed(1) }}s</em>
      </header>
      <ol class="ac-steps">
        <li v-for="(s, i) in STEPS" :key="s" :class="{ on: i === stepIndex, done: i < stepIndex }">
          <i></i><span>{{ s }}</span>
        </li>
      </ol>
      <p class="ac-note">{{ slowHint || '正在调用 best.pt 做烟头目标检测，结果只作为候选线索。' }}</p>
    </template>

    <!-- ============ 完成 ============ -->
    <template v-else-if="state === 'done' && report">
      <header class="ac-head">
        <span class="ac-badge" :class="tone">{{ report.verdict_label }}</span>
        <em class="ac-engine">{{ report.engine }}</em>
      </header>

      <div class="ac-main">
        <div class="ac-score">
          <strong>{{ confidenceText }}</strong>
          <small>最高置信度</small>
        </div>
        <div class="ac-score">
          <strong>{{ report.count }}</strong>
          <small>检出目标数</small>
        </div>
        <div class="ac-bar"><i :style="{ width: `${Math.min(100, report.confidence)}%` }"></i></div>
      </div>

      <p class="ac-summary">{{ report.summary }}</p>

      <ul v-if="report.detections.length" class="ac-dets">
        <li v-for="(d, i) in report.detections.slice(0, 6)" :key="i">
          <b>{{ d.label_zh || d.label }}</b>
          <span class="det-bar"><i :style="{ width: `${Math.min(100, d.confidence)}%` }"></i></span>
          <em>{{ d.confidence }}%</em>
        </li>
      </ul>

      <div class="ac-stages">
        <span v-for="s in report.stages" :key="s.key" class="st" :class="s.state">
          <i></i>
          <b>{{ s.label }}</b>
          <small>{{ stageStateText(s.state) }}</small>
        </span>
      </div>

      <div class="ac-evidence">
        <b>证据链：{{ report.evidence.chain }}</b>
        <p>{{ report.evidence.note }}</p>
      </div>

      <ul v-if="!compact && report.risk_notes.length" class="ac-risks">
        <li v-for="(r, i) in report.risk_notes" :key="i">{{ r }}</li>
      </ul>

      <p class="ac-notice">{{ report.notice }}</p>
      <p v-if="!compact && report.timings" class="ac-timing">
        耗时：读取 {{ report.timings.read_ms }}ms · 推理 {{ report.timings.infer_ms }}ms ·
        合计 {{ report.timings.total_ms }}ms · 设备 {{ report.timings.device }}
      </p>
    </template>

    <!-- ============ 失败 ============ -->
    <template v-else-if="state === 'failed'">
      <header class="ac-head">
        <span class="ac-badge muted">模型未返回结果</span>
      </header>
      <p class="ac-summary">
        {{ error || '模型服务暂时不可用。' }} 已改用本地安全预检，你仍然可以提交线索，
        提交后会由授权人员在复核环节处理。
      </p>
      <button type="button" class="ac-retry" @click="emit('retry')">重试模型复检</button>
    </template>

    <!-- ============ 视频 / 未上传 ============ -->
    <template v-else-if="state === 'skipped'">
      <header class="ac-head">
        <span class="ac-badge muted">视频素材 · 待抽帧分析</span>
      </header>
      <p class="ac-summary">
        当前模型只对图片做即时检测。视频会先按本地预检放行，提交后由授权人员在复核环节抽帧。
      </p>
    </template>

    <template v-else>
      <p class="ac-summary empty">上传素材后，这里会当场给出模型检测报告。</p>
    </template>
  </section>
</template>

<style scoped>
.ai-card {
  margin-top: 12px;
  padding: 14px 15px;
  border: 1px solid #dbe6ef;
  border-radius: 14px;
  background: #f8fbfd;
}
.ai-card.st-done.tone-ok { border-color: #b7e3d2; background: linear-gradient(180deg, #f1fbf6, #fbfefd); }
.ai-card.st-done.tone-warn { border-color: #f2ddb4; background: linear-gradient(180deg, #fffaf0, #fffdf8); }
.ai-card.st-done.tone-muted { border-color: #dbe6ef; background: #f8fbfd; }
.ai-card.compact { margin-top: 10px; }

.ac-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ac-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
  background: #e7f0ff;
  color: #216eff;
}
.ac-badge.tone-ok { background: #e2f7ee; color: #17845f; }
.ac-badge.tone-warn { background: #fdf1dc; color: #b4761a; }
.ac-badge.tone-muted { background: #eef2f6; color: #6b7885; }
.ac-badge.running i { width: 7px; height: 7px; border-radius: 50%; background: #216eff; animation: acBlink 1s infinite; }
@keyframes acBlink { 50% { opacity: 0.25; } }
.ac-engine { color: #93a0ad; font-size: 10.5px; font-style: normal; text-align: right; }
.ac-head em { color: #63809a; font: 600 11px Consolas, monospace; font-style: normal; }

.ac-steps { display: flex; gap: 6px; margin: 12px 0 0; padding: 0; list-style: none; flex-wrap: wrap; }
.ac-steps li {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 999px;
  background: #eef2f6;
  color: #8b98a7;
  font-size: 11px;
}
.ac-steps li i { width: 6px; height: 6px; border-radius: 50%; background: #c3ccd6; }
.ac-steps li.on { background: #e7f0ff; color: #216eff; font-weight: 700; }
.ac-steps li.on i { background: #216eff; }
.ac-steps li.done { background: #e2f7ee; color: #17845f; }
.ac-steps li.done i { background: #2bab7c; }

.ac-main { display: flex; align-items: center; gap: 16px; margin-top: 12px; }
.ac-score { display: grid; gap: 2px; }
.ac-score strong { color: #1c2d44; font: 700 20px Consolas, monospace; }
.ac-score small { color: #93a0ad; font-size: 10.5px; }
.ac-bar { flex: 1; height: 6px; overflow: hidden; border-radius: 6px; background: #e4ebf1; }
.ac-bar i { display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, #2f7cf6, #35bf8f); transition: width .5s; }

.ac-summary { margin: 10px 0 0; color: #5b6b7d; font-size: 12px; line-height: 1.75; }
.ac-summary.empty { color: #93a0ad; }

.ac-dets { display: grid; gap: 6px; margin: 10px 0 0; padding: 0; list-style: none; }
.ac-dets li { display: grid; grid-template-columns: 62px 1fr 46px; align-items: center; gap: 8px; }
.ac-dets b { color: #37465a; font-size: 11.5px; }
.det-bar { height: 5px; border-radius: 5px; background: #e4ebf1; overflow: hidden; }
.det-bar i { display: block; height: 100%; border-radius: 5px; background: linear-gradient(90deg, #216eff, #4baedb); }
.ac-dets em { color: #216eff; font: 700 11px Consolas, monospace; font-style: normal; text-align: right; }

.ac-stages { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }
.ac-stages .st {
  display: grid;
  gap: 2px;
  padding: 9px 10px;
  border: 1px solid #e0e9f1;
  border-radius: 11px;
  background: #fff;
}
.ac-stages .st i { width: 8px; height: 8px; border-radius: 50%; background: #c3ccd6; }
.ac-stages .st.hit i { background: #2bab7c; }
.ac-stages .st.unknown i { background: #e0a63c; }
.ac-stages .st.miss i { background: #b9c4ce; }
.ac-stages .st b { color: #37465a; font-size: 11.5px; }
.ac-stages .st small { color: #93a0ad; font-size: 10px; }

.ac-evidence { margin-top: 12px; padding: 10px 12px; border-radius: 11px; background: #fff; border: 1px dashed #d5e2ec; }
.ac-evidence b { color: #2a4a6b; font-size: 11.5px; }
.ac-evidence p { margin: 4px 0 0; color: #6b7885; font-size: 11px; line-height: 1.65; }

.ac-risks { display: grid; gap: 5px; margin: 10px 0 0; padding: 0 0 0 2px; list-style: none; }
.ac-risks li { position: relative; padding-left: 15px; color: #6b7885; font-size: 11px; line-height: 1.6; }
.ac-risks li::before { content: '·'; position: absolute; left: 3px; color: #216eff; font-weight: 800; }

.ac-notice { margin: 10px 0 0; padding-top: 9px; border-top: 1px dashed #dbe6ef; color: #a3adba; font-size: 10.5px; line-height: 1.6; }
.ac-timing { margin: 5px 0 0; color: #b3bcc7; font: 10px Consolas, monospace; }

.ac-retry {
  margin-top: 11px;
  padding: 7px 16px;
  border: 1px solid #c9d6e4;
  border-radius: 999px;
  background: #fff;
  color: #216eff;
  font-size: 12px;
  cursor: pointer;
}

@media (max-width: 860px) {
  .ac-main { flex-wrap: wrap; gap: 10px; }
  .ac-stages { grid-template-columns: 1fr; }
  .ac-bar { flex-basis: 100%; }
}
</style>
