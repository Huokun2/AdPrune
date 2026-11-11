"""主题配色常量"""

import flet as ft

# === 主色调 ===
PRIMARY = "#1565C0"           # 深蓝（主按钮、强调）
PRIMARY_LIGHT = "#1E88E5"     # 标准蓝
PRIMARY_DARK = "#0D47A1"      # 深蓝（hover）

# === 背景 ===
BG_WHITE = "#FFFFFF"
BG_SURFACE = "#F5F7FA"        # 浅灰背景（卡片区）
BG_INPUT = "#F0F4F8"          # 输入框背景

# === 文字 ===
TEXT_PRIMARY = "#1A1A1A"      # 主文字（近黑）
TEXT_SECONDARY = "#5F6B7A"    # 次要文字
TEXT_HINT = "#9EA7B3"         # 提示文字
TEXT_ON_PRIMARY = "#FFFFFF"   # 主色上的文字（白）

# === 功能色 ===
SUCCESS = "#2E7D32"
WARNING = "#E65100"
ERROR = "#C62828"
AD_TAG = "#FF6D00"            # 广告标记橙

# === 圆角 & 间距 ===
RADIUS = 12
RADIUS_SM = 8
GAP = 12
GAP_SM = 8


def get_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=PRIMARY_LIGHT,
            on_primary=TEXT_ON_PRIMARY,
            surface=BG_WHITE,
            on_surface=TEXT_PRIMARY,
            outline=TEXT_HINT,
        ),
        use_material3=True,
    )