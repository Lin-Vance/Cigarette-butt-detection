<script setup lang="ts">
/** 页面 17 · 全平台基础配置 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { useDemoStore } from '@/stores/demo'
import { FEEDBACK_ROWS, fmtDateTime, PUBLIC_CONTENTS } from '@/mock/pages'
import type { ScaleMode } from '@/mock/config'

const demo = useDemoStore()
demo.init()

/* ---- 基础配置 ---- */
const sysName = ref('烟踪智治城市治理平台')
const alertOn = ref(true)
const pushSite = ref(true)
const pushBrowser = ref(false)
const adminSize = ref('10')
const citizenSize = ref('10')

/* ---- 公共内容 ---- */
const contents = ref({ ...PUBLIC_CONTENTS })

/* ---- 反馈 ---- */
const feedback = ref(FEEDBACK_ROWS.map((f) => ({ ...f })))
const TABS = [
  { key: 'all', label: '全部状态' },
  { key: 'pending', label: '待处理' },
  { key: 'done', label: '已处理' }
] as const
const tab = ref<'all' | 'pending' | 'done'>('all')
const kw = ref('')

const filteredFb = computed(() =>
  feedback.value.filter((f) => {
    if (tab.value === 'pending' && f.handled) return false
    if (tab.value === 'done' && !f.handled) return false
    if (kw.value.trim() && !f.content.includes(kw.value.trim()) && !f.author.includes(kw.value.trim()))
      return false
    return true
  })
)

const fbPage = ref(1)
const fbSize = ref(5)
watch([filteredFb, fbSize], () => (fbPage.value = 1))
const pagedFb = computed(() =>
  filteredFb.value
    .slice((fbPage.value - 1) * fbSize.value, fbPage.value * fbSize.value)
    .map((f) => ({ ...f, ts: fmtDateTime(f.ts) }))
)

const FB_COLS: YzColumn[] = [
  { key: 'ts', label: '提交时间', width: '1.4fr' },
  { key: 'author', label: '提交人', width: '1.1fr' },
  { key: 'content', label: '反馈内容', width: '2.6fr' },
  { key: 'area', label: '所属区域', width: '0.9fr' },
  { key: 'status', label: '反馈状态', width: '90px' },
  { key: 'op', label: '操作', width: '210px', align: 'right' }
]

/* ---- 演示数据量级（对应修订说明 C2） ---- */
const SCALES: { key: ScaleMode; label: string; desc: string }[] = [
  { key: 'design', label: '设计稿量级', desc: '沿用设计稿数值，视觉与已验收页面一致' },
  { key: 'pilot', label: '试点实测量级', desc: '与 2-4 路摄像头校园试点匹配，答辩讲解用' }
]

function switchScale(mode: ScaleMode) {
  if (demo.scaleMode === mode) return
  demo.setScaleMode(mode)
  ElMessage.success(`已切换到「${SCALES.find((s) => s.key === mode)?.label}」，全站数据已重建`)
}

function markHandled(id: string) {
  feedback.value = feedback.value.map((f) => (f.id === id ? { ...f, handled: true } : f))
  ElMessage.success('已标记为已处理')
}
</script>

