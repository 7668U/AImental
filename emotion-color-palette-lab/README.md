# 情绪调色盘初测版

这是一个独立的小实验模块，用来验证“选色 -> 混合 -> HEPAI 命名 -> HEPAI Images API 无字背景 -> Canvas 色卡导出”的初测流程。

## 目录

```text
emotion-color-palette-lab/
  backend/             FastAPI API
  frontend/            无构建静态页面与 Canvas 渲染
  generated/           HEPAI 生成背景输出
```

## 运行

```powershell
cd C:\Users\29537\OneDrive\Desktop\feelyourself\emotion-color-palette-lab
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8756 --reload
```

然后打开：

```text
http://127.0.0.1:8756
```

## 环境变量

本模块从 `emotion-color-palette-lab/.env` 读取 HEPAI 配置。

```env
HEPAI_API_KEY=...
HEPAI_BASE_URL=https://aiapi.ihep.ac.cn/apiv2
HEPAI_MODEL=hepai/deepseek-v4-pro
HEPAI_IMAGE_MODEL=openai/gpt-image-2
HEPAI_IMAGE_SIZE=1088x1456
HEPAI_IMAGE_QUALITY=low
```

如果 HEPAI 命名失败，会返回本地兜底颜色名。生图现在直接使用 HEPAI Images API `openai/gpt-image-2`，只调用 `/images/generations`，不使用 Responses API。

默认请求 1088x1456 的 3:4 竖图，用于贴合 1080x1440 Canvas，避免背景被明显裁切。

## 接口

- `GET /api/colors`：返回 100 个预设颜色
- `POST /api/generate-card-data`：混色、命名，并按需生成背景
- `POST /api/regenerate-background`：只重新生成背景
- `GET /api/health`：查看 HEPAI 配置状态
