<script setup lang="ts">
/**
 * 登录 / 注册页（auth.html）。
 *
 * 版式：左侧品牌面板（深色渐变 + 轨迹视觉）× 右侧表单面板（近白底大留白）。
 * 视觉语言与全站新 logo 同源——青绿主色、大圆角、极细分割线、克制的投影。
 *
 * 三种身份共用一个面板：
 *   市民   → 手机号 + 验证码（首次验证自动建演示账户）
 *   环卫   → worker01 / 123456
 *   管理   → admin / 123456（另有 manager / ai_dev）
 * 登录成功后跳到对应端页面，而不是留在本页。
 *
 * 另支持分角色入口：`auth.html?role=citizen|worker|admin`
 * —— 进入对应身份的单角色登录视图（隐藏跨端入口）。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useCitizenStore } from '@/stores/citizen'
import { sendLoginCode } from '@/api/endpoints'
import { toFailure } from '@/api/client'

const route = useRoute()
const auth = useAuthStore()
const citizen = useCitizenStore()

type Identity = 'citizen' | 'worker' | 'admin'
type Mode = 'login' | 'register'
type CitizenMethod = 'code' | 'password'
type StaffMethod = 'password' | 'code'

const IDENTITIES: { key: Identity; name: string; en: string; tip: string; icon: string }[] = [
  { key: 'citizen', name: '市民', en: 'CITIZEN', tip: '上报线索 · 查看进度', icon: '◎' },
  { key: 'worker', name: '环卫', en: 'SANITATION', tip: '接单 · 现场处置', icon: '✓' },
  { key: 'admin', name: '管理', en: 'ADMIN', tip: '研判 · 调度 · 协同', icon: '▤' }
]

/** 左栏品牌面板上的三条价值点 */
const FEATURES = [
  { no: '01', t: '一条事件，三个端同步', d: '市民上报、环卫处置、管理研判共享同一份状态' },
  { no: '02', t: '环境问题形成时间线', d: '提交、复核、派单、清扫与验收全程留痕' },
  { no: '03', t: '只看垃圾，不识别人', d: '不跟拍、不拦截，素材脱敏后才进入治理流程' }
]

const mode = ref<Mode>('login')
const identity = ref<Identity>('citizen')
const citizenMethod = ref<CitizenMethod>('code')
const staffMethod = ref<StaffMethod>('password')
const roleEntry = computed(() => ['citizen', 'worker', 'admin'].includes(String(route.query.role || '')))
const adminRedirect = computed(() => {
  const value = String(route.query.redirect || '')
  return value.startsWith('/platform/') ? value : '/platform/overview'
})
const identityName = computed(() => IDENTITIES.find((item) => item.key === identity.value)?.name ?? '市民')
const identityIntro = computed(() => {
  if (identity.value === 'worker') return '使用环卫工号进入作业工作台，接收任务、记录到场并提交闭环材料。'
  if (identity.value === 'admin') return '使用授权管理账号进入治理平台，开展研判、调度和系统配置。'
  return '使用手机号进入市民服务端，安全提交线索并查看治理进度。'
})

const phone = ref('13800000000')
const code = ref('')
const account = ref('')
const password = ref('')
const confirm = ref('')
const agreed = ref(true)
const revealed = ref(false)
const busy = ref(false)
const error = ref('')
const codeSentFor = ref('')
const codeCooldown = ref(0)
const sendingCode = ref(false)
const captchaA = ref(3)
const captchaB = ref(5)
const captchaAnswer = ref('')
let codeTimer: ReturnType<typeof setInterval> | undefined

const panel = ref<HTMLElement | null>(null)
const root = ref<HTMLElement | null>(null)

/* 账号默认值按身份切换，减少演示时的手输 */
watch(identity, (v) => {
  error.value = ''
  if (v === 'worker') account.value = 'worker01'
  else if (v === 'admin') account.value = 'admin'
  password.value = v === 'citizen' ? '' : '123456'
  code.value = ''
  codeSentFor.value = ''
  staffMethod.value = 'password'
  refreshCaptcha()
})

const isCitizen = computed(() => identity.value === 'citizen')

const submitText = computed(() =>
  mode.value === 'login' ? '登录' : isCitizen.value ? '创建演示账户' : '提交开通申请'
)

