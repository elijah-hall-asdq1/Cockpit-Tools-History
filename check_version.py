
import requests
import json
import os
import sys
import datetime

# 配置
REPO_OWNER = "jlcodes99"
REPO_NAME = "cockpit-tools"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def get_headers():
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Antigravity-Release-Monitor"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def utc_to_bj_str(utc_str):
    """将 UTC 时间字符串转换为 北京时间字符串"""
    if not utc_str: return "N/A"
    try:
        # 处理可能的 Z 结尾
        cleaned = utc_str.replace("Z", "")
        # 处理可能存在的微秒
        if "." in cleaned:
            cleaned = cleaned.split(".")[0]
            
        dt = datetime.datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S")
        bj_dt = dt + datetime.timedelta(hours=8)
        return bj_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        # 如果解析失败，返回原字符串
        return utc_str

def get_current_bj_time():
    """获取当前北京时间"""
    utc_now = datetime.datetime.utcnow()
    bj_now = utc_now + datetime.timedelta(hours=8)
    return bj_now.strftime("%Y-%m-%d %H:%M:%S")

def 获取所有版本():
    """获取所有 Release 信息"""
    releases = []
    page = 1
    while True:
        url = f"{GITHUB_API_URL}?per_page=100&page={page}"
        try:
            r = requests.get(url, headers=get_headers(), timeout=30)
            if r.status_code == 404:
                break
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            releases.extend(data)
            page += 1
        except Exception as e:
            print(f"获取版本列表失败: {e}", file=sys.stderr)
            break
    return releases

def 获取最新版本():
    """获取最新 Release"""
    url = f"{GITHUB_API_URL}/latest"
    try:
        r = requests.get(url, headers=get_headers(), timeout=30)
        if r.status_code == 404:
            all_releases = 获取所有版本()
            if all_releases:
                return all_releases[0]
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"获取最新版本失败: {e}")
        return None

