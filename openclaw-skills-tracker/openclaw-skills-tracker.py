#!/usr/bin/env python3
"""
OpenClaw Skills Tracker - 追踪 OpenClaw Skills 最新动态
功能：
1. 多源订阅 (ClawdHub, GitHub, Discord, Twitter)
2. 热门/最新 Skills 汇总
3. 已安装对比 + 相似技能检测
4. 安全扫描
5. 趋势分析
6. 分类标签
7. 依赖检查
8. 下载量/评分
"""

import os
import re
import json
import subprocess
import html
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin
from collections import Counter

# ============== 配置 ==============
OUTPUT_DIR = os.path.expanduser("~/openclaw-skills")
GIT_REPO = os.path.expanduser("~/openclaw-skills-tracker")
INSTALLED_SKILLS_DIR = "/opt/homebrew/lib/node_modules/openclaw-cn/skills/"
GITHUB_REPO_URL = "git@github.com:yangshen830-eng/openclaw-skills-tracker.git"

# 分类标签
CATEGORIES = {
    "ai": ["ai", "gpt", "llm", "model", "claude", "openai", "anthropic"],
    "工具": ["tool", "utility", "cli", "command"],
    "集成": ["integration", "adapter", "connector", "plugin", "channel"],
    "自动化": ["automation", "auto", "workflow", "agent", "playwright"],
    "图像": ["image", "comfyui", "绘画", "生成图"],
    "视频": ["video", "短视频", "reel", "youtube"],
    "通信": ["feishu", "telegram", "discord", "slack", "whatsapp", "message"],
    "数据": ["data", "collector", "sync", "backup"],
    "开发": ["code", "dev", "programming", "git", "github"],
    "营销": ["marketing", "销售", "sales"],
}

# 依赖检查（常见依赖）
COMMON_DEPENDENCIES = {
    "node": ["node", "npm"],
    "python": ["python3", "pip3"],
    "go": ["go"],
    "git": ["git"],
    "curl": ["curl"],
}


# ============== 工具函数 ==============
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = ' '.join(text.split())
    return text


def get_installed_skills():
    """获取已安装的技能列表"""
    installed = {}
    try:
        for item in os.listdir(INSTALLED_SKILLS_DIR):
            skill_path = os.path.join(INSTALLED_SKILLS_DIR, item)
            if os.path.isdir(skill_path):
                desc = ""
                skill_md = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_md):
                    with open(skill_md, 'r', encoding='utf-8') as f:
                        content = f.read()
                        match = re.search(r'description:\s*(.+)', content)
                        if match:
                            desc = match.group(1).strip()
                installed[item] = {
                    'name': item,
                    'description': desc,
                    'path': skill_path
                }
    except Exception as e:
        print(f"Error reading installed skills: {e}")
    return installed


def get_category(name, description):
    """获取技能分类标签"""
    text = (name + " " + description).lower()
    tags = []
    for cat, keywords in CATEGORIES.items():
        if any(k in text for k in keywords):
            tags.append(cat)
    return tags if tags else ["其他"]


def check_dependencies(skill_info):
    """检查技能依赖"""
    deps = []
    text = (skill_info.get('name', '') + " " + skill_info.get('description', '')).lower()
    
    for dep_type, commands in COMMON_DEPENDENCIES.items():
        if any(c in text for c in commands):
            deps.append(dep_type)
    
    return deps if deps else ["无特殊依赖"]


def fetch_clawdhub():
    """从 ClawdHub 获取热门 skills（含下载量）"""
    try:
        # 尝试 API
        urls = [
            "https://www.clawdhub.com/api/skills?sort=popular&limit=20",
            "https://clawdhub.com/api/v1/skills?sort=popular&limit=20",
        ]
        
        for url in urls:
            try:
                resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if resp.status_code == 200:
                    data = resp.json()
                    skills = []
                    items = data.get('skills', []) or data.get('data', []) or []
                    for item in items[:10]:
                        skills.append({
                            'name': item.get('name', item.get('slug', '')),
                            'slug': item.get('slug', ''),
                            'description': item.get('description', ''),
                            'source': 'ClawdHub',
                            'url': f"https://www.clawdhub.com/skill/{item.get('slug', '')}",
                            'author': item.get('author', 'Unknown'),
                            'downloads': item.get('downloads', 0) or item.get('installs', 0),
                            'rating': item.get('rating', 0),
                            'install_cmd': f"clawdhub install {item.get('name', '')}"
                        })
                    return skills
            except:
                continue
        return []
    except Exception as e:
        print(f"Error fetching ClawdHub: {e}")
        return []