<template>
  <div class="ad-page">
    <YzPanel title="全平台基础配置">
      <p class="sub">统一控制「超级管理员后台、区域管理员后台、市民前端」三端基础配置</p>

      <div class="grid">
        <label class="fld">
          <span>系统名称</span>
          <input v-model="sysName" class="ad-ctrl wide" />
        </label>

        <div class="fld">
          <span>全局 AI 告警总开关</span>
          <label class="sw">
            <input v-model="alertOn" type="checkbox" />
            <span class="sw-track"><i /></span>
            <b>{{ alertOn ? 'ON' : 'OFF' }}</b>
          </label>
        </div>

        <div class="fld">
          <span>告警消息推送</span>
          <div class="checks">
            <label class="ck"><input v-model="pushSite" type="checkbox" /><span>站内通知</span></label>
            <label class="ck"><input v-model="pushBrowser" type="checkbox" /><span>浏览器通知</span></label>
          </div>
        </div>

        <div class="fld">
          <span>平台 Logo</span>
          <div class="logo-row">
            <span class="logo-box">
              <!-- 全站唯一品牌标识，与后台顶栏 / 入口页 / 各端共用同一张 -->
              <img src="/logo-horizontal.png" alt="平台 Logo 预览" />
            </span>
            <div class="logo-side">
              <p class="hint">当前使用平台统一品牌标识（只读）；替换需走运维审批</p>
              <div class="logo-acts">
                <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('演示环境：品牌标识只读')">
                  选择文件
                </button>
                <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('演示环境：品牌标识只读')">移除</button>
              </div>
            </div>
          </div>
        </div>

        <label class="fld">
          <span>管理员后台分页条数</span>
          <select v-model="adminSize" class="ad-ctrl">
            <option value="10">10 条/页</option>
            <option value="20">20 条/页</option>
            <option value="50">50 条/页</option>
          </select>
        </label>

        <label class="fld">
          <span>市民前端分页条数</span>
          <select v-model="citizenSize" class="ad-ctrl">
            <option value="10">10 条/页</option>
            <option value="20">20 条/页</option>
          </select>
        </label>
      </div>

      <div class="scale">
        <p class="scale-title">演示数据量级</p>
        <p class="scale-note">
          设计稿写「在线设备 3,842 / 今日违规 1,286」，与项目声明的「2–4 路摄像头校园试点」不符，
          评审现场容易被质疑。这里提供两档可切换。
        </p>
        <div class="scale-opts">
          <button
            v-for="s in SCALES"
            :key="s.key"
            class="scale-btn"
            :class="{ on: demo.scaleMode === s.key }"
            type="button"
            @click="switchScale(s.key)"
          >
            <b>{{ s.label }}</b>
            <i>{{ s.desc }}</i>
          </button>
        </div>
      </div>

      <div class="acts">
        <button class="ad-btn" type="button" @click="ElMessage.info('已恢复默认（演示环境）')">恢复默认</button>
        <button class="ad-btn ad-btn--primary" type="button" @click="ElMessage.success('系统设置已保存（演示环境）')">
          保存系统设置
        </button>
      </div>
    </YzPanel>

    <YzPanel title="用户反馈管理" :count="filteredFb.length" grow>
      <div class="fb-bar">
        <div class="tabs">
          <button
            v-for="t in TABS"
            :key="t.key"
            class="tab"
            :class="{ on: tab === t.key }"
            type="button"
            @click="tab = t.key"
          >
            {{ t.label }}
          </button>
        </div>
        <input v-model="kw" class="ad-ctrl" placeholder="请输入反馈内容或提交人" style="width: 240px" />
        <button class="ad-btn" type="button" @click="kw = ''">重置</button>
        <button class="ad-btn ad-btn--primary" type="button" @click="ElMessage.info('已按条件查询（演示环境）')">
          查询
        </button>
      </div>

      <YzTable :columns="FB_COLS" :rows="pagedFb" row-key="id">
        <template #cell-status="{ row }">
          <span class="yz-tag" :class="row.handled ? 'yz-tag--success' : 'yz-tag--warning'">
            {{ row.handled ? '已处理' : '待处理' }}
          </span>
        </template>
        <template #cell-op="{ row }">
          <button class="ad-link" type="button">查看详情</button>
          <button class="ad-link" type="button" style="margin-left: 8px">填写处理备注</button>
          <button
            v-if="!row.handled"
            class="ad-link"
            type="button"
            style="margin-left: 8px"
            @click="markHandled(row.id)"
          >
            标记已处理
          </button>
        </template>
      </YzTable>

      <YzPager v-model:page="fbPage" v-model:size="fbSize" :total="filteredFb.length" :size-options="[5, 10, 20]" />
    </YzPanel>

    <YzPanel title="全平台公共内容配置">
      <div class="editor-grid">
        <label class="ed">
          <span>后台系统提示文案<em>{{ contents.adminTip.length }}/200</em></span>
          <div class="toolbar">
            <button type="button">B</button><button type="button"><i>I</i></button>
            <button type="button"><u>U</u></button><button type="button">•</button><button type="button">↺</button>
          </div>
          <textarea v-model="contents.adminTip" class="ad-ctrl area" maxlength="200" />
        </label>

        <label class="ed">
          <span>市民前端提示文案<em>{{ contents.citizenTip.length }}/200</em></span>
          <div class="toolbar">
            <button type="button">B</button><button type="button"><i>I</i></button>
            <button type="button"><u>U</u></button><button type="button">•</button><button type="button">↺</button>
          </div>
          <textarea v-model="contents.citizenTip" class="ad-ctrl area" maxlength="200" />
        </label>

        <label class="ed">
          <span>报表导出模板文字</span>
          <div class="toolbar">
            <button type="button">B</button><button type="button"><i>I</i></button>
            <button type="button"><u>U</u></button><button type="button">•</button><button type="button">↺</button>
          </div>
          <textarea v-model="contents.reportTemplate" class="ad-ctrl area" />
          <p class="vars">可用变量：<code>{date_range}</code> <code>{organization}</code> <code>{operator}</code></p>
        </label>
      </div>

      <div class="acts">
        <button class="ad-btn" type="button" @click="ElMessage.info('公共内容预览（演示环境）')">预览公共内容</button>
        <button class="ad-btn ad-btn--primary" type="button" @click="ElMessage.success('公共内容已保存（演示环境）')">
          保存公共内容
        </button>
      </div>
    </YzPanel>
  </div>
