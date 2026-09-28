<script setup lang="ts">
/** 页面 11 · 设备档案管理 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { useDemoStore } from '@/stores/demo'
import { AREAS, buildDeviceRows } from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const all = computed(() => buildDeviceRows(demo.cameras))

const filter = ref({ area: '', status: '', kw: '' })

const FIELDS = [
  { key: 'area', label: '所属区域', type: 'select' as const, placeholder: '全部区域', options: AREAS.map((a) => ({ label: a, value: a })) },
  { key: 'status', label: '设备在线状态', type: 'select' as const, placeholder: '全部状态', options: [
    { label: '在线', value: 'online' },
    { label: '离线', value: 'offline' },
    { label: '告警设备', value: 'alarm' }
  ] },
  { key: 'kw', label: '设备名称', type: 'text' as const, placeholder: '请输入设备名称或设备ID', width: '228px' }
]

const filtered = computed(() =>
  all.value.filter((d) => {
    const f = filter.value
    if (f.area && d.area !== f.area) return false
    if (f.status && d.status !== f.status) return false
    if (f.kw) {
      const kw = f.kw.trim().toLowerCase()
      if (!d.name.toLowerCase().includes(kw) && !d.id.toLowerCase().includes(kw)) return false
    }
    return true
  })
)

const page = ref(1)
const size = ref(10)
watch([filtered, size], () => (page.value = 1))
const paged = computed(() => filtered.value.slice((page.value - 1) * size.value, page.value * size.value))

const COLS: YzColumn[] = [
  { key: 'id', label: '设备ID', width: '1fr' },
  { key: 'name', label: '设备名称', width: '1.4fr' },
  { key: 'address', label: '安装地址', width: '1.8fr' },
  { key: 'gis', label: 'GIS 坐标', width: '1.6fr' },
  { key: 'rtsp', label: 'RTSP 视频地址', width: '2fr' },
  { key: 'status', label: '设备状态', width: '118px' },
  { key: 'op', label: '操作', width: '150px', align: 'right' }
]

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('当前环境不支持自动复制，请手动选择')
  }
}
</script>

<template>
  <div class="ad-page">
    <div class="ad-head">
      <div>
        <h1 class="ad-title">设备档案管理</h1>
        <p class="ad-sub">设备基础信息维护与点位绑定</p>
      </div>
      <div class="ad-actions">
        <button class="ad-btn" type="button" @click="ElMessage.info('批量导入设备数据（演示环境）')">
          批量导入设备数据
        </button>
        <button class="ad-btn ad-btn--primary" type="button" @click="ElMessage.info('新增设备（演示环境）')">
          新增设备
        </button>
      </div>
    </div>

    <YzPanel title="设备管理筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
    </YzPanel>

    <YzPanel title="设备管理列表" :count="filtered.length" grow>
      <YzTable :columns="COLS" :rows="paged" selectable row-key="id">
        <template #cell-gis="{ row }">
          <span class="copyable">
            <span class="mono">{{ row.gis }}</span>
            <button class="cp" type="button" aria-label="复制坐标" @click="copy(row.gis)">⧉</button>
          </span>
        </template>
        <template #cell-rtsp="{ row }">
          <span class="copyable">
            <span class="mono ellip">{{ row.rtsp }}</span>
            <button class="cp" type="button" aria-label="复制地址" @click="copy(row.rtsp)">⧉</button>
          </span>
        </template>
        <template #cell-status="{ row }">
          <span class="st">
            <span class="yz-tag" :class="`yz-tag--${row.statusTone}`">{{ row.statusText }}</span>
            <i>{{ row.statusNote }}</i>
          </span>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button">预览</button>
          <button class="ad-link" type="button" style="margin-left: 8px">编辑设备信息</button>
          <button class="ad-link danger" type="button" style="margin-left: 8px">删除设备</button>
        </template>
      </YzTable>

      <YzPager v-model:page="page" v-model:size="size" :total="filtered.length" />
    </YzPanel>
  </div>
</template>

<style scoped>
.mono {
  font-family: Consolas, Monaco, monospace;
  font-size: 11px;
  letter-spacing: 0.2px;
}

.ellip {
  display: inline-block;
  max-width: 210px;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: middle;
  white-space: nowrap;
}

.copyable {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.cp {
  border: 1px solid #cfe0ee;
  border-radius: 4px;
  background: #f5fbfe;
  color: #168dc2;
  font-size: 11px;
  line-height: 1;
  padding: 2px 4px;
}

.cp:hover {
  background: #e9f6fc;
}

.st {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.st i {
  font-style: normal;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.danger {
  color: var(--yz-danger);
}
</style>
