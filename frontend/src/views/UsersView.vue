<script setup lang="ts">
/** 页面 16 · 用户账号管理（账号 + 角色 + 权限分配抽屉） */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import YzPanel from '@/components/ui/YzPanel.vue'
import YzTable, { type YzColumn } from '@/components/ui/YzTable.vue'
import YzPager from '@/components/ui/YzPager.vue'
import { ACCOUNT_ROWS, fmtDateTime, PERMISSION_TREE, ROLE_ROWS } from '@/mock/pages'

const accounts = ref(ACCOUNT_ROWS.map((a) => ({ ...a })))
const roles = ref(ROLE_ROWS.map((r) => ({ ...r })))

const aPage = ref(1)
const aSize = ref(5)
const rPage = ref(1)
const rSize = ref(5)

watch(aSize, () => (aPage.value = 1))
watch(rSize, () => (rPage.value = 1))

const pagedAccounts = computed(() =>
  accounts.value
    .slice((aPage.value - 1) * aSize.value, aPage.value * aSize.value)
    .map((a) => ({ ...a, ts: fmtDateTime(a.ts) }))
)
const pagedRoles = computed(() =>
  roles.value
    .slice((rPage.value - 1) * rSize.value, rPage.value * rSize.value)
    .map((r) => ({ ...r, ts: fmtDateTime(r.ts) }))
)

const ACCOUNT_COLS: YzColumn[] = [
  { key: 'account', label: '账号', width: '1fr' },
  { key: 'name', label: '用户名', width: '1fr' },
  { key: 'role', label: '角色', width: '1.1fr' },
  { key: 'phone', label: '手机号', width: '1.1fr' },
  { key: 'enabled', label: '账号状态', width: '92px' },
  { key: 'ts', label: '更新时间', width: '1.4fr' },
  { key: 'op', label: '操作', width: '210px', align: 'right' }
]

const ROLE_COLS: YzColumn[] = [
  { key: 'name', label: '角色名称', width: '1fr' },
  { key: 'desc', label: '角色描述', width: '1.6fr' },
  { key: 'perms', label: '拥有菜单权限', width: '2.4fr' },
  { key: 'count', label: '账号数量', width: '88px', align: 'right' },
  { key: 'ts', label: '更新时间', width: '1.3fr' },
  { key: 'op', label: '操作', width: '150px', align: 'right' }
]

/* ---- 权限抽屉 ---- */
const drawer = ref<{ open: boolean; roleName: string }>({ open: false, roleName: '' })
const checked = ref<string[]>([])

function openDrawer(roleName: string) {
  drawer.value = { open: true, roleName }
  const role = roles.value.find((r) => r.name === roleName)
  checked.value = role ? [...role.perms] : []
}

function togglePerm(label: string) {
  checked.value = checked.value.includes(label)
    ? checked.value.filter((x) => x !== label)
    : [...checked.value, label]
}

function toggleAll(on: boolean) {
  checked.value = on ? PERMISSION_TREE.map((p) => p.label) : []
}

function savePerm() {
  const role = roles.value.find((r) => r.name === drawer.value.roleName)
  if (role) {
    roles.value = roles.value.map((r) =>
      r.name === role.name ? { ...r, perms: [...checked.value] } : r
    )
  }
  drawer.value.open = false
  ElMessage.success('权限已保存（演示环境，未写入后端）')
}

function toggleAccount(id: string) {
  const acc = accounts.value.find((a) => a.id === id)
  if (!acc) return
  accounts.value = accounts.value.map((a) => (a.id === id ? { ...a, enabled: !a.enabled } : a))
  ElMessage.success(acc.enabled ? '账号已禁用' : '账号已启用')
}

function resetPwd(name: string) {
  ElMessage.info(`已向 ${name} 发送重置指引（演示环境，不展示明文密码）`)
}
</script>

