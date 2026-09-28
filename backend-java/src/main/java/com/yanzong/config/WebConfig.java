package com.yanzong.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {
  /**
   * CORS 白名单。
   *
   * 历史问题（缺陷 D-01）：这里曾把端口写死成 5184，而 `frontend/vite.config.ts`
   * 实际跑在 5180。Spring 对**不在白名单内的 Origin 直接返回 403**，
   * 且 `allowCredentials(true)` 时不能用 `allowedOrigins("*")` 绕过；
   * 关键点在于走 Vite 代理也躲不掉——Vite 会把原始 `Origin` 透传给后端。
   * 结果就是前端全部业务接口 403、管理员端 20 页与市民端全部无法登录。
   *
   * 修法：改用 `allowedOriginPatterns`，把本机任意端口都放行。
   * 这样 `server.port` 漂移（5180 → 5181 …）不会再导致全站不可用。
   * 注意：该写法仅适用于本地开发/演示环境，生产部署应改回精确白名单。
   */
  @Override public void addCorsMappings(CorsRegistry registry) {
    registry.addMapping("/**")
      .allowedOriginPatterns("http://127.0.0.1:*", "http://localhost:*")
      .allowedMethods("GET","POST","PATCH","PUT","DELETE","OPTIONS").allowedHeaders("*").allowCredentials(true);
  }
}
