package com.yanzong.controller;

import com.yanzong.service.ActivityService;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@RestController @RequestMapping("/api/v1")
public class CitizenController {
  private final JdbcTemplate db; private final ActivityService activity;
  public CitizenController(JdbcTemplate db,ActivityService activity){this.db=db;this.activity=activity;}

  @PostMapping("/citizen/reports") public Map<String,Object> submit(@RequestBody Map<String,Object> b,@RequestHeader(value="Authorization",required=false) String auth){
    String no="XZ"+LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")); String phone="13800000000";
    db.update("insert into citizen_report(report_no,phone,kind,media_name,location,description,risk_flag) values(?,?,?,?,?,?,?)",no,phone,b.getOrDefault("kind","photo"),b.getOrDefault("media_name",""),b.getOrDefault("location","浉河区·人民路演示点位"),b.getOrDefault("description",""),Boolean.TRUE.equals(b.get("has_risk"))?1:0);
    activity.record("citizen","REPORT_SUBMITTED","市民 "+phone.substring(7),no,"提交治理线索："+b.getOrDefault("location","演示点位"));
    return report(no);
  }
  @GetMapping("/citizen/reports") public Map<String,Object> mine(){return pageReports("",1,50);}
  @GetMapping("/citizen/reports/{no}") public Map<String,Object> one(@PathVariable String no){return report(no);}
  @PostMapping("/citizen/reports/{no}/withdraw") public Map<String,Object> withdraw(@PathVariable String no){db.update("update citizen_report set status='withdrawn' where report_no=?",no);activity.record("citizen","REPORT_WITHDRAWN","市民",no,"撤回线索");return report(no);}
  @PostMapping("/citizen/reports/{no}/appeal") public Map<String,Object> appeal(@PathVariable String no,@RequestBody Map<String,String> b){activity.record("citizen","REPORT_APPEALED","市民",no,b.getOrDefault("description","提交申诉"));return report(no);}
  @GetMapping("/reports") public Map<String,Object> reports(@RequestParam(defaultValue="1") int page,@RequestParam(defaultValue="20") int size,@RequestParam(defaultValue="") String status){return pageReports(status,page,size);}
  @PostMapping("/reports/{no}/analyze") public Map<String,Object> analyze(@PathVariable String no){String event="EVT"+System.currentTimeMillis();String task="AI"+System.currentTimeMillis();db.update("update citizen_report set event_id=?,task_id=?,status='reviewing' where report_no=?",event,task,no);activity.record("admin","REPORT_ANALYZED","超级管理员",no,"AI预检完成，等待人工复核");return Map.of("report",report(no),"task_id",task,"event_id",event);}
  @PostMapping("/reports/{no}/accept") public Map<String,Object> accept(@PathVariable String no){
    var r=report(no);String order="GD"+LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"));String event=String.valueOf(r.get("event_id"));if(event.isBlank())event="EVT"+System.currentTimeMillis();
    db.update("update citizen_report set status='accepted',accepted_at=now(),event_id=? where report_no=?",event,no);
    db.update("insert into work_order(order_no,report_no,event_id,location_name,status,priority) values(?,?,?,?,?,?)",order,no,event,r.get("location"),"pending","高");
    activity.record("admin","REPORT_ACCEPTED","超级管理员",no,"线索已受理并生成工单 "+order);return Map.of("report",report(no),"order_no",order);
  }
  @PostMapping("/reports/{no}/reject") public Map<String,Object> reject(@PathVariable String no,@RequestBody Map<String,String>b){db.update("update citizen_report set status='rejected',reject_reason=?,rejected_at=now() where report_no=?",b.getOrDefault("reason","资料不完整"),no);activity.record("admin","REPORT_REJECTED","超级管理员",no,"线索不予受理");return Map.of("report",report(no));}
  @PostMapping("/reports/{no}/finish") public Map<String,Object> finish(@PathVariable String no,@RequestBody Map<String,String>b){db.update("update citizen_report set status='finished',public_reply=?,finished_at=now() where report_no=?",b.getOrDefault("public_reply","已完成治理"),no);activity.record("admin","REPORT_FINISHED","超级管理员",no,"治理结果已回告市民");return Map.of("report",report(no));}

  private Map<String,Object> pageReports(String status,int page,int size){String where=status.isBlank()?"":" where status=?";List<Map<String,Object>> rows=status.isBlank()?db.queryForList("select report_no from citizen_report order by id desc limit ? offset ?",size,(page-1)*size):db.queryForList("select report_no from citizen_report where status=? order by id desc limit ? offset ?",status,size,(page-1)*size);long total=status.isBlank()?db.queryForObject("select count(*) from citizen_report",Long.class):db.queryForObject("select count(*) from citizen_report where status=?",Long.class,status);return Map.of("items",rows.stream().map(x->report(String.valueOf(x.get("report_no")))).toList(),"total",total,"page",page,"size",size);}
  private Map<String,Object> report(String no){
    var r=db.queryForMap("select * from citizen_report where report_no=?",no);String status=String.valueOf(r.get("status"));Map<String,String> labels=Map.of("submitted","已提交","reviewing","复核中","accepted","已受理","finished","已完成","rejected","未受理","withdrawn","已撤回");
    Map<String,Object> out=new LinkedHashMap<>();out.put("id",r.get("id"));out.put("report_no",no);out.put("phone",r.get("phone"));out.put("kind",r.get("kind"));out.put("kind_label","video".equals(r.get("kind"))?"行为视频线索":"现场卫生照片");out.put("media_name",n(r.get("media_name")));out.put("media_path","");out.put("location",r.get("location"));out.put("description",n(r.get("description")));out.put("status",status);out.put("status_label",labels.getOrDefault(status,status));out.put("submitted_at",n(r.get("submitted_at")));for(String k:List.of("accepted_at","started_at","finished_at","rejected_at"))out.put(k,r.get(k));out.put("reject_reason",n(r.get("reject_reason")));out.put("public_reply",n(r.get("public_reply")));out.put("result_photo","");out.put("event_id",n(r.get("event_id")));out.put("task_id",n(r.get("task_id")));out.put("appeal_note","");out.put("risk_flag",Integer.valueOf(String.valueOf(r.get("risk_flag")))==1);out.put("timeline",List.of(Map.of("key","submitted","label","线索已提交","ts",n(r.get("submitted_at")))));return out;
  }
  private String n(Object v){return v==null?"":String.valueOf(v);}
}
