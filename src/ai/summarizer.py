"""Daily summary generation — pure programmatic rendering."""

import html as _html
import re
from typing import List, Dict, Optional

from ..models import ContentItem


_CJK = r"[\u4e00-\u9fff\u3400-\u4dbf]"
_ASCII = r"[A-Za-z0-9]"


def _pangu(text: str) -> str:
    """Insert a space between CJK and ASCII letters/digits (Pangu spacing)."""
    text = re.sub(rf"({_CJK})({_ASCII})", r"\1 \2", text)
    text = re.sub(rf"({_ASCII})({_CJK})", r"\1 \2", text)
    return text


LABELS = {
    "en": {
        "header": "Horizon Daily",
        "source": "Source",
        "background": "Background",
        "discussion": "Discussion",
        "references": "References",
        "tags": "Tags",
        "selected_items": "From {total} items, {selected} important content pieces were selected",
        "empty_analyzed": "Analyzed {total} items, but none met the importance threshold.",
        "empty_body": (
            "No significant developments today. This might indicate:\n"
            "- A quiet day in your tracked sources\n"
            "- The AI score threshold is too high\n"
            "- Your information sources need expansion\n\n"
            "Consider:\n"
            "1. Lowering the `ai_score_threshold` in config.json\n"
            "2. Adding more diverse information sources\n"
            "3. Checking if the AI model is working correctly\n"
        ),
    },
    "zh": {
        "header": "Horizon 每日速递",
        "source": "来源",
        "background": "背景",
        "discussion": "社区讨论",
        "references": "参考链接",
        "tags": "标签",
        "selected_items": "从 {total} 条内容中筛选出 {selected} 条重要资讯。",
        "empty_analyzed": "已分析 {total} 条内容，但没有达到重要性阈值的条目。",
        "empty_body": (
            "今日暂无重要动态，可能原因：\n"
            "- 今天关注的信息源较平静\n"
            "- AI 评分阈值设置过高\n"
            "- 信息源种类有待扩充\n\n"
            "建议：\n"
            "1. 在 config.json 中降低 `ai_score_threshold`\n"
            "2. 添加更多多样化的信息源\n"
            "3. 检查 AI 模型是否正常工作\n"
        ),
    },
}


