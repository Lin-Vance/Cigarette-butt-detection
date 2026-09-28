/**
 * 设计画布常量
 * 与 smoke-admin/ 设计稿一致：1672 × 941（16:9）。
 * 所有页面的绝对定位坐标都基于该画布，不得在组件内另写数字。
 */
export const DESIGN_W = 1672
export const DESIGN_H = 941

/** 顶栏高度（设计稿 .topbar） */
export const TOPBAR_H = 60

/** 页面内容安全区（顶栏之下） */
export const CONTENT_TOP = TOPBAR_H
export const CONTENT_H = DESIGN_H - TOPBAR_H
