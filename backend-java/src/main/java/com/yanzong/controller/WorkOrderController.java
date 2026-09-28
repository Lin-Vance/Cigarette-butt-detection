package com.yanzong.controller;

import com.yanzong.service.ActivityService;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.time.*;import java.util.*;

@RestController @RequestMapping("/api/v1/workorders")
public class WorkOrderController {
  private final JdbcTemplate db;private final ActivityService activity;
  public WorkOrderController(JdbcTemplate db,ActivityService activity){this.db=db;this.activity=activity;}
  @GetMapping public Map<String,Object> list(@RequestParam(defaultValue="1")int page,@RequestParam(defaultValue="50")int size,@RequestParam(defaultValue="")String status){
    List<Map<String,Object>> rows=status.isBlank()?db.queryForList("select * from work_order order by id desc limit ? offset ?",size,(page-1)*size):db.queryForList("select * from work_order where status=? order by id desc limit ? offset ?",status,size,(page-1)*size);
    long total=status.isBlank()?db.queryForObject("select count(*) from work_order",Long.class):db.queryForObject("select count(*) from work_order where status=?",Long.class,status);
    return Map.of("items",rows.stream().map(this::shape).toList(),"total",total,"page",page,"size",size);
  }
  @GetMapping("/stats") public Map<String,Object> stats(){long total=db.queryForObject("select count(*) from work_order",Long.class);long closed=db.queryForObject("select count(*) from work_order where status in ('completed','closed')",Long.class);List<Map<String,Object>> groups=db.queryForList("select status,count(*) n from work_order group by status");Map<String,Object> by=new LinkedHashMap<>();groups.forEach(x->by.put(String.valueOf(x.get("status")),x.get("n")));return Map.of("total",total,"by_status",by,"closed",closed,"completion_rate",total==0?0:Math.round(closed*1000.0/total)/10.0,"avg_response_min",9.5,"overdue",db.queryForObject("select count(*) from work_order where escalated=1",Long.class));}
  @PostMapping("/{id}/accept") public Map<String,Object> accept(@PathVariable long id){db.update("update work_order set status='accepted',assigned_to='张建国',accepted_at=now(),response_time_sec=timestampdiff(second,created_at,now()) where id=? and status='pending'",id);activity.record("worker","ORDER_ACCEPTED","张建国",String.valueOf(id),"环卫人员已接单");return get(id);}
  @PostMapping("/{id}/start") public Map<String,Object> start(@PathVariable long id){db.update("update work_order set status='processing' where id=?",id);activity.record("worker","ORDER_STARTED","张建国",String.valueOf(id),"已到场并开始处置");return get(id);}
  @PostMapping("/{id}/complete") public Map<String,Object> complete(@PathVariable long id,@RequestParam(defaultValue="已完成清理")String note,@RequestParam(required=false)MultipartFile photo){db.update("update work_order set status='verifying',completion_note=?,closure_photo=? where id=?",note,photo==null?"":photo.getOriginalFilename(),id);activity.record("worker","ORDER_SUBMITTED","张建国",String.valueOf(id),"已提交清理后材料，等待管理端验收");return get(id);}
  @PostMapping("/{id}/verify") public Map<String,Object> verify(@PathVariable long id,@RequestParam boolean passed,@RequestParam(defaultValue="")String note){db.update("update work_order set status=?,completed_at=? where id=?",passed?"closed":"processing",passed?java.sql.Timestamp.valueOf(LocalDateTime.now()):null,id);activity.record("admin",passed?"ORDER_VERIFIED":"ORDER_RETURNED","超级管理员",String.valueOf(id),passed?"验收通过，工单闭环":"验收未通过，退回处置");return get(id);}
  private Map<String,Object> get(long id){return shape(db.queryForMap("select * from work_order where id=?",id));}
  private Map<String,Object> shape(Map<String,Object> r){Map<String,Object> m=new LinkedHashMap<>();for(String k:List.of("id","order_no","event_id","camera_id","location_name","latitude","longitude","status","assigned_to","created_at","accepted_at","completed_at","response_time_sec","closure_photo","completion_note","priority"))m.put(k,r.get(k));m.put("escalated",Integer.valueOf(String.valueOf(r.get("escalated")))==1);m.put("completion_submitted","verifying".equals(r.get("status")));return m;}
}
