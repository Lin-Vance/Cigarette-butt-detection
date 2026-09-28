# -*- coding: utf-8 -*-
"""验证 yolo 环境：加载 best.pt + GPU 推理 + 检测项目自带实景图。"""
import os
import sys

os.environ.setdefault('YOLO_VERBOSE', 'false')

import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

ROOT = r'C:\Users\20262\Desktop\烟头行为监测'
WEIGHTS = os.path.join(ROOT, 'best.pt')
SAMPLE = os.path.join(ROOT, 'frontend', 'public', 'design-assets', '2', 'event_detection_evidence_photo.png')
OUT = os.path.join(ROOT, 'shots', 'yolo-verify')

print('=' * 58)
print('torch      :', torch.__version__)
print('cuda avail :', torch.cuda.is_available())
if torch.cuda.is_available():
    print('gpu        :', torch.cuda.get_device_name(0))
    print('cuda ver   :', torch.version.cuda)
    print('vram       :', round(torch.cuda.get_device_properties(0).total_memory / 1024 ** 3, 1), 'GB')

# 1) 纯 GPU 冒烟测试
a = torch.randn(2048, 2048, device='cuda')
b = a @ a
torch.cuda.synchronize()
print('gpu matmul : ok  (结果均值 %.4f)' % b.mean().item())

# 2) 加载项目权重
print('-' * 58)
print('加载权重   :', WEIGHTS, '(%d 字节)' % os.path.getsize(WEIGHTS))
model = YOLO(WEIGHTS)
print('任务/类别  :', model.task, '|', model.names)

# 3) 在项目实景图上做一次 GPU 推理
os.makedirs(OUT, exist_ok=True)
res = model.predict(source=SAMPLE, conf=0.25, device=0, verbose=False, save=True,
                    project=OUT, name='run', exist_ok=True)
r = res[0]
print('-' * 58)
print('推理图片   :', os.path.basename(SAMPLE))
print('检出目标数 :', len(r.boxes))
for box in r.boxes:
    cls = int(box.cls.item())
    print('   %-10s conf=%.3f  box=%s' % (model.names[cls], float(box.conf.item()),
                                          [round(v, 1) for v in box.xyxy[0].tolist()]))
saved = os.path.join(OUT, 'run', os.path.basename(SAMPLE))
print('标注图     :', saved, '(存在)' if os.path.exists(saved) else '(缺失)')
print('=' * 58)
print('VERIFY_OK')
