(() => {
  const shell = document.querySelector(".fit-shell");
  const box = document.querySelector(".fit-box");
  const screen = document.querySelector(".screen");
  if (!shell || !box || !screen) return;
  // 嵌入模式（被态势总览壳加载时）：隐藏顶栏，仅按内容区等比缩放
  const EMBED = /embed/.test(location.hash);
  const HEADER_H = (document.querySelector(".top-header") || {}).offsetHeight || 54;
  const fit = () => {
    const shellW = shell.getBoundingClientRect().width;
    const shellH = shell.getBoundingClientRect().height;
    if (EMBED) {
      const availH = 941 - HEADER_H;
      const scale = Math.min(shellW / 1672, document.documentElement.clientHeight / availH);
      box.style.width = (1672 * scale) + "px";
      box.style.height = (availH * scale) + "px";
      screen.style.setProperty("transform", `scale(${scale}) translateY(-${HEADER_H}px)`, "important");
      screen.style.setProperty("transform-origin", "top left", "important");
      return;
    }
    const availableWidth = shell.getBoundingClientRect().width;
    const scale = Math.min(1, availableWidth / 1672);
    box.style.width = (1672 * scale) + "px";
    box.style.height = (941 * scale) + "px";
    screen.style.setProperty("transform", `scale(${scale})`, "important");
    screen.style.setProperty("transform-origin", "top left", "important");
  };
  new ResizeObserver(fit).observe(shell);
  window.addEventListener("resize", fit);
  fit();
})();