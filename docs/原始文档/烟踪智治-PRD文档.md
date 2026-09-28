# 产品需求文档（PRD）

## 烟踪智治：基于行为证据链的公共场所烟头乱扔智能识别与环卫调度决策系统

| 字段 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 编写日期 | 2026-08-07 |
| 项目名称 | 烟踪智治 |
| 申请人 | 黄忠楷 |
| 指导老师 | 李进 |
| 所属单位 | 信阳学院 计算机与人工智能学院 |
| 技术栈 | 后端 Python FastAPI / 前端 Vue3 |
| 部署级别 | 校园试点（2-4 路摄像头） |
| 项目周期 | 2026年5月 — 2027年4月 |

---

## 目录

- [1. 项目概述](#1-项目概述)
  - [1.1 项目背景](#11-项目背景)
  - [1.2 项目目标](#12-项目目标)
  - [1.3 核心创新点](#13-核心创新点)
- [2. 用户角色与使用场景](#2-用户角色与使用场景)
  - [2.1 角色定义](#21-角色定义)
  - [2.2 核心使用场景](#22-核心使用场景)
- [3. 系统总体架构](#3-系统总体架构)
  - [3.1 架构总览](#31-架构总览)
  - [3.2 技术栈选型](#32-技术栈选型)
  - [3.3 部署拓扑](#33-部署拓扑)
- [4. AI 算法管道](#4-ai-算法管道)
  - [4.1 视频流接入与预处理](#41-视频流接入与预处理)
  - [4.2 改进 YOLO 小目标烟头检测](#42-改进-yolo-小目标烟头检测)
  - [4.3 三段式行为证据链](#43-三段式行为证据链)
  - [4.4 ByteTrack 行人跟踪与事件关联](#44-bytetrack-行人跟踪与事件关联)
  - [4.5 证据采集与存储](#45-证据采集与存储)
- [5. 后端服务](#5-后端服务)
  - [5.1 视频流接入与预处理管道](#51-视频流接入与预处理管道)
  - [5.2 业务逻辑引擎](#52-业务逻辑引擎)
  - [5.3 数据统计与决策引擎](#53-数据统计与决策引擎)
  - [5.4 API 设计与安全](#54-api-设计与安全)
- [6. 前端应用](#6-前端应用)
  - [6.1 实时监控大屏](#61-实时监控大屏)
  - [6.2 证据追溯面板](#62-证据追溯面板)
  - [6.3 决策驾驶舱](#63-决策驾驶舱)
  - [6.4 移动端小程序](#64-移动端小程序)
- [7. 两条线协作接口规范](#7-两条线协作接口规范)
  - [7.1 AI → 全栈 事件输出协议](#71-ai--全栈-事件输出协议)
  - [7.2 全栈 → AI 控制指令](#72-全栈--ai-控制指令)
  - [7.3 接口联调约定](#73-接口联调约定)
- [8. 数据模型设计](#8-数据模型设计)
  - [8.1 数据库选型](#81-数据库选型)
  - [8.2 ER 关系图（文字描述）](#82-er-关系图文字描述)
  - [8.3 数据字典](#83-数据字典)
- [9. 非功能需求](#9-非功能需求)
  - [9.1 性能指标](#91-性能指标)
  - [9.2 安全要求](#92-安全要求)
  - [9.3 可用性与可靠性](#93-可用性与可靠性)
  - [9.4 系统压测报告要求](#94-系统压测报告要求)
- [10. 运维与部署](#10-运维与部署)
  - [10.1 Docker 镜像规划](#101-docker-镜像规划)
  - [10.2 K8s Helm Chart 规划](#102-k8s-helm-chart-规划)
  - [10.3 配置管理](#103-配置管理)
  - [10.4 监控与告警](#104-监控与告警)
- [11. 交付物清单](#11-交付物清单)
- [12. 里程碑计划](#12-里程碑计划)
- [13. 术语表](#13-术语表)

---

## 1. 项目概述

### 1.1 项目背景

烟头乱扔是城市环境卫生治理的顽疾。据统计，烟头占路面垃圾数量的 30%-50%，一座中等城市每年因清扫烟头产生的环卫支出超过两百万元。当前治理手段高度依赖环卫工人的人工巡查和监控录像的事后回看，存在三大痛点：

1. **发现难**：烟头体积小（监控画面中仅占 10-20 像素），落地后不易被发现，人工巡查间隔长达 2-3 小时。
2. **取证难**：即使监控拍到乱扔行为，现有系统也无法自动锁定违规行人，难以判断烟头是刚扔下的还是历史遗留。
3. **决策弱**：缺乏对高发区域和高发时段的统计分析，无法自动生成垃圾桶增设或巡查排班等调度建议。

现有 AI 研究大多停留在单帧静态检测层面，无法区分静态遗留烟头和实时乱扔行为，更未能将识别结果转化为可供环卫部门直接使用的治理建议，存在明显的技术断层。

### 1.2 项目目标

构建一套从**智能感知 → 行为识别 → 责任关联 → 治理决策**的完整闭环系统：

- **感知层**：基于改进 YOLO 的小目标烟头检测，实现高召回率（≥85%）与低误报率（≤10%）的平衡。
- **识别层**：构建"手部持烟 → 抛掷动作 → 烟头落地静止"三段式行为证据链，区分实时乱扔与历史遗留。
- **关联层**：基于 ByteTrack 多目标跟踪，将抛掷事件与具体行人 ID 时空绑定，输出完整违规证据链。
- **决策层**：长期运行后统计分析高发区域与高发时段，自动生成垃圾桶增设建议和巡查排班优化方案。
- **交付层**：提供可部署的 Docker 镜像 / K8s Helm Chart、完整 API 文档、数据库 ER 图与数据字典、前端源码与构建产物、系统压测报告。

### 1.3 核心创新点

| 创新点 | 说明 |
|--------|------|
| 三段式行为证据链 | 首次提出"持烟→抛掷→落地"时序验证框架，只有三环节依次触发才输出有效违规事件，从原理上区分历史遗留烟头与实时乱扔行为 |
| 微小抛掷物专用识别 | 基于光流法速度突变检测 + 抛物线轨迹拟合的双重验证，区分主动抛掷与正常挥手/抖烟灰等相似动作 |
| 时空关联全要素追溯 | ByteTrack 跟踪 + 空间距离与时间窗口双重匹配，将抛掷事件绑定到具体行人 ID，解决"谁扔的"问题 |
| 感知-决策完整闭环 | 从智能识别到热力图分析、调度建议输出、治理效果对比，形成从感知到决策的完整闭环 |

---

## 2. 用户角色与使用场景

### 2.1 角色定义

| 角色 | 说明 | 核心诉求 |
|------|------|----------|
| 环卫工人 | 一线清扫人员，通过移动端接收清理微工单 | 快速获知烟头落点位置，提高清扫效率 |
| 管理人员 | 校园后勤/环卫部门负责人，查看数据报表与调度建议 | 掌握高发区域/时段，优化资源配置，量化治理效果 |
| 系统管理员 | 负责系统运维，管理摄像头、用户、权限 | 系统稳定运行，摄像头在线率，权限管控 |
| AI 开发人员 | 负责算法模型迭代与参数调优 | 动态调整检测阈值、查看模型指标、管理训练数据 |

### 2.2 核心使用场景

**场景一：实时违规报警与工单推送**
系统检测到行人乱扔烟头行为，三段式证据链校验通过后，自动截取前后 10 秒视频片段 + 3 张关键帧存入对象存储，生成清理微工单推送至环卫工人移动端，环卫工人前往落点位置清理并拍照闭环。

**场景二：违规证据追溯与回放**
管理人员在证据追溯面板中查看违规事件列表，点击某条事件后查看视频回放、三帧证据缩略图（持烟帧/抛掷帧/落地帧）和行人轨迹可视化，确认违规事实。

**场景三：高发区域分析与调度决策**
系统运行一个月后，管理人员在决策驾驶舱查看 GIS 热力图，发现某教学楼出口烟头乱扔频次超过阈值×1.5。系统自动生成"建议增设烟蒂收集器"卡片。管理人员采纳建议后，系统持续追踪该区域频次变化，生成治理效果对比报告。

**场景四：AI 参数动态调优**
夜间低光照场景下误报率上升，AI 开发人员通过 `POST /ai/config` 接口动态调低置信度阈值并开启图像增强模块，无需重启服务即可生效。

**场景五：巡查打卡与闭环**
环卫工人接到工单后前往指定位置，拍照确认清理完成，系统记录清理时间并自动关闭工单。管理人员可在后台查看工单完成率和平均响应时间。

---

## 3. 系统总体架构

### 3.1 架构总览

系统分为五层，自底向上依次为：

```
┌─────────────────────────────────────────────────────────┐
│                    前端应用层                              │
│  实时监控大屏 │ 证据追溯面板 │ 决策驾驶舱 │ 移动端小程序    │
│              (Vue3 + ECharts + GIS)                      │
├─────────────────────────────────────────────────────────┤
│                    API 网关层                              │
│     RESTful API (FastAPI)  │  WebSocket (实时推送)        │
│     RBAC 鉴权 │ 操作日志审计 │ 视频流鉴权                  │
├─────────────────────────────────────────────────────────┤
│                    业务服务层                              │
│  视频流管理 │ 业务逻辑引擎 │ 数据统计引擎 │ 决策引擎       │
│  工单管理   │ 证据管理     │ 调度规则引擎 │ 用户管理       │
├─────────────────────────────────────────────────────────┤
│                    AI 算法层                              │
│  YOLO 检测 │ 三段式证据链 │ ByteTrack 跟踪 │ 图像增强     │
│  光流法分析 │ 抛物线拟合   │ 证据帧采集     │ 环形缓冲区   │
├─────────────────────────────────────────────────────────┤
│                    数据与基础设施层                        │
│  PostgreSQL │ InfluxDB │ MinIO(对象存储) │ Redis(缓存)   │
│  FFmpeg/OpenCV │ Docker │ K8s │ Nginx                    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 技术栈选型

| 层级 | 技术选型 | 选型理由 |
|------|----------|----------|
| 后端框架 | Python 3.11 + FastAPI | 原生 async 支持，与 AI/CV 生态无缝衔接，自动生成 OpenAPI 文档 |
| 前端框架 | Vue 3 + TypeScript + Vite | 组合式 API，生态成熟，ECharts/地图组件丰富 |
| 可视化 | ECharts 5 + Leaflet/MapLibre | ECharts 覆盖折线/柱状/热力图；Leaflet 轻量 GIS |
| UI 组件库 | Element Plus | Vue3 生态主流组件库，适合管理后台 |
| 关系型数据库 | PostgreSQL 16 | 事务一致性，支持 JSONB 存储半结构化数据 |
| 时序数据库 | InfluxDB 2.x | 专为时序数据优化，适合按小时/天/周聚合违规事件 |
| 对象存储 | MinIO | S3 兼容，本地部署，适合存储视频片段和证据帧 |
| 缓存 | Redis 7 | 环形缓冲区索引、WebSocket 会话管理、限流 |
| 消息队列 | Redis Streams | 轻量级消息队列，适合 AI→后端事件流传输 |
| 视频处理 | FFmpeg + OpenCV | RTSP 拉流、抽帧、视频片段截取 |
| 容器化 | Docker + Docker Compose | 校园试点阶段使用 Compose 编排 |
| 编排（可选） | K8s + Helm | 后续扩展时迁移至 K8s |
| 反向代理 | Nginx | 前端静态资源、WebSocket 代理、视频流代理 |

### 3.3 部署拓扑

校园试点部署（2-4 路摄像头）：

```
                    ┌──────────────┐
                    │  海康威视摄像头  │  ×2-4 台
                    │  (RTSP 输出)   │
                    └──────┬───────┘
                           │ RTSP over LAN
                    ┌──────▼───────┐
                    │   GPU 服务器   │  NVIDIA RTX 3090/3070
                    │  (AI 推理节点)  │
                    │  FFmpeg 拉流   │
                    │  YOLO 推理     │
                    │  ByteTrack    │
                    └──────┬───────┘
                           │ WebSocket / HTTP
                    ┌──────▼───────┐
                    │  应用服务器    │  (可与GPU服务器同机)
                    │  FastAPI 后端  │
                    │  Vue3 前端     │
                    │  PostgreSQL   │
                    │  InfluxDB     │
                    │  MinIO        │
                    │  Redis        │
                    │  Nginx        │
                    └──────┬───────┘
                           │ HTTP/HTTPS
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │ 管理人员PC │ │大屏展示│ │环卫工人手机│
        │ (浏览器)   │ │(浏览器)│ │(微信小程序)│
        └───────────┘ └───────┘ └───────────┘
```

试点阶段 AI 推理与应用服务可部署在同一台 GPU 服务器上（学院配备 RTX 3090/3070），后续扩展时拆分为独立节点。

---

## 4. AI 算法管道

### 4.1 视频流接入与预处理

| 功能项 | 说明 |
|--------|------|
| RTSP 拉流 | 使用 FFmpeg/OpenCV 从海康威视摄像头拉取 RTSP 流，支持自动重连 |
| 自适应抽帧 | 默认 25 FPS 抽帧送入 AI 推理；当 GPU 负载过高或队列堆积时自动降至 15 FPS，负载恢复后回调 |
| 图像增强模块 | 支持 Retinex 算法和直方图均衡化两种模式，可通过 `/ai/preprocess/toggle` 动态开关 |
| 暗光自适应 | 根据画面平均亮度自动判断是否启用图像增强（阈值可配置） |
| 环形缓冲区 | 每路摄像头维护一个环形视频缓冲区（默认保留最近 30 秒），用于违规事件触发时截取前后 10 秒视频片段 |

**自适应抽帧策略：**

```
当 GPU 显存占用 > 80% 或推理队列长度 > 60 帧时:
    抽帧频率降至 15 FPS
    记录降频日志
当 GPU 显存占用 < 60% 且推理队列长度 < 20 帧时:
    恢复 25 FPS
```

### 4.2 改进 YOLO 小目标烟头检测

针对烟头在监控画面中仅占 10-20 像素、特征弱的问题，在 YOLO 框架基础上进行以下改进：

| 改进策略 | 具体方案 | 预期效果 |
|----------|----------|----------|
| 浅层小目标检测头 | 增加 P2 层（160×160）检测头，提升对 10-20 像素目标的感受能力 | 提升小目标召回率 |
| 锚框优化 | 对烟头标注数据集进行 K-means 聚类，重新计算锚框尺寸分布 | 提高锚框匹配度 |
| 注意力机制 | 引入 CBAM 模块（通道+空间注意力），增强烟头区域特征响应 | 抑制地面纹理、落叶等背景干扰 |
| 暗光增强 | 集成 Retinex/直方图均衡化预处理，在送入检测网络前增强画面 | 提升夜间检出率 |

**性能目标：**

| 指标 | 目标值 |
|------|--------|
| 召回率（Recall） | ≥ 85% |
| 误报率（False Positive Rate） | ≤ 10% |
| 推理速度（FPS） | ≥ 25 FPS / 路（RTX 3090） |
| mAP@0.5 | ≥ 0.75 |

### 4.3 三段式行为证据链

系统的核心创新——"手部持烟 → 抛掷动作 → 烟头落地静止"三段式时序验证状态机：

```
                    IoU > 阈值
                    且持续 N 帧
    ┌─────────┐ ──────────────> ┌───────────┐
    │  IDLE   │                 │  HOLDING  │
    │ (空闲)  │ <────────────── │ (持烟)    │
    └─────────┘    超时未触发    └─────┬─────┘
                                        │
                                        │ 光流法检测到速度突变
                                        │ + 抛物线轨迹拟合通过
                                        ▼
    ┌─────────┐                  ┌───────────┐
    │ LANDED  │ <────────────── │ THROWING  │
    │ (落地)  │  烟头静止超30帧  │ (抛掷中)  │
    └────┬────┘                  └───────────┘
         │
         │ 证据链校验通过
         ▼
    ┌───────────┐
    │ CONFIRMED │ ──> 输出违规事件 JSON
    │ (确认违规)│      截取视频片段+3帧证据
    └───────────┘
```

**各阶段判定规则：**

| 阶段 | 判定条件 | 超时/异常处理 |
|------|----------|-------------|
| HOLDING（持烟） | 烟头检测框与手部检测框 IoU > 0.3 且持续 ≥ 5 帧 | 超过 10 秒未进入 THROWING 则回退至 IDLE |
| THROWING（抛掷） | 光流法检测到烟头速度突变（> v_threshold）且抛物线轨迹拟合误差 < ε_threshold | 超过 2 秒未进入 LANDED 则回退至 IDLE |
| LANDED（落地） | 烟头在画面下方区域（地面附近）静止超过 30 帧 | 直接进入 CONFIRMED |
| CONFIRMED（确认） | 三段式状态完整、时间戳连续 | 输出违规事件，附带完整证据链 |

**抛掷动作双重验证（核心难点）：**

1. **光流法速度突变检测**：计算烟头候选区域在连续帧中的运动速度和方向变化幅度，当速度超过阈值 `v_threshold` 且方向与重力方向一致时，判定为速度突变。
2. **抛物线轨迹拟合**：对烟头最近 N 帧的轨迹点进行抛物线拟合（`y = ax² + bx + c`），若拟合误差 `R² > 0.85` 且初速度方向合理，判定为主动抛掷。

两个条件同时满足才判定为抛掷动作，有效区分正常挥手、抖烟灰、扔纸团等相似行为。

### 4.4 ByteTrack 行人跟踪与事件关联

| 功能项 | 说明 |
|--------|------|
| 行人跟踪 | 使用 ByteTrack 算法对画面中所有行人进行实时跟踪，记录移动路径和手部位置 |
| 事件关联 | 检测到抛掷事件时，计算抛掷起点与各行人手部检测框的欧氏距离，筛选最近行人候选 |
| 时间窗口匹配 | 验证该行人手部在抛掷事件发生时间点前后是否与烟头轨迹存在时空重合 |
| 遮挡处理 | 利用行人重识别（ReID）特征进行轨迹片段拼接，恢复遮挡导致的轨迹断裂 |
| 跨摄像头追踪 | 支持跨摄像头接力追踪（基于 ReID 特征匹配） |

**双重匹配策略：**

```
Step 1: 空间匹配
    计算抛掷起点 P_throw 与所有行人手部框 H_i 的欧氏距离
    筛选距离 < d_threshold 的行人候选集 C

Step 2: 时间窗口匹配
    对候选集 C 中每个行人，检查其手部轨迹在 [t_throw - Δt, t_throw + Δt] 
    时间窗口内是否与烟头轨迹存在空间重合（IoU > 0 或距离 < d_proximity）
    
    选择重合度最高的行人作为违规行人，绑定 track_id
```

### 4.5 证据采集与存储

当三段式证据链校验通过（进入 CONFIRMED 阶段）时：

| 证据类型 | 采集方式 | 存储位置 |
|----------|----------|----------|
| 视频片段 | 从环形缓冲区截取违规时刻前后各 10 秒视频，通过 FFmpeg 编码为 MP4 | MinIO 对象存储 |
| 关键帧 1 - 持烟帧 | 从 HOLDING 阶段截取最佳帧（IoU 最大的帧） | MinIO 对象存储 |
| 关键帧 2 - 抛掷帧 | 从 THROWING 阶段截取速度突变最大的帧 | MinIO 对象存储 |
| 关键帧 3 - 落地帧 | 从 LANDED 阶段截取烟头静止后的首帧 | MinIO 对象存储 |
| 轨迹数据 | 记录行人 track_id 的最近 N 帧轨迹点序列 | PostgreSQL (JSONB) |

---

## 5. 后端服务

### 5.1 视频流接入与预处理管道

#### 5.1.1 RTSP 流管理

| 功能项 | 说明 |
|--------|------|
| 流注册 | 管理员通过 API 注册摄像头信息（camera_id, RTSP URL, 位置坐标, ROI 区域） |
| 流健康检查 | 每 10 秒检测一次 RTSP 连接状态，断线自动重连（最多 3 次，间隔 5 秒） |
| 流状态监控 | 实时上报每路流的状态（在线/离线/降频）、当前 FPS、帧率、分辨率 |
| ROI 配置 | 支持为每路摄像头配置感兴趣区域（ROI），仅在 ROI 内进行检测 |

#### 5.1.2 图像增强模块

| 功能项 | 说明 |
|--------|------|
| 增强算法 | 支持 Retinex 和直方图均衡化两种模式，可按摄像头独立配置 |
| 动态开关 | 通过 `/ai/preprocess/toggle` 接口动态开关，无需重启服务 |
| 自适应触发 | 根据画面平均亮度自动判断是否启用（亮度 < threshold 时自动开启） |

#### 5.1.3 自适应抽帧

| 功能项 | 说明 |
|--------|------|
| 默认帧率 | 25 FPS |
| 降频策略 | GPU 显存 > 80% 或队列 > 60 帧时降至 15 FPS |
| 恢复策略 | GPU 显存 < 60% 且队列 < 20 帧时恢复 25 FPS |
| 环形缓冲区 | 每路摄像头保留最近 30 秒视频帧，用于证据截取 |

### 5.2 业务逻辑引擎

#### 5.2.1 证据链校验

接收 AI 输出的 JSON 事件流，执行以下校验：

| 校验项 | 规则 | 失败处理 |
|--------|------|----------|
| 三段式完整性 | 检查 HOLDING → THROWING → LANDED → CONFIRMED 四阶段是否齐全 | 丢弃事件，记录异常日志 |
| 时间戳连续性 | 相邻阶段时间差 ≤ 合理阈值（HOLDING→THROWING ≤ 10s, THROWING→LANDED ≤ 2s） | 丢弃事件，记录异常日志 |
| 置信度校验 | confidence ≥ 配置的最小阈值（默认 0.75） | 标记为低置信度事件，不触发工单 |
| 轨迹完整性 | trajectory 数组长度 ≥ 最小帧数（默认 5） | 丢弃事件，记录异常日志 |
| 行人 ID 有效性 | track_id 存在于当前活跃跟踪列表中 | 标记为未关联事件，人工审核 |

#### 5.2.2 证据采集与存储

违规事件触发时自动执行：

1. 从环形缓冲区截取前后 10 秒视频片段，FFmpeg 编码为 MP4。
2. 提取 3 张关键帧（持烟帧、抛掷帧、落地帧），保存为 JPEG。
3. 将视频片段和关键帧上传至 MinIO 对象存储。
4. 在 PostgreSQL 中创建违规事件记录，关联存储路径。
5. 生成清理微工单，推送至移动端。

#### 5.2.3 工单管理

| 功能项 | 说明 |
|--------|------|
| 工单生成 | 违规事件确认后自动生成清理工单，包含事件 ID、摄像头位置、烟头落点坐标、证据链接 |
| 工单推送 | 通过 WebSocket 推送至环卫工人移动端，支持声音/震动提醒 |
| 工单状态 | 待处理 → 已接收 → 处理中 → 已完成（拍照闭环）→ 已关闭 |
| 超时处理 | 工单超过 30 分钟未接收，自动升级推送至管理人员 |
| 工单统计 | 按日/周统计工单数量、完成率、平均响应时间 |

### 5.3 数据统计与决策引擎

#### 5.3.1 时序数据聚合

| 聚合维度 | 说明 |
|----------|------|
| 小时级 | 每小时统计各摄像头/区域的违规数量，写入 InfluxDB |
| 天级 | 每天聚合各区域违规频次，生成日报 |
| 周级 | 每周聚合趋势数据，生成周报对比 |

#### 5.3.2 热力图计算

采用核密度估计（KDE）算法计算违规事件的空间分布密度：

```
输入: 违规事件的地理坐标集合 {(lat_i, lon_i)}
输出: 二维密度网格 (grid)

对每个网格点 (x, y):
    density(x, y) = (1 / n) * Σ K_h(distance((x,y), (lat_i, lon_i)))
    
其中 K_h 为高斯核函数, h 为带宽参数（默认 50m）
```

热力图数据以网格 JSON 格式提供给前端渲染。

#### 5.3.3 调度规则引擎

| 规则条件 | 触发动作 | 输出格式 |
|----------|----------|----------|
| 某区域频次 > 阈值 × 1.5 | 生成"增设设施"建议 | "建议在 {区域名称} 附近增设烟蒂收集器，该区域近 {N} 天违规频次 {X} 次，超出平均值 {Y}%" |
| 某时段频次 > 阈值 × 1.5 | 生成"调整排班"建议 | "建议在 {时段} 增派巡查人员，该时段近 {N} 天违规频次 {X} 次，占全天 {P}%" |
| 连续 N 天频次下降 > 30% | 生成"治理有效"报告 | " {区域名称} 治理措施生效，违规频次已下降 {D}%，建议保持当前方案" |
| 连续 N 天频次上升 > 30% | 生成"预警"通知 | "{区域名称} 违规频次持续上升，建议加强巡查或分析原因" |

阈值和倍数参数均可通过管理后台配置。

### 5.4 API 设计与安全

#### 5.4.1 RESTful API

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| 认证 | `/api/v1/auth/login` | POST | 用户登录，返回 JWT |
| 认证 | `/api/v1/auth/refresh` | POST | 刷新 Token |
| 摄像头 | `/api/v1/cameras` | GET/POST | 摄像头列表/注册 |
| 摄像头 | `/api/v1/cameras/{id}` | GET/PUT/DELETE | 摄像头详情/更新/删除 |
| 摄像头 | `/api/v1/cameras/{id}/status` | GET | 摄像头实时状态 |
| 摄像头 | `/api/v1/cameras/{id}/stream` | GET | 获取视频流地址（鉴权后） |
| 事件 | `/api/v1/events` | GET | 违规事件列表（分页/筛选） |
| 事件 | `/api/v1/events/{id}` | GET | 事件详情（含证据链） |
| 事件 | `/api/v1/events/stats` | GET | 事件统计（按时间/区域聚合） |
| 事件 | `/api/v1/events/heatmap` | GET | 热力图数据 |
| 工单 | `/api/v1/workorders` | GET/POST | 工单列表/创建 |
| 工单 | `/api/v1/workorders/{id}` | GET/PUT | 工单详情/更新状态 |
| 工单 | `/api/v1/workorders/{id}/complete` | POST | 工单完成（拍照闭环） |
| 决策 | `/api/v1/suggestions` | GET | 调度建议列表 |
| 决策 | `/api/v1/suggestions/{id}/feedback` | POST | 建议采纳/驳回反馈 |
| 决策 | `/api/v1/dashboard/overview` | GET | 驾驶舱概览数据 |
| AI 控制 | `/ai/config` | POST | 动态调整 AI 参数 |
| AI 控制 | `/ai/preprocess/toggle` | POST | 开关图像增强 |
| AI 控制 | `/ai/metrics` | GET | 获取 AI 运行指标 |
| 用户 | `/api/v1/users` | GET/POST | 用户列表/创建 |
| 用户 | `/api/v1/users/{id}` | GET/PUT/DELETE | 用户详情/更新/删除 |
| 审计 | `/api/v1/audit/logs` | GET | 操作日志列表 |

#### 5.4.2 WebSocket

| 频道 | 方向 | 说明 |
|------|------|------|
| `/ws/alerts` | 服务端 → 客户端 | 实时违规报警推送（含事件摘要、摄像头 ID、证据缩略图 URL） |
| `/ws/camera-status` | 服务端 → 客户端 | 摄像头状态变更通知（上线/离线/降频） |
| `/ws/workorders` | 服务端 → 客户端 | 工单推送（面向环卫工人移动端） |
| `/ws/system-metrics` | 服务端 → 客户端 | 系统指标实时推送（FPS、显存、队列长度） |

#### 5.4.3 安全设计

| 安全项 | 方案 |
|--------|------|
| 认证 | JWT Token，Access Token 有效期 2 小时，Refresh Token 有效期 7 天 |
| 授权 | RBAC 角色权限控制，按角色限制可访问的 API 和数据范围 |
| 视频流鉴权 | RTSP 流地址不直接暴露；前端通过 API 获取带签名的临时流地址（有效期 10 分钟） |
| 操作日志审计 | 所有写操作（创建/更新/删除）记录操作人、时间、IP、操作内容，不可篡改 |
| API 限流 | 基于 Redis 的令牌桶限流，普通用户 100 次/分钟，AI 控制接口 10 次/分钟 |
| HTTPS | 所有 HTTP 通信强制 HTTPS（Nginx 终结 TLS） |
| CORS | 仅允许配置的前端域名跨域访问 |
| 输入校验 | 所有 API 入参使用 Pydantic 模型校验，防止 SQL 注入和 XSS |

---

## 6. 前端应用

### 6.1 实时监控大屏

| 功能项 | 说明 |
|--------|------|
| 多路视频矩阵 | 支持 2×2 / 1×3 / 1×4 布局，实时展示各路摄像头画面 |
| AI 渲染开关 | 一键切换原始画面 / AI 渲染画面（叠加检测框、轨迹线、状态标签） |
| 实时报警弹窗 | 违规事件触发时，大屏右上角弹出报警卡片，含缩略图、摄像头位置、时间，支持点击查看详情 |
| 摄像头状态条 | 底部状态栏显示各路摄像头的在线状态、FPS、是否降频 |
| 全屏模式 | 支持单路全屏放大，适合大屏展示场景 |

### 6.2 证据追溯面板

| 功能项 | 说明 |
|--------|------|
| 违规事件列表 | 分页表格展示违规事件，支持按时间范围、摄像头、置信度筛选 |
| 视频回放播放器 | 内嵌视频播放器，播放违规前后 10 秒视频片段，支持暂停/拖拽/倍速 |
| 三帧证据缩略图 | 横向展示持烟帧、抛掷帧、落地帧三张关键帧，点击可放大查看 |
| 行人轨迹可视化 | 在视频画面上叠加行人运动轨迹（折线）和抛掷轨迹（抛物线），标注关键时间点 |
| 证据链时间轴 | 时间轴展示 HOLDING → THROWING → LANDED → CONFIRMED 四阶段时间节点 |
| 导出功能 | 支持单条事件证据包导出（视频 + 图片 + 事件 JSON） |

### 6.3 决策驾驶舱

| 功能项 | 说明 |
|--------|------|
| GIS 热力图 | 基于校园地图渲染违规事件热力图，支持按时间段筛选，点击热区查看该区域事件列表 |
| 时段潮汐折线图 | 24 小时违规频次折线图，标注高发时段，支持对比不同日期 |
| 治理效果对比图 | 柱状图/折线图对比治理措施实施前后的违规频次变化 |
| 调度建议卡片 | 卡片式展示系统自动生成的调度建议（增设设施/调整排班/治理有效/预警通知），支持采纳/驳回 |
| 数据概览卡片 | 总违规数、今日违规数、工单完成率、平均响应时间等关键指标 |

### 6.4 移动端小程序

| 功能项 | 说明 |
|--------|------|
| 工单接收 | 实时接收清理工单推送，显示位置、烟头落点、证据缩略图 |
| 拍照闭环 | 环卫工人到达现场后拍照确认清理完成，上传照片关闭工单 |
| 巡查打卡 | 支持巡查路线打卡功能，记录巡查轨迹和时间 |
| 工单历史 | 查看个人历史工单记录和完成情况 |
| 消息通知 | 接收系统通知（新工单、超时提醒、调度变更） |

---

## 7. 两条线协作接口规范

### 7.1 AI → 全栈 事件输出协议

AI 算法层通过 WebSocket（主通道，实时）和 HTTP POST（备通道，重试保障）向全栈后端推送事件。

**传输方式：** JSON over WebSocket / HTTP POST

**WebSocket 地址：** `ws://backend:8000/ws/ai-events`

**HTTP 备用地址：** `POST http://backend:8000/api/v1/ai/events`

**事件 JSON 结构：**

```json
{
  "event_id": "uuid-v4",
  "timestamp": "2026-08-07T22:10:35.123+08:00",
  "camera_id": "cam_003",
  "track_id": 1847,
  "stage": "THROW_CONFIRMED",
  "confidence": 0.92,
  "bbox": [120, 340, 25, 18],
  "trajectory": [
    [115, 335, "2026-08-07T22:10:33.100+08:00"],
    [118, 338, "2026-08-07T22:10:33.140+08:00"],
    [122, 342, "2026-08-07T22:10:33.180+08:00"]
  ],
  "evidence_frames": [
    {
      "frame_ts": "2026-08-07T22:10:32.500+08:00",
      "type": "holding",
      "path": "/evidence/cam_003_1847_h.jpg"
    },
    {
      "frame_ts": "2026-08-07T22:10:34.200+08:00",
      "type": "throwing",
      "path": "/evidence/cam_003_1847_t.jpg"
    },
    {
      "frame_ts": "2026-08-07T22:10:35.100+08:00",
      "type": "landed",
      "path": "/evidence/cam_003_1847_l.jpg"
    }
  ],
  "video_clip_path": "/evidence/cam_003_1847_clip.mp4"
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| event_id | string (uuid) | 是 | 事件唯一标识，UUID v4 格式 |
| timestamp | string (ISO 8601) | 是 | 事件确认时间，含时区 |
| camera_id | string | 是 | 摄像头 ID，与后端注册一致 |
| track_id | int | 是 | ByteTrack 分配的行人轨迹 ID |
| stage | string | 是 | 事件阶段：`HOLDING` / `THROWING` / `LANDED` / `THROW_CONFIRMED` |
| confidence | float | 是 | 置信度，0.0-1.0 |
| bbox | array[int] | 是 | 当前帧目标框 [x, y, w, h] |
| trajectory | array[array] | 是 | 最近 N 帧轨迹点 [[x, y, timestamp], ...] |
| evidence_frames | array[object] | CONFIRMED 阶段必填 | 三张关键帧信息 |
| video_clip_path | string | CONFIRMED 阶段必填 | 视频片段存储路径 |

**stage 字段说明：**

| stage 值 | 含义 | evidence_frames | video_clip_path |
|-----------|------|-----------------|-----------------|
| HOLDING | 持烟状态触发 | 不返回 | 不返回 |
| THROWING | 抛掷动作触发 | 不返回 | 不返回 |
| LANDED | 落地静止触发 | 不返回 | 不返回 |
| THROW_CONFIRMED | 三段式确认，违规事件成立 | 返回 3 帧 | 返回视频路径 |

### 7.2 全栈 → AI 控制指令

全栈后端通过 HTTP RESTful 接口向 AI 算法层发送控制指令。

#### 7.2.1 动态调整 AI 配置

```
POST /ai/config
Content-Type: application/json
Authorization: Bearer <token>
```

**请求体：**

```json
{
  "camera_id": "cam_003",
  "confidence_threshold": 0.80,
  "state_machine_params": {
    "holding_iou_threshold": 0.3,
    "holding_min_frames": 5,
    "throwing_velocity_threshold": 50.0,
    "trajectory_fit_threshold": 0.85,
    "landed_min_static_frames": 30
  },
  "roi": {
    "enabled": true,
    "polygon": [[100, 100], [800, 100], [800, 600], [100, 600]]
  }
}
```

**响应：**

```json
{
  "status": "ok",
  "applied_config": {
    "camera_id": "cam_003",
    "confidence_threshold": 0.80,
    "updated_at": "2026-08-07T22:15:00.000+08:00"
  }
}
```

#### 7.2.2 开关图像增强

```
POST /ai/preprocess/toggle
Content-Type: application/json
Authorization: Bearer <token>
```

**请求体：**

```json
{
  "camera_id": "cam_003",
  "enabled": true,
  "algorithm": "retinex",
  "auto_mode": false
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| camera_id | string | 摄像头 ID |
| enabled | bool | true=开启, false=关闭 |
| algorithm | string | `retinex` 或 `histogram_eq` |
| auto_mode | bool | true=根据亮度自动判断是否启用 |

**响应：**

```json
{
  "status": "ok",
  "camera_id": "cam_003",
  "preprocess_enabled": true,
  "algorithm": "retinex",
  "updated_at": "2026-08-07T22:15:00.000+08:00"
}
```

#### 7.2.3 获取 AI 运行指标

```
GET /ai/metrics
Authorization: Bearer <token>
```

**响应：**

```json
{
  "cameras": [
    {
      "camera_id": "cam_003",
      "status": "online",
      "current_fps": 25.0,
      "gpu_memory_used_mb": 3200,
      "gpu_memory_total_mb": 24576,
      "inference_queue_length": 12,
      "preprocess_enabled": false,
      "dropped_frames": 0,
      "avg_inference_ms": 38.5
    },
    {
      "camera_id": "cam_004",
      "status": "degraded",
      "current_fps": 15.0,
      "gpu_memory_used_mb": 4100,
      "gpu_memory_total_mb": 24576,
      "inference_queue_length": 68,
      "preprocess_enabled": true,
      "dropped_frames": 3,
      "avg_inference_ms": 62.3
    }
  ],
  "gpu_summary": {
    "device": "NVIDIA RTX 3090",
    "utilization": 0.72,
    "memory_used_mb": 7300,
    "memory_total_mb": 24576,
    "temperature_c": 68
  }
}
```

### 7.3 接口联调约定

| 约定项 | 说明 |
|--------|------|
| 时间格式 | 统一使用 ISO 8601 带时区格式（`2026-08-07T22:10:35.123+08:00`） |
| 坐标系 | 图像坐标原点在左上角，x 向右 y 向下，单位为像素 |
| 地理坐标 | 使用 WGS84 坐标系（经纬度） |
| camera_id 命名 | `cam_` 前缀 + 三位数字，如 `cam_003` |
| event_id 格式 | UUID v4 |
| 重试机制 | HTTP 备用通道失败时指数退避重试（1s, 2s, 4s），最多 3 次 |
| 幂等性 | 后端基于 event_id 去重，AI 侧可安全重试 |
| 心跳机制 | WebSocket 连接每 30 秒发送一次 ping，60 秒无响应则断开重连 |
| Mock 数据 | 开发第一天双方各自提供 Mock 数据，确保接口联调不阻塞 |

---

## 8. 数据模型设计

### 8.1 数据库选型

| 数据库 | 用途 | 说明 |
|--------|------|------|
| PostgreSQL 16 | 关系型主库 | 存储用户、摄像头、违规事件、工单、调度建议、审计日志等核心业务数据 |
| InfluxDB 2.x | 时序数据库 | 存储按小时/天/周聚合的违规事件时序数据，支持时序查询和降采样 |
| MinIO | 对象存储 | 存储视频片段（MP4）、关键帧图片（JPEG）、证据包 |
| Redis 7 | 缓存 | 环形缓冲区索引、WebSocket 会话管理、API 限流令牌桶、热数据缓存 |

### 8.2 ER 关系图（文字描述）

```
用户 (users)
  │ 1:N
  ▼
操作日志 (audit_logs)          摄像头 (cameras)
                                  │ 1:N
                                  ▼
                              违规事件 (violation_events)
                                  │ 1:1
                                  ▼
                              证据文件 (evidence_files)
                                  │
                              违规事件 │ 1:N
                                  ▼
                              工单 (work_orders) ──── 1:N ──── 工单照片 (workorder_photos)
                                  │
                              违规事件 │ 1:N
                                  ▼
                              调度建议 (suggestions)

时序数据 (InfluxDB):
  measurement: violation_count
  tags: camera_id, area_name
  fields: count, avg_confidence
  time: 自动时间戳
```

### 8.3 数据字典

#### 8.3.1 users（用户表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希（bcrypt） |
| real_name | VARCHAR(50) | NOT NULL | 真实姓名 |
| role | VARCHAR(20) | NOT NULL | 角色：admin / manager / worker / ai_dev |
| phone | VARCHAR(20) | | 手机号 |
| avatar_url | VARCHAR(255) | | 头像 URL |
| status | VARCHAR(10) | DEFAULT 'active' | 状态：active / disabled |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

#### 8.3.2 cameras（摄像头表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| camera_id | VARCHAR(20) | UNIQUE, NOT NULL | 摄像头编号（cam_003） |
| name | VARCHAR(100) | NOT NULL | 摄像头名称 |
| rtsp_url | VARCHAR(500) | NOT NULL | RTSP 流地址 |
| location_name | VARCHAR(100) | NOT NULL | 安装位置名称 |
| latitude | DECIMAL(10,7) | | 纬度 |
| longitude | DECIMAL(10,7) | | 经度 |
| roi_polygon | JSONB | | ROI 多边形顶点坐标 |
| status | VARCHAR(10) | DEFAULT 'offline' | 状态：online / offline / degraded |
| fps | DECIMAL(5,2) | | 当前帧率 |
| preprocess_enabled | BOOLEAN | DEFAULT false | 是否启用图像增强 |
| preprocess_algorithm | VARCHAR(20) | | 增强算法：retinex / histogram_eq |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT NOW() | 更新时间 |

#### 8.3.3 violation_events（违规事件表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| event_id | UUID | UNIQUE, NOT NULL | 事件唯一标识（UUID v4） |
| camera_id | VARCHAR(20) | FK, NOT NULL | 关联摄像头 |
| track_id | INT | | 行人轨迹 ID |
| stage | VARCHAR(20) | NOT NULL | 事件阶段 |
| confidence | DECIMAL(4,3) | NOT NULL | 置信度 |
| bbox | JSONB | | 目标框 [x, y, w, h] |
| trajectory | JSONB | | 轨迹点序列 |
| event_timestamp | TIMESTAMP | NOT NULL | 事件发生时间 |
| status | VARCHAR(20) | DEFAULT 'confirmed' | 状态：confirmed / false_alarm / pending_review |
| created_at | TIMESTAMP | DEFAULT NOW() | 记录创建时间 |

#### 8.3.4 evidence_files（证据文件表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| event_id | UUID | FK, NOT NULL | 关联违规事件 |
| file_type | VARCHAR(20) | NOT NULL | 类型：video_clip / holding_frame / throwing_frame / landed_frame |
| file_path | VARCHAR(500) | NOT NULL | MinIO 存储路径 |
| file_size | INT | | 文件大小（字节） |
| frame_ts | TIMESTAMP | | 关键帧时间戳（仅图片类型） |
| created_at | TIMESTAMP | DEFAULT NOW() | 上传时间 |

#### 8.3.5 work_orders（工单表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| order_no | VARCHAR(30) | UNIQUE, NOT NULL | 工单编号 |
| event_id | UUID | FK, NOT NULL | 关联违规事件 |
| assigned_to | INT | FK | 分配给的用户 ID |
| status | VARCHAR(20) | DEFAULT 'pending' | 状态：pending / accepted / processing / completed / closed / timeout |
| location_name | VARCHAR(100) | NOT NULL | 工单位置 |
| latitude | DECIMAL(10,7) | | 纬度 |
| longitude | DECIMAL(10,7) | | 经度 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| accepted_at | TIMESTAMP | | 接收时间 |
| completed_at | TIMESTAMP | | 完成时间 |
| closed_at | TIMESTAMP | | 关闭时间 |
| response_time_sec | INT | | 响应时间（秒） |

#### 8.3.6 workorder_photos（工单照片表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| workorder_id | INT | FK, NOT NULL | 关联工单 |
| file_path | VARCHAR(500) | NOT NULL | MinIO 存储路径 |
| uploaded_by | INT | FK, NOT NULL | 上传人 |
| created_at | TIMESTAMP | DEFAULT NOW() | 上传时间 |

#### 8.3.7 suggestions（调度建议表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 主键 |
| type | VARCHAR(30) | NOT NULL | 类型：add_facility / adjust_schedule / treatment_effective / warning |
| area_name | VARCHAR(100) | | 相关区域 |
| time_range | VARCHAR(50) | | 相关时段 |
| content | TEXT | NOT NULL | 建议文本 |
| frequency_data | JSONB | | 触发时的频次数据 |
| status | VARCHAR(20) | DEFAULT 'pending' | 状态：pending / accepted / rejected / expired |
| feedback_note | TEXT | | 反馈备注 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| resolved_at | TIMESTAMP | | 处理时间 |

#### 8.3.8 audit_logs（操作日志表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGSERIAL | PK | 主键 |
| user_id | INT | FK | 操作人 |
| action | VARCHAR(50) | NOT NULL | 操作类型（create/update/delete/login 等） |
| resource_type | VARCHAR(50) | | 资源类型 |
| resource_id | VARCHAR(50) | | 资源 ID |
| detail | JSONB | | 操作详情 |
| ip_address | VARCHAR(45) | | 操作 IP |
| created_at | TIMESTAMP | DEFAULT NOW() | 操作时间 |

#### 8.3.9 InfluxDB 时序数据结构

```
measurement: violation_count
  tags:
    camera_id    (string)
    area_name    (string)
  fields:
    count        (int)        违规数量
    avg_confidence (float)    平均置信度
  time: 自动写入时间戳

查询示例（按小时聚合）:
  SELECT SUM("count") AS "total"
  FROM "violation_count"
  WHERE time > now() - 7d
  GROUP BY time(1h), "camera_id"
```

---

## 9. 非功能需求

### 9.1 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 并发视频路数 | ≥ 4 路（校园试点） | 同时接入 4 路 RTSP 流进行 AI 推理 |
| AI 推理速度 | ≥ 25 FPS / 路（正常） | RTX 3090 单卡；降频模式 ≥ 15 FPS |
| API 平均响应时间 | ≤ 200ms | 不含视频流和文件上传 |
| WebSocket 推送延迟 | ≤ 500ms | 从 AI 确认到前端弹窗 |
| 视频片段截取耗时 | ≤ 3 秒 | 从触发到 MP4 写入 MinIO |
| 热力图计算耗时 | ≤ 2 秒 | 7 天数据量级 |
| 前端首屏加载 | ≤ 3 秒 | 生产环境（gzip + CDN） |

### 9.2 安全要求

| 要求 | 说明 |
|------|------|
| 数据传输加密 | 全站 HTTPS，WebSocket 使用 WSS |
| 密码存储 | bcrypt 哈希，cost factor ≥ 12 |
| JWT 安全 | Access Token 2h 过期，Refresh Token 7d 过期，支持主动吊销 |
| SQL 注入防护 | 全部使用 ORM（SQLAlchemy）参数化查询，禁止拼接 SQL |
| XSS 防护 | 前端输入使用 Vue 模板自动转义，后端 Pydantic 校验 |
| 文件上传限制 | 图片 ≤ 10MB，视频 ≤ 50MB，仅允许 JPEG/PNG/MP4 |
| 敏感数据脱敏 | 日志中 RTSP 地址、密码等字段脱敏输出 |

### 9.3 可用性与可靠性

| 要求 | 说明 |
|------|------|
| RTSP 断线重连 | 最多 3 次，间隔 5 秒，超过后标记摄像头离线并告警 |
| WebSocket 断线重连 | 客户端自动重连，间隔 3 秒，最多 10 次 |
| 事件不丢失 | AI→后端事件推送支持 HTTP 备用通道 + 重试机制 |
| 证据文件冗余 | MinIO 配置纠删码模式，数据冗余度可承受 1 块磁盘故障 |
| 数据备份 | PostgreSQL 每日全量备份，保留 30 天 |
| 服务自恢复 | Docker 容器配置 `restart: unless-stopped` |

### 9.4 系统压测报告要求

交付阶段需完成以下压测项并出具报告：

| 压测项 | 测试方法 | 验收标准 |
|--------|----------|----------|
| 并发路数 | 逐步增加 RTSP 流路数（1→2→4→6→8），观察 AI 推理 FPS 和 GPU 占用 | 4 路时每路 ≥ 25 FPS，6 路时每路 ≥ 15 FPS |
| 存储 IO | 持续触发违规事件（模拟 100 次），测量 MinIO 写入吞吐和 PostgreSQL 写入延迟 | MinIO 写入 ≥ 50MB/s，PG 写入延迟 ≤ 50ms |
| API 响应时间 | 使用 Locust 模拟 50 并发用户访问主要 API | P95 ≤ 500ms，P99 ≤ 1000ms |
| WebSocket 推送 | 模拟 10 个 WebSocket 客户端同时接收报警推送 | 推送延迟 ≤ 500ms，无丢消息 |
| 前端性能 | Lighthouse 审计 | Performance ≥ 80，FCP ≤ 2s |

---

## 10. 运维与部署

### 10.1 Docker 镜像规划

| 镜像名 | 基础镜像 | 说明 |
|--------|----------|------|
| `yanzong/backend` | python:3.11-slim | FastAPI 后端服务 |
| `yanzong/ai-pipeline` | nvidia/cuda:12.1-runtime-ubuntu22.04 | AI 推理管道（YOLO + ByteTrack + OpenCV） |
| `yanzong/frontend` | nginx:alpine | Vue3 前端静态资源 + Nginx |
| `yanzong/worker` | python:3.11-slim | 后台任务（工单超时检查、定时统计、建议生成） |

### 10.2 K8s Helm Chart 规划

校园试点阶段使用 Docker Compose 编排。后续扩展时迁移至 K8s，Helm Chart 结构如下：

```
yanzong-helm/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── ai-pipeline-deployment.yaml
│   ├── ai-pipeline-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── worker-deployment.yaml
│   ├── postgres-statefulset.yaml
│   ├── postgres-service.yaml
│   ├── redis-deployment.yaml
│   ├── minio-statefulset.yaml
│   ├── influxdb-deployment.yaml
│   ├── ingress.yaml
│   └── configmap.yaml
```

values.yaml 关键配置项：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `replicaCount.backend` | 2 | 后端副本数 |
| `replicaCount.aiPipeline` | 1 | AI 推理副本数（受 GPU 限制） |
| `gpu.enabled` | true | 是否启用 GPU |
| `gpu.nodeSelector` | nvidia.com/gpu.present | GPU 节点选择器 |
| `storage.minio.size` | 500Gi | MinIO 存储容量 |
| `storage.postgres.size` | 50Gi | PostgreSQL 存储容量 |
| `camera.maxStreams` | 4 | 最大并发路数 |

### 10.3 配置管理

| 配置类型 | 管理方式 | 说明 |
|----------|----------|------|
| 环境变量 | `.env` 文件 + Docker Compose `environment` | 数据库连接、MinIO 密钥、JWT Secret 等 |
| 应用配置 | `config.yaml` | 摄像头默认参数、抽帧策略、阈值参数等 |
| AI 模型配置 | 数据库 cameras 表 | 按摄像头独立配置置信度阈值、ROI、增强算法 |
| 运行时配置 | API 动态更新 | 通过 `/ai/config` 等接口热更新 |

### 10.4 监控与告警

| 监控项 | 工具 | 告警条件 |
|--------|------|----------|
| 容器状态 | Docker Compose / K8s | 容器异常退出 |
| GPU 占用 | nvidia-smi + 脚本 | 显存 > 90% 持续 5 分钟 |
| 摄像头离线 | 后端健康检查 | 任一路摄像头离线 > 1 分钟 |
| API 错误率 | 后端中间件 | 5xx 错误率 > 5% |
| 磁盘空间 | 系统监控 | 可用空间 < 20% |
| MinIO 容量 | MinIO Admin API | 使用率 > 80% |

---

## 11. 交付物清单

| 序号 | 交付物 | 格式 | 说明 |
|------|--------|------|------|
| 1 | 后端源码 | Git 仓库 | FastAPI 后端，含完整业务逻辑、API、数据模型 |
| 2 | AI 管道源码 | Git 仓库 | YOLO 检测、三段式证据链、ByteTrack 跟踪、图像增强 |
| 3 | 前端源码与构建产物 | Git 仓库 + dist/ | Vue3 前端源码 + 构建后的静态文件 |
| 4 | 移动端小程序源码 | Git 仓库 | 微信小程序源码 |
| 5 | Docker 镜像 | Docker Registry | backend / ai-pipeline / frontend / worker 四个镜像 |
| 6 | Docker Compose 文件 | docker-compose.yml | 校园试点一键部署 |
| 7 | K8s Helm Chart | Helm 包 | 后续扩展部署（可选） |
| 8 | API 文档 | OpenAPI 3.0 (Swagger) | FastAPI 自动生成 + 手动补充说明 |
| 9 | 数据库 ER 图与数据字典 | Markdown + 图片 | 含建表 SQL 脚本 |
| 10 | 系统压测报告 | Markdown / PDF | 含并发路数、存储 IO、响应时间测试结果 |
| 11 | 部署手册 | Markdown | 环境准备、配置、启动、验证步骤 |
| 12 | 标注数据集 | COCO 格式 | 烟头目标、持烟姿态、抛掷轨迹、落地位置标注 |
| 13 | 研究报告 | Markdown / PDF | 系统总结、技术方案、实验结果、应用建议 |

---

## 12. 里程碑计划

对齐科研项目申报书的研究进度安排（2026年5月 — 2027年4月）：

| 阶段 | 时间 | 里程碑 | 主要交付 |
|------|------|--------|----------|
| 一、项目启动与准备 | 2026.05 — 2026.06 | 数据采集与标注完成 | 标注数据集、文献综述、技术路线确定 |
| 二、核心算法研发 | 2026.07 — 2026.09 | YOLO 改进模型训练完成 | 改进 YOLO 模型权重、检测性能评估报告 |
| 三、行为识别与跟踪 | 2026.10 — 2026.11 | 三段式证据链 + ByteTrack 集成完成 | AI 管道端到端可运行、事件输出协议联调 |
| 四、后端与前端开发 | 2026.12 — 2027.01 | 全栈系统开发完成 | 后端 API、前端大屏/追溯面板/驾驶舱、移动端 |
| 五、系统集成与测试 | 2027.02 | 系统集成测试通过 | Docker 镜像、API 文档、ER 图、压测报告 |
| 六、试点部署 | 2027.03 | 校园试点运行一个月 | 试点运行数据、准确率/漏检率/误报率统计 |
| 七、总结与结题 | 2027.04 | 结题答辩 | 论文、研究报告、原型系统、结题报告 |

---

## 13. 术语表

| 术语 | 说明 |
|------|------|
| 行为证据链 | "手部持烟 → 抛掷动作 → 烟头落地静止"三段式时序验证框架 |
| ROI | Region of Interest，感兴趣区域，仅在指定区域内进行检测 |
| IoU | Intersection over Union，交并比，衡量两个检测框的重叠程度 |
| KDE | Kernel Density Estimation，核密度估计，用于计算热力图 |
| ByteTrack | 多目标跟踪算法，在低质量检测结果下仍能保持跟踪连续性 |
| ReID | Re-Identification，行人重识别，用于跨摄像头和遮挡后恢复轨迹 |
| 光流法 | 通过分析连续帧中像素的运动模式来检测物体运动 |
| 环形缓冲区 | 固定大小的循环缓冲区，用于保留最近的视频帧以供证据截取 |
| RBAC | Role-Based Access Control，基于角色的访问控制 |
| JWT | JSON Web Token，用于用户认证的无状态 Token |
| mAP | mean Average Precision，平均精度均值，目标检测的核心评估指标 |
| FPS | Frames Per Second，每秒处理帧数 |
| RTSP | Real-Time Streaming Protocol，实时流传输协议 |
| MinIO | S3 兼容的对象存储系统，适合本地部署 |
| InfluxDB | 时序数据库，专为时间序列数据优化 |

---

*文档结束*
