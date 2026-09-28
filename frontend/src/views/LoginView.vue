<script setup lang="ts">
/**
 * 页面 1 · 管理员登录
 *
 * 逐值移植 smoke-admin/1.png-html/{index.html,styles.css}：
 * 背景为双层 artwork（AI 原图 + 本地合成图），左侧品牌区 + 三张功能卡片，
 * 右侧玻璃拟态登录面板。所有坐标、字号、圆角、渐变均取自设计稿，未做改动。
 *
 * 登录校验当前走本地模拟（后端未实现），接入后端后替换为
 * POST /api/v1/auth/login（见 docs/烟踪智治-文档缺陷与修订说明.md）。
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FitShell from '@/layouts/FitShell.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const account = ref('admin')
const password = ref('123456')
const captcha = ref('')
const remember = ref(true)
const revealed = ref(false)
const submitting = ref(false)

const FEATURES = [
  {
    key: 'ai',
    title: 'AI智能识别',
    art: '/design-assets/1/ai_recognition_icon.png',
    cls: 'ai'
  },
  {
    key: 'evidence',
    title: '行为证据链',
    art: '/design-assets/1/evidence_chain_icon.png',
    cls: 'evidence'
  },
  {
    key: 'sanitation',
    title: '环卫协同调度',
    art: '/design-assets/1/sanitation_dispatch_icon.png',
    cls: 'sanitation'
  }
]

async function onSubmit() {
  if (!account.value.trim()) {
    ElMessage.warning('请输入管理员账号')
    return
  }
  if (!password.value) {
    ElMessage.warning('请输入登录密码')
    return
  }
  submitting.value = true
  const res = await auth.login(account.value, password.value)
  submitting.value = false
  if (!res.ok) {
    ElMessage.error(res.message)
    return
  }
  ElMessage.success('登录成功')
  const redirect = (route.query.redirect as string) || '/platform/overview'
  router.push(redirect)
}
</script>

<template>
  <FitShell>
    <section class="screen" aria-label="烟踪智治管理员登录页面">
      <img
        class="page-artwork composite"
        src="/design-assets/1/blue_city_skyline_login_background_local_composite.png"
        alt=""
      />

      <section class="brand-area" aria-label="品牌标识">
        <!-- 全站唯一品牌标识：与后台顶栏、入口页、各端共用同一张 logo -->
        <img class="brand-logo" src="/logo-horizontal.png" alt="烟踪智治" />
        <p class="brand-tagline">城市公共空间 · 扔烟头行为证据复核与治理闭环</p>
      </section>

      <section class="feature-grid" aria-label="平台功能">
        <article
          v-for="f in FEATURES"
          :key="f.key"
          class="feature-card"
          :class="f.cls"
        >
          <img class="feature-art" :class="`${f.cls}-art`" :src="f.art" alt="" />
          <h2 class="feature-title">{{ f.title }}</h2>
        </article>
      </section>

      <section class="login-panel" aria-label="管理员登录">
        <header class="login-heading">
          <h1 class="login-title">管理员登录</h1>
          <p class="login-subtitle">欢迎登录烟踪智治超级管理员端</p>
        </header>

        <form class="login-form" novalidate @submit.prevent="onSubmit">
          <div class="field-group account">
            <label class="field-label" for="account">管理员账号</label>
            <div class="input-shell">
              <span class="field-icon" aria-hidden="true">
                <svg viewBox="0 0 32 32" fill="none">
                  <circle cx="16" cy="10" r="6.2" stroke="currentColor" stroke-width="2.2" />
                  <path
                    d="M5.8 27.2c.8-5.1 4.3-7.4 10.2-7.4s9.4 2.3 10.2 7.4"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                  />
                  <path d="M5.8 27.2h20.4" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
                </svg>
              </span>
              <input
                id="account"
                v-model="account"
                class="field-input"
                type="text"
                placeholder="请输入管理员账号"
                autocomplete="username"
              />
            </div>
          </div>

          <div class="field-group password">
            <label class="field-label" for="password">登录密码</label>
            <div class="input-shell">
              <span class="field-icon" aria-hidden="true">
                <svg viewBox="0 0 32 32" fill="none">
                  <rect
                    x="5.3"
                    y="13.1"
                    width="21.4"
                    height="15.1"
                    rx="1.8"
                    stroke="currentColor"
                    stroke-width="2.2"
                  />
                  <path
                    d="M9.8 13.1V9.7a6.2 6.2 0 0 1 12.4 0v3.4"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                  />
                  <circle cx="16" cy="20" r="1.5" fill="currentColor" />
                  <path d="M16 21.5v3.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
                </svg>
              </span>
              <input
                id="password"
                v-model="password"
                class="field-input"
                :type="revealed ? 'text' : 'password'"
                placeholder="请输入登录密码"
                autocomplete="current-password"
              />
              <button
                class="password-eye"
                :class="{ revealed }"
                type="button"
                title="显示/隐藏密码"
                @click="revealed = !revealed"
              >
                <svg viewBox="0 0 34 30" fill="none">
                  <path
                    d="M2.4 15s5.1-8.2 14.6-8.2S31.6 15 31.6 15 26.5 23.2 17 23.2 2.4 15 2.4 15Z"
                    stroke="currentColor"
                    stroke-width="2.3"
                    stroke-linejoin="round"
                  />
                  <circle cx="17" cy="15" r="4" stroke="currentColor" stroke-width="2.3" />
                </svg>
              </button>
            </div>
          </div>

          <div class="field-group captcha">
            <label class="field-label" for="captcha">验证码</label>
            <div class="input-shell captcha-input">
              <span class="field-icon" aria-hidden="true">
                <svg viewBox="0 0 32 32" fill="none">
                  <path
                    d="M16 3.8 26.7 8v7.8c0 6.1-4 10.6-10.7 13.2C11.3 26.4 5.3 21.9 5.3 15.8V8L16 3.8Z"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linejoin="round"
                  />
                  <path
                    d="m11.3 15.8 3.1 3.2 6.5-6.7"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </span>
              <input
                id="captcha"
                v-model="captcha"
                class="field-input"
                type="text"
                placeholder="请输入验证码"
                autocomplete="off"
              />
            </div>
            <img
              class="captcha-image"
              src="/design-assets/1/captcha_verification_image.png"
              alt="验证码"
              title="验证码校验待后端接口提供后启用"
            />
          </div>

          <div class="login-options">
            <label class="remember">
              <input v-model="remember" class="remember-check" type="checkbox" />
              <span>记住账号</span>
            </label>
            <button class="forgot-password" type="button" @click="ElMessage.info('请联系系统管理员重置密码')">
              忘记密码
            </button>
          </div>

          <button class="secure-login" type="submit" :disabled="submitting">安全登录</button>

          <p class="demo-hint">演示账号：admin / 123456　（后端未接入，登录走本地模拟校验）</p>
        </form>
      </section>

      <footer class="copyright">烟踪智治公共场所无烟治理平台 · © 2026</footer>
    </section>
  </FitShell>
</template>

<style scoped>
.screen {
  position: relative;
  width: 1672px;
  height: 941px;
  overflow: hidden;
  background: var(--yz-login-bg);
}

.page-artwork {
  position: absolute;
  left: 0;
  top: 0;
  width: 1672px;
  height: 941px;
  object-fit: fill;
  pointer-events: none;
}
.page-artwork.composite {
  z-index: 0;
}

/* ---- 左侧品牌区 ---- */
.brand-area {
  position: absolute;
  left: 0;
  top: 0;
  width: 850px;
  height: 520px;
  z-index: 5;
  pointer-events: none;
}
/* 横版品牌 logo：比例固定 160:47，全站统一尺寸口径。
   位置对准背景图里被抹掉的那组旧标识（中心 x≈447 / y≈268）。 */
