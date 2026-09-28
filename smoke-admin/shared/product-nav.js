/* ============================================================
   烟踪智治 · 产品级交互层 v4（注入到所有页面末尾，统一维护）
   当前阶段：纯前端 UI 交互（不接后端真实数据）

   v4（2026-09-16）下拉面板重设计 + 残留浮层清理：
   - yz-dd 重设计为「悬浮卡片菜单」（参照 Ant Design / Element）：
     圆角卡片 + 箭头锚点 + 模块名头部 + 每项图标 + 悬停滑入箭头 +
     当前页「当前」徽标 + 缩放淡入动画
   - 切换子页后下拉立即收起（不再钉住遮挡内容）
   - 清理设计稿遗留的常驻静态下拉：页面 2 overview-menu、
     页面 8 dispatch-dropdown、页面 11 resource-dropdown、
     页面 18 system-dropdown（统一改由 yz-dd 承担）
   - 页面 3 自带下拉换装为 v4 同款外观，隐藏导航项的 ﹀ 下拉箭头字样
   - 修复页面 5 地图切片图内烙印的下拉面板（图片已重绘，
     见 5.png-html/assets/slice_01.orig.png 备份）

   v3（2026-09-15）态势总览「单壳 + 内容区切换」：
   - 页面 2 = 模块壳：主标题栏固定不动
   - 治理态势/设备状态/工作看板 = iframe 嵌入页面 3/4/5 的
     「#embed 模式」（子页隐藏自带顶栏、按内容区重新缩放）
   - 事件总览 = 壳自身原生内容
   - 从其他页面进入态势总览 = 跳转壳页面并带 #sub=N 直达子视图
   ============================================================ */
