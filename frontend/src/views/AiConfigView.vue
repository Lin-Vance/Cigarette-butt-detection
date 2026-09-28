<script setup lang="ts">
/** 页面 14 · AI 识别配置（阈值配置 + 规则策略） */
import { reactive, ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import { AI_ALERT_RULES, AI_THRESHOLDS, CAMERA_BLACKLIST, CAMERA_WHITELIST } from '@/mock/pages'

const thresholds = reactive(AI_THRESHOLDS.map((t) => ({ ...t })))
const rules = reactive(AI_ALERT_RULES.map((r) => ({ ...r })))

const chainOn = ref(true)
const alertLevel = ref('auto')
const repeatGap = ref(10)

const whitelist = ref([...CAMERA_WHITELIST])
const blacklist = ref([...CAMERA_BLACKLIST])
const newWhite = ref('')
const newBlack = ref('')

const log = ref<string[]>([])

function snapshot() {
  return thresholds.map((t) => `${t.label} ${t.value}${t.unit}`).join(' / ')
}

function save() {
  log.value.unshift(`已保存 · ${new Date().toLocaleTimeString('zh-CN')} · ${snapshot()}`)
  ElMessage.success('阈值配置已保存（演示环境，未写入后端）')
}

function resetThresholds() {
  thresholds.forEach((t) => {
    const origin = AI_THRESHOLDS.find((x) => x.key === t.key)
    if (origin) t.value = origin.value
  })
  ElMessage.info('已恢复默认值')
}

/** 模板中的 ref 会自动解包，因此把「输入框 + 目标数组」的成对操作收进闭包 */
function append(input: Ref<string>, target: Ref<string[]>) {
  const v = input.value.trim().toUpperCase()
  if (!v) return
  if (!/^CAM-\d{3}$/.test(v)) {
    ElMessage.warning('设备编号格式应为 CAM-000')
    return
  }
  if (target.value.includes(v)) {
    ElMessage.warning('该设备已在列表中')
    return
  }
  target.value.push(v)
  input.value = ''
}

const addWhite = () => append(newWhite, whitelist)
const addBlack = () => append(newBlack, blacklist)
</script>

<template>
  <div class="ad-page">
    <YzPanel title="阈值配置">
      <template #tools>
        <span class="yz-tag yz-tag--info">当前配置 v3.2</span>
      </template>

      <div class="params">
        <div v-for="t in thresholds" :key="t.key" class="param">
          <div class="p-head">
            <b>{{ t.label }}</b>
            <span class="p-desc">{{ t.desc }}</span>
          </div>
          <div class="p-ctrl">
            <input
              v-if="t.control === 'range'"
              v-model.number="t.value"
              class="rng"
              type="range"
              :min="t.min"
              :max="t.max"
              :step="t.step"
            />
            <input
              v-model.number="t.value"
              class="ad-ctrl num"
              type="number"
              :min="t.min"
              :max="t.max"
              :step="t.step"
            />
            <span class="unit">{{ t.unit || '—' }}</span>
            <span class="range-hint">范围 {{ t.min }} – {{ t.max }}</span>
          </div>
        </div>
      </div>

      <p class="tip">
        调低阈值会提高召回，同时增加误报；调高阈值更保守，但可能漏检。当前四项参数的组合与
        「三段式证据链」的判定帧数共同决定候选事件是否生成。
      </p>

      <div class="acts">
        <button class="ad-btn" type="button" @click="resetThresholds">重置默认值</button>
        <button class="ad-btn" type="button" @click="ElMessage.info('修改日志（演示环境）')">查看修改日志</button>
        <button class="ad-btn ad-btn--primary" type="button" @click="save">保存阈值配置</button>
      </div>

      <ul v-if="log.length" class="log">
        <li v-for="(l, i) in log" :key="i">{{ l }}</li>
      </ul>
    </YzPanel>

    <YzPanel title="规则策略" grow>
      <template #tools>
        <span class="yz-tag" :class="chainOn ? 'yz-tag--success' : 'yz-tag--muted'">
          {{ chainOn ? '策略已启用' : '策略已停用' }}
        </span>
      </template>

      <div class="policy">
        <section class="block">
          <label class="chain-sw">
            <input v-model="chainOn" type="checkbox" />
            <span class="sw-track"><i /></span>
            <b>三段式证据链</b>
          </label>
          <div class="steps">
            <span v-for="(s, i) in ['启用持续识别', '抛掷识别', '烟头落地']" :key="s" :class="{ on: chainOn }">
              <i>{{ i + 1 }}</i>{{ s }}
            </span>
          </div>
        </section>

        <section class="block">
          <p class="b-title">告警触发条件</p>
          <div class="checks">
            <label v-for="r in rules" :key="r.key" class="ck">
              <input v-model="r.on" type="checkbox" />
              <span>{{ r.label }}</span>
            </label>
          </div>
          <div class="inline">
            <label class="fld">
              <span>告警等级</span>
              <select v-model="alertLevel" class="ad-ctrl">
                <option value="auto">自动判定</option>
                <option value="high">一律高风险</option>
                <option value="mid">一律中风险</option>
              </select>
            </label>
            <label class="fld">
              <span>重复告警间隔</span>
              <input v-model.number="repeatGap" class="ad-ctrl num" type="number" min="1" max="120" />
              <i>分钟</i>
            </label>
          </div>
        </section>

        <section class="block">
          <p class="b-title">摄像头识别黑白名单配置</p>
          <div class="lists">
            <div class="list">
              <p class="l-title">白名单设备</p>
              <div class="tags">
                <span v-for="c in whitelist" :key="c" class="c-tag">
                  {{ c }}
                  <button type="button" aria-label="移除" @click="whitelist = whitelist.filter((x) => x !== c)">×</button>
                </span>
              </div>
              <div class="add">
                <input v-model="newWhite" class="ad-ctrl" placeholder="输入设备编号检索" @keydown.enter.prevent="addWhite" />
                <button class="ad-btn ad-btn--sm" type="button" @click="addWhite">添加设备</button>
              </div>
            </div>

            <div class="list">
              <p class="l-title">黑名单设备</p>
              <div class="tags">
                <span v-for="c in blacklist" :key="c" class="c-tag c-tag--dark">
                  {{ c }}
                  <button type="button" aria-label="移除" @click="blacklist = blacklist.filter((x) => x !== c)">×</button>
                </span>
              </div>
              <div class="add">
                <input v-model="newBlack" class="ad-ctrl" placeholder="输入设备编号检索" @keydown.enter.prevent="addBlack" />
                <button class="ad-btn ad-btn--sm" type="button" @click="addBlack">添加设备</button>
              </div>
            </div>
          </div>
        </section>
      </div>

      <section class="policy-dashboard">
        <article><span>策略覆盖</span><b>{{ whitelist.length + 24 }} 台</b><small>白名单与默认设备持续生效</small><i><em style="width:82%"></em></i></article>
        <article><span>近24小时候选</span><b>137 条</b><small>其中 28 条进入人工复核</small><i><em style="width:64%"></em></i></article>
        <article><span>规则命中率</span><b>88.4%</b><small>较上一版本提升 2.7%</small><i><em style="width:88%"></em></i></article>
        <article><span>误报复核</span><b>7.6%</b><small>主要来自遮挡与夜间反光</small><i><em style="width:38%"></em></i></article>
      </section>

      <section class="impact-notes">
        <div><b>本次修改影响</b><p>阈值和规则只影响候选事件生成，不会绕过人工复核，也不会自动形成处罚结论。</p></div>
        <div><b>发布检查</b><p>保存后将执行配置合法性校验，并记录操作者、版本号、修改时间和参数差异。</p></div>
        <div><b>回滚保障</b><p>系统保留最近 10 个配置版本；异常时可恢复到上一稳定版本 v3.1。</p></div>
      </section>

      <div class="acts">
        <button class="ad-btn" type="button">取消修改</button>
        <button class="ad-btn" type="button" @click="ElMessage.info('规则预览（演示环境）')">预览规则</button>
        <button class="ad-btn ad-btn--primary" type="button" @click="ElMessage.success('策略配置已保存（演示环境）')">
          保存配置
        </button>
      </div>
    </YzPanel>
  </div>
</template>

<style scoped>
.params {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 26px;
}

.param {
  padding: 12px 14px;
  border: 1px solid #e2ecf4;
  border-radius: 10px;
  background: rgba(248, 251, 253, 0.8);
}

.p-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.p-head b {
  font-size: 13px;
  color: var(--yz-text-strong);
}

.p-desc {
  font-size: 11px;
  color: var(--yz-text-muted);
}

.p-ctrl {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.num {
  width: 88px;
  min-width: 0;
  text-align: center;
}

.unit {
  font-size: 11px;
  color: var(--yz-text-muted);
  min-width: 34px;
}

.range-hint {
  margin-left: auto;
  font-size: 11px;
  color: var(--yz-text-placeholder);
}

.rng {
  flex: 1;
  max-width: 260px;
  accent-color: var(--yz-primary);
}

.tip {
  margin-top: 14px;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid #cfe4f5;
  background: #f2f9ff;
  font-size: 12px;
  line-height: 20px;
  color: var(--yz-text-2);
}

.acts {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}

.log {
  margin-top: 10px;
  font-size: 11px;
  color: var(--yz-text-muted);
  line-height: 20px;
}

.policy {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.block {
  padding-bottom: 16px;
  border-bottom: 1px dashed #dbe8f2;
}

.block:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.chain-sw {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.chain-sw input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.sw-track {
  position: relative;
  width: 38px;
  height: 21px;
  border-radius: 11px;
  background: #cfdce8;
  transition: background 0.18s;
}

.sw-track i {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.18s;
}

.chain-sw input:checked + .sw-track {
  background: var(--yz-primary);
}

.chain-sw input:checked + .sw-track i {
  transform: translateX(17px);
}

.chain-sw b {
  font-size: 13px;
  color: var(--yz-text-strong);
}

.steps {
  display: flex;
  align-items: center;
  gap: 26px;
  margin-top: 14px;
}

.steps span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--yz-text-placeholder);
}

.steps span i {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  border: 1px solid #cfdce8;
  font-style: normal;
  font-size: 11px;
}

.steps span.on {
  color: var(--yz-text-2);
}

.steps span.on i {
  border-color: transparent;
  background: var(--yz-primary);
  color: #fff;
}

.b-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--yz-text-strong);
}

