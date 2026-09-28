package com.yanzong.controller;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@RestController @RequestMapping("/api/v1/auth")
public class AuthController {
  private final JdbcTemplate db; private final StringRedisTemplate redis; private final Map<String,String> fallback=new ConcurrentHashMap<>();
  public AuthController(JdbcTemplate db,StringRedisTemplate redis){this.db=db;this.redis=redis;}
  @PostMapping("/login") public ResponseEntity<?> login(@RequestBody Map<String,String> body){
    var rows=db.queryForList("select * from yz_user where username=? and password=? and enabled=1",body.getOrDefault("username",""),body.getOrDefault("password",""));
    if(rows.isEmpty()) return ResponseEntity.status(401).body(Map.of("error_code","AUTH_INVALID","message","账号或密码错误"));
    var u=rows.get(0); String token=UUID.randomUUID().toString(); saveToken(token,String.valueOf(u.get("username")));
    return ResponseEntity.ok(Map.of("access_token",token,"token_type","bearer","expires_in",7200,"user",user(u)));
  }
  @PostMapping("/citizen/login") public ResponseEntity<?> citizen(@RequestBody Map<String,String> body){
    String phone=body.getOrDefault("phone","");
    if(!phone.matches("1\\d{10}") || !"123456".equals(body.get("code"))) return ResponseEntity.status(401).body(Map.of("error_code","CITIZEN_AUTH_INVALID","message","手机号或验证码错误，演示验证码为 123456"));
    String token=UUID.randomUUID().toString(); saveToken(token,phone);
    return ResponseEntity.ok(Map.of("access_token",token,"profile",Map.of("phone",phone,"displayName","市民 "+phone.substring(7),"district","浉河区","contribution",36)));
  }
  @PostMapping("/logout") public Map<String,String> logout(){return Map.of("status","ok");}
  private void saveToken(String token,String who){fallback.put(token,who);try{redis.opsForValue().set("yz:token:"+token,who,Duration.ofHours(2));}catch(Exception ignored){}}
  private Map<String,Object> user(Map<String,Object> u){
    String role=String.valueOf(u.get("role")); String label=Map.of("admin","超级管理员","manager","治理主管","worker","环卫工人","ai_dev","算法工程师").getOrDefault(role,role);
    return Map.of("id",u.get("id"),"username",u.get("username"),"real_name",u.get("real_name"),"role",role,"role_label",label,"phone",String.valueOf(u.get("phone")),"enabled",true,"allowed_pages",List.of("*"),"created_at",String.valueOf(u.get("created_at")));
  }
}