</template>

<style scoped>
.sub {
  font-size: 12px;
  color: var(--yz-text-muted);
  margin-bottom: 14px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 30px;
}

.fld {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fld > span {
  width: 150px;
  flex: none;
  font-size: 12px;
  color: var(--yz-text-muted);
}

.wide {
  flex: 1;
  min-width: 0;
}

.checks {
  display: flex;
  gap: 18px;
}

.ck {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--yz-text-2);
  cursor: pointer;
}

.ck input {
  width: 14px;
  height: 14px;
  accent-color: var(--yz-primary);
}

.sw {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.sw input {
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

.sw input:checked + .sw-track {
  background: var(--yz-primary);
}

.sw input:checked + .sw-track i {
  transform: translateX(17px);
}

.sw b {
  font-size: 12px;
  color: var(--yz-success);
}

.logo-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-box {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  border: 1px solid #dbe8f2;
  background: #fff;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.logo-box img {
  max-width: 42px;
  max-height: 42px;
  object-fit: contain;
}

.hint {
  font-size: 11px;
  color: var(--yz-text-placeholder);
}

.logo-acts {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}

/* ---- 量级切换 ---- */
.scale {
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid #cfe4f5;
  background: #f2f9ff;
}

.scale-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--yz-text-strong);
}

.scale-note {
  margin-top: 4px;
  font-size: 11px;
  line-height: 18px;
  color: var(--yz-text-2);
}

.scale-opts {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.scale-btn {
  flex: 1;
  text-align: left;
  padding: 10px 14px;
  border-radius: 9px;
  border: 1px solid var(--yz-border-soft);
  background: #fff;
}

.scale-btn b {
  display: block;
  font-size: 13px;
  color: var(--yz-text-strong);
}

.scale-btn i {
  display: block;
  margin-top: 3px;
  font-style: normal;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.scale-btn.on {
  border-color: var(--yz-primary);
  background: #eaf5ff;
}

.scale-btn.on b {
  color: var(--yz-primary);
}

/* ---- 反馈 ---- */
.fb-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.tabs {
  display: flex;
  gap: 6px;
}

.tab {
  height: 30px;
  padding: 0 14px;
  border-radius: 7px;
  border: 1px solid var(--yz-border-soft);
  background: #fff;
  font-size: 12px;
  color: var(--yz-text-2);
}

.tab.on {
  border-color: transparent;
  background: var(--yz-primary);
  color: #fff;
}

/* ---- 富文本 ---- */
.editor-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.ed > span {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--yz-text-muted);
}

.ed > span em {
  font-style: normal;
  color: var(--yz-text-placeholder);
}

.toolbar {
  display: flex;
  gap: 4px;
  margin: 6px 0;
  padding: 4px 6px;
  border: 1px solid #dbe8f2;
  border-radius: 7px;
  background: #f7fbfe;
}

.toolbar button {
  width: 24px;
  height: 22px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--yz-text-2);
  font-size: 12px;
}

.toolbar button:hover {
  background: #e8f3fc;
  color: var(--yz-primary);
}

.area {
  width: 100%;
  height: 74px;
  padding: 8px 10px;
  line-height: 20px;
  resize: none;
}

.vars {
  margin-top: 6px;
  font-size: 11px;
  color: var(--yz-text-placeholder);
}

.vars code {
  padding: 1px 5px;
  border-radius: 4px;
  background: #eef6fd;
  color: #1a72b8;
  font-size: 11px;
}

.acts {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
</style>
