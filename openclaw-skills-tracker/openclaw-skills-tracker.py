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
GIT_REPO = os.path.expanduser("~/openclaw-find-skills")
INSTALLED_SKILLS_DIR = "/opt/homebrew/lib/node_modules/openclaw-cn/skills/"
GITHUB_REPO_URL = "git@github.com:yangshen830-eng/openclaw-find-skills.git"

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
        req = urllib.request.Request(
            "https://clawdhub.com/api/skills?sort=popular&limit=20",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            skills = []
            for item in data.get('skills', [])[:10]:
                skills.append({
                    'name': item.get('name', ''),
                    'slug': item.get('slug', ''),
                    'description': item.get('description', ''),
                    'source': 'ClawdHub',
                    'url': f"https://clawdhub.com/skill/{item.get('slug', '')}",
                    'author': item.get('author', 'Unknown'),
                    'install_cmd': f"clawdhub install {item.get('name', '')}"
                })
            return skills
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
    """生成个人评论"""
    name = skill.get('name', '').lower()
    desc = skill.get('description', '').lower()
    
    if 'ai' in name or 'ai' in desc:
        return "AI 相关技能，适合当前趋势。"
    elif 'tool' in name or 'utility' in name:
        return "工具类技能，提升效率。"
    elif 'api' in name or 'integration' in name:
        return "集成类技能，扩展能力。"
    elif 'search' in name or 'find' in name:
        return "搜索类技能，资源发现。"
    else:
        return "值得关注的技能。"


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
    
    print("\n✨ 完成!")


if __name__ == "__main__":
    main()