def fetch_github():
    """从 GitHub 搜索 openclaw skills"""
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories?q=openclaw+skill&sort=updated&per_page=20",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if resp.status_code == 200:
            data = resp.json()
            skills = []
            for item in data.get('items', []):
                skills.append({
                    'name': item.get('name', ''),
                    'slug': item.get('name', ''),
                    'description': item.get('description', '') or '暂无描述',
                    'source': 'GitHub',
                    'url': item.get('html_url', ''),
                    'author': item.get('owner', {}).get('login', 'Unknown'),
                    'stars': item.get('stargazers_count', 0),
                    'forks': item.get('forks_count', 0),
                    'install_cmd': f"git clone {item.get('clone_url', '')}"
                })
            return skills
        return []
    except Exception as e:
        print(f"Error fetching GitHub: {e}")
        return []


def fetch_discord():
    """模拟 Discord 热门推荐（实际需要 API）"""
    # 这里可以接入 Discord API，暂时返回空
    return []


def check_similarity(new_skill, installed_skills):
    """检测相似技能（增强版）"""
    similarities = []
    new_name = new_skill['name'].lower()
    new_desc = new_skill.get('description', '').lower()
    new_tags = new_skill.get('tags', [])
    
    for inst_name, inst_info in installed_skills.items():
        inst_name_lower = inst_name.lower()
        inst_desc = inst_info.get('description', '').lower()
        
        score = 0
        
        # 精确匹配
        if new_name == inst_name_lower:
            score = 100
        # 名称相似
        elif new_name in inst_name_lower or inst_name_lower in new_name:
            score = 80
        # 共同关键词
        common = set(new_name.split()) & set(inst_name_lower.split())
        if len(common) >= 2:
            score += 30
        # 标签重叠
        if inst_info.get('tags'):
            overlap = set(new_tags) & set(inst_info['tags'])
            if overlap:
                score += 20
        
        if score >= 30:
            diff = "功能类似，已安装"
            if score >= 80:
                diff = "名称高度相似，可能功能重复"
            similarities.append({
                'name': inst_info['name'],
                'score': score,
                'diff': diff
            })
    
    return sorted(similarities, key=lambda x: x['score'], reverse=True)[:3]


def security_check(skill):
    """安全检查"""
    source = skill.get('source', '')
    url = skill.get('url', '')
    
    trusted = ['ClawdHub', 'GitHub', 'openclaw-cn']
    
    if any(t in source for t in trusted):
        return {
            'code_source': '可信平台',
            'risk': '✅ 无明显风险',
            'level': 'safe'
        }
    
    if 'github.com' in url:
        return {
            'code_source': 'GitHub 开源',
            'risk': '⚠️ 建议审查代码',
            'level': 'warning'
        }
    
    return {
        'code_source': '未知来源',
        'risk': '⚠️ 需人工审查',
        'level': 'review'
    }


def analyze_trend(skills_list, history_dir):
    """分析趋势（对比历史数据）"""
    trend = {"new": [], "up": [], "stable": []}
    
    # 读取历史数据
    if os.path.exists(history_dir):
        past_skills = set()
        for f in os.listdir(history_dir):
            if f.endswith('.md'):
                try:
                    date = f.replace('.md', '')
                    past_date = datetime.strptime(date, '%Y-%m-%d')
                    if (datetime.now() - past_date).days <= 7:
                        with open(os.path.join(history_dir, f), 'r') as fp:
                            content = fp.read()
                            # 简单提取名称
                            for line in content.split('\n'):
                                if line.startswith('### '):
                                    name = line.replace('### ', '').strip()
                                    past_skills.add(name.lower())
                except:
                    continue
        
        # 分类
        current_names = set(s['name'].lower() for s in skills_list)
        
        for skill in skills_list:
            if skill['name'].lower() not in past_skills:
                trend['new'].append(skill['name'])
        
        trend['stable'] = list(current_names - set(trend['new']))
    
    return trend