class DailySummarizer:
    """Generates daily Markdown summaries from pre-analyzed content items."""

    def __init__(self):
        pass

    async def generate_summary(
        self,
        items: List[ContentItem],
        date: str,
        total_fetched: int,
        language: str = "en",
    ) -> str:
        """Generate daily summary in Markdown format.

        Items are rendered in score-descending order (already sorted by orchestrator).

        Args:
            items: High-scoring content items (already enriched)
            date: Date string (YYYY-MM-DD)
            total_fetched: Total number of items fetched before filtering
            language: Output language, either "en" or "zh"

        Returns:
            str: Markdown formatted summary
        """
        labels = LABELS.get(language, LABELS["en"])

        if not items:
            return self._generate_empty_summary(date, total_fetched, labels)

        header = (
            f"# {labels['header']} - {date}\n\n"
            f"> {labels['selected_items'].format(total=total_fetched, selected=len(items))}\n\n"
            "---\n\n"
        )

        # TOC
        toc_entries = []
        for i, item in enumerate(items):
            _t = item.metadata.get(f"title_{language}") or item.title
            t = str(_t).replace("[", "(").replace("]", ")")
            if language == "zh":
                t = _pangu(t)
            score = item.ai_score or "?"
            toc_entries.append(f"{i + 1}. [{t}](#item-{i + 1}) \u2b50\ufe0f {score}/10")
        toc = "\n".join(toc_entries) + "\n\n---\n\n"

        parts = [self._format_item(item, labels, language, i + 1) for i, item in enumerate(items)]

        return header + toc + "".join(parts)

    def generate_webhook_overview(
        self,
        items: List[ContentItem],
        date: str,
        total_fetched: int,
        language: str = "en",
    ) -> str:
        """Generate a compact overview for multi-message webhook delivery."""
        labels = LABELS.get(language, LABELS["en"])
        if not items:
            return self._generate_empty_summary(date, total_fetched, labels)

        if language == "zh":
            header = (
                f"# {labels['header']} - {date}\n\n"
                f"> 从 {total_fetched} 条内容中筛选出 {len(items)} 条重要资讯。\n\n"
                "下面会按新闻逐条发送详情，你可以只看感兴趣的标题。\n\n"
            )
        else:
            header = (
                f"# {labels['header']} - {date}\n\n"
                f"> Selected {len(items)} important items from {total_fetched} fetched items.\n\n"
                "Details will be sent item by item so you can read only the topics you care about.\n\n"
            )

        entries = []
        for i, item in enumerate(items, start=1):
            title = str(item.metadata.get(f"title_{language}") or item.title).replace("[", "(").replace("]", ")")
            if language == "zh":
                title = _pangu(title)
            score = item.ai_score or "?"
            entries.append(f"{i}. [{title}]({item.url}) \u2b50\ufe0f {score}/10")

        return header + "\n".join(entries)

    def generate_webhook_item(
        self,
        item: ContentItem,
        language: str,
        index: int,
        total: int,
    ) -> str:
        """Generate one item message for multi-message webhook delivery."""
        labels = LABELS.get(language, LABELS["en"])
        prefix = f"第 {index}/{total} 条\n\n" if language == "zh" else f"Item {index}/{total}\n\n"
        return prefix + self._format_item(item, labels, language, index).rstrip("-\n ")

    def _format_item(self, item: ContentItem, labels: dict, language: str, index: int) -> str:
        """Format a single ContentItem into Markdown."""
        _title = item.metadata.get(f"title_{language}") or item.title
        title = str(_title).replace("[", "(").replace("]", ")")
        url = str(item.url)
        score = item.ai_score or "?"
        meta = item.metadata

        summary = (
            meta.get(f"detailed_summary_{language}")
            or meta.get("detailed_summary")
            or item.ai_summary
            or ""
        )
        background = meta.get(f"background_{language}") or meta.get("background") or ""
        discussion = (
            meta.get(f"community_discussion_{language}")
            or meta.get("community_discussion")
            or ""
        )

        if language == "zh":
            title = _pangu(title)
            summary = _pangu(summary)
            background = _pangu(background)
            discussion = _pangu(discussion)

        # Source line with parts joined by " · ", link appended at end
        source_type = item.source_type.value
        source_parts = [source_type]
        if meta.get("subreddit"):
            source_parts.append(f"r/{meta['subreddit']}")
        if meta.get("feed_name"):
            source_parts.append(meta["feed_name"])
        else:
            source_parts.append(item.author or "unknown")
        if item.published_at:
            if language == "zh":
                source_parts.append(
                    f"{item.published_at.month}月{item.published_at.day}日 "
                    f"{item.published_at:%H:%M}"
                )
            else:
                day = item.published_at.strftime("%d").lstrip("0")
                source_parts.append(item.published_at.strftime(f"%b {day}, %H:%M"))
        source_line = " \u00b7 ".join(source_parts)  # ·

        discussion_url = meta.get("discussion_url")
        if discussion_url:
            discussion_url = str(discussion_url)
            if discussion_url != url:
                source_line += f' · [{labels["discussion"]}]({discussion_url})'

        lines = [
            f'<a id="item-{index}"></a>',
            f"## [{title}]({url}) \u2b50\ufe0f {score}/10",  # ⭐️
            "",
            summary,
            "",
            source_line,
        ]

        if background:
            lines.append("")
            lines.append(f"**{labels['background']}**: {background}")

        sources = meta.get("sources") or []
        if sources:
            items_html = "".join(f'<li><a href="{s["url"]}">{s["title"]}</a></li>\n' for s in sources)
            lines += [
                "",
                f'<details><summary>{labels["references"]}</summary>\n<ul>\n{items_html}\n</ul>\n</details>',
            ]

        if discussion:
            lines.append("")
            lines.append(f"**{labels['discussion']}**: {discussion}")

        if item.ai_tags:
            tags_str = ", ".join([f"`#{t}`" for t in item.ai_tags])
            lines.append("")
            lines.append(f"**{labels['tags']}**: {tags_str}")

        lines.append("")
        lines.append("---")

        return "\n".join(lines) + "\n\n"

    # ------------------------------------------------------------------ #
    # Telegram HTML rendering                                             #
    # ------------------------------------------------------------------ #

    _TG_NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
                         "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    _TG_MAX_CHARS = 4000  # Telegram's hard limit is 4096; leave a margin

    def generate_telegram_item(
        self,
        item: "ContentItem",
        language: str,
        index: int,
        total: int,
    ) -> str:
        """Generate Telegram HTML for one item (parse_mode=HTML)."""
        meta = item.metadata
        title = _html.escape(str(meta.get(f"title_{language}") or item.title))
        url = _html.escape(str(item.url))
        score = item.ai_score or "?"

        summary_raw = (
            meta.get(f"detailed_summary_{language}")
            or meta.get("detailed_summary")
            or item.ai_summary
            or ""
        )
        background_raw = meta.get(f"background_{language}") or meta.get("background") or ""

        if language == "zh":
            summary_raw = _pangu(summary_raw)
            background_raw = _pangu(background_raw)

        summary = _html.escape(str(summary_raw))
        background = _html.escape(str(background_raw)) if background_raw else ""

        # Source line
        source_type = item.source_type.value
        source_parts = [_html.escape(source_type)]
        if meta.get("subreddit"):
            source_parts.append(f"r/{_html.escape(str(meta['subreddit']))}")
        if meta.get("feed_name"):
            source_parts.append(_html.escape(str(meta["feed_name"])))
        elif item.author:
            source_parts.append(_html.escape(str(item.author)))
        if item.published_at:
            day = item.published_at.strftime("%d").lstrip("0")
            source_parts.append(item.published_at.strftime(f"%b {day}, %H:%M"))
        source_line = " · ".join(source_parts)

        lines = [
            f"📰 <b>{index}/{total}</b>",
            "",
            f'<b><a href="{url}">{title}</a></b>',
            f"⭐️ <b>{score}</b>/10",
            "",
            summary,
        ]

        if background:
            lines += ["", f"📖 <b>Background:</b> {background}"]

        discussion_url = meta.get("discussion_url")
        if discussion_url and str(discussion_url) != str(item.url):
            du = _html.escape(str(discussion_url))
            lines += ["", f'💬 <a href="{du}">Discussion</a>']

        if item.ai_tags:
            tags_str = " ".join(f"<code>#{_html.escape(t)}</code>" for t in item.ai_tags)
            lines += ["", f"🏷 {tags_str}"]

        lines += ["", f"<i>{source_line}</i>"]

        result = "\n".join(lines)
        if len(result) > self._TG_MAX_CHARS:
            result = result[: self._TG_MAX_CHARS - 3] + "..."
        return result

    def generate_telegram_overview(
        self,
        items: List["ContentItem"],
        date: str,
        total_fetched: int,
        language: str = "en",
        telegram_links: Optional[Dict[int, str]] = None,
    ) -> str:
        """Generate Telegram HTML overview (parse_mode=HTML).

        Args:
            telegram_links: Optional mapping of {item_index: t.me_url}.
                            When provided, TOC entries link to the Telegram
                            message rather than the original article URL.
        """
        if not items:
            count = total_fetched
            return (
                f"<b>📡 Horizon Daily — {_html.escape(date)}</b>\n\n"
                f"Analyzed <b>{count}</b> items, but none met the importance threshold."
            )

        lines = [
            f"<b>📡 Horizon Daily — {_html.escape(date)}</b>",
            "",
            f"Analyzed <b>{total_fetched}</b> items · "
            f"Selected <b>{len(items)}</b> important update{'s' if len(items) != 1 else ''}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, item in enumerate(items, start=1):
            title = _html.escape(
                str(item.metadata.get(f"title_{language}") or item.title)
            )
            score = item.ai_score or "?"
            num = self._TG_NUMBER_EMOJIS[i - 1] if i <= len(self._TG_NUMBER_EMOJIS) else f"{i}."
            link = _html.escape((telegram_links or {}).get(i) or str(item.url))
            lines.append(f'{num} <a href="{link}">{title}</a> ⭐️ {score}')

        lines += [
            "━━━━━━━━━━━━━━━━━━━━━",
            "",
            "<i>Tap a title to jump to its full message 👆</i>",
        ]

        return "\n".join(lines)

    def _generate_empty_summary(self, date: str, total_fetched: int, labels: dict) -> str:
        """Generate summary when no high-scoring items were found."""
        return (
            f"# {labels['header']} - {date}\n\n"
            f"> {labels['empty_analyzed'].format(total=total_fetched)}\n\n"
            + labels["empty_body"]
        )