<template>
  <div class="ad-page">
    <YzPanel title="用户账号管理" :count="accounts.length" count-unit="个账号">
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('新增账号（演示环境）')">新增账号</button>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('批量导入（演示环境）')">批量导入</button>
      </template>

      <YzTable :columns="ACCOUNT_COLS" :rows="pagedAccounts" selectable row-key="id">
        <template #cell-role="{ row }">
          <span class="yz-tag" :class="`yz-tag--${row.roleTone}`">{{ row.role }}</span>
        </template>
        <template #cell-enabled="{ row }">
          <span class="yz-tag" :class="row.enabled ? 'yz-tag--info' : 'yz-tag--muted'">
            {{ row.enabled ? '正常' : '已禁用' }}
          </span>
        </template>
        <template #cell-op="{ row }">
          <button class="ad-link" type="button">编辑信息</button>
          <button class="ad-link" type="button" style="margin-left: 8px" @click="resetPwd(row.name)">
            重置密码
          </button>
          <button class="ad-link" :class="{ danger: row.enabled }" type="button" style="margin-left: 8px" @click="toggleAccount(row.id)">
            {{ row.enabled ? '禁用账号' : '启用账号' }}
          </button>
        </template>
      </YzTable>

      <YzPager v-model:page="aPage" v-model:size="aSize" :total="accounts.length" :size-options="[5, 10, 20]" />
    </YzPanel>

    <YzPanel title="角色配置" :count="roles.length" count-unit="个角色" grow>
      <template #tools>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('新增角色（演示环境）')">新增角色</button>
        <button class="ad-btn ad-btn--sm" type="button" @click="ElMessage.info('复制角色（演示环境）')">复制角色</button>
      </template>

      <YzTable :columns="ROLE_COLS" :rows="pagedRoles" row-key="id">
        <template #cell-name="{ row }"><b>{{ row.name }}</b></template>
        <template #cell-perms="{ row }">
          <span class="perms">
            <span v-for="p in row.perms.slice(0, 4)" :key="p" class="p-tag">{{ p }}</span>
            <span v-if="row.perms.length > 4" class="p-more">+{{ row.perms.length - 4 }}项</span>
          </span>
        </template>
        <template #cell-op="{ row }">
          <button class="ad-link" type="button">编辑角色</button>
          <button class="ad-link" type="button" style="margin-left: 8px" @click="openDrawer(row.name)">
            分配权限
          </button>
        </template>
      </YzTable>

      <YzPager v-model:page="rPage" v-model:size="rSize" :total="roles.length" :size-options="[5, 10, 20]" />
    </YzPanel>

    <!-- 分配权限抽屉 -->
    <div v-if="drawer.open" class="mask" @click.self="drawer.open = false">
      <aside class="drawer">
        <header class="d-head">
          <div>
            <p class="d-title">分配菜单权限</p>
            <p class="d-sub">{{ drawer.roleName }}</p>
          </div>
          <button class="d-close" type="button" aria-label="关闭" @click="drawer.open = false">×</button>
        </header>

        <div class="d-body">
          <label class="ck">
            <input
              type="checkbox"
              :checked="checked.length === PERMISSION_TREE.length"
              @change="toggleAll(($event.target as HTMLInputElement).checked)"
            />
            <b>全选</b>
          </label>

          <ul class="tree">
            <li v-for="p in PERMISSION_TREE" :key="p.key">
              <label class="ck">
                <input
                  type="checkbox"
                  :checked="checked.includes(p.label)"
                  @change="togglePerm(p.label)"
                />
                <b>{{ p.label }}</b>
              </label>
              <div class="leaves">
                <span v-for="c in p.children" :key="c">{{ c }}</span>
              </div>
            </li>
          </ul>
        </div>

        <footer class="d-foot">
          <span>已选择 {{ checked.length }} 项</span>
          <div>
            <button class="ad-btn" type="button" @click="drawer.open = false">取消</button>
            <button class="ad-btn ad-btn--primary" type="button" @click="savePerm">确定</button>
          </div>
        </footer>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.perms {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 5px;
}

.p-tag {
  padding: 1px 7px;
  border-radius: 4px;
  background: #eef6fd;
  border: 1px solid #cfe4f5;
  font-size: 11px;
  color: #1a72b8;
}

.p-more {
  font-size: 11px;
  color: var(--yz-text-muted);
}

.danger {
  color: var(--yz-danger);
}

/* ---- 抽屉 ---- */
.mask {
  position: absolute;
  inset: 0;
  background: rgba(23, 63, 105, 0.18);
  z-index: 20;
  display: flex;
  justify-content: flex-end;
}

.drawer {
  width: 420px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  box-shadow: -6px 0 24px rgba(23, 63, 105, 0.14);
}

.d-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e6eef5;
}

.d-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--yz-text-strong);
}

.d-sub {
  font-size: 12px;
  color: var(--yz-text-muted);
  margin-top: 2px;
}

.d-close {
  width: 28px;
  height: 28px;
  border: 1px solid #dbe8f2;
  border-radius: 50%;
  background: #fff;
  color: var(--yz-text-muted);
  font-size: 15px;
  line-height: 1;
}

.d-body {
  flex: 1;
  overflow: auto;
  padding: 14px 20px;
}

.ck {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--yz-text-2);
  cursor: pointer;
}

.ck input {
  width: 14px;
  height: 14px;
  accent-color: var(--yz-primary);
}

.tree {
  margin-top: 12px;
}

.tree > li {
  padding: 10px 0;
  border-bottom: 1px dashed #e6eef5;
}

.leaves {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 0 22px;
}

.leaves span {
  padding: 1px 8px;
  border-radius: 4px;
  border: 1px solid #e2ecf4;
  background: #f7fbfe;
  font-size: 11px;
  color: var(--yz-text-muted);
}

.d-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-top: 1px solid #e6eef5;
  font-size: 12px;
  color: var(--yz-text-muted);
}

.d-foot > div {
  display: flex;
  gap: 10px;
}
</style>
