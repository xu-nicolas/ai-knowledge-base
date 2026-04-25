#!/usr/bin/env python3
"""MCP 知识库 Server — 让 AI 通过自然语言搜索本地知识库。

提供 3 个 MCP 工具：
- search_articles: 按关键词搜索文章标题和摘要
- get_article: 按 ID 获取文章完整内容
- knowledge_stats: 返回统计信息（文章总数、来源分布、热门标签）

使用 JSON-RPC 2.0 over stdio 协议，无第三方依赖。
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# ── 项目路径 ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent
ENTRIES_DIR = PROJECT_ROOT / "knowledge" / "entries"


# ── 工具实现 ─────────────────────────────────────────────────────────────

def search_articles(keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    """按关键词搜索文章标题和摘要。"""
    results = []
    if not ENTRIES_DIR.exists():
        return results

    keyword_lower = keyword.lower()
    for filepath in sorted(ENTRIES_DIR.glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            title = data.get("title", "").lower()
            summary = data.get("summary", "").lower()
            tags = [t.lower() for t in data.get("tags", [])]

            if keyword_lower in title or keyword_lower in summary or keyword_lower in tags:
                results.append({
                    "id": data.get("id", ""),
                    "title": data.get("title", ""),
                    "source": data.get("source", ""),
                    "score": data.get("metadata", {}).get("score", ""),
                    "tags": data.get("tags", []),
                    "summary": data.get("summary", ""),
                    "source_url": data.get("source_url", ""),
                })
                if len(results) >= limit:
                    break
        except (json.JSONDecodeError, IOError):
            continue

    return results


def get_article(article_id: str) -> dict[str, Any] | None:
    """按 ID 获取文章完整内容。"""
    if not ENTRIES_DIR.exists():
        return None

    for filepath in sorted(ENTRIES_DIR.glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("id") == article_id:
                return data
        except (json.JSONDecodeError, IOError):
            continue

    return None


def knowledge_stats() -> dict[str, Any]:
    """返回统计信息（文章总数、来源分布、热门标签）。"""
    if not ENTRIES_DIR.exists():
        return {"total": 0, "sources": {}, "top_tags": []}

    articles = []
    for filepath in sorted(ENTRIES_DIR.glob("*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                articles.append(json.load(f))
        except (json.JSONDecodeError, IOError):
            continue

    total = len(articles)
    sources = Counter(a.get("source", "unknown") for a in articles)
    all_tags = []
    for a in articles:
        all_tags.extend(a.get("tags", []))
    top_tags = Counter(all_tags).most_common(10)

    return {
        "total": total,
        "sources": dict(sources.most_common()),
        "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
    }


# ── MCP 工具定义 ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_articles",
        "description": "按关键词搜索知识库文章（标题和摘要）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量上限",
                    "default": 5,
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "get_article",
        "description": "按 ID 获取知识条目的完整内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "知识条目 ID，如 2026-04-23-001",
                },
            },
            "required": ["article_id"],
        },
    },
    {
        "name": "knowledge_stats",
        "description": "返回知识库统计信息（文章总数、来源分布、热门标签）",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ── JSON-RPC 2.0 Handler ─────────────────────────────────────────────────

def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """处理 MCP JSON-RPC 2.0 请求。"""
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "knowledge-server", "version": "0.1.0"},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "search_articles":
            keyword = arguments.get("keyword", "")
            limit = arguments.get("limit", 5)
            results = search_articles(keyword, limit)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(results, ensure_ascii=False, indent=2)}
                    ]
                },
            }

        if tool_name == "get_article":
            article_id = arguments.get("article_id", "")
            article = get_article(article_id)
            if article:
                content = json.dumps(article, ensure_ascii=False, indent=2)
            else:
                content = f"未找到 ID 为 {article_id} 的文章"
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": content}]
                },
            }

        if tool_name == "knowledge_stats":
            stats = knowledge_stats()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(stats, ensure_ascii=False, indent=2)}
                    ]
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Unknown tool: {tool_name}",
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Unknown method: {method}",
        },
    }


# ── Stdio 主循环 ─────────────────────────────────────────────────────────

def main() -> None:
    """读取 stdin 的 JSON-RPC 请求，处理并输出响应到 stdout。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            print(json.dumps(response))
            sys.stdout.flush()
            continue

        response = handle_request(request)
        print(json.dumps(response, ensure_ascii=False))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
