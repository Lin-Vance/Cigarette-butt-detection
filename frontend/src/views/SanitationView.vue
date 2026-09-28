<script setup lang="ts">
/** 页面 12 · 环卫资源管理 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzFilter from '@/components/ui/YzFilter.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { useDemoStore } from '@/stores/demo'
import { AREAS, buildSanitationRows } from '@/mock/pages'

const demo = useDemoStore()
demo.init()

const all = computed(() => buildSanitationRows(demo.cameras))

const filter = ref({ area: '', kw: '' })

const FIELDS = [
  { key: 'area', label: '所属区域', type: 'select' as const, placeholder: '全部区域', options: AREAS.map((a) => ({ label: a, value: a })) },
  { key: 'kw', label: '路段检索', type: 'text' as const, placeholder: '请输入路段名称或区域编号', width: '240px' }
]

const filtered = computed(() =>
  all.value.filter((r) => {
    const f = filter.value
    if (f.area && r.area !== f.area) return false
    if (f.kw) {
      const kw = f.kw.trim().toLowerCase()
      if (!r.road.toLowerCase().includes(kw) && !r.areaCode.toLowerCase().includes(kw)) return false
    }
    return true
  })
)

const page = ref(1)
const size = ref(10)
watch([filtered, size], () => (page.value = 1))
const paged = computed(() => filtered.value.slice((page.value - 1) * size.value, page.value * size.value))

const COLS: YzColumn[] = [
  { key: 'areaCode', label: '区域编号', width: '1fr' },
  { key: 'road', label: '路段名称', width: '1.8fr' },
  { key: 'location', label: '地理位置', width: '1.6fr' },
  { key: 'team', label: '管辖环卫班组', width: '1.4fr' },
  { key: 'op', label: '操作', width: '110px', align: 'right' }
]

const stats = computed(() => [
  { label: '区域总数', value: AREAS.length },
  { label: '治理路段', value: all.value.length },
  { label: '管辖环卫班组', value: new Set(all.value.map((r) => r.team)).size }
])
</script>

<template>
  <div class="ad-page">
    <div class="overview">
      <template v-for="s in stats" :key="s.label">
        <span class="mini">
          <b class="yz-num">{{ s.value }}</b>
          <i>{{ s.label }}</i>
        </span>
      </template>
      <div class="acts">
        <button class="ad-btn" type="button" @click="ElMessage.info('批量导入环卫资源数据（演示环境）')">
          批量导入环卫资源数据
        </button>
        <button class="ad-btn ad-btn--primary" type="button" @click="ElMessage.info('新增路段资源（演示环境）')">
          新增路段资源
        </button>
      </div>
    </div>

    <YzPanel title="环卫资源筛选">
      <YzFilter v-model="filter" :fields="FIELDS" />
    </YzPanel>

    <YzPanel title="环卫资源列表" :count="filtered.length" grow>
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.success('已导出资源数据（演示环境）')">
          导出资源数据
        </button>
      </template>

      <YzTable :columns="COLS" :rows="paged" selectable row-key="id">
        <template #cell-road="{ row }">
          <b>{{ row.road }}</b>
        </template>
        <template #cell-op>
          <button class="ad-link" type="button">编辑路段信息</button>
        </template>
      </YzTable>

      <YzPager v-model:page="page" v-model:size="size" :total="filtered.length" />
    </YzPanel>
  </div>
</template>

<style scoped>
.overview {
  display: flex;
  align-items: center;
  gap: 26px;
  flex: none;
  padding: 10px 16px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid #dbe8f2;
}

.mini {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.mini b {
  font-size: 20px;
  font-weight: 700;
  color: #117fba;
}

.mini i {
  font-style: normal;
  font-size: 12px;
  color: var(--yz-text-muted);
}

.acts {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
</style>
