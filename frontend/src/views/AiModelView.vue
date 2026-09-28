<script setup lang="ts">
/** 页面 13 · 模型与数据集管理 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { DATASET_ROWS, MODEL_ROWS, rand } from '@/mock/pages'

const models = ref([...MODEL_ROWS])
const datasets = ref([...DATASET_ROWS])

const mPage = ref(1)
const mSize = ref(5)
const dPage = ref(1)
const dSize = ref(5)

watch(mSize, () => (mPage.value = 1))
watch(dSize, () => (dPage.value = 1))

const pagedModels = computed(() =>
  models.value.slice((mPage.value - 1) * mSize.value, mPage.value * mSize.value)
)
const pagedDatasets = computed(() =>
  datasets.value.slice((dPage.value - 1) * dSize.value, dPage.value * dSize.value)
)

const MODEL_COLS: YzColumn[] = [
  { key: 'id', label: '模型ID', width: '0.9fr' },
  { key: 'name', label: '模型名称', width: '1.8fr' },
  { key: 'version', label: '版本号', width: '80px' },
  { key: 'ts', label: '上传时间', width: '1.4fr' },
  { key: 'state', label: '状态', width: '96px' },
  { key: 'desc', label: '描述', width: '2.2fr' },
  { key: 'op', label: '操作', width: '160px', align: 'right' }
]

const DATASET_COLS: YzColumn[] = [
  { key: 'id', label: '数据集ID', width: '0.9fr' },
  { key: 'name', label: '数据集名称', width: '2fr' },
  { key: 'samples', label: '样本数量', width: '100px', align: 'right' },
  { key: 'ts', label: '上传时间', width: '1.4fr' },
  { key: 'status', label: '数据状态', width: '96px' },
  { key: 'op', label: '操作', width: '170px', align: 'right' }
]

function enableModel(id: string) {
  models.value = models.value.map((m) => ({ ...m, enabled: m.id === id }))
  ElMessage.success('已切换启用版本')
}

function removeModel(id: string) {
  const row = models.value.find((m) => m.id === id)
  if (row?.enabled) {
    ElMessage.warning('当前启用版本不可删除，请先切换到其他版本')
    return
  }
  models.value = models.value.filter((m) => m.id !== id)
  ElMessage.success('已删除历史模型')
}

/** 模型状态是「已启用 / 未启用」二值，不写进数据层是为了保持可切换 */
function modelState(enabled: boolean) {
  const r = rand(3)
  return enabled
    ? { text: '已启用', tone: 'success' }
    : r() > 0.5
      ? { text: '未启用', tone: 'muted' }
      : { text: '未启用', tone: 'muted' }
}
</script>

<template>
  <div class="ad-page">
    <YzPanel title="模型管理" :count="models.length" count-unit="个模型版本">
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('上传模型文件（演示环境）')">
          上传模型文件
        </button>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('批量管理（演示环境）')">批量管理</button>
      </template>

      <YzTable :columns="MODEL_COLS" :rows="pagedModels" selectable row-key="id">
        <template #cell-name="{ row }"><b>{{ row.name }}</b></template>
        <template #cell-version="{ row }">
          <span class="ver mono">{{ row.version }}</span>
        </template>
        <template #cell-state="{ row }">
          <span class="yz-tag" :class="`yz-tag--${modelState(row.enabled).tone}`">
            {{ modelState(row.enabled).text }}
          </span>
        </template>
        <template #cell-op="{ row }">
          <button class="ad-link" type="button" :disabled="row.enabled" @click="enableModel(row.id)">
            {{ row.enabled ? '当前启用' : '切换启用版本' }}
          </button>
          <button class="ad-link danger" type="button" style="margin-left: 10px" @click="removeModel(row.id)">
            删除历史模型
          </button>
        </template>
      </YzTable>

      <YzPager v-model:page="mPage" v-model:size="mSize" :total="models.length" :size-options="[5, 10, 20]" />
    </YzPanel>

    <YzPanel title="数据集管理" :count="datasets.length" count-unit="个数据集" grow>
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('上传数据集包（演示环境）')">
          上传数据集包
        </button>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('批量下载（演示环境）')">批量下载</button>
      </template>

      <YzTable :columns="DATASET_COLS" :rows="pagedDatasets" selectable row-key="id">
        <template #cell-name="{ row }"><b>{{ row.name }}</b></template>
        <template #cell-samples="{ row }">{{ row.samples.toLocaleString('zh-CN') }}</template>
        <template #cell-status="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.statusTone}`">{{ row.statusText }}</span>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button">下载数据集</button>
          <button class="ad-link" type="button" style="margin-left: 10px">查看数据集简介</button>
        </template>
      </YzTable>

      <YzPager v-model:page="dPage" v-model:size="dSize" :total="datasets.length" :size-options="[5, 10, 20]" />
    </YzPanel>
  </div>
</template>

<style scoped>
.ver {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  background: #eef6fd;
  border: 1px solid #cfe4f5;
  font-size: 11px;
  color: #1a72b8;
}

.mono {
  font-family: Consolas, Monaco, monospace;
}

.danger {
  color: var(--yz-danger);
}

.ad-link:disabled {
  color: var(--yz-text-placeholder);
  text-decoration: none;
  cursor: default;
}
</style>