def generate_comment(skill):
    """生成详细的个人评论"""
    name = skill.get('name', '').lower()
    desc = skill.get('description', '').lower()
    source = skill.get('source', '')
    tags = skill.get('tags', [])
    downloads = skill.get('downloads', 0)
    stars = skill.get('stars', 0)
    
    # 热门指标
    hot_indicator = ""
    if downloads and downloads > 1000:
        hot_indicator = f"该技能在 ClawdHub 上已有超过 {downloads} 次安装，热度很高。"
    elif stars and stars > 100:
        hot_indicator = f"在 GitHub 上有 {stars} 颗星，社区认可度高。"
    
    # 功能评论
    if 'console' in name or 'dashboard' in name or 'ui' in name:
        return f"这是一个管理控制台类技能，可以帮助用户通过可视化界面管理 OpenClaw 的配置、模型和技能。对于不熟悉命令行的用户来说非常友好，建议安装。{hot_indicator}"
    elif 'collector' in name or 'gather' in name:
        return f"这是一个数据收集类技能，可以自动从各种来源抓取信息并整理。对于需要持续监控某些资源变化的场景很有用。{hot_indicator}"
    elif 'comfyui' in name or 'workflow' in name:
        return f"这是一个工作流集成技能，将 ComfyUI 的高级图像生成能力封装成可调用的技能。如果你需要 AI 图像生成功能，这个技能可以实现很强大的定制能力。{hot_indicator}"
    elif 'search' in name or 'find' in name:
        return f"这是一个搜索发现类技能，帮助你找到其他可用的 OpenClaw 技能。对于探索 OpenClaw 生态系统很有价值。{hot_indicator}"
    elif 'code' in name or 'dev' in name:
        return f"这是一个开发类技能，提供代码编写、调试或重构的能力。适合需要编程辅助的开发者。{hot_indicator}"
    elif 'playwright' in name or 'automation' in name:
        return f"这是一个浏览器自动化技能，可以帮你自动完成网页操作、测试等任务。功能强大，适合高级用户。{hot_indicator}"
    elif 'feishu' in name or '飞书' in name:
        return f"这是一个飞书集成技能，让你的 Agent 能够在飞书平台工作。如果你主要使用飞书沟通，这个技能非常实用。{hot_indicator}"
    elif source == 'ClawdHub':
        return f"这是来自 ClawdHub 官方市场的技能，经过一定审核流程，可信度较高。可以放心安装使用。{hot_indicator}"
    else:
        return f"这是一个来自社区的技能，建议查看完整描述和代码后再决定是否安装。社区技能可能功能多样，值得探索。{hot_indicator}"


def generate_md(skills_list, installed_skills, trend):
    """生成 markdown 文档"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 按热度排序
    sorted_skills = sorted(skills_list, 
        key=lambda x: (x.get('downloads', 0), x.get('stars', 0)), reverse=True)
    
    md = f"""# OpenClaw Skills 每日动态 - {today}

> 每天自动抓取整理，记录 OpenClaw Skills 最新动态

---

## 📊 今日概览

- **新增 Skills**: {len(trend.get('new', []))} 个
- **持续热门**: {len(trend.get('stable', []))} 个
- **数据来源**: ClawdHub, GitHub

"""
    
    # 新增技能
    if trend.get('new'):
        md += "## 🆕 今日新增 Skills\n\n"
        for name in trend['new'][:5]:
            md += f"- **{name}**\n"
        md += "\n"
    
    # 热门技能
    md += """## 🔥 今日热门 Skills

"""
    
    for i, skill in enumerate(sorted_skills[:5], 1):
        is_installed = skill['name'] in installed_skills
        installed_str = "✅ 已安装" if is_installed else "❌ 未安装"
        
        similarities = check_similarity(skill, installed_skills)
        sim_str = "\n".join([f"  - **{s['name']}**: {s['diff']}" for s in similarities]) if similarities else "无"
        
        sec = security_check(skill)
        tags = skill.get('tags', [])
        deps = skill.get('dependencies', [])
        
        # 热门指标
        metrics = []
        if skill.get('downloads'):
            metrics.append(f"📥 {skill['downloads']} 次安装")
        if skill.get('stars'):
            metrics.append(f"⭐ {skill['stars']} stars")
        metrics_str = " | ".join(metrics) if metrics else "暂无数据"
        
        md += f"""### {i}. {skill['name']}
