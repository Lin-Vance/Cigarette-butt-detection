package com.yanzong.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class ActivityService {
  private final JdbcTemplate db; private final StringRedisTemplate redis; private final ObjectMapper json;
  public ActivityService(JdbcTemplate db, StringRedisTemplate redis, ObjectMapper json) { this.db=db;this.redis=redis;this.json=json; }
  public void record(String source,String action,String actor,String target,String detail) {
    db.update("insert into activity_log(source,action,actor,target,detail) values(?,?,?,?,?)",source,action,actor,target,detail);
    try {
      String body=json.writeValueAsString(Map.of("source",source,"action",action,"actor",actor,"target",target,"detail",detail,"created_at",LocalDateTime.now().toString()));
      redis.opsForList().leftPush("yz:activity:latest",body); redis.opsForList().trim("yz:activity:latest",0,99);
      redis.convertAndSend("yz:activity",body);
    } catch (Exception ignored) { /* Redis 临时离线不影响核心业务落库 */ }
  }
  public List<Map<String,Object>> latest(int limit) {
    return db.queryForList("select id,source,action,actor,target,detail,date_format(created_at,'%Y-%m-%d %H:%i:%s') created_at from activity_log order by id desc limit ?",Math.min(limit,50));
  }
}
