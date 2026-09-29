<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

type FeedState = 'alert' | 'watch' | 'normal' | 'offline'
interface Feed {
  id: string
  name: string
  area: string
  image: string
  state: FeedState
  verdict: string
  confidence: number
  note: string
}

const FEEDS: Feed[] = [
  { id: 'CAM-037', name: '信阳学院北门', area: '新七大道西段', image: '/media/admin-carousel-ai.png', state: 'alert', verdict: '疑似烟蒂垃圾', confidence: 91.2, note: '地面疑似烟蒂 4 处，建议清扫复核' },
  { id: 'CAM-052', name: '校园东侧步道', area: '信阳学院周边', image: '/media/street-hero.png', state: 'watch', verdict: '散落垃圾增多', confidence: 82.6, note: '连续 3 个时间窗数量上升' },
  { id: 'CAM-018', name: '城市书房点位', area: '北京大街', image: '/media/admin-carousel-facility.png', state: 'normal', verdict: '设施状态正常', confidence: 96.8, note: '投放口与周边地面未见异常' },
  { id: 'CAM-061', name: '人民路公交站', area: '浉河区人民路', image: '/media/banner-dawn.png', state: 'alert', verdict: '设施接近满溢', confidence: 88.4, note: '建议 30 分钟内安排巡检' },
  { id: 'CAM-086', name: '羊山公园南入口', area: '羊山新区', image: '/media/banner-park.png', state: 'normal', verdict: '画面正常', confidence: 97.1, note: '未发现明确烟蒂垃圾或满溢' },
  { id: 'CAM-103', name: '环卫协同作业区', area: '学院路口', image: '/media/worker-operations-hero.png', state: 'watch', verdict: '清扫作业进行中', confidence: 93.5, note: '候选线索已转环卫任务' }
]

const now = ref(new Date())
const router = useRouter()
const reviewQueued = ref<string[]>([])
const tasked = ref<string[]>([])
const selectedId = ref(FEEDS[0].id)
const layout = ref<'six' | 'four'>('six')
const paused = ref(false)
let clock: ReturnType<typeof setInterval> | undefined

const visibleFeeds = computed(() => FEEDS.slice(0, layout.value === 'six' ? 6 : 4))
const selected = computed(() => FEEDS.find((f) => f.id === selectedId.value) ?? FEEDS[0])
const timeText = computed(() => now.value.toLocaleTimeString('zh-CN', { hour12: false }))
const dateText = computed(() => now.value.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }))
const stateText: Record<FeedState, string> = { alert: '需复核', watch: '观察中', normal: '正常', offline: '离线' }

function addReview() {
  if (!reviewQueued.value.includes(selected.value.id)) reviewQueued.value.push(selected.value.id)
  ElMessage.success(`${selected.value.id} 已加入“扔烟头动作”人工复核队列`)
}

function createTask() {
  if (!tasked.value.includes(selected.value.id)) tasked.value.push(selected.value.id)
  ElMessage.success(`已由 ${selected.value.id} 生成模拟清扫任务`)
  router.push({ name: 'dispatch-pool', query: { camera: selected.value.id, source: 'monitor-wall' } })
}

onMounted(() => {
  clock = setInterval(() => { if (!paused.value) now.value = new Date() }, 1000)
})
onBeforeUnmount(() => { if (clock) clearInterval(clock) })
</script>