- **来源**: [{skill['source']}]({skill['url']})
- **分类标签**: {', '.join(tags) if tags else '其他'}
- **功能简介**: {skill.get('description', '暂无描述')}
- **热门指标**: {metrics_str}
- **是否已安装**: {installed_str}
- **依赖**: {', '.join(deps) if deps else '无特殊依赖'}
- **安全评估**: {sec['risk']}
"""
        if sim_str != "无":
            md += f"- **相似技能**:\n{sim_str}\n"
        md += f"- **💡 简评**: {generate_comment(skill)}\n\n"
    
    # 完整列表
    md += """## 📋 完整 Skills 列表

| # | 名称 | 分类 | 来源 | 安装量 | 已安装 | 依赖 |
|---|------|------|------|--------|--------|------|
"""
    
    for i, skill in enumerate(sorted_skills, 1):
        is_installed = "✅" if skill['name'] in installed_skills else "❌"
        name = skill['name'][:20] + ".." if len(skill['name']) > 20 else skill['name']
        cat = (', '.join(skill.get('tags', ['其他'])[:2]))[:15]
        source = skill['source'][:8]
        downloads = skill.get('downloads', skill.get('stars', 0))
        deps = ', '.join(skill.get('dependencies', ['无'])[:2])[:12]
        md += f"| {i} | {name} | {cat} | {source} | {downloads} | {is_installed} | {deps} |\n"
    
    # 已安装技能
    md += """---

## ✅ 你已安装的 Skills

"""
    for name, info in installed_skills.items():
        desc = info.get('description', '')[:40]
        md += f"- **{name}**: {desc}...\n"
    
    md += f"""

---

*更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*  
*数据来源: ClawdHub, GitHub, (Discord 待接入)*
"""
    
    return md


def send_to_feishu(skills_list, installed_skills, trend):
    """发送飞书通知（完整版）"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    msg = f"# 🦔 OpenClaw Skills 每日动态 - {today}\n\n"
    msg += f"今日共发现 **{len(skills_list)}** 个 Skills，以下是完整报告：\n\n"
    
    # 概览
    msg += f"## 📊 今日概览\n"
    msg += f"- 🆕 新增 Skills: **{len(trend.get('new', []))}** 个\n"
    msg += f"- ✅ 已安装: **{len(installed_skills)}** 个\n\n"
    
    # 新增
    if trend.get('new'):
        msg += "## 🆕 今日新增\n\n"
        for name in trend['new'][:10]:
            msg += f"- {name}\n"
        msg += "\n"
    
    # 热门
    sorted_skills = sorted(skills_list, 
        key=lambda x: (x.get('downloads', 0), x.get('stars', 0)), reverse=True)
    
    msg += "## 🔥 热门 Skills 详细列表\n\n"
    
    for i, skill in enumerate(sorted_skills, 1):
        is_installed = "✅ 已安装" if skill['name'] in installed_skills else "❌ 未安装"
        similarities = check_similarity(skill, installed_skills)
        
        # 热门指标
        metrics = []
        if skill.get('downloads'):
            metrics.append(f"{skill['downloads']}次安装")
        if skill.get('stars'):
            metrics.append(f"{skill['stars']}⭐")
        metrics_str = " | ".join(metrics) if metrics else "暂无数据"
        
        tags = ', '.join(skill.get('tags', ['其他']))
        deps = ', '.join(skill.get('dependencies', ['无']))
        
        msg += f"### {i}. {skill['name']}\n"
        msg += f"- **分类**: {tags}\n"
        msg += f"- **功能**: {skill.get('description', '暂无描述')}\n"
        msg += f"- **热门度**: {metrics_str}\n"
        msg += f"- **状态**: {is_installed}\n"
        msg += f"- **依赖**: {deps}\n"
        
        if similarities:
            sim_names = ', '.join([s['name'] for s in similarities[:2]])
            msg += f"- **相似**: {sim_names}\n"
        
        msg += f"- **安装**: `{skill.get('install_cmd', 'N/A')}`\n\n"
    
    # 已安装
    msg += "## ✅ 你已安装的 Skills\n\n"
    for name, info in list(installed_skills.items())[:20]:
        desc = info.get('description', '')[:30]
        msg += f"- **{name}**: {desc}...\n"
    
    if len(installed_skills) > 20:
        msg += f"- ...还有 {len(installed_skills) - 20} 个\n"
    
    msg += f"\n---\n📋 完整报告: https://github.com/yangshen830-eng/openclaw-skills-tracker"
    
    return msg


