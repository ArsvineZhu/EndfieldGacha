# Web App Module Knowledge Base

**Generated:** 2026-03-07
**Module:** Flask Web应用前端与服务

## OVERVIEW
Web界面实现，包含Flask服务、HTML模板、静态资源和压缩工具，提供完整的用户交互功能。

## STRUCTURE
```
app/
├── __init__.py          # 模块初始化
├── templates/           # HTML模板文件
│   └── index.html       # 主页面模板
├── static/              # 压缩后的CSS/JS/图片资源
│   ├── css/
│   ├── js/
│   └── images/
└── utils/
    ├── __init__.py
    └── compress.py      # 静态资源压缩和混淆工具
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| 修改页面布局 | `templates/index.html` | 主页面模板 |
| 调整样式 | `static/css/` | 修改后需运行compress.py压缩 |
| 前端交互逻辑 | `static/js/` | 修改后需运行compress.py压缩 |
| 压缩静态资源 | `utils/compress.py` | 运行`python app/utils/compress.py` |
| 服务逻辑 | `../server.py` | Flask服务主文件在根目录 |

## CONVENTIONS
- 静态资源修改后必须运行compress.py压缩，否则不会生效
- 模板使用Jinja2语法，避免硬编码文本
- 前端资源使用CDN加速，优先使用稳定的第三方库
- 响应式设计，支持桌面和移动设备

## ANTI-PATTERNS
- 不要直接修改static目录下的压缩文件，修改源文件后重新压缩
- 不要在模板中写入复杂逻辑，保持前后端分离
- 避免使用大型第三方库，保持页面加载速度