.brand-logo {
  position: absolute;
  left: 212px;
  top: 199px;
  width: 470px;
  height: 138px;
  object-fit: contain;
}
.brand-tagline {
  position: absolute;
  left: 212px;
  top: 351px;
  width: 470px;
  text-align: center;
  color: #46597a;
  font-size: 19px;
  line-height: 28px;
  letter-spacing: 0.4px;
}

/* ---- 功能卡片 ---- */
.feature-grid {
  position: absolute;
  left: 0;
  top: 0;
  width: 850px;
  height: 760px;
  z-index: 6;
}
.feature-card {
  position: absolute;
  top: 523px;
  height: 204px;
  border: 2px solid var(--yz-glass-border);
  border-radius: var(--yz-radius-art);
  background: var(--yz-glass-card);
  box-shadow: var(--yz-shadow-card), inset 0 1px 0 rgba(255, 255, 255, 0.64);
}
.feature-card.ai {
  left: 88px;
  width: 230px;
}
.feature-card.evidence {
  left: 335px;
  width: 226px;
}
.feature-card.sanitation {
  left: 579px;
  width: 218px;
}
.feature-art {
  position: absolute;
  object-fit: fill;
  z-index: 1;
  pointer-events: none;
}
.feature-art.ai-art {
  left: -8px;
  top: -9px;
  width: 241px;
  height: 217px;
}
.feature-art.evidence-art {
  left: -9px;
  top: -7px;
  width: 240px;
  height: 215px;
}
.feature-art.sanitation-art {
  left: -12px;
  top: -7px;
  width: 234px;
  height: 215px;
}
.feature-title {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 25px;
  z-index: 3;
  color: #102c67;
  text-align: center;
  font-size: 28px;
  line-height: 34px;
  font-weight: 700;
  white-space: nowrap;
}

