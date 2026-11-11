"""数据模型"""

from dataclasses import dataclass, field


@dataclass
class Segment:
    """m3u8 分片"""
    index: int              # 在 m3u8 中的序号（从 1 开始）
    duration: float         # 时长（秒）
    filename: str           # 分片文件名
    is_ad: bool = False     # 是否被识别为广告
    ad_reason: str = ""     # 识别为广告的依据

    def __repr__(self):
        tag = " [AD]" if self.is_ad else ""
        return f"#{self.index} {self.filename} ({self.duration:.1f}s){tag}"


@dataclass
class M3U8Info:
    """m3u8 文件解析结果"""
    filepath: str
    segments: list[Segment] = field(default_factory=list)
    target_duration: int = 10
    media_sequence: int = 0
    discontinuity_positions: list[int] = field(default_factory=list)
    header_lines: list[str] = field(default_factory=list)
    total_duration: float = 0.0

    @property
    def ad_segments(self) -> list[Segment]:
        return [s for s in self.segments if s.is_ad]

    @property
    def clean_segments(self) -> list[Segment]:
        return [s for s in self.segments if not s.is_ad]


@dataclass
class AdDetectionRule:
    """广告识别规则"""
    keywords: list[str] = field(default_factory=lambda: [
        "ad", "promo", "vip", "advert", "advertisement",
        "guanggao", "广告", "pianhua", "片花",
    ])
    typical_durations: list[float] = field(default_factory=lambda: [15.0, 30.0, 60.0])
    duration_tolerance: float = 1.0  # 时长容差（秒）


@dataclass
class ProcessResult:
    """处理结果"""
    source_path: str
    output_path: str
    total_segments: int = 0
    ad_segments: int = 0
    ad_groups: int = 0
    removed_duration: float = 0.0
    remaining_duration: float = 0.0
    details: list[str] = field(default_factory=list)