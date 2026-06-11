# 魔镜 Mojing API
颜值评分后端服务，部署于 Railway

## 部署步骤
1. Fork 此仓库
2. 在 Railway 创建项目 → 连接 GitHub → 选择此仓库
3. 设置环境变量：
   - `BAIDU_API_KEY` = 你的百度云API Key
   - `BAIDU_SECRET_KEY` = 你的百度云Secret Key
4. 部署完成，获得公网URL

## API 端点
- `GET /api/status` - 服务状态
- `POST /api/grade` - 颜值评分（body: `{"image": "base64..."}`)
- `GET /api/tts?text=xxx` - 文字转语音
