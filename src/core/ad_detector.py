"""三层规则广告分片识别"""

import re
from collections import Counter
from itertools import groupby

from src.models.segment import AdDetectionRule, M3U8Info, Segment


def detect_ads(info: M3U8Info, rule: AdDetectionRule | None = None) -> M3U8Info:
    """执行三层规则识别广告分片，直接在传入的 info 上标记"""
    if rule is None:
        rule = AdDetectionRule()

    _layer1_keyword(info, rule)
    _layer2_duration(info, rule)
    _layer3_discontinuity(info)

    return info


def _layer1_keyword(info: M3U8Info, rule: AdDetectionRule):
    """第一层：关键词匹配"""
    if not rule.keywords:
        return

    pattern = re.compile("|".join(re.escape(k) for k in rule.keywords), re.IGNORECASE)

    for seg in info.segments:
        if seg.is_ad:
            continue
        if pattern.search(seg.filename):
            seg.is_ad = True
            seg.ad_reason = "关键词命中"


def _layer2_duration(info: M3U8Info, rule: AdDetectionRule):
    """第二层：时长校验 —— 以 DISCONTINUITY 为天然边界，
    相邻断点之间的片段作为整体判断是否为广告块。
    无 DISCONTINUITY 时退化为滑动窗口扫描。"""
    if not rule.typical_durations:
        return

    tolerance = rule.duration_tolerance
    segments = info.segments
    n = len(segments)

    # 统计时长基线（取众数）
    dur_rounded = [round(s.duration) for s in segments]
    baseline_dur = Counter(dur_rounded).most_common(1)[0][0]

    def _is_anomalous(seg: Segment) -> bool:
        return abs(round(seg.duration) - baseline_dur) >= 2

    if info.discontinuity_positions:
        # 以 DISCONTINUITY 为边界，逐块判断
        boundaries = sorted(info.discontinuity_positions)
        if boundaries[-1] < n:
            boundaries.append(n)

        for i in range(len(boundaries) - 1):
            lo = boundaries[i]
            hi = boundaries[i + 1]
            block = segments[lo:hi]
            if len(block) < 1:
                continue

            block_dur = sum(s.duration for s in block)
            hit_target = any(
                abs(block_dur - target) <= tolerance
                for target in rule.typical_durations
            )
            anomalous_count = sum(1 for s in block if _is_anomalous(s))
            is_anomalous_block = anomalous_count >= max(1, len(block) // 2)

            # 正片首块（第一个 DISCONTINUITY 之前）：跳过，避免误判片头
            is_head = (i == 0) and len(info.discontinuity_positions) > 1

            if is_head:
                continue

            should_flag = hit_target or is_anomalous_block

            if should_flag:
                for s in block:
                    if not s.is_ad:
                        s.is_ad = True
                        if hit_target:
                            s.ad_reason = f"时长校验 (DISCONTINUITY 间 {len(block)}段×{block_dur:.1f}s)"
                        else:
                            s.ad_reason = f"DISCONTINUITY 间异常块 ({anomalous_count}/{len(block)}段异常)"
    else:
        # 无 DISCONTINUITY：滑动窗口扫描，要求半数以上分片异常
        for dur_target in sorted(rule.typical_durations):
            i = 0
            while i < n:
                total = 0.0
                j = i
                while j < n and total < dur_target + tolerance:
                    total += segments[j].duration
                    if abs(total - dur_target) <= tolerance:
                        group = segments[i : j + 1]
                        if len(group) >= 2 and not any(s.is_ad for s in group):
                            anomalous_count = sum(1 for s in group if _is_anomalous(s))
                            if anomalous_count >= len(group) // 2:
                                for s in group:
                                    s.is_ad = True
                                    s.ad_reason = f"时长校验 ({len(group)}段×{dur_target}s)"
                                i = j + 1
                                break
                    j += 1
                i += 1


def _layer3_discontinuity(info: M3U8Info):
    """第三层：DISCONTINUITY 边界锚定 ——
    广告块通常被 DISCONTINUITY 边界分隔，据此校验前两层标记的广告块边界
    是否与断点对齐，为识别结果补充锚定依据（仅标注，不改变标记结果）。"""
    if not info.discontinuity_positions:
        return

    boundaries = set(info.discontinuity_positions)
    n = len(info.segments)

    # 将连续广告片段分组为广告块
    blocks: list[list[Segment]] = []
    current: list[Segment] = []
    for seg in info.segments:
        if seg.is_ad:
            current.append(seg)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)

    for block in blocks:
        start_idx = block[0].index
        end_idx = block[-1].index

        # 广告块起始应位于断点之后（或视频开头），结束应位于断点处（或视频末尾）
        anchored_start = (start_idx == 1) or ((start_idx - 1) in boundaries)
        anchored_end = (end_idx == n) or (end_idx in boundaries)

        note = "DISCONTINUITY 锚定" if (anchored_start and anchored_end) else "DISCONTINUITY 未对齐"
        for seg in block:
            if "DISCONTINUITY" not in seg.ad_reason:
                seg.ad_reason += f" + {note}"


def analyze_ads(info: M3U8Info) -> list[dict]:
    """分析广告分片，返回连续的广告段信息"""
    ad_segments = [s for s in info.segments if s.is_ad]
    if not ad_segments:
        return []

    groups = []
    for _, g in groupby(enumerate(ad_segments), lambda x: x[0] - x[1].index):
        group_items = list(g)
        segs = [item[1] for item in group_items]
        total_dur = sum(s.duration for s in segs)
        groups.append({
            "segments": segs,
            "count": len(segs),
            "duration": round(total_dur, 1),
            "start_index": segs[0].index,
            "end_index": segs[-1].index,
        })

    return groups