function goPanel(next: Mode) {
  mode.value = next
  error.value = ''
  panel.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function refreshCaptcha() {
  captchaA.value = 2 + Math.floor(Math.random() * 7)
  captchaB.value = 1 + Math.floor(Math.random() * 8)
  captchaAnswer.value = ''
}

async function requestCode() {
  const target = isCitizen.value ? phone.value.trim() : account.value.trim()
  if (isCitizen.value && !/^1\d{10}$/.test(target)) { error.value = '请先输入正确的 11 位手机号'; return }
  if (!isCitizen.value && !target) { error.value = '请先输入账号'; return }
  sendingCode.value = true
  error.value = ''
  try {
    const res = await sendLoginCode(target, identity.value)
    codeSentFor.value = target
    code.value = ''
    codeCooldown.value = 60
    if (codeTimer) clearInterval(codeTimer)
    codeTimer = setInterval(() => {
      codeCooldown.value -= 1
      if (codeCooldown.value <= 0 && codeTimer) { clearInterval(codeTimer); codeTimer = undefined }
    }, 1000)
    ElMessage.success(`验证码已发送至 ${res.masked_target}${res.demo_code ? `；本地联调码 ${res.demo_code}` : ''}`)
  } catch (err) {
    error.value = toFailure(err).message
  } finally { sendingCode.value = false }
}

function jumpToEnd(kind: Identity) {
  if (kind === 'citizen') location.href = './citizen.html'
  else if (kind === 'worker') location.href = './worker.html'
  else location.href = `./admin.html#${adminRedirect.value}`
}

async function doCitizenLogin() {
  if (!/^\d{11}$/.test(phone.value.trim())) {
    error.value = '请输入 11 位手机号'
    return
  }
  const usePassword = mode.value === 'register' || citizenMethod.value === 'password'
  if (usePassword) {
    if (password.value.length < 6) {
      error.value = '密码至少需要 6 位'
      return
    }
    if (mode.value === 'register' && password.value !== confirm.value) {
      error.value = '两次输入的密码不一致'
      return
    }
    if (mode.value === 'register' && (!/^\d{6}$/.test(code.value.trim()) || codeSentFor.value !== phone.value.trim())) {
      error.value = '注册前请先获取并填写当前手机号收到的验证码'
      return
    }
  } else if (!/^\d{6}$/.test(code.value.trim()) || codeSentFor.value !== phone.value.trim()) {
    error.value = '请先获取并填写当前手机号收到的 6 位验证码'
    return
  }
  const res = await citizen.login(phone.value.trim(), usePassword ? password.value : code.value.trim(), usePassword ? 'password' : 'code', mode.value, mode.value === 'register' ? code.value.trim() : '')
  if (!res.ok) {
    error.value = res.message
    return
  }
  ElMessage.success(mode.value === 'login' ? '登录成功' : '账户已创建，正在进入市民端')
  jumpToEnd('citizen')
}

async function doStaffLogin() {
  if (!account.value.trim()) {
    error.value = '请输入账号'
    return
  }
  if (staffMethod.value === 'password' && !password.value) { error.value = '请输入密码'; return }
  if (staffMethod.value === 'code' && (!/^\d{6}$/.test(code.value.trim()) || codeSentFor.value !== account.value.trim())) {
    error.value = '请先获取并填写该账号绑定手机收到的验证码'; return
  }
  const res = staffMethod.value === 'password'
    ? await auth.login(account.value.trim(), password.value)
    : await auth.loginByCode(account.value.trim(), code.value.trim(), identity.value as 'worker' | 'admin')
  if (!res.ok) {
    error.value = res.message
    return
  }
  // 身份与账号角色必须对得上，避免「用管理员账号点环卫」这类演示事故。
  // 注意 roleLabel 要在 logout 之前读——logout 会清掉 user，之后读只能拿到默认值。
  const role = auth.user?.role
  const label = auth.roleLabel
  if (identity.value === 'worker' && role !== 'worker') {
    auth.logout()
    error.value = `该账号角色是「${label}」，不是环卫工人。请切换到「管理」或换用 worker01`
    return
  }
  if (identity.value === 'admin' && role === 'worker') {
    auth.logout()
    error.value = '该账号是环卫工人账号，请切换到「环卫」登录'
    return
  }
  ElMessage.success('登录成功')
  jumpToEnd(identity.value)
}

async function onSubmit() {
  error.value = ''
  if (busy.value) return
  if (!agreed.value) {
    error.value = '请先阅读并同意隐私说明'
    return
  }
  if (Number(captchaAnswer.value) !== captchaA.value + captchaB.value) {
    error.value = '安全验证计算错误，请重新填写'
    refreshCaptcha()
    return
  }

  if (mode.value === 'register' && !isCitizen.value) {
    // 环卫与管理员账号不开放自助注册——这是治理系统的基本边界
    ElMessage({
      type: 'info',
      duration: 3200,
      message: '环卫与管理员账号由平台管理员在后台开通，请先在管理端「用户账号」中创建'
    })
    return
  }

  if (mode.value === 'register' && isCitizen.value) {
    if (password.value && confirm.value && password.value !== confirm.value) {
      error.value = '两次输入的密码不一致'
      return
    }
  }

  busy.value = true
  try {
    if (isCitizen.value) await doCitizenLogin()
    else await doStaffLogin()
  } finally {
    busy.value = false
  }
}

/* 首屏逐条淡入（纯 CSS 过渡 + class，不引动画库）；
   带 ?role= 时直接进入该身份的登录视图 */
function applyRouteRole() {
  const requested = String(route.query.role || '') as Identity
  if (['citizen', 'worker', 'admin'].includes(requested)) {
    identity.value = requested
    mode.value = 'login'
    if (requested === 'worker') account.value = 'worker01'
    else if (requested === 'admin') account.value = 'admin'
    if (requested !== 'citizen') password.value = '123456'
  }
}

watch(() => route.query.role, applyRouteRole, { immediate: true })

onMounted(() => {
  requestAnimationFrame(() => root.value?.classList.add('ready'))
})
onBeforeUnmount(() => { if (codeTimer) clearInterval(codeTimer) })
</script>

<template>
  <div ref="root" class="au" :class="{ 'role-entry': roleEntry }">
    <!-- 氛围光斑：随载入淡入 -->
    <div class="au-bloom" aria-hidden="true"><i class="b1" /><i class="b2" /><i class="b3" /></div>

    <!-- ---------------- 顶栏 ---------------- -->
    <header class="au-bar">
      <a class="au-brand" href="./index.html" aria-label="返回首页">
        <img src="/logo-horizontal.png" alt="烟踪智治" />
      </a>
      <nav class="au-nav" aria-label="页面导航">
        <a href="./index.html">首页</a>
        <a href="./citizen.html#/citizen?app=1">市民 App</a>
      </nav>
      <div class="au-bar-acts">
        <button class="au-text" type="button" @click="goPanel('login')">登录</button>
        <button class="au-pill" type="button" @click="goPanel('register')">注册</button>
      </div>
    </header>

    <!-- ---------------- 主体：品牌面板 × 表单面板 ---------------- -->
    <main class="au-main">
      <!-- 左：品牌 -->
      <section class="au-side">
        <div class="au-side-grid" aria-hidden="true"></div>

        <div class="au-side-top">
          <span class="au-tile"><img src="/logo-mark.png" alt="" /></span>
          <div>
            <strong>烟踪智治</strong>
            <small>YANZONG ZHIZHI</small>
          </div>
        </div>

        <div class="au-side-copy">
          <p class="au-eyebrow">城市公共空间治理原型</p>
          <h1>让每一次发现，<br /><em>都有回音</em></h1>
          <p class="au-sub">
            一个账户连接市民、环卫与治理三方。同一条事件的状态，在三个端之间实时流转。
          </p>
        </div>

        <ul class="au-feats">
          <li v-for="f in FEATURES" :key="f.no">
            <span>{{ f.no }}</span>
            <div><b>{{ f.t }}</b><em>{{ f.d }}</em></div>
          </li>
        </ul>

        <!-- 抽象轨迹：呼应「动作被还原成一条时间线」 -->
        <div class="au-viz" aria-hidden="true">
          <svg viewBox="0 0 720 150" preserveAspectRatio="none">
            <defs>
              <linearGradient id="auLine" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stop-color="#5eead4" />
                <stop offset="0.5" stop-color="#7dd3fc" />
                <stop offset="1" stop-color="#a7f3d0" />
              </linearGradient>
            </defs>
            <path
              class="viz-path"
              d="M20 126C160 126 196 32 360 32c150 0 178 84 340 84"
              fill="none"
              stroke="url(#auLine)"
              stroke-width="2.5"
              stroke-linecap="round"
            />
            <circle class="viz-dot d1" cx="20" cy="126" r="4.5" />
            <circle class="viz-dot d2" cx="360" cy="32" r="4.5" />
            <circle class="viz-dot d3" cx="700" cy="116" r="4.5" />
          </svg>
          <div class="au-viz-labels"><span>捕捉</span><span>研判</span><span>闭环</span></div>
        </div>

        <p class="au-side-note">
          演示原型 · 页面内数据、点位与工单均为模拟；行为识别管道尚未接入真实视频流。
        </p>
      </section>

      <!-- 右：表单 -->
      <section id="auth" ref="panel" class="au-auth">
        <div class="au-auth-inner">
          <header class="au-auth-head">
            <span class="au-mini-brand">
              <img src="/logo-mark.png" alt="" /><b>烟踪智治</b>
            </span>
            <span v-if="roleEntry" class="role-badge">{{ identityName }}身份入口</span>
            <h2>{{ mode === 'login' ? `${identityName}端登录` : '创建一个账户' }}</h2>
            <p>
              {{
                roleEntry
                  ? identityIntro
                  : mode === 'login'
                    ? '选择身份后填写对应凭据。演示环境不发送真实短信，也不外传任何素材。'
                    : '市民账户开箱即用；环卫与管理员账号由平台管理员在后台开通。'
              }}
            </p>
          </header>

          <div class="au-box">
            <!-- 模式切换 -->
            <div class="au-seg" role="tablist" aria-label="登录或注册">
              <button
                type="button"
                role="tab"
                :aria-selected="mode === 'login'"
                :class="{ on: mode === 'login' }"
                @click="mode = 'login'; error = ''"
              >
                登录
              </button>
              <button
                type="button"
                role="tab"
                :aria-selected="mode === 'register'"
                :class="{ on: mode === 'register' }"
                @click="mode = 'register'; error = ''"
              >
                注册
              </button>
            </div>

            <!-- 身份切换 -->
            <div class="au-ids">
              <button
                v-for="it in IDENTITIES"
                :key="it.key"
                type="button"
                class="au-id"
                :class="{ on: identity === it.key }"
                @click="identity = it.key"
              >
                <i class="au-id-ic">{{ it.icon }}</i>
                <span class="au-id-tx">
                  <strong>{{ it.name }}</strong>
                  <em>{{ it.tip }}</em>
                </span>
                <span class="au-id-en">{{ it.en }}</span>
              </button>
            </div>

            <form class="au-form" novalidate @submit.prevent="onSubmit">
              <!-- 市民：验证码 / 密码双登录，注册时设置密码 -->
              <template v-if="isCitizen">
                <div v-if="mode === 'login'" class="citizen-method" aria-label="市民登录方式">
                  <button type="button" :class="{ on: citizenMethod === 'code' }" @click="citizenMethod = 'code'; error = ''">验证码登录</button>
                  <button type="button" :class="{ on: citizenMethod === 'password' }" @click="citizenMethod = 'password'; error = ''">密码登录</button>
                </div>
                <label class="au-field">
                  <span>手机号</span>
                  <input
                    v-model="phone"
                    type="tel"
                    inputmode="tel"
                    maxlength="11"
                    autocomplete="tel"
                    placeholder="请输入 11 位手机号"
                  />
                </label>
                <label v-if="mode === 'login' && citizenMethod === 'code'" class="au-field">
                  <span>短信验证码</span>
                  <div class="au-code">
                    <input
                      v-model="code"
                      type="text"
                      inputmode="numeric"
                      maxlength="6"
                      placeholder="6 位验证码"
                    />
                    <button type="button" :disabled="sendingCode || codeCooldown > 0" @click="requestCode">
                      {{ codeCooldown > 0 ? `${codeCooldown}s` : sendingCode ? '发送中' : '获取验证码' }}
                    </button>
                  </div>
                </label>
                <label v-else class="au-field">
                  <span>{{ mode === 'register' ? '设置登录密码' : '密码' }}</span>
                  <div class="au-code">
                    <input v-model="password" :type="revealed ? 'text' : 'password'" autocomplete="current-password" placeholder="请输入至少 6 位密码" />
                    <button type="button" @click="revealed = !revealed">{{ revealed ? '隐藏' : '显示' }}</button>
                  </div>
                </label>
                <label v-if="mode === 'register'" class="au-field">
                  <span>确认密码</span>
                  <input v-model="confirm" type="password" autocomplete="new-password" placeholder="再次输入密码" />
                </label>
                <label v-if="mode === 'register'" class="au-field">
                  <span>注册验证码</span>
                  <div class="au-code">
                    <input v-model="code" inputmode="numeric" maxlength="6" placeholder="先获取验证码" />
                    <button type="button" :disabled="sendingCode || codeCooldown > 0" @click="requestCode">
                      {{ codeCooldown > 0 ? `${codeCooldown}s` : sendingCode ? '发送中' : '获取验证码' }}
                    </button>
                  </div>
                </label>
              </template>

              <!-- 环卫 / 管理员：账号密码 / 绑定手机验证码双登录 -->
              <template v-else>
                <div v-if="mode === 'login'" class="citizen-method" :aria-label="`${identityName}登录方式`">
                  <button type="button" :class="{ on: staffMethod === 'password' }" @click="staffMethod = 'password'; error = ''">密码登录</button>
                  <button type="button" :class="{ on: staffMethod === 'code' }" @click="staffMethod = 'code'; error = ''">验证码登录</button>
                </div>
                <label class="au-field">
                  <span>{{ identity === 'worker' ? '环卫工号' : '管理员账号' }}</span>
                  <input
                    v-model="account"
                    type="text"
                    autocomplete="username"
                    :placeholder="identity === 'worker' ? '例如 worker01' : '例如 admin'"
                  />
                </label>
                <label v-if="staffMethod === 'password' || mode === 'register'" class="au-field">
                  <span>密码</span>
                  <div class="au-code">
                    <input
                      v-model="password"
                      :type="revealed ? 'text' : 'password'"
                      autocomplete="current-password"
                      placeholder="请输入密码"
                    />
                    <button type="button" @click="revealed = !revealed">
                      {{ revealed ? '隐藏' : '显示' }}
                    </button>
                  </div>
                </label>
                <label v-else class="au-field">
                  <span>绑定手机验证码</span>
                  <div class="au-code">
                    <input v-model="code" inputmode="numeric" maxlength="6" placeholder="请输入 6 位验证码" />
                    <button type="button" :disabled="sendingCode || codeCooldown > 0" @click="requestCode">
                      {{ codeCooldown > 0 ? `${codeCooldown}s` : sendingCode ? '发送中' : '获取验证码' }}
                    </button>
                  </div>
                </label>
                <label v-if="mode === 'register'" class="au-field">
                  <span>确认密码</span>
                  <input v-model="confirm" type="password" placeholder="再次输入密码" />
                </label>
              </template>

              <label class="au-field">
                <span>安全验证</span>
                <div class="au-code au-captcha">
                  <input v-model="captchaAnswer" inputmode="numeric" placeholder="请输入计算结果" />
                  <button type="button" title="点击更换题目" @click="refreshCaptcha">{{ captchaA }} + {{ captchaB }} = ?</button>
                </div>
              </label>

              <label class="au-check">
                <input v-model="agreed" type="checkbox" />
                <span>我已了解：不得跟拍、拦截他人，也不得公开传播他人画面</span>
              </label>

              <p v-if="error" class="au-error" role="alert">{{ error }}</p>

              <button class="au-submit" type="submit" :disabled="busy">
                {{ busy ? '处理中…' : submitText }}<i>→</i>
              </button>

              <p class="au-tip">
                <template v-if="isCitizen">
                  验证码由后端动态生成，5 分钟有效且使用一次后失效
                </template>
                <template v-else-if="identity === 'worker'">
                  演示账号 <code>worker01 / 123456</code> · 验证码发送至绑定手机
                </template>
                <template v-else>
                  演示账号 <code>admin / 123456</code>，另可试 <code>manager</code> / <code>ai_dev</code>
                </template>
              </p>
            </form>

            <div class="au-switch">
              <template v-if="mode === 'login'">
                还没有账户？<button type="button" @click="goPanel('register')">立即注册</button>
              </template>
              <template v-else>
                已经有账户了？<button type="button" @click="goPanel('login')">去登录</button>
              </template>
            </div>
          </div>

          <div class="au-quick">
            <span>免登录体验</span>
            <a href="./citizen.html">市民端</a>
            <a href="./worker.html">环卫端</a>
            <a href="./admin.html">管理端</a>
            <a href="./index.html">介绍页</a>
          </div>
        </div>
      </section>
    </main>

    <footer class="au-foot">
      <img src="/logo-horizontal.png" alt="烟踪智治" />
      <p>烟踪智治 · 公共场所扔烟头行为证据复核与治理闭环原型 · © 2026</p>
    </footer>
  </div>
</template>

<style scoped>
/* ============================================================
   令牌：与全站新 logo 同源的青绿主色 + 近白底大留白
   ============================================================ */
.au {
  --bg: #eef7fc;
  --ink: #10202f;
  --muted: #61707f;
  --dim: #8b98a6;
  --line: #e2e8ee;
  --line-soft: #eef2f6;
  --brand: #12866f;
  --brand-2: #1f9d63;
  --cyan: #2c9fc0;
  --deep: #072330;

  position: relative;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background:
    radial-gradient(circle at 9% 28%, rgba(118, 214, 239, .22), transparent 34%),
    radial-gradient(circle at 76% 88%, rgba(105, 224, 184, .16), transparent 31%),
    linear-gradient(135deg, #edf8fd 0%, #f7fbfe 52%, #edf6fb 100%);
  color: var(--ink);
  font-family: "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
}

.au-bloom {
  position: absolute;
  inset: 0 0 auto 0;
  height: 760px;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}
.au-bloom i {
  position: absolute;
  border-radius: 50%;
  filter: blur(72px);
  opacity: 0;
  transition: opacity 1.4s ease 0.15s;
}
.au.ready .au-bloom i {
  opacity: 1;
}
.b1 {
  left: -8%;
  top: -160px;
  width: 560px;
  height: 560px;
  background: radial-gradient(circle, rgba(94, 234, 212, 0.32), transparent 68%);
}
.b2 {
  right: -6%;
  top: -140px;
  width: 520px;
  height: 520px;
  background: radial-gradient(circle, rgba(125, 211, 252, 0.28), transparent 68%);
}
.b3 {
  left: 34%;
  top: 300px;
  width: 460px;
  height: 460px;
  background: radial-gradient(circle, rgba(167, 243, 208, 0.22), transparent 70%);
}

/* ============================================================
   顶栏
   ============================================================ */
.au-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 26px;
  height: 62px;
  padding: 0 clamp(18px, 4vw, 48px);
  border-bottom: 1px solid rgba(9, 40, 60, 0.07);
  background: rgba(247, 249, 251, 0.76);
  backdrop-filter: saturate(180%) blur(20px);
}
.au-brand {
  display: inline-flex;
  flex: none;
}
.au-brand img {
  height: 30px;
  width: auto;
}
.au-nav {
  display: flex;
  align-items: center;
  gap: 24px;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.au-nav::-webkit-scrollbar {
  display: none;
}
.au-nav a {
  color: var(--muted);
  font-size: 13.5px;
  white-space: nowrap;
  text-decoration: none;
  transition: color 0.16s;
}
.au-nav a:hover {
  color: var(--ink);
}
.au-bar-acts {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex: none;
}
.au-text,
.au-pill {
  border: 0;
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.16s, color 0.16s, transform 0.16s;
}
.au-text {
  padding: 8px 12px;
  border-radius: 980px;
  background: transparent;
  color: var(--ink);
}
.au-text:hover {
  background: rgba(9, 40, 60, 0.06);
}
.au-pill {
  padding: 8px 18px;
  border-radius: 980px;
  color: #fff;
  background: linear-gradient(100deg, var(--brand), var(--cyan));
}
.au-pill:hover {
  transform: translateY(-1px);
}

/* ============================================================
   主体：左品牌 × 右表单
   ============================================================ */
.au-main {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.18fr) minmax(420px, .82fr);
  align-items: center;
  gap: clamp(44px, 6vw, 92px);
  max-width: 1320px;
  min-height: calc(100vh - 62px);
  margin: 0 auto;
  padding: clamp(42px, 5vw, 72px) clamp(24px, 5vw, 64px) 52px;
}

/* ---- 左侧品牌面板 ---- */
.au-side {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 22px;
  overflow: visible;
  padding: 20px 0;
  color: #102f64;
  background: transparent;
  box-shadow: none;
  align-self: center;
  height: min(470px, calc(100vh - 130px));
  min-height: 390px;
  justify-content: center;
}
.au-side-grid {
  display: none;
}
.au-side-top {
  display: none;
}
.au-tile {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 20px -10px rgba(0, 0, 0, 0.5);
}
.au-tile img {
  width: 30px;
  height: auto;
}
.au-side-top strong {
  display: block;
  font-size: 17px;
  letter-spacing: 0.04em;
}
.au-side-top small {
  display: block;
  margin-top: 2px;
  color: rgba(234, 246, 244, 0.5);
  font-family: Consolas, monospace;
  font-size: 9.5px;
  letter-spacing: 0.2em;
}
.au-side-copy {
  position: relative;
}
.au-eyebrow {
  font-family: Consolas, monospace;
  font-size: 11px;
  letter-spacing: 0.2em;
  color: #087dc7;
}
.au-side-copy h1 {
  margin: 18px 0 0;
  font-size: clamp(44px, 5vw, 66px);
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -.045em;
}
.au-side-copy h1 em {
  font-style: normal;
  background: linear-gradient(96deg, #1477f5, #36aee9 54%, #63dca2);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.au-sub {
  max-width: 590px;
  margin: 20px 0 0;
  color: #58779a;
  font-size: 15px;
  line-height: 1.95;
}
.au-feats {
  display: none;
}
.au-feats li {
  display: flex;
  gap: 13px;
  align-items: flex-start;
  padding: 13px 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.045);
}
.au-feats li > span {
  flex: none;
  width: 26px;
  color: rgba(167, 243, 208, 0.9);
  font: 700 11px Consolas, monospace;
  letter-spacing: 0.06em;
}
.au-feats b {
  display: block;
  font-size: 13.5px;
  font-weight: 600;
}
.au-feats em {
  display: block;
  margin-top: 4px;
  color: rgba(234, 246, 244, 0.6);
  font-size: 11.5px;
  font-style: normal;
  line-height: 1.6;
}
.au-viz {
  position: relative;
  margin-top: 20px;
  padding: 16px 22px 12px;
  border: 1px solid rgba(92, 166, 214, .22);
  border-radius: 18px;
  background: rgba(255,255,255,.78);
  box-shadow: 0 18px 45px -35px rgba(36,95,136,.34);
}
.au-viz svg {
  display: block;
  width: 100%;
  height: 118px;
}
.viz-path {
  stroke-dasharray: 900;
  stroke-dashoffset: 900;
  transition: stroke-dashoffset 2.2s cubic-bezier(0.4, 0, 0.2, 1) 0.4s;
}
.au.ready .viz-path {
  stroke-dashoffset: 0;
}
.viz-dot {
  fill: #fff;
  stroke-width: 2.5;
  opacity: 0;
  transition: opacity 0.5s ease;
}
.d1 {
  stroke: #5eead4;
  transition-delay: 0.5s;
}
.d2 {
  stroke: #7dd3fc;
  transition-delay: 1.3s;
}
.d3 {
  stroke: #bbf7d0;
  transition-delay: 2.2s;
}
.au.ready .viz-dot {
  opacity: 1;
}
.au-viz-labels {
  display: flex;
  justify-content: space-between;
  padding: 0 6px;
  color: #7790aa;
  font-size: 11px;
  letter-spacing: 0.12em;
}
.au-side-note {
  display: none;
}

/* ---- 右侧表单面板 ---- */
.au-auth {
  display: flex;
  align-items: center;
  scroll-margin-top: 82px;
}
.au-auth-inner {
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
}
.au-mini-brand {
  display: none;
  align-items: center;
  gap: 9px;
  margin-bottom: 16px;
}
.au-mini-brand img {
  width: 26px;
  height: auto;
}
.au-mini-brand b {
  color: var(--ink);
  font-size: 15px;
  letter-spacing: 0.03em;
}
.au-auth-head h2 {
  font-size: clamp(24px, 2.4vw, 31px);
  font-weight: 700;
  letter-spacing: -0.01em;
}
.au-auth-head p {
  margin: 10px 0 0;
  color: var(--muted);
  font-size: 13.5px;
  line-height: 1.85;
}
.role-badge {
  display: inline-block;
  margin-bottom: 10px;
  padding: 4px 12px;
  border-radius: 999px;
  color: var(--brand);
  background: rgba(18, 134, 111, 0.1);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.au-box {
  margin-top: 22px;
  padding: 20px 24px 24px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 26px 60px -40px rgba(16, 32, 47, 0.42);
}

.citizen-method {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 12px;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: #f6f8fa;
}
.citizen-method button {
  height: 32px;
  border: 0;
  border-radius: 8px;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
}
.citizen-method button.on {
  color: var(--brand);
  background: #fff;
  box-shadow: 0 2px 8px rgba(16, 32, 47, .08);
  font-weight: 600;
}

/* 模式切换 */
.au-seg {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: 980px;
  background: #f1f4f7;
}
.au-seg button {
  padding: 9px 0;
  border: 0;
  border-radius: 980px;
  background: transparent;
  color: var(--muted);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.18s, color 0.18s, box-shadow 0.18s;
}
.au-seg button.on {
  background: #fff;
  color: var(--ink);
  box-shadow: 0 1px 4px rgba(9, 40, 60, 0.12);
}

/* 身份切换：横向三卡 */
.au-ids {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
}
.au-id {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px 12px 13px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s, background 0.18s;
}
.au-id:hover {
  transform: translateY(-1px);
  border-color: #cfe0dc;
}
.au-id.on {
  border-color: transparent;
  background: linear-gradient(140deg, rgba(18, 134, 111, 0.1), rgba(44, 159, 192, 0.09));
  box-shadow: 0 0 0 1.5px var(--brand);
}
.au-id-ic {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  color: #fff;
  font-size: 14px;
  font-style: normal;
  background: linear-gradient(135deg, var(--brand), var(--cyan));
}
.au-id-tx {
  display: block;
  min-width: 0;
}
.au-id-tx strong {
  display: block;
  color: var(--ink);
  font-size: 14px;
  font-weight: 600;
}
.au-id-tx em {
  display: block;
  margin-top: 3px;
  color: var(--dim);
  font-size: 10.5px;
  font-style: normal;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.au-id-en {
  position: absolute;
  right: 11px;
  top: 15px;
  color: #c3ccd6;
  font-family: Consolas, monospace;
  font-size: 8px;
  letter-spacing: 0.14em;
}

/* 表单 */
.au-form {
  margin-top: 18px;
}
.au-field {
  display: block;
  margin-top: 14px;
}
.au-field > span {
  display: block;
  margin-bottom: 7px;
  color: var(--ink);
  font-size: 12.5px;
  font-weight: 500;
}
.au-field input {
  width: 100%;
  height: 48px;
  padding: 0 15px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: #fbfcfd;
  color: var(--ink);
  font-size: 14.5px;
  outline: none;
  transition: border-color 0.18s, box-shadow 0.18s, background 0.18s;
}
.au-field input::placeholder {
  color: #b3bcc6;
}
.au-field input:focus {
  border-color: var(--brand);
  background: #fff;
  box-shadow: 0 0 0 3.5px rgba(18, 134, 111, 0.13);
}
.au-code {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
}
.au-code button {
  padding: 0 15px;
  border: 0;
  border-radius: 13px;
  background: #eef3f4;
  color: var(--brand);
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.16s;
}
.au-code button:hover {
  background: #e2ecec;
}

.au-check {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: 18px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
  cursor: pointer;
}
.au-check input {
  flex: none;
  width: 15px;
  height: 15px;
  margin-top: 2px;
  accent-color: var(--brand);
}

.au-error {
  margin-top: 13px;
  padding: 10px 13px;
  border-radius: 12px;
  background: #fef2f2;
  color: #b3261e;
  font-size: 12.5px;
  line-height: 1.6;
}

.au-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 50px;
  margin-top: 18px;
  border: 0;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(100deg, var(--brand), var(--cyan));
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: filter 0.18s, transform 0.16s;
}
.au-submit:hover {
  filter: brightness(1.06);
}
.au-submit:active {
  transform: translateY(1px);
}
.au-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.au-submit i {
  font-style: normal;
}

.au-tip {
  margin-top: 13px;
  color: var(--dim);
  font-size: 11.5px;
  text-align: center;
  line-height: 1.7;
}
.au-tip code {
  font-family: Consolas, monospace;
  color: var(--ink);
}

.au-switch {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line-soft);
  color: var(--muted);
  font-size: 13px;
  text-align: center;
}
.au-switch button {
  padding: 0;
  border: 0;
  background: none;
  color: var(--brand);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.au-switch button:hover {
  text-decoration: underline;
}

/* 免登录体验 */
.au-quick {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  color: var(--dim);
  font-size: 11.5px;
}
.au-quick a {
  padding: 5px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  text-decoration: none;
  transition: border-color 0.16s, color 0.16s;
}
.au-quick a:hover {
  border-color: var(--brand);
  color: var(--brand);
}

/* 分角色入口：隐藏跨端入口，表单更聚焦 */
.role-entry .au-quick {
  display: none;
}
.role-entry .au-side-copy h1 {
  font-size: clamp(44px, 5vw, 66px);
}

/* ============================================================
   页脚
   ============================================================ */
.au-foot {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 26px 20px 34px;
  border-top: 1px solid var(--line-soft);
  text-align: center;
}
.au-foot { display: none; }

@media (min-width: 1021px) and (max-height: 860px) {
  .au-main { min-height: calc(100vh - 62px); padding-top: 16px; padding-bottom: 16px; gap: clamp(32px, 4vw, 60px); }
  .au-side { height: 430px; min-height: 0; gap: 10px; padding: 0; }
  .au-side-copy h1 { margin-top: 8px; font-size: clamp(38px, 4vw, 53px); }
  .au-sub { margin-top: 8px; line-height: 1.65; }
  .au-viz { margin-top: 4px; padding: 7px 18px; }
  .au-viz svg { height: 68px; }
  .au-auth-head p { margin-top: 5px; line-height: 1.5; }
  .au-box { margin-top: 8px; padding: 12px 20px 14px; }
  .au-seg button { padding: 6px 0; }
  .au-ids { margin-top: 8px; }
  .au-id { gap: 3px; padding: 8px 10px 9px; }
  .au-form { margin-top: 6px; }
  .citizen-method { margin-top: 7px; }
  .au-field { margin-top: 7px; }
  .au-field > span { margin-bottom: 3px; }
  .au-field input { height: 38px; }
  .au-check { margin-top: 8px; }
  .au-submit { height: 40px; margin-top: 8px; }
  .au-tip { margin-top: 5px; }
  .au-switch { margin-top: 7px; padding-top: 7px; }
  .au-quick { margin-top: 6px; }
}
.au-foot img {
  height: 26px;
  width: auto;
  opacity: 0.8;
}
.au-foot p {
  margin: 0;
  color: var(--dim);
  font-size: 11.5px;
}

/* ============================================================
   响应式
   ============================================================ */
@media (max-width: 1020px) {
  .au-main {
    grid-template-columns: 1fr;
  }
  .au-side {
    gap: 20px;
    height: auto;
    min-height: 0;
  }
  .au-viz,
  .au-side-note {
    display: none;
  }
  .au-feats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .au-nav {
    display: none;
  }
  .au-feats {
    grid-template-columns: 1fr;
  }
  .au-mini-brand {
    display: flex;
  }
}

@media (max-width: 560px) {
  .au-bar {
    height: 56px;
    gap: 12px;
  }
  .au-brand img {
    height: 26px;
  }
  .au-main {
    padding: 16px 14px 28px;
    gap: 16px;
  }
  .au-side {
    padding: 22px 18px;
    border-radius: 22px;
  }
  .au-side-copy h1 {
    font-size: 26px;
  }
  .au-side-copy h1 br {
    display: none;
  }
  .au-box {
    padding: 16px 16px 20px;
    border-radius: 20px;
  }
  .au-ids {
    grid-template-columns: 1fr;
  }
  .au-id {
    flex-direction: row;
    align-items: center;
    gap: 11px;
  }
  .au-id-en {
    position: static;
    margin-left: auto;
  }
  .au-id-tx em {
    white-space: normal;
  }
  .au-auth {
    scroll-margin-top: 66px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .viz-path {
    stroke-dashoffset: 0;
    transition: none;
  }
  .viz-dot,
  .au-bloom i {
    opacity: 1;
    transition: none;
  }
}
</style>
