#!/usr/bin/env python3
"""
project_tree.py — 通用项目目录树扫描 + Mermaid 结构图生成器

用法:
    python project_tree.py                          # 扫描当前目录，输出到 stdout
    python project_tree.py /path/to/project         # 扫描指定目录
    python project_tree.py /path -o tree.md         # 输出到文件
    python project_tree.py /path --depth 3          # 限制扫描深度
    python project_tree.py /path --no-icons         # 不使用 emoji 图标
    python project_tree.py /path --exclude .git,node_modules,__pycache__  # 自定义排除

返回码: 0 成功, 1 路径不存在
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Set

# ── 文件图标映射（按后缀） ─────────────────────────
EXT_ICONS = {
    # 开发语言
    ".py":    "\U0001f40d",   # 🐍
    ".js":    "\U0001f7e8",   # 🟨
    ".ts":    "\U0001f7e6",   # 🟦
    ".tsx":   "\u269b\ufe0f", # ⚛️
    ".jsx":   "\u269b\ufe0f", # ⚛️
    ".java":  "\u2615",       # ☕
    ".go":    "\U0001f426",   # 🐦
    ".rs":    "\U0001f980",   # 🦀
    ".rb":    "\U0001f48e",   # 💎
    ".php":   "\U0001f43e",   # 🐾
    ".c":     "\U0001f4e0",   # 📠
    ".cpp":   "\U0001f4e0",   # 📠
    ".h":     "\U0001f4e0",   # 📠
    ".css":   "\U0001f3a8",   # 🎨
    ".scss":  "\U0001f3a8",   # 🎨
    ".less":  "\U0001f3a8",   # 🎨
    ".html":  "\U0001f310",   # 🌐
    ".sql":   "\U0001f4be",   # 💾
    # 配置 & 数据
    ".json":  "\U0001f4cb",   # 📋
    ".yaml":  "\u2699\ufe0f", # ⚙️
    ".yml":   "\u2699\ufe0f", # ⚙️
    ".toml":  "\u2699\ufe0f", # ⚙️
    ".xml":   "\U0001f4c4",   # 📄
    ".csv":   "\U0001f4ca",   # 📊
    # 文档
    ".md":    "\U0001f4dd",   # 📝
    ".rst":   "\U0001f4dd",   # 📝
    ".txt":   "\U0001f4c4",   # 📄
    ".pdf":   "\U0001f4d1",   # 📑
    # 构建 & 部署
    ".bat":   "\U0001f5a5\ufe0f", # 🖥️
    ".sh":    "\U0001f427",   # 🐧
    ".ps1":   "\U0001f5a5\ufe0f", # 🖥️
    ".dockerfile": "\U0001f433", # 🐳
    "Dockerfile":  "\U0001f433", # 🐳
    ".yml":   "\U0001f433",   # 🐳
    ".nginx": "\U0001f310",   # 🌐
    # 其他
    ".gitignore": "\U0001f6ab", # 🚫
    ".env":   "\U0001f511",   # 🔑
    ".lock":  "\U0001f512",   # 🔒
}

DIR_ICON = "\U0001f4c1"    # 📁
ROOT_ICON = "\U0001f4e6"   # 📦


def scan_directory(
    root: Path,
    exclude_dirs: Set[str],
    exclude_files: Set[str],
    max_depth: int,
    show_icons: bool,
) -> Tuple[List[str], int]:
    """递归扫描目录，返回（文件相对路径列表，扫描到的文件总数）"""

    results: List[str] = []
    root_str = str(root.resolve())

    for dirpath_str, dirnames, filenames in os.walk(str(root)):
        dirpath = Path(dirpath_str)
        rel_dir = dirpath.relative_to(root)

        # 计算当前深度
        depth = len(rel_dir.parts) if rel_dir != Path(".") else 0
        if max_depth > 0 and depth > max_depth:
            dirnames[:] = []  # 不再进入子目录
            continue

        # 过滤子目录（修改 dirnames 影响 os.walk 后续迭代）
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs and not d.startswith(".")
        ]

        # 过滤文件
        for fname in sorted(filenames):
            if fname in exclude_files or fname.startswith("."):
                continue
            rel_path = rel_dir / fname if rel_dir != Path(".") else Path(fname)
            results.append(str(rel_path).replace("\\", "/"))
            filenames.remove(fname)  # 防止重复

    return results, len(results)


def generate_mermaid(
    files: List[str],
    root_name: str = "project",
    show_icons: bool = True,
) -> str:
    """将文件列表转换为 Mermaid graph TD 格式"""

    lines: List[str] = []
    lines.append("```mermaid")
    lines.append("graph TD")

    root_id = _safe_id(root_name)
    icon = f"{ROOT_ICON} " if show_icons else ""
    lines.append(f'  {root_id}("[{icon}{root_name}]")')

    seen_dirs: Set[str] = set()

    # 收集所有目录节点
    dir_nodes: Set[str] = set()
    for fp in files:
        parts = fp.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            dir_nodes.add(parent)

    # 输出目录节点（排序保证稳定性）
    for dn in sorted(dir_nodes, key=lambda x: (x.count("/"), x)):
        parts = dn.split("/")
        label = parts[-1]
        dn_id = _safe_id(dn)
        icon_str = f"{DIR_ICON} " if show_icons else ""
        lines.append(f'  {dn_id}("[{icon_str}{label}]")')

        # 连线到父目录 / root
        if "/" in dn:
            parent = "/".join(parts[:-1])
            parent_id = _safe_id(parent)
        else:
            parent_id = root_id
        lines.append(f'  {parent_id} --> {dn_id}')

    # 输出文件节点 + 连线
    for fp in files:
        parts = fp.split("/")
        fname = parts[-1]
        fp_id = _safe_id(fp)

        # 图标
        icon_str = ""
        if show_icons:
            icon_str = _file_icon(fname) + " "

        lines.append(f'  {fp_id}[{icon_str}{fname}]')

        # 连线到父目录
        if len(parts) > 1:
            parent = "/".join(parts[:-1])
            parent_id = _safe_id(parent)
        else:
            parent_id = root_id
        lines.append(f'  {parent_id} --> {fp_id}')

    lines.append("```")
    return "\n".join(lines)


def _safe_id(name: str) -> str:
    """将路径转为合法的 Mermaid 节点 ID"""
    return name.replace("/", "_").replace(".", "_").replace("-", "_").replace(" ", "_").replace("#", "")


def _file_icon(fname: str) -> str:
    """根据文件名返回 emoji 图标"""
    # 精确文件名匹配
    exact_map = {
        "Dockerfile": "\U0001f433",
        "Makefile": "\u2699",
        "README.md": "\U0001f4d6",
    }
    if fname in exact_map:
        return exact_map[fname]

    # 后缀匹配
    _, ext = os.path.splitext(fname)
    if ext.lower() in EXT_ICONS:
        return EXT_ICONS[ext.lower()]

    # 特殊前缀匹配
    if fname.startswith("docker-compose"):
        return "\U0001f433"

    return "\U0001f4c4"  # 📄


def generate_markdown(
    files: List[str],
    root_name: str = "project",
    show_icons: bool = True,
) -> str:
    """生成完整 Markdown（mermaid + 统计信息 + 技术栈表格）"""

    mermaid_block = generate_mermaid(files, root_name, show_icons)

    # 统计
    by_ext: dict = {}
    for fp in files:
        _, ext = os.path.splitext(fp)
        by_ext[ext or "(无后缀)"] = by_ext.get(ext or "(无后缀)", 0) + 1
    ext_summary = ", ".join(f"`{k}` x{v}" for k, v in sorted(by_ext.items(), key=lambda x: -x[1])[:10])

    parts = [""]
    parts.append(f"# {ROOT_ICON} {root_name} — 项目结构")
    parts.append("")
    parts.append(f"> 共 **{len(files)}** 个文件 | {ext_summary}")
    parts.append("")
    parts.append(mermaid_block)
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("### 📊 文件类型统计")
    parts.append("")
    parts.append("| 类型 | 数量 |")
    parts.append("|------|------|")
    for ext, cnt in sorted(by_ext.items(), key=lambda x: -x[1])[:15]:
        icon = _file_icon(f"file{ext}") if ext else "\U0001f4c4"
        parts.append(f"| {icon} `{ext or '(无后缀)'}` | {cnt} |")
    parts.append("")
    parts.append("---")
    parts.append(f"_由 [project_tree.py](scripts/project_tree.py) 自动生成_")
    parts.append("")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="扫描项目目录，生成 Mermaid 格式结构图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python project_tree.py\n"
               "  python project_tree.py /path/to/proj -o tree.md\n"
               "  python project_tree.py . --depth 2 --no-icons\n"
               "  python project_tree.py . --exclude .git,node_modules,dist",
    )
    parser.add_argument("path", nargs="?", default=".",
                        help="项目根目录（默认当前目录）")
    parser.add_argument("-o", "--output",
                        help="输出文件（默认 stdout）")
    parser.add_argument("--depth", type=int, default=0,
                        help="最大扫描深度（0=不限）")
    parser.add_argument("--no-icons", action="store_true",
                        help="不使用 emoji 图标")
    parser.add_argument("--exclude", default="",
                        help="额外排除的目录/文件，逗号分隔")
    parser.add_argument("--name", default=None,
                        help="项目名称（默认取目录名）")

    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"错误: 目录不存在 — {root}", file=sys.stderr)
        sys.exit(1)

    # 排除列表
    default_exclude_dirs = {".git", "__pycache__", "node_modules",
                            ".venv", "venv", ".idea", ".vscode",
                            ".sass-cache", ".mypy_cache", ".pytest_cache",
                            ".eggs", "egg-info", ".tox", "dist", "build",
                            ".next", ".nuxt", ".output"}
    default_exclude_files = {".DS_Store", "Thumbs.db", ".gitkeep"}
    extra = {s.strip() for s in args.exclude.split(",") if s.strip()}
    exclude_dirs = default_exclude_dirs | extra
    exclude_files = default_exclude_files | extra

    project_name = args.name or root.name
    show_icons = not args.no_icons

    # 扫描
    files, total = scan_directory(root, exclude_dirs, exclude_files,
                                   args.depth, show_icons)

    # 生成
    markdown = generate_markdown(files, project_name, show_icons)

    # 输出
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(markdown, encoding="utf-8")
        print(f"已生成: {out_path.resolve()}", file=sys.stderr)
    else:
        print(markdown)

    print(f"\n扫描完成: {total} 个文件", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
