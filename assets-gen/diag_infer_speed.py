# -*- coding: utf-8 -*-
"""诊断预检接口慢的原因：拆开模型加载 / 预热 / 稳态三段计时，并打印设备与各阶段耗时。"""
import os
import time

os.environ.setdefault('YOLO_VERBOSE', 'false')
os.environ.setdefault('ULTRALYTICS_OFFLINE', '1')  # 关掉联网更新检查（本机 GitHub 不可达）

import torch
from ultralytics import YOLO, settings

IMG = r'C:\Users\20262\Desktop\烟头行为监测\frontend\public\media\banner-park.png'
W = r'C:\Users\20262\Desktop\烟头行为监测\best.pt'

print('cuda available :', torch.cuda.is_available())
print('settings sync  :', settings.get('sync'))

t = time.time()
m = YOLO(W)
print('1) 加载模型     : %.2fs' % (time.time() - t))

t = time.time()
r = m.predict(source=IMG, conf=0.25, device=0, verbose=False)[0]
print('2) 首次推理     : %.2fs  speed=%s' % (time.time() - t, r.speed))

t = time.time()
r = m.predict(source=IMG, conf=0.25, device=0, verbose=False)[0]
d = time.time() - t
print('3) 二次推理     : %.2fs  speed=%s' % (d, r.speed))
print('   设备         :', r.boxes.data.device if r.boxes is not None else 'n/a')
print('   检出         :', len(r.boxes))
print('   speed 说明   : preprocess/inference/postprocess，单位毫秒（不含调用开销）')
print('DIAG_OK')
