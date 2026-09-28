# 烟踪智治 Java 后端

Spring Boot 3 + MySQL + Redis，承载市民上报、管理受理、环卫处置和管理验收的三端闭环。

## 本机准备

1. 创建数据库：`CREATE DATABASE yanzong CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
2. 启动 MySQL 8 与 Redis 6+。
3. 按需设置环境变量 `MYSQL_USERNAME`、`MYSQL_PASSWORD`、`REDIS_PASSWORD`（默认 root / 123456，Redis 无密码）。
4. 启动：`mvn spring-boot:run`
5. 健康检查：`http://127.0.0.1:8080/healthz`

Windows 中文路径下如 `mvn spring-boot:run` 受终端编码影响，可使用已验证的启动方式：

```powershell
mvn -DskipTests package
java -jar target/governance-api-1.0.0.jar
```

首次启动自动执行 `schema.sql` 与幂等演示种子。Redis 暂时离线时核心业务仍会写入 MySQL，Redis 恢复后新动作继续发布。

## 与前端的关系（2026-09-28 起）

> ⚠️ **本后端目前不是前端默认后端，前端代理已不再引用 8080。**
>
> 前端 `vite.config.ts` 的 `/api`、`/storage`、`/ws` 三条代理**统一指向
> `backend/`（FastAPI, 8000）**，因为 8000 的接口清单完整，而本服务只实现了
> 约四成（探测 14 个前端必需接口有 11 个为 404），且没有 `/storage` 静态资源映射。
>
> 若要改回本服务，需先补齐接口清单与 `/storage` 映射，再改 `vite.config.ts`。
> CORS 白名单已从写死的 5184 改为 `allowedOriginPatterns("http://127.0.0.1:*", ...)`，
> 改完后**需要重新构建**（`mvn -DskipTests package`）才会生效。