/* ---- 登录面板 ---- */
.login-panel {
  position: absolute;
  left: 883px;
  top: 52px;
  width: 718px;
  height: 823px;
  z-index: 10;
  padding: 76px 54px 0 54px;
  border: 3px solid var(--yz-glass-border);
  border-radius: var(--yz-radius-panel);
  background: var(--yz-glass-panel);
  box-shadow: var(--yz-shadow-panel), var(--yz-shadow-inset);
}
.login-heading {
  width: 100%;
  text-align: center;
}
.login-title {
  color: var(--yz-text-title);
  font-size: 53px;
  line-height: 64px;
  font-weight: 800;
  letter-spacing: 3px;
  white-space: nowrap;
}
.login-subtitle {
  margin-top: 10px;
  color: var(--yz-text-2);
  font-size: 23px;
  line-height: 32px;
  white-space: nowrap;
}

.login-form {
  position: absolute;
  left: 54px;
  top: 218px;
  width: 610px;
  height: 526px;
}
.field-group {
  position: absolute;
  left: 0;
  width: 610px;
}
.field-group.account {
  top: 0;
}
.field-group.password {
  top: 130px;
}
.field-group.captcha {
  top: 260px;
}
.field-label {
  display: block;
  height: 31px;
  color: #111d3e;
  font-size: 21px;
  line-height: 31px;
  font-weight: 700;
  white-space: nowrap;
}
.input-shell {
  position: absolute;
  left: 0;
  top: 42px;
  width: 610px;
  height: 64px;
  border: 1.5px solid var(--yz-border);
  border-radius: var(--yz-radius-input);
  background: rgba(255, 255, 255, 0.28);
  transition: border-color 0.18s, box-shadow 0.18s;
}
.input-shell:focus-within {
  border-color: var(--yz-primary-deep);
  box-shadow: 0 0 0 3px rgba(18, 98, 232, 0.1);
}
.input-shell.captcha-input {
  width: 357px;
}
.field-icon {
  position: absolute;
  left: 21px;
  top: 17px;
  width: 28px;
  height: 28px;
  color: var(--yz-text-muted);
  pointer-events: none;
}
.field-icon svg,
.password-eye svg {
  width: 100%;
  height: 100%;
}
.field-input {
  position: absolute;
  left: 72px;
  right: 20px;
  top: 0;
  height: 62px;
  padding: 0;
  background: transparent;
  border: 0;
  outline: none;
  color: var(--yz-text-1);
  font-size: 20px;
  line-height: 62px;
}
.field-input::placeholder {
  color: var(--yz-text-placeholder);
}
.field-group.password .field-input {
  right: 66px;
}
.password-eye {
  position: absolute;
  right: 18px;
  top: 18px;
  width: 31px;
  height: 27px;
  padding: 0;
  background: none;
  border: 0;
  color: var(--yz-text-muted);
}
.password-eye.revealed {
  color: var(--yz-primary-deep);
}
.captcha-image {
  position: absolute;
  left: 373px;
  top: 38px;
  width: 233px;
  height: 65px;
  object-fit: fill;
  border-radius: var(--yz-radius-input);
  z-index: 2;
}

.login-options {
  position: absolute;
  left: 0;
  top: 394px;
  width: 610px;
  height: 33px;
}
.remember {
  position: absolute;
  left: 0;
  top: 0;
  height: 31px;
  display: flex;
  align-items: center;
  color: var(--yz-text-3);
  font-size: 20px;
  line-height: 31px;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
}
.remember-check {
  appearance: none;
  -webkit-appearance: none;
  width: 25px;
  height: 25px;
  margin: 0 14px 0 0;
  flex: none;
  position: relative;
  border: 0;
  border-radius: 5px;
  background: #2878ef;
  box-shadow: 0 1px 2px rgba(35, 104, 218, 0.22);
  cursor: pointer;
}
.remember-check::after {
  content: "";
  position: absolute;
  left: 6px;
  top: 4px;
  width: 11px;
  height: 6px;
  border-left: 3px solid #fff;
  border-bottom: 3px solid #fff;
  transform: rotate(-45deg);
  opacity: 0;
  transition: opacity 0.12s ease;
}
.remember-check:checked::after {
  opacity: 1;
}
.forgot-password {
  position: absolute;
  right: 0;
  top: 0;
  padding: 0;
  background: none;
  border: 0;
  color: var(--yz-primary-deep);
  font-size: 20px;
  line-height: 31px;
  white-space: nowrap;
}

.secure-login {
  position: absolute;
  left: 0;
  top: 461px;
  width: 610px;
  height: 70px;
  border: 0;
  border-radius: var(--yz-radius-input);
  color: #fff;
  background: var(--yz-primary-grad);
  box-shadow: 0 3px 5px rgba(55, 151, 224, 0.12);
  font-size: 28px;
  line-height: 70px;
  font-weight: 700;
  text-align: center;
  white-space: nowrap;
}
.secure-login:active {
  filter: brightness(0.96);
}
.secure-login:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.demo-hint {
  position: absolute;
  left: 0;
  top: 545px;
  width: 610px;
  text-align: center;
  font-size: 13px;
  line-height: 20px;
  color: #5c6f8c;
}

.copyright {
  position: absolute;
  left: 1043px;
  top: 895px;
  width: 385px;
  height: 30px;
  z-index: 8;
  color: #314563;
  font-size: 19px;
  line-height: 30px;
  white-space: nowrap;
  text-align: center;
}
</style>
