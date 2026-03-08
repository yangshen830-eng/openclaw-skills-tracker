---
name: OpenClaw Skills 追踪
description: 追踪 OpenClaw Skills 最新动态，汇总热门/新增技能，对比已安装技能，分析安全性
emoji: 🦔
metadata:
  clawdbot:
    emoji: 🦔
    requires:
      bins: ["clawdhub", "curl", "git"]
    install:
      - id: clawdhub
        kind: node
        package: clawdhub
        label: Install ClawdHub CLI
    config:
      - key: skills_dir
        description: 已安装技能目录
        default: /opt/homebrew/lib/node_modules/openclaw-cn/skills/
      - key: output_dir
        description: 输出目录
        default: ~/openclaw-skills/
      - key: github_repo
        description: GitHub 仓库
        default: git@github.com:yangshen830-eng/openclaw-find-skills.git
---

# OpenClaw Skills 追踪

每天抓取 OpenClaw Skills 最新动态，汇总热门技能，分析安全性。

## 功能

- 追踪 ClawdHub、官方论坛、GitHub 等来源
- 汇总当日热门/新增 Skills
- 对比已安装技能，标记差异
- 安全扫描（代码来源、风险检查）
- 生成规范化 md 文档
- 推送到 GitHub

## 使用方法

```bash
# 手动运行
python3 ~/openclaw-cn/skills/openclaw-skills-tracker/openclaw-skills-tracker.py

# 查看今日汇总
cat ~/openclaw-skills/skills/$(date +%Y-%m-%d).md
```

## 数据来源

- ClawdHub: https://clawdhub.com
- OpenClaw 论坛: Discord 社区
- GitHub: 搜索 openclaw 相关技能
- 自媒体: Twitter/X, 博客等

## 安全评估标准

| 评估项 | 说明 |
|--------|------|
| ✅ 安全 | 官方/可信来源，无明显风险 |
| ⚠️ 需审查 | 社区贡献，建议人工查看代码 |
| ❌ 风险 | 未知来源或有安全隐患 |
