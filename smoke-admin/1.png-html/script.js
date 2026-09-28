(() => {
  const DESIGN_W = 1672; // 设计稿宽度
  const DESIGN_H = 941;  // 设计稿高度

  const screen = document.querySelector(".screen");

  // cover 缩放：等比放大铺满整个视口，多余部分裁剪到背景天空
  const fit = () => {
    if (!screen) return;
    const vw = document.documentElement.clientWidth;
    const vh = document.documentElement.clientHeight;
    const scale = Math.max(vw / DESIGN_W, vh / DESIGN_H);
    screen.style.transform = "translate(-50%, -50%) scale(" + scale + ")";
  };

  window.addEventListener("resize", fit);
  fit();

  // 密码显示 / 隐藏
  const pwd = document.getElementById("password");
  const eye = document.querySelector(".password-eye");
  if (pwd && eye) {
    eye.addEventListener("click", () => {
      const hidden = pwd.type === "password";
      pwd.type = hidden ? "text" : "password";
      eye.classList.toggle("revealed", hidden);
    });
  }

  // 登录提交：真实表单校验（后端接口待接入）
  const form = document.querySelector(".login-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const account = document.getElementById("account").value.trim();
      const password = document.getElementById("password").value;
      const captcha = document.getElementById("captcha").value.trim();
      if (!account) {
        alert("请输入管理员账号");
        return;
      }
      if (!password) {
        alert("请输入登录密码");
        return;
      }
      if (!captcha) {
        alert("请输入验证码");
        return;
      }
      alert("登录信息已填写，等待接入后端接口");
    });
  }

  // 忘记密码（占位，后端接口待接入）
  const forgot = document.querySelector(".forgot-password");
  if (forgot) {
    forgot.addEventListener("click", () => {
      alert("忘记密码流程待接入");
    });
  }
})();
