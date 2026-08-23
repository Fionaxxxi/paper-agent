# PaperAgent 发布核验清单

核验日期：2026-08-21

## 本轮结论

最终发布所需的页面、启动入口、Docker/CI 配置和演示材料已完成核验。未重复运行 422 项完整回归；该套件在 PDF Visual v2 完成后已取得 422/422 通过，本轮只运行与发布面直接相关的最小测试。

## 核验结果

| 核验项 | 作用 | 通过代表什么 | 失败代表什么 | 本轮结果 |
|---|---|---|---|---|
| `/health` 冷启动检查 | 验证指定 Conda 环境能启动 FastAPI | 依赖可导入、应用可初始化、服务可响应 | 安装、配置或应用初始化存在问题 | 通过，HTTP 200 |
| 首页真实浏览器检查 | 验证页面资源与核心入口 | 首页、认证、论文库和研究表单可见 | 静态资源或前端初始化失败 | 通过 |
| 零 API Research 示例 | 验证稳定演示闭环 | 计划、波次、证据、质量闸门和结论均可展示 | 前端状态渲染或示例契约损坏 | 通过 |
| 零 API PDF 示例 | 验证视觉能力展示 | 自动选页、视觉任务、结构化契约与 Grounding 可见 | PDF Visual v2 前端契约损坏 | 通过 |
| `tests/test_demo_page.py` | 回归 FastAPI 首页和演示页结构 | 页面入口及关键能力面板仍存在 | API 路由或 HTML/JS 结构回归 | 通过 |
| `tests/test_deployment_config.py` | 检查容器和 CI 安全配置 | 非 root、健康检查、敏感文件排除、离线 CI 均已配置 | 发布配置不完整或存在泄露风险 | 通过 |
| `node --check app/static/app.js` | 检查浏览器脚本语法 | JavaScript 可被运行时解析 | 页面会在加载阶段出现语法错误 | 通过 |
| `docker compose config --quiet` | 校验 Compose 结构 | 服务、端口、卷和健康检查声明有效 | Compose 无法启动或配置字段错误 | 通过；本机 Docker 配置文件有权限警告，不影响结构校验 |

本轮定向自动化结果：13 passed，0 failed，耗时 3.36 秒；所有测试均为离线测试，LLM 调用 0 次。

## 已有关键基线

| 基线 | 结果 | 含义 |
|---|---:|---|
| 完整离线回归 | 422/422 | 当前主工作流、工具、RAG、记忆、个人库、视觉与报告导出的确定性回归全部通过 |
| LLM 核心正式评测 | 29/30，96.67% | 同一轮 30 个结构化真实问题经修复导出并按落盘原始响应复核后，29 个达到能力检查要求，供应商失败 0 |
| PDF Vision 在线冒烟 | 通过 | GraphRAG 论文第 4 页完成 qwen3.5-ocr 视觉解析、主模型综合、结构化契约和 Grounding |

## 发布前仍需人工确认

- GitHub Actions 最近一次远端运行是否为绿色；本地已核验工作流语法与所覆盖的定向测试。
- 在一台没有项目缓存的新机器上按 README 从克隆、安装到启动完整走一遍。当前指定 Conda 环境冷启动已经通过，但不等同于全新机器验证。
- 确认仓库 Settings 中没有提交或暴露真实 API Key，`.env` 只保留在本地。

## 演示素材

- `docs/screenshots/01-home.png`：研究入口、登录和个人论文库。
- `docs/screenshots/02-research-run.png`：Research Agent 研究输出。
- `docs/screenshots/03-pdf-vision.png`：PDF 图表理解与 Grounding。
- `docs/INTERVIEW_GUIDE.md`：三分钟讲解、简历描述和常见追问。