(() => {
  'use strict';

  /* ================= 模块 → 子页面配置 ================= */
  var MODULES = {
    "态势总览": [
      { n: 2, label: "事件总览" },
      { n: 3, label: "治理态势" },
      { n: 4, label: "设备状态" },
      { n: 5, label: "工作看板" }
    ],
    "事件中心": [
      { n: 6, label: "告警中心" },
      { n: 7, label: "事件报表" }
    ],
    "调度中心": [
      { n: 8, label: "任务池" },
      { n: 9, label: "调度记录" }
    ],
    "全域地图": [
      { n: 10, label: "GIS 全屏地图" }
    ],
    "资源管理": [
      { n: 11, label: "设备资源" },
      { n: 12, label: "环卫资源" }
    ],
    "AI治理": [
      { n: 13, label: "模型与数据集" },
      { n: 14, label: "AI识别配置" },
      { n: 15, label: "数据分析" }
    ],
    "系统管理": [
      { n: 16, label: "权限与账号" },
      { n: 17, label: "系统配置" },
      { n: 18, label: "审计日志" }
    ]
  };

  var OVERVIEW_LABELS = { "事件总览": 2, "治理态势": 3, "设备状态": 4, "工作看板": 5 };

  /* ================= 下拉菜单图标（线性小图标，currentColor） ================= */
  function ico(paths) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + paths + '</svg>';
  }
  var CHEV = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>';
  var ICONS = {
    2: ico('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
    3: ico('<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z"/><path d="M9.5 11.5l2 2 3.5-3.5"/>'),
    4: ico('<path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/>'),
    5: ico('<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/>'),
    6: ico('<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>'),
    7: ico('<path d="M6 20v-5M12 20V8M18 20V4"/>'),
    8: ico('<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>'),
    9: ico('<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1H9V4z"/><path d="M9 11h6M9 15h4"/>'),
    10: ico('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z"/>'),
    11: ico('<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>'),
    12: ico('<path d="M1 5h13v11H1z"/><path d="M14 9h4.5L22 12.5V16h-8"/><circle cx="6.5" cy="18.5" r="2"/><circle cx="17.5" cy="18.5" r="2"/>'),
    13: ico('<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/>'),
    14: ico('<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/><path d="M1 14h6M9 8h6M17 16h6"/>'),
    15: ico('<path d="M23 6l-9.5 9.5-5-5L1 18"/><path d="M17 6h6v6"/>'),
    16: ico('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>'),
    17: ico('<circle cx="12" cy="12" r="3.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>'),
    18: ico('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8"/>')
  };
  var ICO_DEFAULT = ICONS[2];

  var match = /(\d+)\.png-html/.exec(decodeURIComponent(location.pathname));
  var SELF = match ? match[1] : null;
  var IS_LOGIN = SELF === "1";
  var IS_SHELL = SELF === "2";
  var IS_EMBED = /embed/.test(location.hash);

  function pageUrl(n) { return "../" + n + ".png-html/index.html"; }
  function shellUrl(n) { return "../2.png-html/index.html#sub=" + n; }

  function cleanText(el) {
    return (el.textContent || "")
      .replace(/[▾▴▼▲]/g, "")
      .replace(/\s+/g, "");
  }

  function markLink(el) {
    if (el.classList) el.classList.add("yz-link");
  }

  /* ================= 嵌入模式：尽早隐藏子页自带顶栏 ================= */
  if (IS_EMBED) {
    document.documentElement.classList.add("yz-embed");
  }

  /* ================= 全局样式 ================= */
  var styleEl = document.createElement("style");
  styleEl.textContent = [
    "/* 顶部导航可点击反馈 */",
    ".yz-link{cursor:pointer;}",
    ".yz-nav.yz-open{background:rgba(8,169,194,.10);border-radius:8px;color:#0798ad;}",
    "/* 隐藏设计稿中的常驻静态下拉（各页命名不一，全家族清单；统一由 yz-dd 承担） */",
    ".nav-dropdown,.nav-popover,.overview-menu,.dispatch-dropdown,.resource-dropdown,.system-dropdown,.event-menu,.dispatch-menu,.resource-menu,.ai-menu,.system-menu,.system-popup{display:none !important;}",
    "/* 嵌入模式：隐藏子页自带顶栏 / 残留下拉 / 页内菜单 */",
    ".yz-embed .topbar,.yz-embed .top-header{display:none !important;}",
    ".yz-embed .stage{padding-top:0 !important;}",
    ".yz-embed .nav-popover,.yz-embed .nav-dropdown,.yz-embed .overview-menu,.yz-embed .event-menu,.yz-embed .dispatch-menu,.yz-embed .dispatch-dropdown,.yz-embed .resource-dropdown,.yz-embed .system-dropdown,.yz-embed .yz-dd{display:none !important;}",
    "/* 壳模式：保留主标题栏、二级标签、内容 iframe */",
    ".yz-shelled > :not(header):not(.yz-module-frame):not(.yz-subnav):not(.yz-dd){display:none !important;}",
    ".yz-module-frame{position:absolute;left:0;width:100%;border:0;background:#fff;display:none;z-index:1;}",
    "/* 二级标签栏（固定在顶栏下方，不覆盖内容） */",
    ".yz-subnav{position:absolute;left:0;right:0;top:60px;height:44px;display:flex;align-items:stretch;gap:2px;padding:0 24px;background:#fff;border-bottom:1px solid #e4eef6;z-index:30;box-sizing:border-box;}",
    ".yz-subnav-item{height:44px;padding:0 20px;display:flex;align-items:center;font-size:14px;color:#3a4a6a;cursor:pointer;position:relative;user-select:none;white-space:nowrap;}",
    ".yz-subnav-item:hover{color:#0798ad;}",
    ".yz-subnav-item.active{color:#0798ad;font-weight:600;}",
    ".yz-subnav-item.active::after{content:'';position:absolute;left:16px;right:16px;bottom:0;height:2px;background:#08a9c2;border-radius:2px 2px 0 0;}",
    "/* 页面3：禁用自带下拉的 hover 展开，统一为点击开合 */",
    ".nav-group#navGroupOverview:hover .dropdown{opacity:0 !important;visibility:hidden !important;transform:translateY(-6px) !important;}",
    ".nav-group#navGroupOverview.open .dropdown{opacity:1 !important;visibility:visible !important;transform:translateY(0) !important;}",
    "/* 一级导航下拉 v4：悬浮卡片菜单（参照 Ant Design / Element 菜单形态） */",
    ".yz-dd{position:absolute;top:60px;min-width:244px;padding:8px;background:#fff;border:1px solid #e2ecf4;border-radius:14px;box-shadow:0 24px 48px -16px rgba(23,84,125,.28),0 6px 16px -8px rgba(23,84,125,.12);opacity:0;visibility:hidden;transform:translateY(-8px) scale(.97);transform-origin:26px top;transition:opacity .2s cubic-bezier(.3,1,.4,1),transform .2s cubic-bezier(.3,1,.4,1),visibility .2s;z-index:400;}",
    ".yz-dd.show{opacity:1;visibility:visible;transform:translateY(0) scale(1);}",
    ".yz-dd::before{content:'';position:absolute;top:-5px;left:var(--yz-cx,26px);width:11px;height:11px;background:#fff;border-left:1px solid #e2ecf4;border-top:1px solid #e2ecf4;transform:rotate(45deg);border-radius:2px 0 0 0;}",
    ".yz-dd-head{display:flex;align-items:center;gap:7px;margin:2px 4px 7px;padding:5px 8px 8px;border-bottom:1px solid #eef4f9;font-size:12px;font-weight:600;letter-spacing:2px;color:#8fa6bc;}",
    ".yz-dd-head i{width:6px;height:6px;border-radius:50%;background:#0aa5bd;box-shadow:0 0 0 3px rgba(10,165,189,.14);}",
    ".yz-dd-item{display:flex;align-items:center;gap:11px;width:100%;height:41px;padding:0 10px;font-size:14px;color:#23324d;border-radius:9px;white-space:nowrap;cursor:pointer;transition:background .16s ease,color .16s ease;}",
    ".yz-dd-item .yz-ico{width:27px;height:27px;border-radius:8px;flex:none;display:flex;align-items:center;justify-content:center;background:#edf6fb;color:#2e8db0;transition:background .16s ease,color .16s ease;}",
    ".yz-dd-item .yz-ico svg{width:15px;height:15px;display:block;}",
    ".yz-dd-item .yz-t{flex:none;}",
    ".yz-dd-item .yz-go{margin-left:auto;display:flex;color:#0aa5bd;opacity:0;transform:translateX(-5px);transition:opacity .16s ease,transform .16s ease;}",
    ".yz-dd-item .yz-go svg{width:14px;height:14px;}",
    ".yz-dd-item .yz-now{display:none;}",
    ".yz-dd-item.selected .yz-now::after{content:'当前';}",
    ".yz-dd-item:hover{background:#f2fafc;color:#0798ad;}",
    ".yz-dd-item:hover .yz-ico{background:#dcf1f7;color:#0798ad;}",
    ".yz-dd-item:hover .yz-go{opacity:1;transform:translateX(0);}",
    ".yz-dd-item.selected{background:linear-gradient(90deg,#e7f8fb,#f4fcfd);color:#0798ad;font-weight:600;}",
    ".yz-dd-item.selected .yz-ico{background:#c9ecf4;color:#0798ad;}",
    ".yz-dd-item.selected .yz-go{display:none;}",
    ".yz-dd-item.selected .yz-now{display:inline-block;margin-left:auto;font-size:11px;font-weight:600;color:#0a9cb4;background:rgba(10,165,189,.13);padding:2px 9px;border-radius:20px;}",
    ".yz-dd-item.selected:hover{background:linear-gradient(90deg,#ddf4f8,#ecfafc);}",
    "/* 页面3 自带下拉 → 换装 v4 同款外观 */",
    ".nav-group#navGroupOverview .nav-caret{display:none !important;}",
    "#navGroupOverview .dropdown{top:54px;min-width:244px;padding:8px;border:1px solid #e2ecf4;border-radius:14px;box-shadow:0 24px 48px -16px rgba(23,84,125,.28),0 6px 16px -8px rgba(23,84,125,.12);}",
    "#navGroupOverview .dropdown::before{content:'';position:absolute;top:-5px;left:26px;width:11px;height:11px;background:#fff;border-left:1px solid #e2ecf4;border-top:1px solid #e2ecf4;transform:rotate(45deg);border-radius:2px 0 0 0;}",
    "#navGroupOverview .menu-item{background:transparent;gap:11px;height:41px;padding:0 10px;font-size:14px;border-color:transparent;border-radius:9px;transition:background .16s ease,color .16s ease;}",
    "#navGroupOverview .menu-item .yz-ico{width:27px;height:27px;border-radius:8px;flex:none;display:flex;align-items:center;justify-content:center;background:#edf6fb;color:#2e8db0;transition:background .16s ease,color .16s ease;}",
    "#navGroupOverview .menu-item .yz-ico svg{width:15px;height:15px;display:block;}",
    "#navGroupOverview .menu-item .yz-go{margin-left:auto;display:flex;color:#0aa5bd;opacity:0;transform:translateX(-5px);transition:opacity .16s ease,transform .16s ease;}",
    "#navGroupOverview .menu-item .yz-go svg{width:14px;height:14px;}",
    "#navGroupOverview .menu-item .yz-now{display:none;}",
    "#navGroupOverview .menu-item:hover{background:#f2fafc;color:#0798ad;}",
    "#navGroupOverview .menu-item:hover .yz-ico{background:#dcf1f7;color:#0798ad;}",
    "#navGroupOverview .menu-item:hover .yz-go{opacity:1;transform:translateX(0);}",
    "#navGroupOverview .menu-item.selected{color:#0798ad;font-weight:600;border-color:transparent;}",
    "#navGroupOverview .menu-item.selected .yz-ico{background:#c9ecf4;color:#0798ad;}",
    "#navGroupOverview .menu-item.selected .yz-now{display:inline-block;margin-left:auto;font-size:11px;font-weight:600;color:#0a9cb4;background:rgba(10,165,189,.13);padding:2px 9px;border-radius:20px;}",
    "#navGroupOverview .menu-item.selected .yz-now::after{content:'当前';}",
    "#navGroupOverview .menu-item.selected:hover{background:linear-gradient(90deg,#ddf4f8,#ecfafc);}",
    "/* 图层开关关闭态（页面10） */",
    ".switch-group .toggle.off{background:#c4d0dd;}",
    ".switch-group .toggle.off::after{left:2px;right:auto;}",
    "/* 全局 toast */",
    ".yz-toast{position:fixed;left:50%;bottom:46px;transform:translateX(-50%) translateY(8px);background:rgba(13,27,62,.92);color:#fff;font-size:14px;padding:10px 24px;border-radius:22px;box-shadow:0 6px 20px rgba(0,0,0,.25);opacity:0;transition:opacity .22s,transform .22s;z-index:99999;pointer-events:none;white-space:nowrap;}",
    ".yz-toast.show{opacity:1;transform:translateX(-50%) translateY(0);}"
  ].join("\n");
  document.head.appendChild(styleEl);

  /* ================= Toast ================= */
  var toastEl = null, toastTimer = null;
  function toast(msg) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "yz-toast";
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 1800);
  }

  /* ================= 壳模式（页面2）：内容区切换 ================= */
  var shellFrame = null;
  var overviewRec = null;
  var subnavEl = null;
  var currentSub = 2;

  function syncOverviewSelected(n) {
    currentSub = Number(n) || 2;
    if (overviewRec) {
      overviewRec.items.forEach(function (it) {
        it.el.classList.toggle("selected", String(it.n) === String(n));
      });
    }
    if (subnavEl) {
      subnavEl.querySelectorAll(".yz-subnav-item").forEach(function (tab) {
        tab.classList.toggle("active", String(tab.getAttribute("data-n")) === String(n));
      });
    }
  }

  function yzSwap(n) {
    var screenEl = document.querySelector(".screen");
    if (!screenEl || !IS_SHELL) return;
    if (String(n) === "2") {
      screenEl.classList.remove("yz-shelled");
      if (shellFrame) shellFrame.style.display = "none";
    } else {
      screenEl.classList.add("yz-shelled");
      if (shellFrame) {
        shellFrame.src = pageUrl(n) + "#embed";
        shellFrame.style.display = "block";
      }
    }
    syncOverviewSelected(n);
    closeAllPanels();
  }

  /* ================= 顶部导航下拉菜单（点击钉住模型） ================= */
  var NAV_SELECTORS = [
    ".main-nav .nav-item",
    ".main-navigation .nav-item",
    ".primary-nav .nav-item",
    ".primary-nav-item",
    ".top-nav-item",
    ".top-menu-item",
    ".header-menu-item"
  ];
  var NAV_GROUP_SELECTORS = ".main-nav,.main-navigation,.primary-nav,.top-nav,.top-menu,.header-menu";
  var allPanels = [];
  var pinnedRec = null;
  var closeTimer = null;

  function screenScale(screenEl) {
    return screenEl.getBoundingClientRect().width / screenEl.offsetWidth;
  }

  function closeAllPanels() {
    allPanels.forEach(function (rec) {
      rec.panel.classList.remove("show");
      rec.btn.classList.remove("yz-open");
    });
    pinnedRec = null;
  }

  function positionPanel(rec) {
    var screenEl = document.querySelector(".screen") || document.body;
    var scale = screenScale(screenEl);
    var screenRect = screenEl.getBoundingClientRect();
    var btnRect = rec.btn.getBoundingClientRect();
    var centerX = (btnRect.left + btnRect.width / 2 - screenRect.left) / scale;
    var panel = rec.panel;
    var w = panel.offsetWidth || 180;
    var left = Math.max(12, Math.min(centerX - w / 2, screenEl.offsetWidth - w - 12));
    panel.style.left = left + "px";
    panel.style.top = rec.top || "60px";
    var cx = Math.max(22, Math.min(centerX - left, w - 22));
    panel.style.setProperty("--yz-cx", cx + "px");
    panel.style.transformOrigin = cx + "px top";
  }

  function openPanel(rec) {
    clearTimeout(closeTimer);
    allPanels.forEach(function (r) {
      if (r !== rec) { r.panel.classList.remove("show"); r.btn.classList.remove("yz-open"); }
    });
    positionPanel(rec);
    rec.panel.classList.add("show");
    rec.btn.classList.add("yz-open");
  }

  function scheduleClose() {
    if (pinnedRec) return;
    clearTimeout(closeTimer);
    closeTimer = setTimeout(closeAllPanels, 180);
  }

  function cancelClose() { clearTimeout(closeTimer); }

  if (!IS_LOGIN && !IS_EMBED) {
    var seen = [];
    NAV_SELECTORS.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        if (seen.indexOf(el) === -1) seen.push(el);
      });
    });

    seen.forEach(function (btn) {
      var text = cleanText(btn);
      var subs = MODULES[text];
      if (!subs) return;

      /* 页面3：自带下拉，与全站统一为「点击开合」+ v4 同款外观 */
      if (text === "态势总览" && btn.closest && btn.closest("#navGroupOverview")) {
        markLink(btn);
        btn.classList.add("yz-nav");
        var group3 = btn.closest("#navGroupOverview");
        btn.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopImmediatePropagation();
          if (group3) group3.classList.toggle("open");
        }, true);
        var dd3 = group3.querySelector(".dropdown");
        if (dd3 && !dd3.querySelector(".yz-dd-head")) {
          var head3 = document.createElement("div");
          head3.className = "yz-dd-head";
          head3.innerHTML = "<i></i>态势总览";
          dd3.insertBefore(head3, dd3.firstChild);
          var self3 = Number(SELF);
          dd3.querySelectorAll(".menu-item").forEach(function (mi) {
            var label3 = cleanText(mi);
            var n3 = OVERVIEW_LABELS[label3];
            mi.innerHTML =
              '<span class="yz-ico">' + (ICONS[n3] || ICO_DEFAULT) + '</span>' +
              '<span class="yz-t">' + label3 + '</span>' +
              '<span class="yz-go">' + CHEV + '</span><span class="yz-now"></span>';
            if (n3 === self3) mi.classList.add("selected");
          });
        }
        return;
      }

      markLink(btn);
      btn.classList.add("yz-nav");

      var panel = document.createElement("div");
      panel.className = "yz-dd";
      panel.innerHTML = '<div class="yz-dd-head"><i></i>' + text + '</div>';
      var screenEl = document.querySelector(".screen") || document.body;
      var topbar = btn.closest("header") || btn.closest(NAV_GROUP_SELECTORS);
      var recItems = [];

      subs.forEach(function (sub) {
        var item = document.createElement("div");
        item.className = "yz-dd-item";
        item.innerHTML =
          '<span class="yz-ico">' + (ICONS[sub.n] || ICO_DEFAULT) + '</span>' +
          '<span class="yz-t">' + sub.label + '</span>' +
          '<span class="yz-go">' + CHEV + '</span><span class="yz-now"></span>';
        if (String(sub.n) === SELF) item.classList.add("selected");
        markLink(item);
        item.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          if (text === "态势总览") {
            /* 态势总览 = 单壳模块：事件总览/治理态势/设备状态/工作看板 */
            if (IS_SHELL) {
              yzSwap(sub.n);            /* 不刷新；切换后下拉立即收起 */
            } else {
              location.href = shellUrl(sub.n);
            }
            return;
          }
          if (String(sub.n) === SELF) { closeAllPanels(); return; }
          location.href = pageUrl(sub.n);
        });
        panel.appendChild(item);
        recItems.push({ el: item, n: sub.n });
      });

      var topPx = "60";
      if (topbar) {
        var scale = screenScale(screenEl);
        var topbarRect = topbar.getBoundingClientRect();
        var screenRect = screenEl.getBoundingClientRect();
        topPx = String((topbarRect.bottom - screenRect.top) / scale + 8);
      }
      screenEl.appendChild(panel);
      var rec = { btn: btn, panel: panel, top: topPx + "px", module: text, items: recItems };
      allPanels.push(rec);
      if (text === "态势总览") overviewRec = rec;

      /* 悬停 = 临时预览；点击 = 钉住/取消钉住 */
      btn.addEventListener("mouseenter", function () { if (!pinnedRec) openPanel(rec); });
      btn.addEventListener("mouseleave", scheduleClose);
      panel.addEventListener("mouseenter", cancelClose);
      panel.addEventListener("mouseleave", scheduleClose);
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (pinnedRec === rec) {
          closeAllPanels();
        } else {
          pinnedRec = rec;
          openPanel(rec);
        }
      });
    });

    /* 点击空白处 / Esc / 点入内容区(iframe) 关闭（并解除钉住） */
    document.addEventListener("click", function (e) {
      var insidePanel = e.target.closest && e.target.closest(".yz-dd");
      var insideNav = e.target.closest && e.target.closest(NAV_GROUP_SELECTORS);
      if (!insidePanel && !insideNav) closeAllPanels();
    }, true);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeAllPanels();
    }, true);
    window.addEventListener("resize", closeAllPanels);
    /* 点击 iframe 内部时 click 不冒泡到父文档，借窗口失焦收起下拉 */
    window.addEventListener("blur", closeAllPanels);
  }

  /* ================= 壳页面初始化（页面2） ================= */
  if (IS_SHELL && !IS_EMBED) {
    var shellScreen = document.querySelector(".screen");
    if (shellScreen) {
      var shellTopbar = shellScreen.querySelector("header");
      var topOffset = shellTopbar ? shellTopbar.offsetHeight + 1 : 60;
      shellFrame = document.createElement("iframe");
      shellFrame.className = "yz-module-frame";
      shellFrame.style.top = topOffset + "px";
      shellFrame.style.height = (shellScreen.offsetHeight - topOffset) + "px";
      shellFrame.title = "模块内容区";
      shellScreen.appendChild(shellFrame);

      /* 页面底部横条菜单（事件总览/治理态势/设备状态/工作看板）原地切换 */
      document.querySelectorAll(".overview-menu .menu-item").forEach(function (el) {
        var target = OVERVIEW_LABELS[cleanText(el)];
        if (!target) return;
        markLink(el);
        el.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          yzSwap(target);
        });
      });

      /* 首页 CTA：查看项目态势 → 原地切到治理态势 */
      var heroBtn = document.querySelector(".hero-button");
      if (heroBtn) {
        markLink(heroBtn);
        heroBtn.addEventListener("click", function (e) {
          e.preventDefault();
          yzSwap(3);
        });
      }

      /* URL 带 #sub=N 时：直达子视图（保持界面干净，不自动展开下拉） */
      var subMatch = /sub=(\d+)/.exec(location.hash);
      if (subMatch) {
        yzSwap(subMatch[1]);
      }
    }
  }

  /* ================= 页面内二级菜单跨页跳转（非壳页） ================= */
  if (!IS_LOGIN && !IS_EMBED && !IS_SHELL) {
    var SUB_SELECTORS = [
      ".dropdown .menu-item",
      ".event-menu-item",
      ".dispatch-menu-item",
      ".resource-menu-item",
      ".ai-menu-item",
      ".system-menu-item"
    ];
    var SUBROUTES = {
      "告警中心": 6, "事件报表": 7,
      "任务池": 8, "调度记录": 9,
      "设备资源": 11, "环卫资源": 12,
      "模型与数据集": 13, "AI识别配置": 14, "数据分析": 15,
      "权限与账号": 16, "系统配置": 17, "审计日志": 18
    };
    SUB_SELECTORS.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        var label = cleanText(el);
        var target = SUBROUTES[label];
        if (OVERVIEW_LABELS[label]) {
          /* 态势总览子项 → 统一进入壳页面 */
          markLink(el);
          el.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            location.href = shellUrl(OVERVIEW_LABELS[label]);
          });
          return;
        }
        if (!target) return;
        markLink(el);
        el.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          if (String(target) !== SELF) location.href = pageUrl(target);
        });
      });
    });
  }

  /* ================= 图层开关（页面10，嵌入/独立均可用） ================= */
  document.querySelectorAll(".switch-group").forEach(function (sg) {
    markLink(sg);
    sg.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var t = sg.querySelector(".toggle");
      if (!t) return;
      var turningOn = t.classList.contains("off");
      t.classList.toggle("off", !turningOn);
      var label = sg.querySelector("span:not(.toggle)");
      toast((label ? label.textContent : "图层") + (turningOn ? "已开启" : "已关闭"));
    });
  });

  /* ================= 状态筛选标签（页面17等） ================= */
  document.querySelectorAll(".status-tab").forEach(function (tab) {
    markLink(tab);
    tab.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      tab.parentElement.querySelectorAll(".status-tab").forEach(function (t) {
        t.classList.remove("active");
      });
      tab.classList.add("active");
      toast("已按「" + cleanText(tab) + "」筛选（演示）");
    });
  });

  /* ================= 通用按钮交互反馈（嵌入/独立均可用） ================= */
  if (!IS_LOGIN) {
    function isSpecial(el) {
      if (!el.closest) return false;
      if (el.closest(NAV_GROUP_SELECTORS)) return true;
      if (el.closest(".dropdown,.nav-dropdown,.nav-popover,.overview-menu,.event-menu,.dispatch-menu,.resource-menu,.ai-menu,.system-menu,.status-tabs,.yz-dd")) return true;
      if (el.closest(".switch-group")) return true;
      if (/logout|hero-button|page-btn|zoom-button|map-locate/.test(el.className)) return true;
      return false;
    }

    function respond(el) {
      var t = cleanText(el);
      if (/查询|搜索/.test(t)) return toast("查询完成，结果已按条件刷新（演示）");
      if (/重置/.test(t)) {
        document.querySelectorAll("input[type=text],input[type=search],select").forEach(function (inp) {
          if (inp.tagName === "SELECT") inp.selectedIndex = 0; else inp.value = "";
        });
        return toast("筛选条件已重置");
      }
      if (/导出/.test(t)) return toast("已导出当前数据（演示）");
      if (/导入/.test(t)) return toast("导入成功，数据已更新（演示）");
      if (/保存/.test(t)) return toast("配置已保存（演示）");
      if (/删除/.test(t)) return toast("记录已删除（演示）");
      if (/派发/.test(t)) return toast("任务已派发至责任人（演示）");
      if (/改派/.test(t)) return toast("已发起改派（演示）");
      if (/标记/.test(t)) return toast("标记成功（演示）");
      if (/预览/.test(t)) return toast("预览已生成（演示）");
      if (/编辑/.test(t)) return toast("进入编辑状态（演示）");
      if (/启用|禁用/.test(t)) return toast("账号状态已更新（演示）");
      if (/恢复默认/.test(t)) return toast("已恢复默认设置（演示）");
      if (/关闭/.test(t)) return toast("已关闭（演示）");
      if (/取消/.test(t)) return toast("已取消操作（演示）");
      if (/确定/.test(t)) return toast("操作已确认（演示）");
      if (/新增|新建|添加/.test(t)) return toast("已新增一条记录（演示）");
      if (/切换|启用版本/.test(t)) return toast("版本已切换（演示）");
      return toast("「" + t + "」已触发（演示交互）");
    }

    document.querySelectorAll("button").forEach(function (btn) {
      var t = cleanText(btn);
      if (!t || t.length < 2) return;
      if (isSpecial(btn)) return;
      markLink(btn);
      btn.addEventListener("click", function () { respond(btn); });
    });
  }

  /* ================= 登录（页面1）：直接进入系统 ================= */
  if (IS_LOGIN) {
    var form = document.querySelector(".login-form");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        location.href = pageUrl(2);
      }, true);
    }
  }

  /* ================= 退出登录（非嵌入的系统页面） ================= */
  if (!IS_LOGIN && !IS_EMBED) {
    document.querySelectorAll('[class*="logout"]').forEach(function (el) {
      markLink(el);
      el.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        location.href = pageUrl(1);
      }, true);
    });
  }
})();
