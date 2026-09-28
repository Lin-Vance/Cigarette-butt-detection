<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCitizenStore } from '@/stores/citizen'

const router = useRouter()
const route = useRoute()
const citizen = useCitizenStore()
const phone = ref('13800000000')
const code = ref('123456')
const agreed = ref(true)
const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  if (!agreed.value) {
    error.value = '请先阅读并同意隐私说明'
    return
  }
  if (submitting.value) return
  submitting.value = true
  try {
    const result = await citizen.login(phone.value, code.value)
    if (!result.ok) {
      error.value = result.message
      return
    }
    router.push(String(route.query.redirect || '/citizen'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="citizen-login">
    <router-link class="back-home" to="/">← 返回官网</router-link>
    <section class="login-story">
      <div class="story-brand"><i></i><span><b>烟踪智治</b><small>CIVIC FORENSICS</small></span></div>
      <p class="story-index">CITIZEN / 01</p>
      <h1>你的线索，<br />应该有回音。</h1>
      <p>登录后可以安全提交环境线索、查看本人记录和治理结果。平台不会向其他普通用户公开你的身份信息。</p>
      <div class="privacy-notes">
        <span>禁止追拍拦截</span><span>提交前检查隐私</span><span>仅授权角色可见</span>
      </div>
    </section>

    <section class="login-panel" aria-labelledby="citizen-login-title">
      <div class="panel-head">
        <img class="panel-logo" src="/logo-horizontal.png" alt="烟踪智治" />
        <span>市民用户端</span>
        <h2 id="citizen-login-title">手机号登录</h2>
        <p>首次验证后自动创建演示账户</p>
      </div>
      <form @submit.prevent="submit">
        <label for="citizen-phone">手机号</label>
        <input id="citizen-phone" v-model="phone" inputmode="tel" autocomplete="tel" maxlength="11" />
        <label for="citizen-code">短信验证码</label>
        <div class="code-row">
          <input id="citizen-code" v-model="code" inputmode="numeric" maxlength="6" />
          <button type="button">获取验证码</button>
        </div>
        <label class="agreement">
          <input v-model="agreed" type="checkbox" />
          <span>我已了解：不得跟拍、拦截或公开传播他人画面</span>
        </label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="submit-button" type="submit">进入市民端 <span>→</span></button>
        <p class="demo-tip">演示验证码：123456　·　当前未接入真实短信服务</p>
      </form>
      <router-link class="governance-entry" to="/login">治理人员与平台管理员入口 ↗</router-link>
    </section>
  </main>
</template>

<style scoped>
.citizen-login {
  --ink: #0b1320;
  --paper: #f4f1e8;
  --ember: #ff6847;
  --cyan: #38c8d4;
  position: relative;
  display: grid;
  grid-template-columns: 1.18fr .82fr;
  width: 100%;
  min-height: 100vh;
  overflow: auto;
  color: var(--ink);
  background: var(--paper);
}
.back-home { position: absolute; z-index: 3; top: 30px; left: 36px; color: rgba(255,255,255,.72); font-size: 13px; }
.login-story { display: flex; flex-direction: column; justify-content: center; min-height: 100vh; padding: 90px clamp(35px, 8vw, 140px); color: #fff; background: #0b1320 url('/media/street-hero-alt.jpg') center/cover; }
.login-story::before { content: ""; position: absolute; inset: 0 41% 0 0; background: rgba(6,11,18,.74); pointer-events: none; }
.login-story > * { position: relative; z-index: 1; }
.story-brand { display: flex; gap: 13px; align-items: center; margin-bottom: 90px; }
.story-brand > i { width: 31px; height: 31px; border: 2px solid var(--ember); border-top-color: var(--cyan); }
.story-brand b,.story-brand small { display: block; }
.story-brand small { margin-top: 3px; opacity: .55; font: 9px Consolas,monospace; letter-spacing: .16em; }
.story-index { color: var(--ember); font: 11px Consolas,monospace; letter-spacing: .16em; }
.login-story h1 { margin: 22px 0 28px; font-size: clamp(48px,6vw,88px); line-height: 1.02; letter-spacing: -.055em; }
.login-story > p:not(.story-index) { max-width: 570px; color: rgba(255,255,255,.68); font-size: 17px; line-height: 1.8; }
.privacy-notes { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 38px; }
.privacy-notes span { padding: 8px 10px; border: 1px solid rgba(255,255,255,.25); font-size: 12px; }
.login-panel { align-self: center; padding: clamp(36px,7vw,110px); }
.panel-head > span { color: #d94a2c; font: 11px Consolas,monospace; letter-spacing: .14em; }
.panel-head h2 { margin: 15px 0 9px; font-size: 38px; }
.panel-head p { color: #75808b; }
form { margin-top: 50px; }
form > label:not(.agreement) { display: block; margin: 22px 0 9px; font-size: 14px; font-weight: 700; }
input:not([type='checkbox']) { width: 100%; height: 52px; padding: 0 15px; border: 1px solid rgba(11,19,32,.25); background: #fbfaf6; outline: none; }
input:focus { border-color: var(--ink); box-shadow: 0 0 0 3px rgba(56,200,212,.22); }
.code-row { display: grid; grid-template-columns: 1fr auto; }
.code-row input { border-right: 0; }
.code-row button { padding: 0 18px; border: 1px solid var(--ink); color: #fff; background: var(--ink); }
.agreement { display: flex; gap: 10px; align-items: flex-start; margin: 24px 0; color: #65707c; font-size: 13px; line-height: 1.55; }
.agreement input { margin-top: 3px; accent-color: var(--ember); }
.form-error { margin-bottom: 14px; color: #b52d25; font-size: 13px; }
.submit-button { display: flex; align-items: center; justify-content: space-between; width: 100%; height: 56px; padding: 0 22px; border: 0; color: var(--ink); background: var(--ember); font-weight: 700; }
.submit-button span { font-size: 22px; }
.demo-tip { margin-top: 14px; color: #7b8490; font-size: 12px; }
.governance-entry { display: inline-block; margin-top: 42px; color: var(--ink); border-bottom: 1px solid rgba(11,19,32,.35); font-size: 13px; }
@media (max-width: 900px) {
  .citizen-login { grid-template-columns: 1fr; }
  .back-home { top: 20px; left: 20px; }
  .login-story { min-height: 560px; padding: 100px 22px 60px; }
  .login-story::before { inset: 0; }
  .story-brand { margin-bottom: 55px; }
  .login-panel { padding: 60px 22px 80px; }
}
</style>

<style scoped>
/* 与用户提供的白底蓝色市民端保持同一视觉体系。 */
.citizen-login {
  --blue: #1677e8;
  --blue-deep: #075fca;
  --orange: #ff7a32;
  --text: #15243a;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 38px 20px;
  color: var(--text);
  background: #104651;
}
.back-home {
  top: 24px;
  left: 28px;
  color: rgba(255,255,255,.82);
}
.login-story { display: none; }
.login-panel {
  width: min(100%, 460px);
  padding: 42px 34px 34px;
  border-radius: 26px;
  background: #fff;
  box-shadow: 0 24px 80px rgba(0,0,0,.24);
}
/* 品牌标识：全站统一，用真 logo 图而不是 CSS 拼的假方块 */
.panel-logo {
  display: block;
  width: 168px;
  height: auto;
  margin-bottom: 30px;
}
.panel-head > span { color: var(--blue); }
.panel-head h2 { margin-top: 12px; font-size: 32px; }
.panel-head p { color: #7d8999; }
form { margin-top: 36px; }
input:not([type='checkbox']) {
  height: 50px;
  border-color: #dce2ea;
  border-radius: 11px;
  background: #f7f9fc;
}
input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(22,119,232,.15); }
.code-row { gap: 8px; }
.code-row input { border-right: 1px solid #dce2ea; }
.code-row button {
  border: 0;
  border-radius: 11px;
  color: var(--blue);
  background: #e9f3ff;
}
.agreement input { accent-color: var(--blue); }
.submit-button {
  border-radius: 12px;
  color: #fff;
  background: var(--blue);
  box-shadow: 0 9px 20px rgba(22,119,232,.2);
}
.submit-button span { color: #fff; }
.governance-entry { color: #637188; }
@media (max-width: 540px) {
  .citizen-login { align-items: stretch; padding: 0; background: #fff; }
  .back-home { top: 20px; left: 18px; color: #66748a; }
  .login-panel { width: 100%; min-height: 100vh; padding: 82px 22px 35px; border-radius: 0; box-shadow: none; }
}
</style>
