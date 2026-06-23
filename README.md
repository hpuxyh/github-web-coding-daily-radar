# GitHub 每日好项目雷达

这个项目复制自 `github-web-coding-radar`，页面外观基本保持一致，新的重点是“按天留档、按天查看”。

它每天从公开 GitHub 项目里抓取 AI 编程、Agent、MCP、网页编辑器、低代码、开发者工具等方向的项目，生成中文榜单和小红书草稿，并把每一天的数据保存成独立快照。

## 在线页面

主页面：

```text
https://hpuxyh.github.io/github-web-coding-daily-radar/radar.html
```

页面里可以切换日期。默认读取 `public/daily/index.json` 里的最新快照；如果外部 JSON 没加载成功，会回退到 `radar.html` 内嵌的数据。

## 今天跑一遍

```bash
python3 scripts/github_xhs_daily.py run
python3 scripts/github_xhs_daily.py embed
npm run build
```

生成结果会写到：

- `output/latest.md`
- `output/latest.json`
- `output/YYYY-MM-DD/github-web-coding-daily.md`
- `output/YYYY-MM-DD/repos.json`
- `public/daily/YYYY-MM-DD.json`
- `public/daily/latest.json`
- `public/daily/index.json`

其中 `public/daily/` 会被提交到 GitHub，用来支撑网页上的日期切换。

## 自动刷新

每日刷新逻辑已经写好，模板放在 `docs/workflows/`：

- `docs/workflows/daily-radar.yml`
- `docs/workflows/deploy-pages.yml`

要在 GitHub 上真正启用 Actions，需要把这两个文件复制到 `.github/workflows/`。注意：GitHub 要求创建或更新 workflow 文件的 token 带 `workflow` scope；普通 Git 凭据可能会被拒绝。

`daily-radar.yml` 会每天 01:10 UTC 运行一次，也就是北京时间 09:10 左右：

1. 抓取当天 GitHub 项目。
2. 写入当天 JSON 快照。
3. 更新 `radar.html` 和 `public/radar.html` 里的内嵌数据。
4. 构建检查。
5. 如果有变化，提交回 `main`。

`deploy-pages.yml` 会在 `main` 更新后部署 GitHub Pages。当前也可以直接把 `dist/` 推到 `gh-pages` 分支发布静态页面。

## 配置

主要配置文件是 `config/github_xhs_config.json`：

- `all_time_queries`：长期高收藏项目。
- `rising_queries`：近期增长项目。
- `frontier_queries`：AI 编程、Agent、MCP 等前沿项目。
- `product_queries`：可试用、可改造、可做内容选题的产品项目。
- `expert_sources`：公开人物/专家观察源，只读公开 GitHub star、公开链接和手工配置的项目引用。

如果想提高 GitHub API 抓取额度，可以在仓库 Secrets 里配置 `RADAR_GITHUB_TOKEN`；没配置时，GitHub Actions 会用默认 `github.token`。

## 本地预览

```bash
npm install
npm run dev
```

打开 Vite 提示的本地地址，再进入 `/radar.html`。

## 数据口径

候选项目来自 GitHub 搜索、仓库主题、README、更新记录和可配置的公开人物观察源。系统会生成四个互斥榜单：

- 热度榜：看最近涨星、项目年龄、更新活跃和热点方向。
- 大家都在用：看 fork、README、截图示例、官网和持续维护。
- 高收藏：看累计 stars、forks 和长期认可度。
- 参与讨论：看 issue、fork、最近更新和公开协作痕迹。

同一个项目只进入最匹配的一个榜单，避免每天页面里重复出现。