<template>
  <div class="monitor-wall">
    <header class="mw-head">
      <div>
        <span>ENVIRONMENT MONITORING · SIMULATION</span>
        <h1>区域环境监控研判大屏</h1>
        <p>模拟视频流 · 识别“手部释放—烟头下落—落点遗留”的动作链 · 不启用人脸识别</p>
      </div>
      <div class="mw-clock"><strong>{{ timeText }}</strong><span>{{ dateText }} · 信阳</span></div>
      <div class="mw-tools">
        <button :class="{ on: layout === 'six' }" @click="layout = 'six'">6 画面</button>
        <button :class="{ on: layout === 'four' }" @click="layout = 'four'">4 画面</button>
        <button @click="paused = !paused">{{ paused ? '继续轮巡' : '暂停轮巡' }}</button>
      </div>
    </header>

    <section class="mw-metrics">
      <div><i class="green"></i><span>模拟在线流</span><strong>6<small>/ 6</small></strong></div>
      <div><i class="red"></i><span>需人工复核</span><strong>2<small>路</small></strong></div>
      <div><i class="amber"></i><span>环境观察中</span><strong>2<small>路</small></strong></div>
      <div><i class="blue"></i><span>今日生成任务</span><strong>12<small>件</small></strong></div>
    </section>

    <main class="mw-main">
      <section class="feed-grid" :class="`layout-${layout}`">
        <button
          v-for="feed in visibleFeeds"
          :key="feed.id"
          type="button"
          class="feed"
          :class="[`state-${feed.state}`, { selected: selectedId === feed.id }]"
          @click="selectedId = feed.id"
        >
          <img :src="feed.image" :alt="`${feed.name}模拟监控画面`" />
          <div class="feed-shade"></div><div class="scan"></div>
          <header><span><i></i> SIMULATED LIVE</span><b>{{ feed.id }}</b></header>
          <div class="focus-box" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
          <div v-if="feed.state !== 'normal'" class="action-box"><b>抛掷动作</b><span>{{ feed.confidence }}%</span></div>
          <svg v-if="feed.state !== 'normal'" class="trajectory" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d="M43 35 Q55 50 66 70"/><circle cx="66" cy="70" r="4"/></svg>
          <div v-if="feed.state !== 'normal'" class="landing-tag">烟头落点</div>
          <footer>
            <div><strong>{{ feed.name }}</strong><span>{{ feed.area }} · {{ timeText }}</span></div>
            <em>{{ stateText[feed.state] }}</em>
          </footer>
          <aside><b>{{ feed.verdict }}</b><span>{{ feed.confidence }}%</span></aside>
        </button>
      </section>

      <aside class="mw-side">
        <section class="judge-card">
          <header><span>当前画面 AI 判断</span><em>辅助判断</em></header>
          <div class="judge-place"><b>{{ selected.name }}</b><span>{{ selected.id }} · {{ selected.area }}</span></div>
          <div class="judge-score"><strong>{{ selected.confidence }}%</strong><span>动作链候选置信度</span></div>
          <h2>{{ selected.state === 'normal' ? selected.verdict : '疑似扔烟头动作' }}</h2>
          <p>{{ selected.state === 'normal' ? selected.note : `已捕捉手部释放、物体下落与地面烟蒂落点；${selected.note}。结果仅供人工复核。` }}</p>
          <div class="judge-chain"><span>① 持烟手部</span><span>② 释放下落</span><span>③ 烟头落地</span><span>关键帧 12</span></div>
          <div class="judge-actions"><button @click="addReview">{{ reviewQueued.includes(selected.id) ? '已加入复核' : '加入人工复核' }}</button><button class="primary" @click="createTask">{{ tasked.includes(selected.id) ? '查看清扫任务' : '生成清扫任务' }}</button></div>
        </section>

        <section class="queue-card">
          <header><b>实时研判队列</b><span>模拟数据</span></header>
          <ul>
            <li><i class="red"></i><div><b>信阳学院北门</b><span>疑似烟蒂垃圾 · 91.2%</span></div><time>刚刚</time></li>
            <li><i class="amber"></i><div><b>人民路公交站</b><span>设施接近满溢 · 88.4%</span></div><time>1 分钟</time></li>
            <li><i class="blue"></i><div><b>学院路口</b><span>已转清扫任务 · GD09290012</span></div><time>3 分钟</time></li>
          </ul>
        </section>

        <section class="privacy-card">
          <b>隐私与使用边界</b>
          <p>画面仅用于公共区域环境巡检；当前均为模拟素材。正式接入时默认开启脱敏，不做人脸识别、不追踪个人、不自动定责。</p>
        </section>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.monitor-wall{height:100%;padding:14px 16px 16px;overflow:hidden;color:#ddecff;background:radial-gradient(circle at 40% -10%,#12395a 0,transparent 38%),linear-gradient(145deg,#07131f,#091b2a 58%,#06111c);font-family:"Microsoft YaHei",sans-serif}
.mw-head{height:72px;display:flex;align-items:center;gap:26px;border-bottom:1px solid rgba(98,185,231,.18)}
.mw-head>div:first-child{flex:1}.mw-head h1{margin:3px 0 0;font-size:22px;letter-spacing:.06em}.mw-head p,.mw-head>div:first-child>span{margin:3px 0 0;color:#7897af;font-size:10px}.mw-head>div:first-child>span{color:#3cc9d3;letter-spacing:.18em}
.mw-clock{text-align:right}.mw-clock strong{display:block;font:700 24px Consolas}.mw-clock span{display:block;color:#7897af;font-size:10px}
.mw-tools{display:flex;gap:6px}.mw-tools button{padding:7px 10px;border:1px solid #24445d;border-radius:7px;background:#0c2030;color:#9bb3c5;font-size:11px;cursor:pointer}.mw-tools button.on{border-color:#23a7cf;background:#0b6280;color:#fff}
.mw-metrics{height:64px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:9px 0}.mw-metrics>div{display:flex;align-items:center;gap:8px;padding:0 13px;border:1px solid rgba(102,181,223,.15);border-radius:8px;background:rgba(12,35,52,.82)}.mw-metrics i,.queue-card i{width:7px;height:7px;border-radius:50%;box-shadow:0 0 10px currentColor}.green{color:#35d394;background:#35d394}.red{color:#ff6868;background:#ff6868}.amber{color:#ffbd4b;background:#ffbd4b}.blue{color:#32aef1;background:#32aef1}.mw-metrics span{color:#8ea9bd;font-size:11px}.mw-metrics strong{margin-left:auto;font:700 22px Consolas;color:#fff}.mw-metrics small{margin-left:3px;color:#68859a;font-size:10px}
.mw-main{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:12px;height:calc(100% - 136px)}
.feed-grid{display:grid;gap:8px;min-height:0}.layout-six{grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,1fr)}.layout-four{grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(2,1fr)}
.feed{position:relative;min-width:0;min-height:0;padding:0;overflow:hidden;border:1px solid #1e3e55;border-radius:8px;background:#081522;color:#fff;text-align:left;cursor:pointer}.feed.selected{border-color:#30bce0;box-shadow:0 0 0 1px #30bce0,0 0 24px rgba(48,188,224,.16)}.feed>img{width:100%;height:100%;object-fit:cover;filter:saturate(.75) brightness(.66);transition:transform 5s linear}.feed:hover>img{transform:scale(1.04)}.feed-shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,12,22,.55),transparent 40%,rgba(0,12,22,.88))}.scan{position:absolute;left:0;right:0;top:-15%;height:18%;background:linear-gradient(180deg,transparent,rgba(64,218,235,.08),transparent);animation:scan 4s linear infinite}@keyframes scan{to{transform:translateY(650%)}}
.feed>header{position:absolute;left:10px;right:10px;top:8px;display:flex;justify-content:space-between;align-items:center;font:10px Consolas}.feed>header span{color:#b8eddf}.feed>header i{display:inline-block;width:6px;height:6px;margin-right:5px;border-radius:50%;background:#31d394;box-shadow:0 0 8px #31d394}.feed>header b{color:#a0b5c5}.feed>footer{position:absolute;left:10px;right:10px;bottom:8px;display:flex;align-items:end;justify-content:space-between}.feed>footer strong{display:block;font-size:13px}.feed>footer span{display:block;margin-top:3px;color:#a3b4c1;font-size:9px}.feed>footer em{padding:3px 7px;border-radius:999px;background:#23805f;color:#fff;font-size:9px;font-style:normal}.state-alert>footer em{background:#b84c50}.state-watch>footer em{background:#a77222}
.feed>aside{position:absolute;right:9px;top:30px;padding:5px 7px;border:1px solid rgba(255,255,255,.16);border-radius:5px;background:rgba(3,15,24,.7);backdrop-filter:blur(4px)}.feed>aside b{font-size:9px}.feed>aside span{margin-left:7px;color:#5dd9e8;font:700 10px Consolas}.focus-box{position:absolute;left:46%;top:45%;width:54px;height:38px;border:1px solid rgba(255,101,101,.8)}.focus-box i{position:absolute;width:7px;height:7px;border-color:#ff6868}.focus-box i:nth-child(1){left:-1px;top:-1px;border-left:2px solid;border-top:2px solid}.focus-box i:nth-child(2){right:-1px;top:-1px;border-right:2px solid;border-top:2px solid}.focus-box i:nth-child(3){left:-1px;bottom:-1px;border-left:2px solid;border-bottom:2px solid}.focus-box i:nth-child(4){right:-1px;bottom:-1px;border-right:2px solid;border-bottom:2px solid}
.mw-side{display:grid;grid-template-rows:minmax(0,1fr) auto auto;gap:8px;min-height:0}.mw-side>section{border:1px solid rgba(99,181,223,.17);border-radius:9px;background:rgba(10,31,47,.92)}.judge-card{display:flex;flex-direction:column;min-height:0;padding:14px}.judge-card header,.queue-card header{display:flex;justify-content:space-between;align-items:center}.judge-card header span{font-size:12px;font-weight:700}.judge-card header em,.queue-card header span{color:#47c8d4;font-size:9px;font-style:normal}.judge-place{margin-top:15px;padding:9px;border-left:2px solid #35bfd4;background:#0d2639}.judge-place b,.judge-place span{display:block}.judge-place b{font-size:13px}.judge-place span{margin-top:3px;color:#6f91aa;font-size:9px}.judge-score{display:flex;align-items:end;gap:9px;margin-top:14px}.judge-score strong{color:#45d4df;font:700 34px/1 Consolas}.judge-score span{padding-bottom:3px;color:#69889f;font-size:9px}.judge-card h2{margin:13px 0 0;font-size:17px}.judge-card>p{margin:6px 0 0;color:#8ea9bd;font-size:10px;line-height:1.6}.judge-chain{display:flex;flex-wrap:wrap;gap:5px;margin-top:12px}.judge-chain span{padding:4px 6px;border-radius:4px;background:#102c42;color:#87a6ba;font-size:8px}.judge-actions{display:flex;gap:6px;margin-top:auto}.judge-actions button{flex:1;padding:8px 3px;border:1px solid #2b5c78;border-radius:6px;background:transparent;color:#9fc3d8;font-size:9px}.judge-actions .primary{border:0;background:linear-gradient(90deg,#1589ce,#16b790);color:#fff}
.queue-card{padding:11px 12px}.queue-card header b{font-size:11px}.queue-card ul{margin:7px 0 0;padding:0;list-style:none}.queue-card li{display:flex;align-items:center;gap:8px;padding:6px 0;border-top:1px solid rgba(255,255,255,.06)}.queue-card li div{flex:1}.queue-card li b,.queue-card li span{display:block}.queue-card li b{font-size:9px}.queue-card li span,.queue-card time{margin-top:2px;color:#6f8ea4;font-size:8px}.privacy-card{padding:10px 12px;border-color:rgba(51,205,154,.22)!important}.privacy-card b{color:#66dbb3;font-size:10px}.privacy-card p{margin:4px 0 0;color:#7695aa;font-size:8px;line-height:1.55}
.monitor-wall{font-size:13px;font-weight:500}.mw-head p,.mw-head>div:first-child>span{font-size:12px}.mw-tools button{padding:8px 12px;font-size:12px;font-weight:700}.mw-metrics span{font-size:12px}.feed>header{font-size:11px}.feed>footer strong{font-size:14px}.feed>footer span{font-size:11px}.judge-card header span{font-size:13px;font-weight:800}.judge-card>p{color:#afc2d0;font-size:12px;line-height:1.65}.judge-chain span{padding:5px 7px;font-size:10px}.judge-actions button{padding:10px 4px;font-size:11px;font-weight:700;cursor:pointer}
.action-box{position:absolute;left:38%;top:32%;padding:3px 6px;border:1px solid #ff6868;background:rgba(79,8,15,.78);color:#fff;font-size:9px}.action-box span{margin-left:5px;color:#ffb0a8}.trajectory{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.trajectory path{fill:none;stroke:#ffb23e;stroke-width:1;stroke-dasharray:3 2}.trajectory circle{fill:none;stroke:#ffb23e;stroke-width:1}.landing-tag{position:absolute;left:62%;top:70%;padding:2px 5px;border-radius:3px;background:#ff9b28;color:#142131;font-size:8px;font-weight:800}
@media(max-width:1000px){.mw-main{grid-template-columns:minmax(0,1fr) 260px}.layout-six{grid-template-columns:repeat(2,1fr);grid-template-rows:repeat(3,1fr)}.mw-head p{display:none}}
</style>
