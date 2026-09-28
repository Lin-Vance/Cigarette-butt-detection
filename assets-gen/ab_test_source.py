# -*- coding: utf-8 -*-
"""决定性对比：同样的模型与图片，分别用「直接路径 / 临时文件 / numpy 数组」喂给 predict，
定位接口慢在哪一步（沙箱对临时文件 I/O 或网络检查的干扰）。"""
import os
import tempfile
import time

os.environ.setdefault('YOLO_VERBOSE', 'false')
os.environ.setdefault('ULTRALYTICS_OFFLINE', '1')

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = r'C:\Users\20262\Desktop\烟头行为监测'
IMG = os.path.join(ROOT, 'frontend', 'public', 'media', 'banner-park.png')
W = os.path.join(ROOT, 'best.pt')

m = YOLO(W)
t = time.time()
m.predict(source=np.zeros((640, 640, 3), dtype=np.uint8), device=0, verbose=False)
print('预热          : %.2fs' % (time.time() - t))

t = time.time()
r = m.predict(source=IMG, device=0, verbose=False)[0]
print('A 直接路径     : %.2fs  检出 %d  speed=%s' % (time.time() - t, len(r.boxes), r.speed))

data = open(IMG, 'rb').read()
print('   图片大小     : %d KB' % (len(data) // 1024))
with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
    tf = time.time()
    f.write(data)
    print('   写临时文件   : %.2fs' % (time.time() - tf))
    p = f.name
t = time.time()
r = m.predict(source=p, device=0, verbose=False)[0]
print('B 临时文件路径 : %.2fs  检出 %d' % (time.time() - t, len(r.boxes)))
os.unlink(p)

arr = cv2.imread(IMG)
t = time.time()
r = m.predict(source=arr, device=0, verbose=False)[0]
print('C numpy 数组   : %.2fs  检出 %d' % (time.time() - t, len(r.boxes)))
print('AB_TEST_OK')
