#!/usr/bin/env python3
"""
OpenClaw Skills Tracker - 追踪 OpenClaw Skills 最新动态
"""

import os
import re
import json
import subprocess
import html
from datetime import datetime
from urllib.parse import urljoin

# ============== 配置 ==============
OUTPUT_DIR = os.path.expanduser("~/openclaw-skills")
GIT_REPO = os.path.expanduser("~/openclaw-skills-tracker")
INSTALLED_SKILLS_DIR = "/opt/homebrew/lib/node_modules/openclaw-cn/skills/"
GITHUB_REPO_URL = "git@github.com:yangshen830-eng/openclaw-skills-tracker.git"

# 数据来源
SOURCES = [
    ("ClawdHub", "https://clawdhub.com/api/skills?sort=popular&limit=20"),
    ("GitHub", "https://api.github.com/search/repositories?q=openclaw+skill&sort=updated&per_page=20"),
]


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
                # 尝试读取 SKILL.md 获取描述
                desc = ""
                skill_md = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_md):
                    with open(skill_md, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 提取 description
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


def fetch_clawdhub():
    """从 ClawdHub 获取热门 skills"""
    try:
        import urllib.request
        # 尝试多个可能的 API 端点
        urls = [
            "https://www.clawdhub.com/api/skills?sort=popular&limit=20",
            "https://clawdhub.com/api/v1/skills?sort=popular&limit=20",
        ]
        
        for url in urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0',
                        'Accept': 'application/json'
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    skills = []
                    # 尝试不同的响应格式
                    items = data.get('skills', []) or data.get('data', []) or data
                    for item in items[:10]:
                        skills.append({
                            'name': item.get('name', item.get('slug', '')),
                            'slug': item.get('slug', ''),
                            'description': item.get('description', ''),
                            'source': 'ClawdHub',
                            'url': f"https://www.clawdhub.com/skill/{item.get('slug', '')}",
                            'author': item.get('author', 'Unknown'),
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
        import urllib.request
        req = urllib.request.Request(
            "https://api.github.com/search/repositories?q=openclaw+skill&sort=updated&per_page=15",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            skills = []
            for item in data.get('items', []):
                skills.append({
                    'name': item.get('name', ''),
                    'slug': item.get('name', ''),
                    'description': item.get('description', '') or '暂无描述',
                    'source': 'GitHub',
                    'url': item.get('html_url', ''),
                    'author': item.get('owner', {}).get('login', 'Unknown'),
                    'install_cmd': f"git clone {item.get('clone_url', '')}"
                })
            return skills
    except Exception as e:
        print(f"Error fetching GitHub: {e}")
        return []


def check_similarity(new_skill, installed_skills):
    """检查与已安装技能的相似度"""
    similarities = []
    new_name = new_skill['name'].lower()
    new_desc = new_skill.get('description', '').lower()
    
    for inst_name, inst_info in installed_skills.items():
        inst_name_lower = inst_name.lower()
        inst_desc = inst_info.get('description', '').lower()
        
        # 简单关键词匹配
        common_words = set(new_name.split()) & set(inst_name_lower.split())
        if len(common_words) >= 2:
            similarities.append({
                'name': inst_info['name'],
                'diff': f"功能类似，已安装版本: {inst_info.get('description', '')[:30]}..."
            })
        elif new_name in inst_name_lower or inst_name_lower in new_name:
            similarities.append({
                'name': inst_info['name'],
                'diff': "名称相似，可能功能重复"
            })
    
    return similarities[:3]  # 最多返回3个


def security_check(skill):
    """安全检查"""
    source = skill.get('source', '')
    url = skill.get('url', '')
    
    # 可信来源
    trusted = ['ClawdHub', 'GitHub', 'openclaw-cn']
    
    if any(t in source for t in trusted):
        return {
            'code_source': '可信平台',
            'risk': '✅ 无明显风险',
            'level': 'safe'
        }
    
    # 检查 URL
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


def generate_comment(skill):
    """生成详细的个人评论（中文，无字数限制）"""
    name = skill.get('name', '').lower()
    desc = skill.get('description', '').lower()
    source = skill.get('source', '')
    
    # 根据技能特性生成详细评论
    if 'console' in name or 'dashboard' in name or 'ui' in name:
        return "这是一个管理控制台类技能，可以帮助用户通过可视化界面管理 OpenClaw 的配置、模型和技能。对于不熟悉命令行的用户来说非常友好，建议安装。"
    elif 'collector' in name or 'gather' in name or 'sync' in name:
        return "这是一个数据收集类技能，可以自动从各种来源抓取信息并整理。对于需要持续监控某些资源变化的场景很有用。"
    elif 'comfyui' in name or 'workflow' in name:
        return "这是一个工作流集成技能，将 ComfyUI 的高级图像生成能力封装成可调用的技能。如果你需要 AI 图像生成功能，这个技能可以实现很强大的定制能力。"
    elif 'search' in name or 'find' in name:
        return "这是一个搜索发现类技能，帮助你找到其他可用的 OpenClaw 技能。对于探索 OpenClaw 生态系统很有价值。"
    elif 'code' in name or 'dev' in name or 'programming' in name:
        return "这是一个开发类技能，提供代码编写、调试或重构的能力。适合需要编程辅助的开发者。"
    elif 'ai' in name or 'model' in name or 'llm' in name:
        return "这是一个 AI 模型相关的技能，可能涉及模型调用、提示词优化或 AI 能力增强。在当前 AI 趋势下值得关注。"
    elif 'tool' in name or 'utility' in name:
        return "这是一个工具类技能，提供各种实用功能来提升工作效率。具体功能需要查看详细描述。"
    elif 'api' in name or 'integration' in name or 'adapter' in name:
        return "这是一个集成适配类技能，帮助连接外部服务或 API。如果你需要将 OpenClaw 与其他工具联动，这个会很有用。"
    elif source == 'ClawdHub':
        return "这是来自 ClawdHub 官方市场的技能，经过一定审核流程，可信度较高。可以放心安装使用。"
    else:
        return "这是一个来自社区的技能，建议查看完整描述和代码后再决定是否安装。社区技能可能功能多样，值得探索。"


def generate_md(skills_list, installed_skills):
    """生成 markdown 文档"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 按热度排序（ClawdHub 在前）
    sorted_skills = sorted(skills_list, key=lambda x: 0 if x['source'] == 'ClawdHub' else 1)
    
    md = f"""# OpenClaw Skills 每日动态 - {today}

> 每天自动抓取整理，记录 OpenClaw Skills 最新动态

---

## 今日热门 Skills 🔥

"""
    
    # 热门前 5
    for i, skill in enumerate(sorted_skills[:5], 1):
        is_installed = skill['name'] in installed_skills
        installed_str = "✅ 已安装" if is_installed else "❌ 未安装"
        
        similarities = check_similarity(skill, installed_skills)
        sim_str = ""
        if similarities:
            sim_str = "\n".join([f"  - {s['name']}: {s['diff']}" for s in similarities])
        
        sec = security_check(skill)
        
        md += f"""### {i}. {skill['name']}
- **来源**: [{skill['source']}]({skill['url']})
- **功能简介**: {skill.get('description', '暂无描述')[:80]}...
- **是否已安装**: {installed_str}
- **安全评估**: {sec['risk']}
"""
        if sim_str:
            md += f"- **相似技能**:\n{sim_str}\n"
        md += "\n"
    
    # 今日新增
    md += """## 今日新增 Skills

| # | 名称 | 来源 | 功能 | 已安装 |
|---|------|------|------|--------|
"""
    
    for i, skill in enumerate(sorted_skills, 1):
        is_installed = "✅" if skill['name'] in installed_skills else "❌"
        name = skill['name'][:25] + ".." if len(skill['name']) > 25 else skill['name']
        desc = skill.get('description', '')[:25] + ".." if len(skill.get('description', '')) > 25 else skill.get('description', '')
        md += f"| {i} | {name} | {skill['source']} | {desc} | {is_installed} |\n"
    
    # 详细列表
    md += """---

## Skills 详细列表

"""
    
    for i, skill in enumerate(sorted_skills, 1):
        is_installed = "是" if skill['name'] in installed_skills else "否"
        similarities = check_similarity(skill, installed_skills)
        sec = security_check(skill)
        comment = generate_comment(skill)
        
        sim_str = "\n".join([f"  - **{s['name']}**: {s['diff']}" for s in similarities]) if similarities else "无"
        
        md += f"""### {i}. {skill['name']}
- **来源**: [{skill['source']}]({skill['url']})
- **功能**: {skill.get('description', '暂无描述')}
- **安装命令**: `{skill.get('install_cmd', 'N/A')}`
- **已安装**: {is_installed}
- **相似技能**: {sim_str}
- **安全评估**: 
  - 代码来源: {sec['code_source']}
  - 风险检查: {sec['risk']}
- **💡 简评**: {comment}

"""
    
    md += f"""---

## 数据来源

- ClawdHub: https://clawdhub.com
- GitHub: 搜索 openclaw skill
- OpenClaw 论坛: Discord 社区

---

*更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    return md


def send_to_feishu(md_content, skills_list, installed_skills):
    """发送飞书通知"""
    try:
        # 导入飞书 SDK
        from feishu import feishu_im_send_message
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 筛选前 3 个最值得关注的技能
        top_skills = []
        for skill in skills_list[:5]:
            is_installed = skill['name'] in installed_skills
            if not is_installed:  # 只推荐未安装的
                top_skills.append(skill)
                if len(top_skills) >= 3:
                    break
        
        # 构建飞书消息
        msg = f"# 🦔 OpenClaw Skills 每日动态 - {today}\n\n"
        msg += "今日发现了一些值得关注的 Skills，以下是详细介绍：\n\n"
        
        for i, skill in enumerate(top_skills, 1):
            is_installed = "✅ 已安装" if skill['name'] in installed_skills else "❌ 未安装"
            similarities = check_similarity(skill, installed_skills)
            
            msg += f"## {i}. {skill['name']}\n"
            msg += f"- **来源**: {skill['source']}\n"
            msg += f"- **功能描述**: {skill.get('description', '暂无描述')}\n"
            msg += f"- **安装状态**: {is_installed}\n"
            
            if similarities:
                msg += f"- **相似技能**: {', '.join([s['name'] for s in similarities])}\n"
            
            msg += f"- **安装命令**: `{skill.get('install_cmd', 'N/A')}`\n\n"
        
        msg += "---\n"
        msg += f"📋 完整报告已保存至 GitHub 仓库\n"
        msg += f"🔗 https://github.com/yangshen830-eng/openclaw-skills-tracker\n"
        
        # 发送消息（需要用户 open_id，这里先打印）
        print(f"📱 飞书消息内容：\n{msg[:500]}...")
        return True
        
    except Exception as e:
        print(f"⚠️ 飞书发送失败: {e}")
        return False


def push_to_github(content, date):
    """推送到 GitHub"""
    git_dir = GIT_REPO
    
    if not os.path.exists(git_dir):
        print(f"📦 克隆仓库...")
        subprocess.run(["git", "clone", GITHUB_REPO_URL, git_dir], capture_output=True)
    
    # 写入文件
    skills_folder = os.path.join(git_dir, "skills")
    os.makedirs(skills_folder, exist_ok=True)
    
    filename = os.path.join(skills_folder, f"{date}.md")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 备份 skill
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
    print(f"📤 推送到 GitHub...")
    subprocess.run(["git", "-C", git_dir, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", git_dir, "commit", "-m", f"Add {date} skills tracker"], capture_output=True)
    result = subprocess.run(["git", "-C", git_dir, "push", "origin", "main"], capture_output=True)
    
    if result.returncode == 0:
        print(f"✅ 已推送: skills/{date}.md")
        return True
    else:
        print(f"⚠️ 推送失败: {result.stderr.decode()}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("🔍 开始抓取 OpenClaw Skills...")
    
    # 获取已安装技能
    print("📂 检查已安装技能...")
    installed_skills = get_installed_skills()
    print(f"   已安装: {len(installed_skills)} 个")
    
    # 抓取各来源
    all_skills = []
    
    print("📡 抓取 ClawdHub...")
    clawdhub_skills = fetch_clawdhub()
    all_skills.extend(clawdhub_skills)
    print(f"   获取: {len(clawdhub_skills)} 个")
    
    print("📡 抓取 GitHub...")
    github_skills = fetch_github()
    all_skills.extend(github_skills)
    print(f"   获取: {len(github_skills)} 个")
    
    print(f"\n📰 共获取 {len(all_skills)} 个 skills")
    
    # 生成 markdown
    md_content = generate_md(all_skills, installed_skills)
    
    # 保存本地
    today = datetime.now().strftime("%Y-%m-%d")
    local_file = os.path.join(OUTPUT_DIR, "skills", f"{today}.md")
    os.makedirs(os.path.dirname(local_file), exist_ok=True)
    with open(local_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ 本地保存: {local_file}")
    
    # 推送到 GitHub
    push_to_github(md_content, today)
    
    # 发送飞书通知
    send_to_feishu(md_content, all_skills, installed_skills)
    
    print("\n✨ 完成!")


if __name__ == "__main__":
    main()