def 下载资源(assets, download_dir="."):
    """下载 Release 中的所有资源"""
    downloaded_files = []
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        
    for asset in assets:
        name = asset["name"]
        url = asset["browser_download_url"]
        path = os.path.join(download_dir, name)
        print(f"正在下载: {name} ...")
        
        try:
            with requests.get(url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            downloaded_files.append(name)
            print(f"下载完成: {name}")
        except Exception as e:
            print(f"下载失败 {name}: {e}")
            
    return downloaded_files

def 保存历史记录(history):
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def 格式化资产(assets):
    """将资产按系统分类"""
    systems = {
        "Windows": [],
        "macOS": [],
        "Linux": [],
        "Other": []
    }
    
    for asset in assets:
        name = asset["name"].lower()
        link = asset["browser_download_url"]
        item = f"[{asset['name']}]({link})"
        
        if ".exe" in name or ".msi" in name or "win" in name:
            systems["Windows"].append(item)
        elif ".dmg" in name or "mac" in name or "darwin" in name:
            systems["macOS"].append(item)
        elif ".deb" in name or ".rpm" in name or ".appimage" in name or "linux" in name:
            systems["Linux"].append(item)
        else:
            systems["Other"].append(item)
            
    return systems

def 生成版本详情卡片(item, title_prefix=""):
    tag = item.get("tag_name", "N/A")
    # 原时间
    raw_date = item.get("published_at", "")
    # 转换为北京时间
    bj_date = utc_to_bj_str(raw_date)
    
    assets_grouped = 格式化资产(item.get("assets", []))
    
    # 构建发布说明链接
    release_url = item.get("html_url", "#")
    
    md = f"### {title_prefix} {tag}\n"
    md += f"**发布时间 (UTC+8)**: `{bj_date}`  |  [查看详细变更日志]({release_url})\n\n"
    
    md += "| 平台 (Platform) | 为了美观，请下载对应的版本 (Download) |\n"
    md += "| :--- | :--- |\n"
    
    def format_cell(links):
        # 排序，让同名的文件靠在一起 (简单的字母排序)
        links.sort()
        return "<br>".join(links)
    
    if assets_grouped["Windows"]:
        md += f"| 🪟 **Windows** | {format_cell(assets_grouped['Windows'])} |\n"
    if assets_grouped["macOS"]:
        md += f"| 🍎 **macOS** | {format_cell(assets_grouped['macOS'])} |\n"
    if assets_grouped["Linux"]:
        md += f"| 🐧 **Linux** | {format_cell(assets_grouped['Linux'])} |\n"
    if assets_grouped["Other"]:
        md += f"| 📦 **Other** | {format_cell(assets_grouped['Other'])} |\n"
        
    md += "\n"
    return md

def 生成README(history):
    # 按照发布时间倒序 (Newest -> Oldest) 用于 README 展示
    history.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    current_time_bj = get_current_bj_time()
    
    latest = history[0] if history else None
    
    # 查找稳定版 2.2.3
    # stable_version = next((x for x in history if "2.2.3" in x.get("tag_name", "")), None)
    
    md = f"""# {REPO_NAME} Release 监控与备份

> [!TIP]
> 本仓库自动监控并备份 [{REPO_OWNER}/{REPO_NAME}](https://github.com/{REPO_OWNER}/{REPO_NAME}) 的 Release 版本。
> 上次检测时间 (UTC+8): {current_time_bj}

"""

    if latest:
        md += "## 🌟 最新版本 (Latest)\n"
        md += 生成版本详情卡片(latest, "🔥")

    
    md += "## 📜 所有历史版本 (All Versions)\n\n"
    
    for item in history:
        tag = item.get("tag_name", "N/A")
        date_bj = utc_to_bj_str(item.get("published_at", ""))
        url = item.get("html_url", "#")
        assets_grouped = 格式化资产(item.get("assets", []))
        
        # 使用引用块和列表展示，避免表格横向滚动
        md += f"### {tag}\n"
        md += f"> 📅 **发布时间**: `{date_bj}` &nbsp;&nbsp;|&nbsp;&nbsp; 🔗 [查看原始发布页面 (Source)]({url})\n\n"
        
        # 辅助函数：生成链接列表
        def format_links_list(links, icon, name):
            if not links: return ""
            links.sort()
            # 只有当有内容时才显示标题
            content = f"#### {icon} {name}\n"
            # 使用无序列表展示文件，更清晰
            for link in links:
                content += f"- {link}\n"
            return content + "\n"

        md += format_links_list(assets_grouped["Windows"], "🪟", "Windows")
        md += format_links_list(assets_grouped["macOS"], "🍎", "macOS")
        md += format_links_list(assets_grouped["Linux"], "🐧", "Linux")
        md += format_links_list(assets_grouped["Other"], "📦", "Other")
        
        md += "---\n\n"

    md += "*Auto-generated by Antigravity Monitoring System*\n"
    return md

def 获取指定版本(tag):
    """通过 Tag 获取特定 Release"""
    url = f"{GITHUB_API_URL}/tags/{tag}"
    try:
        r = requests.get(url, headers=get_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"获取版本 {tag} 失败: {e}")
        return None

def main():
    # 命令行模式
    if len(sys.argv) > 1:
        if sys.argv[1] == "--api-history":
            # 返回精简版本列表供 Matrix 使用
            releases = 获取所有版本()
            
            # 排序：按发布时间 升序 (Oldest -> Newest / Smallest -> Largest)
            # 以满足 "倒叙排列版本，从最小的开始执行"
            releases.sort(key=lambda x: x.get("published_at", ""))
            
            output = [{"version": r["tag_name"]} for r in releases]
            print(json.dumps(output))
            return

        if sys.argv[1] == "--download":
            version_tag = sys.argv[2]
            print(f"正在处理版本 {version_tag} ...")
            target_release = 获取指定版本(version_tag)
            
            if target_release:
                file_list = 下载资源(target_release["assets"])
                if "GITHUB_OUTPUT" in os.environ:
                    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                        # NEW: 使用 Heredoc 避免乱码
                        body_content = target_release.get('body', '') or ''
                        f.write("body<<EOF\n")
                        f.write(body_content)
                        f.write("\nEOF\n")
                        
                        # NEW: 转换时间
                        bj_time = utc_to_bj_str(target_release['published_at'])
                        f.write(f"published_at={bj_time}\n")
                        
                        f.write(f"html_url={target_release['html_url']}\n")
                        f.write("assets<<EOF\n")
                        f.write('\n'.join(file_list))
                        f.write("\nEOF\n")
            else:
                print(f"未找到版本 {version_tag}")
                sys.exit(1)
            return

    # 默认模式：检查更新
    print("开始检查最新版本...")
    # 获取所有版本列表以构建完整的 README
    print("正在获取所有历史版本信息...")
    all_releases = 获取所有版本()
    
    if not all_releases:
        print("无法获取版本列表")
        sys.exit(1)
        
    latest_release = all_releases[0]
    tag_name = latest_release["tag_name"]
    
    # 读取本地版本
    local_version = ""
    if os.path.exists("VERSION"):
        with open("VERSION", "r", encoding="utf-8") as f:
            local_version = f.read().strip()
            
    print(f"本地版本: {local_version}, 远程最新: {tag_name}")
    
    version_changed = (tag_name != local_version)
    
    # 始终重新生成 history.json
    history = []
    for r in all_releases:
        history.append({
            "tag_name": r["tag_name"],
            "published_at": r["published_at"],
            "html_url": r["html_url"],
            "assets": [{"name": a["name"], "browser_download_url": a["browser_download_url"]} for a in r["assets"]]
        })
    
    保存历史记录(history)
    
    # 始终生成 README
    readme_content = 生成README(history)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
        
    # 写入 Output
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"version_changed={'true' if version_changed else 'false'}\n")
            f.write("readme_changed=true\n")
            f.write(f"version={tag_name}\n")
            
            if version_changed:
                # NEW: 使用 Heredoc 避免乱码
                body_content = latest_release.get('body', '') or ''
                f.write("body<<EOF\n")
                f.write(body_content)
                f.write("\nEOF\n")
                
                print("版本更新，开始下载资源...")
                file_list = 下载资源(latest_release["assets"])
                
                f.write("assets<<EOF\n")
                f.write('\n'.join(file_list))
                f.write("\nEOF\n")
                
                with open("VERSION", "w", encoding="utf-8") as vf:
                    vf.write(tag_name)

if __name__ == "__main__":
    main()