def push_to_github(content, date):
    """推送到 GitHub"""
    git_dir = GIT_REPO
    
    if not os.path.exists(git_dir):
        subprocess.run(["git", "clone", GITHUB_REPO_URL, git_dir], capture_output=True)
    
    # Skills 报告
    skills_folder = os.path.join(git_dir, "skills")
    os.makedirs(skills_folder, exist_ok=True)
    with open(os.path.join(skills_folder, f"{date}.md"), 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Skill 源码
    skill_backup = os.path.join(git_dir, "openclaw-skills-tracker")
    skill_src = os.path.expanduser("~/openclaw-cn/skills/openclaw-skills-tracker")
    if os.path.exists(skill_src):
        os.makedirs(skill_backup, exist_ok=True)
        for f in os.listdir(skill_src):
            src_file = os.path.join(skill_src, f)
            if os.path.isfile(src_file):
                with open(src_file, 'r') as sf:
                    with open(os.path.join(skill_backup, f), 'w') as df:
                        df.write(sf.read())
    
    # Git 推送
    subprocess.run(["git", "-C", git_dir, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", git_dir, "commit", "-m", f"Update {date} skills tracker"], capture_output=True)
    result = subprocess.run(["git", "-C", git_dir, "push", "origin", "main"], capture_output=True)
    
    if result.returncode == 0:
        print(f"✅ 已推送: skills/{date}.md")
        return True
    else:
        print(f"⚠️ 推送失败")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("🔍 开始抓取 OpenClaw Skills...")
    
    # 已安装
    print("📂 检查已安装技能...")
    installed_skills = get_installed_skills()
    print(f"   已安装: {len(installed_skills)} 个")
    
    # 抓取
    all_skills = []
    
    print("📡 抓取 ClawdHub...")
    clawdhub_skills = fetch_clawdhub()
    for s in clawdhub_skills:
        s['tags'] = get_category(s['name'], s.get('description', ''))
        s['dependencies'] = check_dependencies(s)
    all_skills.extend(clawdhub_skills)
    print(f"   获取: {len(clawdhub_skills)} 个")
    
    print("📡 抓取 GitHub...")
    github_skills = fetch_github()
    for s in github_skills:
        s['tags'] = get_category(s['name'], s.get('description', ''))
        s['dependencies'] = check_dependencies(s)
    all_skills.extend(github_skills)
    print(f"   获取: {len(github_skills)} 个")
    
    # 趋势分析
    history_dir = os.path.join(OUTPUT_DIR, "skills")
    trend = analyze_trend(all_skills, history_dir)
    
    print(f"\n📰 共获取 {len(all_skills)} 个 skills")
    print(f"🆕 新增: {len(trend.get('new', []))} 个")
    
    # 生成
    md_content = generate_md(all_skills, installed_skills, trend)
    
    # 保存
    today = datetime.now().strftime("%Y-%m-%d")
    local_file = os.path.join(OUTPUT_DIR, "skills", f"{today}.md")
    os.makedirs(os.path.dirname(local_file), exist_ok=True)
    with open(local_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ 本地保存: {local_file}")
    
    # GitHub
    push_to_github(md_content, today)
    
    # 飞书（完整版）
    feishu_msg = send_to_feishu(all_skills, installed_skills, trend)
    print(f"\n📱 飞书消息长度: {len(feishu_msg)} 字符")
    print("💡 飞书消息已准备好，可通过 feishu_im_send_message 工具发送")
    
    print("\n✨ 完成!")


if __name__ == "__main__":
    main()
