"""m3u8 索引文件解析"""

import re
from pathlib import Path

from src.models.segment import M3U8Info, Segment


def parse_m3u8(filepath: str) -> M3U8Info:
    """解析 m3u8 文件，提取所有分片信息"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    info = M3U8Info(filepath=str(path.resolve()))
    segment_index = 0
    pending_duration: float | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("#EXT-X-TARGETDURATION:"):
            try:
                info.target_duration = int(float(stripped.split(":")[1]))
            except (ValueError, IndexError):
                pass
            info.header_lines.append(line)

        elif stripped.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            try:
                info.media_sequence = int(stripped.split(":")[1])
            except (ValueError, IndexError):
                pass
            info.header_lines.append(line)

        elif stripped == "#EXT-X-DISCONTINUITY":
            info.discontinuity_positions.append(segment_index)
            info.header_lines.append(line)

        elif stripped.startswith("#EXTINF:"):
            duration = _parse_duration(stripped)
            if duration is not None:
                pending_duration = duration

        elif stripped and not stripped.startswith("#"):
            segment_index += 1
            filename = stripped

            if pending_duration is not None:
                seg = Segment(
                    index=segment_index,
                    duration=pending_duration,
                    filename=filename,
                )
                info.segments.append(seg)
                info.total_duration += pending_duration
                pending_duration = None
            else:
                seg = Segment(
                    index=segment_index,
                    duration=0.0,
                    filename=filename,
                )
                info.segments.append(seg)

    return info


def _parse_duration(line: str) -> float | None:
    """从 #EXTINF 行提取时长"""
    m = re.search(r"#EXTINF:\s*([\d.]+)", line)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None