.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 26px;
  margin-top: 10px;
}

.ck {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--yz-text-2);
  cursor: pointer;
}

.ck input {
  width: 14px;
  height: 14px;
  accent-color: var(--yz-primary);
}

.inline {
  display: flex;
  gap: 26px;
  margin-top: 12px;
}

.fld {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--yz-text-muted);
}

.fld i {
  font-style: normal;
}

.lists {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
  margin-top: 12px;
}

.l-title {
  font-size: 12px;
  color: var(--yz-text-muted);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 9px 0;
  min-height: 26px;
}

.c-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 6px 0 10px;
  border-radius: 6px;
  border: 1px solid #bdebd9;
  background: #ebfaf4;
  color: #1d9e75;
  font-size: 12px;
  font-family: Consolas, Monaco, monospace;
}

.c-tag--dark {
  border-color: #ffc6be;
  background: #fff0ee;
  color: #f05a4e;
}

.c-tag button {
  border: 0;
  background: none;
  color: inherit;
  font-size: 13px;
  line-height: 1;
  opacity: 0.7;
}

.c-tag button:hover {
  opacity: 1;
}

.add {
  display: flex;
  gap: 8px;
}

.add .ad-ctrl {
  flex: 1;
  min-width: 0;
}
.policy-dashboard { display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px; }
.policy-dashboard article { padding:14px;border:1px solid #dce8f1;border-radius:10px;background:linear-gradient(145deg,#f8fbff,#f7fcfa); }
.policy-dashboard span,.policy-dashboard small { display:block;color:var(--yz-text-muted);font-size:10px; }
.policy-dashboard b { display:block;margin:7px 0 4px;color:#1f4767;font-size:19px; }
.policy-dashboard i { display:block;height:6px;margin-top:10px;overflow:hidden;border-radius:6px;background:#e5edf3; }
.policy-dashboard em { display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,#238aff,#32be88); }
.impact-notes { display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px; }
.impact-notes div { padding:12px 14px;border-left:3px solid #2e8be8;background:#f4f9fd; }
.impact-notes b { color:var(--yz-text-strong);font-size:11px; }
.impact-notes p { margin-top:5px;color:var(--yz-text-muted);font-size:10px;line-height:1.6; }
</style>
