"""文案池模块，负责生成去重的主题、风格、标签组合并执行敏感词过滤。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from hashlib import md5
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

from rich.console import Console

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

    def sample(self, max_title: int, max_desc: int, max_tags: int, seed: Optional[int] = None) -> PromptCandidate:
        """采样生成一条完整的 PromptCandidate。"""

        rnd = random.Random(seed or time.time_ns())
        attempts = 0
        while attempts < 10:
            base_text = rnd.choice(self.texts)
            if self._is_blacklisted(base_text):
                attempts += 1
                continue

            style = rnd.choice(self.styles) if self.styles else ""
            tag_candidates = rnd.sample(self.tags, k=min(max_tags, len(self.tags))) if self.tags else []
            prompt_parts = [base_text, style, ", ".join(tag_candidates[:3])]
            prompt = " | ".join([part for part in prompt_parts if part])
            prompt_hash = self._build_hash(base_text, style, tag_candidates)
            if prompt_hash in self.used_hashes:
                attempts += 1
                continue

            # 构建标题与描述
            title = self._truncate(f"{base_text} · {style}" if style else base_text, max_title)
            desc = self._truncate(
                f"灵感主题：{base_text}；风格：{style or '默认'}；标签：{' '.join(tag_candidates[:max_tags])}",
                max_desc,
            )
            if self._contains_sensitive(" ".join([prompt, title, desc])):
                console.log("[yellow]检测到敏感词，重新抽取文案。[/yellow]")
                attempts += 1
                continue
            if self._contains_ad(desc):
                console.log("[yellow]检测到疑似广告词，重新抽取。[/yellow]")
                attempts += 1
                continue

            tags = [tag for tag in tag_candidates[:max_tags] if tag]
            self.used_hashes.add(prompt_hash)
            final_seed = seed if seed is not None else rnd.randint(0, 2**32 - 1)
            return PromptCandidate(prompt=prompt, title=title, description=desc, tags=tags, seed=final_seed)

        raise RuntimeError("多次尝试后仍无法抽取安全文案，请检查敏感词配置或补充素材。")

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
