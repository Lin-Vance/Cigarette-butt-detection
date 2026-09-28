(() => {
  'use strict';

  /* ===== 顶部日期时间实时刷新 ===== */
  var clock = document.getElementById('clock');
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function tick() {
    var d = new Date();
    clock.textContent = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) +
      ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }
  tick();
  setInterval(tick, 1000);

  /* ===== 轻提示 ===== */
  var toastEl = document.createElement('div');
  toastEl.className = 'toast';
  document.body.appendChild(toastEl);
  var toastTimer = null;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 2200);
  }

  /* ===== 二级下拉：悬停展开（CSS），点击再叠加开关（触屏可用） ===== */
  var navGroup = document.getElementById('navGroupOverview');
  var navBtn = navGroup.querySelector('.nav-item');
  navBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    navGroup.classList.toggle('open');
  });
  document.addEventListener('click', function (e) {
    if (!navGroup.contains(e.target)) navGroup.classList.remove('open');
  });

  /* ===== 菜单 / 导航跳转（平滑滚动到画布内对应区域） ===== */
  function smoothTo(el) {
    if (!el) return;
    var scale = screen.scale || 1;
    var box = document.querySelector('.fit-box');
    var screenEl = document.querySelector('.screen');
    // 计算元素在画布中的绝对纵坐标，再换算到页面坐标
    var topInScreen = el.offsetTop;
    var screenRect = screenEl.getBoundingClientRect();
    var baseY = window.scrollY + screenRect.top;
    var targetY = baseY + topInScreen * scale - 76; // 顶部导航高度 + 间隙
    window.scrollTo({ top: targetY, behavior: 'smooth' });
  }

  var menuItems = document.querySelectorAll('.dropdown .menu-item');
  menuItems.forEach(function (item) {
    item.addEventListener('click', function (e) {
      e.preventDefault();
      menuItems.forEach(function (i) { i.classList.remove('selected'); });
      item.classList.add('selected');
      navGroup.classList.remove('open');
      var target = document.querySelector(item.getAttribute('data-target'));
      smoothTo(target);
    });
  });

  var navItems = document.querySelectorAll('.main-nav > .nav-group:not(#navGroupOverview) .nav-item');
  function clearActive() {
    document.querySelectorAll('.main-nav .nav-item').forEach(function (i) { i.classList.remove('active'); });
  }
  navItems.forEach(function (item) {
    item.addEventListener('click', function () {
      clearActive();
      item.classList.add('active');
      var target = document.querySelector(item.getAttribute('data-target'));
      smoothTo(target);
    });
  });

  /* ===== 地图缩放 / 定位 ===== */
  var mapCanvas = document.querySelector('.map-canvas');
  var zoom = 1;
  function applyZoom() { mapCanvas.style.setProperty('--zoom', zoom); }
  document.querySelector('.zoom-button.plus').addEventListener('click', function () {
    zoom = Math.min(2, +(zoom + 0.2).toFixed(2));
    applyZoom();
    toast('地图已放大 · ' + Math.round(zoom * 100) + '%');
  });
  document.querySelector('.zoom-button.minus').addEventListener('click', function () {
    zoom = Math.max(0.8, +(zoom - 0.2).toFixed(2));
    applyZoom();
    toast('地图已缩小 · ' + Math.round(zoom * 100) + '%');
  });
  document.querySelector('.map-locate').addEventListener('click', function () {
    zoom = 1;
    applyZoom();
    toast('已定位到默认视野');
  });

  /* ===== 通知 / 退出 ===== */
  document.getElementById('bell').addEventListener('click', function () {
    toast('暂无新的告警通知');
  });
  document.querySelector('.logout').addEventListener('click', function () {
    toast('已安全退出系统（演示）');
  });

  /* ===== 排行榜分页 ===== */
  var rankRows = document.querySelectorAll('.ranking-table tbody tr');
  var pageBtns = document.querySelectorAll('.page-btn.num');
  var pagePrev = document.getElementById('pagePrev');
  var pageNext = document.getElementById('pageNext');
  var pageCur = document.getElementById('pageCur');
  var totalPages = pageBtns.length || 1;
  var currentPage = 1;

  function renderPage(p) {
    currentPage = p;
    rankRows.forEach(function (row) {
      row.style.display = (row.getAttribute('data-page') === String(p)) ? '' : 'none';
    });
    pageBtns.forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-page') === String(p));
    });
    pageCur.textContent = p;
    pagePrev.disabled = (p <= 1);
    pageNext.disabled = (p >= totalPages);
  }
  pageBtns.forEach(function (b) {
    b.addEventListener('click', function () { renderPage(parseInt(b.getAttribute('data-page'), 10)); });
  });
  pagePrev.addEventListener('click', function () { if (currentPage > 1) renderPage(currentPage - 1); });
  pageNext.addEventListener('click', function () { if (currentPage < totalPages) renderPage(currentPage + 1); });
  renderPage(1);

  /* ===== 画布自适应缩放（保留原始排版，随窗口等比缩放） ===== */
  var stage = document.querySelector('.stage');
  var box = document.querySelector('.fit-box');
  var screen = document.querySelector('.screen');
  var BOARD_W = 1660, BOARD_H = 875;
  // 嵌入模式（被态势总览壳加载时）：顶栏已隐藏，画布按内容区等比缩放
  var EMBED = /embed/.test(location.hash);

  function fit() {
    var vw = document.documentElement.clientWidth;
    if (EMBED) {
      var vhE = document.documentElement.clientHeight;
      var scaleE = Math.min(vw / BOARD_W, vhE / BOARD_H);
      box.style.width = (BOARD_W * scaleE) + 'px';
      box.style.height = (BOARD_H * scaleE) + 'px';
      screen.style.transform = 'scale(' + scaleE + ')';
      return;
    }
    var scaleW = (vw - 24) / BOARD_W;
    // 铺满宽度：随窗口等比放大，消除左右两侧空白；允许超过 1:1，最大 2 倍
    var scale = Math.max(0.22, Math.min(2, scaleW));
    screen.scale = scale;
    box.style.width = (BOARD_W * scale) + 'px';
    box.style.height = (BOARD_H * scale) + 'px';
    screen.style.transform = 'scale(' + scale + ')';
  }
  window.addEventListener('resize', fit);
  if (window.ResizeObserver) new ResizeObserver(fit).observe(stage);
  fit();
})();
