"""m3u8 索引修复 —— 删除广告行并修正元标签"""

from pathlib import Path

from src.models.segment import M3U8Info


def build_m3u8_content(info: M3U8Info) -> str:
    """生成修复后的 m3u8 内容（不落盘），供移动端保存对话框使用"""
    source = Path(info.filepath)
    seg_dir = source.parent / source.stem
    lines = _build_m3u8_content(info, seg_dir)
    return "\n".join(lines) + "\n"


def fix_m3u8(info: M3U8Info, output_path: str | None = None) -> str:
    """根据识别结果生成修复后的 m3u8 文件"""
    source = Path(info.filepath)

    if output_path is None:
        stem = source.stem
        output_path = str(source.parent / f"[去广告]{stem}.m3u8")
    else:
        output_path = str(Path(output_path))

    if info.segments:
        content = build_m3u8_content(info)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")

    return output_path


def _build_m3u8_content(info: M3U8Info, seg_dir: Path) -> list[str]:
    """构建修复后的 m3u8 内容"""
    lines = ["#EXTM3U", f"#EXT-X-VERSION:3"]

    clean = [s for s in info.segments if not s.is_ad]

    max_dur = max((s.duration for s in clean), default=10)
    lines.append(f"#EXT-X-TARGETDURATION:{int(max_dur) + 1}")
    lines.append("#EXT-X-MEDIA-SEQUENCE:0")

    for seg in clean:
        lines.append(f"#EXTINF:{seg.duration:.3f},")
        seg_path = seg_dir / seg.filename
        if seg_path.exists():
            lines.append(str(seg_path.resolve()))
        else:
            lines.append(seg.filename)

    lines.append("#EXT-X-ENDLIST")
    return lines