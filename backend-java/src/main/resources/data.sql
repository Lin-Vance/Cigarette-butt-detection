INSERT IGNORE INTO yz_user(username,password,real_name,role,phone) VALUES
('admin','123456','超级管理员','admin',''),('manager','123456','治理主管','manager',''),
('ai_dev','123456','算法工程师','ai_dev',''),('worker01','123456','张建国','worker','13800000001');
INSERT IGNORE INTO work_order(order_no,event_id,camera_id,location_name,status,assigned_to,priority,created_at) VALUES
('GD202609280001','EVT20260928001','CAM-037','体育馆西广场','pending','待派发','常规','2026-09-28 18:03:00'),
('GD202609280005','EVT20260928005','CAM-052','学生食堂东侧','pending','待派发','高','2026-09-28 16:40:00'),
('GD202609280013','EVT20260928013','CAM-018','教学楼 A 座出口','pending','待派发','高','2026-09-28 13:05:00'),
('GD202609280024','EVT20260928024','CAM-061','图书馆北门','processing','张建国','高','2026-09-28 08:38:00');
