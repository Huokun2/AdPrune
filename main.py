"""净播 AdPrune — m3u8 广告清理器

纯文本处理工具：读取本地 m3u8 → 按三层规则识别广告分片 →
删掉对应索引行并修正元标签 → 生成新 m3u8。
全程不缝合、不重编码、不动物理分片。
"""

import flet as ft

from src.ui.app import main


if __name__ == "__main__":
    ft.run(main)