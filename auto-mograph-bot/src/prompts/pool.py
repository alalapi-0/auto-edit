"""文案池模块，负责生成去重的主题、风格、标签组合并执行敏感词过滤。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from hashlib import md5
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set

from rich.console import Console

from ..logging.structlog import log_event

console = Console()


DEFAULT_TOPICS: Sequence[str] = (
    "晨光中的海岛瑜伽", "雨夜霓虹街头快闪", "星河下的无人机表演", "樱花飘落的校园告白",
    "赛博朋克城市夜跑", "古风庭院茶席仪式", "热带雨林探险纪录", "未来感健身舞蹈课",
    "极简水墨风建筑漫游", "黑白胶片摇滚现场", "秋日森林露营烟火", "北欧清晨手冲咖啡",
    "沙漠公路机车旅途", "云端办公室远程协作", "宇航员登陆火星开会", "废墟中绽放的花田",
    "夏夜烟花市集漫步", "街头滑板与灯光秀", "雪山之巅极光冥想", "未来空间站园艺课堂",
    "水下珊瑚城市探索", "复古像素风电台直播", "山野乡间手作插画", "雨林深处的光绘摄影",
)

DEFAULT_STYLES: Sequence[str] = (
    "超写实光追质感", "胶片颗粒复古色", "手绘插画感线条", "霓虹赛博高对比",
    "柔焦梦幻漫散光", "电影级调色 LUT", "黑金高级质感", "蓝橙对撞主色",
    "低饱和莫兰迪色系", "HDR 高动态范围", "镜头眩光加花絮", "动态景深追焦",
)

DEFAULT_TAGS: Sequence[str] = (
    "#灵感随手记", "#治愈系日常", "#视觉冲击", "#赛博都市", "#旅拍分享",
    "#慢生活", "#未来科技", "#探索未知", "#情绪大片", "#创意短片",
    "#vlog", "#开箱体验", "#光影艺术", "#潮流出街", "#极限运动",
)

DEFAULT_SENSITIVE: Sequence[str] = (
    "政治", "暴力", "侵权", "违法", "赌博", "毒品", "诈骗", "色情",
    "未成年人不宜", "枪支", "仇恨", "极端", "恐怖",
)

AD_KEYWORDS: Sequence[str] = (
    "最低价", "一元秒杀", "官方授权", "立刻下单", "扫码购买", "拉新奖励", "返利",
)


@dataclass
class PromptCandidate:
    """用于承载单次抽取的完整文案信息。"""

    prompt: str
    title: str
    description: str
    tags: List[str]
    seed: int


@dataclass
class PromptPool:
    """文案池管理器，负责去重抽样与敏感词过滤。"""

    texts: List[str] = field(default_factory=lambda: list(DEFAULT_TOPICS))
    styles: List[str] = field(default_factory=lambda: list(DEFAULT_STYLES))
    tags: List[str] = field(default_factory=lambda: list(DEFAULT_TAGS))
    blacklist: Set[str] = field(default_factory=set)
    sensitive_words: Set[str] = field(default_factory=lambda: set(DEFAULT_SENSITIVE))
    ad_words: Set[str] = field(default_factory=lambda: set(AD_KEYWORDS))
    used_hashes: Set[str] = field(default_factory=set, init=False, repr=False)

    def extend_texts(self, values: Iterable[str]) -> None:
        """追加额外主题文本，自动去除空行。"""

        self.texts.extend([item.strip() for item in values if item and item.strip()])

    def extend_styles(self, values: Iterable[str]) -> None:
        """追加额外风格描述。"""

        self.styles.extend([item.strip() for item in values if item and item.strip()])

    def extend_tags(self, values: Iterable[str]) -> None:
        """追加额外标签。"""

        self.tags.extend([item.strip() for item in values if item and item.strip()])

    def add_blacklist(self, values: Iterable[str]) -> None:
        """添加黑名单主题关键字。"""

        self.blacklist.update(item.strip() for item in values if item and item.strip())

    def add_sensitive_words(self, values: Iterable[str]) -> None:
        """添加敏感词库。"""

        self.sensitive_words.update(item.strip() for item in values if item and item.strip())

    def reset_usage(self) -> None:
        """清空历史抽样，通常用于批量任务结束后。"""

        self.used_hashes.clear()

    def _is_blacklisted(self, text: str) -> bool:
        lower = text.lower()
        return any(word.lower() in lower for word in self.blacklist)

    def _contains_sensitive(self, text: str) -> bool:
        combined = text.lower()
        return any(word.lower() in combined for word in self.sensitive_words)

    def _contains_ad(self, text: str) -> bool:
        combined = text.lower()
        return any(word.lower() in combined for word in self.ad_words)

    def _build_hash(self, prompt: str, style: str, tags: Sequence[str]) -> str:
        raw = "|".join([prompt, style, ",".join(tags)])
        return md5(raw.encode("utf-8")).hexdigest()

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max(0, max_len - 1)] + "…"

    def sample(
        self,
        max_title: int,
        max_desc: int,
        max_tags: int,
        seed: Optional[int] = None,
        sampling_cfg: Optional[Mapping[str, object]] = None,
    ) -> PromptCandidate:
        """采样生成一条完整的 PromptCandidate，支持统计失败并自动回退。"""

        cfg = dict(sampling_cfg or {})
        additional_blacklist = cfg.get("blacklist")
        if isinstance(additional_blacklist, (list, tuple, set)):
            self.add_blacklist(additional_blacklist)

        max_retries = int(cfg.get("max_retries", 10) or 1)
        stats_enabled = bool(cfg.get("stats_log", True))
        fallback_cfg = cfg.get("fallback") if isinstance(cfg.get("fallback"), Mapping) else {}
        safe_words = cfg.get("safe_words") if isinstance(cfg.get("safe_words"), (list, tuple, set)) else []

        stats: Dict[str, int] = {
            "tries_total": 0,
            "hits_blacklist": 0,
            "hits_sensitive": 0,
            "empty_pool": 0,
            "resource_exhausted": 0,
            "other": 0,
        }
        last_reason: Optional[str] = None

        rnd = random.Random(seed or time.time_ns())
        attempts_allowed = max(1, max_retries)
        for _ in range(attempts_allowed):
            stats["tries_total"] += 1
            if not self.texts:
                stats["empty_pool"] += 1
                last_reason = "empty_pool"
                break

            base_text = rnd.choice(self.texts)
            if self._is_blacklisted(base_text):
                stats["hits_blacklist"] += 1
                last_reason = "hits_blacklist"
                continue

            style = rnd.choice(self.styles) if self.styles else ""
            tag_candidates = rnd.sample(self.tags, k=min(max_tags, len(self.tags))) if self.tags else []
            prompt_parts = [base_text, style, ", ".join(tag_candidates[:3])]
            prompt = " | ".join([part for part in prompt_parts if part])
            prompt_hash = self._build_hash(base_text, style, tag_candidates)
            if prompt_hash in self.used_hashes:
                stats["resource_exhausted"] += 1
                last_reason = "resource_exhausted"
                continue

            title = self._truncate(f"{base_text} · {style}" if style else base_text, max_title)
            desc = self._truncate(
                f"灵感主题：{base_text}；风格：{style or '默认'}；标签：{' '.join(tag_candidates[:max_tags])}",
                max_desc,
            )
            combined = " ".join([prompt, title, desc])
            if self._contains_sensitive(combined):
                stats["hits_sensitive"] += 1
                last_reason = "hits_sensitive"
                continue
            if self._contains_ad(desc):
                stats.setdefault("hits_ad", 0)
                stats["hits_ad"] += 1
                last_reason = "hits_ad"
                continue

            tags = [tag for tag in tag_candidates[:max_tags] if tag]
            self.used_hashes.add(prompt_hash)
            final_seed = seed if seed is not None else rnd.randint(0, 2**32 - 1)
            candidate = PromptCandidate(prompt=prompt, title=title, description=desc, tags=tags, seed=final_seed)
            if stats_enabled:
                log_event(
                    "prompt_sample_success",
                    stats=stats,
                    candidate={
                        "prompt": candidate.prompt,
                        "title": candidate.title,
                        "description": candidate.description,
                        "tags": candidate.tags,
                    },
                )
            return candidate

        if fallback_cfg and fallback_cfg.get("enabled"):
            fallback_candidate = self._build_fallback_candidate(
                fallback_cfg,
                safe_words,
                max_title,
                max_desc,
                max_tags,
                seed,
            )
            log_event(
                "prompt_fallback_used",
                stats=stats,
                reason=last_reason,
                fallback={
                    "prompt": fallback_candidate.prompt,
                    "title": fallback_candidate.title,
                    "description": fallback_candidate.description,
                    "tags": fallback_candidate.tags,
                },
            )
            return fallback_candidate

        log_event("prompt_sample_exhausted", stats=stats, reason=last_reason)
        raise RuntimeError("多次尝试后仍无法抽取安全文案，请检查敏感词配置或补充素材。")

    def _build_fallback_candidate(
        self,
        fallback_cfg: Mapping[str, object],
        safe_words: Iterable[object],
        max_title: int,
        max_desc: int,
        max_tags: int,
        seed: Optional[int],
    ) -> PromptCandidate:
        """构建回退使用的 PromptCandidate。"""

        base_prompt = str(fallback_cfg.get("prompt_text", "") or "").strip()
        fallback_title = str(fallback_cfg.get("title", "安全默认文案") or "安全默认文案").strip()
        fallback_desc = str(fallback_cfg.get("description", "") or "").strip()
        fallback_tags = list(
            dict.fromkeys(
                str(item).strip()
                for item in fallback_cfg.get("tags", [])
                if isinstance(item, str) and item.strip()
            )
        )

        safe_tokens = [str(item).strip() for item in safe_words if isinstance(item, str) and item.strip()]
        if safe_tokens:
            extra_segment = " ".join(safe_tokens)
            if extra_segment not in base_prompt:
                base_prompt = f"{base_prompt} | {extra_segment}" if base_prompt else extra_segment
            for token in safe_tokens:
                if token not in fallback_tags and len(fallback_tags) < max_tags:
                    fallback_tags.append(token)

        trimmed_title = self._truncate(fallback_title, max_title)
        trimmed_desc = self._truncate(fallback_desc, max_desc)
        trimmed_tags = fallback_tags[:max_tags]

        if (
            trimmed_title != fallback_title
            or trimmed_desc != fallback_desc
            or len(trimmed_tags) != len(fallback_tags)
        ):
            log_event(
                "prompt_fallback_trimmed",
                original={
                    "title": fallback_title,
                    "description": fallback_desc,
                    "tags": fallback_tags,
                },
                trimmed={
                    "title": trimmed_title,
                    "description": trimmed_desc,
                    "tags": trimmed_tags,
                },
            )

        final_seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        return PromptCandidate(
            prompt=base_prompt,
            title=trimmed_title,
            description=trimmed_desc,
            tags=trimmed_tags,
            seed=final_seed,
        )

    def load_from_file(self, path: Path) -> None:
        """从文本文件加载额外文案，每行一条。"""

        if not path.exists():
            return
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.extend_texts(lines)


def load_prompt_pool(pool_path: Optional[Path] = None, extra_texts: Optional[Iterable[str]] = None) -> PromptPool:
    """工厂方法：根据外部数据创建 PromptPool。"""

    pool = PromptPool()
    if pool_path:
        pool.load_from_file(pool_path)
    if extra_texts:
        pool.extend_texts(extra_texts)
    return pool


__all__ = ["PromptPool", "PromptCandidate", "load_prompt_pool"]
