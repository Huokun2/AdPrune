"""主界面"""

import asyncio
import json
import os
from pathlib import Path

import flet as ft

from src.core.ad_detector import AdDetectionRule, analyze_ads, detect_ads
from src.core.m3u8_fixer import build_m3u8_content, fix_m3u8
from src.core.m3u8_parser import parse_m3u8
from src.models.segment import ProcessResult
from src.ui import theme


class AdPruneApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self._setup_page()

        self.selected_files: list[str] = []
        self.m3u8_info = None
        self.process_result: ProcessResult | None = None
        # 移动端待保存内容: (文件名, m3u8 文本内容)
        self.pending_saves: list[tuple[str, str]] = []
        # 记住的移动端保存目录
        self.save_dir: str | None = self._load_save_dir()

        self._build_ui()
        self._bind_events()

    def _setup_page(self):
        self.page.title = "净播 AdPrune"
        self.page.theme = theme.get_theme()
        self.page.bgcolor = theme.BG_SURFACE
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.window.width = 400
        self.page.window.min_width = 360
        self.page.window.height = 780
        self.page.window.min_height = 600

    def _build_ui(self):
        # ── 文件选择区 ──
        self.file_path_text = ft.Text(
            "未选择文件",
            color=theme.TEXT_HINT,
            size=13,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.file_info_text = ft.Text("", color=theme.TEXT_SECONDARY, size=12)

        self.file_picker_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            icon_color=theme.TEXT_SECONDARY,
            icon_size=20,
            tooltip="选择 m3u8 文件（可多选）",
        )

        self.file_picker = ft.FilePicker()

        # ── 处理按钮 ──
        self.progress = ft.ProgressBar(
            visible=False,
            color=theme.PRIMARY,
            bgcolor=ft.Colors.TRANSPARENT,
        )

        self.process_btn = ft.FilledButton(
            content="开始处理",
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
            style=ft.ButtonStyle(
                bgcolor=theme.PRIMARY,
                color=theme.TEXT_ON_PRIMARY,
                padding=ft.padding.Padding.symmetric(horizontal=32, vertical=14),
                shape=ft.RoundedRectangleBorder(radius=theme.RADIUS),
                elevation=0,
            ),
        )

        # ── 覆盖原文件选项 ──
        self.overwrite_switch = ft.Switch(
            value=False,
            active_color=theme.PRIMARY,
        )

        # ── 结果区 ──
        self.result_title = ft.Text("", size=15, weight=ft.FontWeight.W_600, visible=False)
        self.result_output_path = ft.Text("", size=12, color=theme.TEXT_SECONDARY, visible=False)
        self.log_column = ft.Column(spacing=4, visible=False)
        self.save_list_column = ft.Column(spacing=4, visible=False)
        self.save_all_btn = ft.FilledButton(
            content="保存全部",
            icon=ft.Icons.SAVE_ALT_ROUNDED,
            visible=False,
            style=ft.ButtonStyle(
                bgcolor=theme.PRIMARY,
                color=theme.TEXT_ON_PRIMARY,
                padding=ft.padding.Padding.symmetric(horizontal=32, vertical=12),
                shape=ft.RoundedRectangleBorder(radius=theme.RADIUS),
                elevation=0,
            ),
        )
        self.change_dir_btn = ft.TextButton(
            content="更改文件夹",
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            visible=False,
            style=ft.ButtonStyle(
                color=theme.PRIMARY,
                padding=ft.padding.Padding.symmetric(horizontal=16, vertical=12),
            ),
        )
        self.result_container = ft.Container(
            visible=False,
            padding=ft.padding.Padding.all(16),
            border_radius=theme.RADIUS,
            bgcolor=theme.BG_WHITE,
            content=ft.Column([
                self.result_title,
                self.result_output_path,
                ft.Divider(height=16, color=theme.BG_SURFACE),
                self.log_column,
                self.save_list_column,
                ft.Row([
                    self.save_all_btn,
                    self.change_dir_btn,
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            ]),
        )

        # ── 统计行 ──
        self.stats_row = ft.Row(visible=False, spacing=24, wrap=True)
        self.stat_widgets: dict[str, ft.Text] = {}
        for label in ["总分片", "广告段", "移除时长", "剩余时长"]:
            t = ft.Text("—", size=20, weight=ft.FontWeight.W_700, color=theme.PRIMARY_LIGHT)
            l = ft.Text(label, size=11, color=theme.TEXT_HINT)
            self.stat_widgets[label] = t
            self.stats_row.controls.append(
                ft.Column([t, l], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

        # ── 组装页面 ──
        self.page.add(
            ft.SafeArea(
                content=ft.Column([
                    self._build_app_bar(),
                    ft.Container(
                        padding=ft.padding.Padding.symmetric(horizontal=20),
                        content=ft.Column([
                            self._build_file_section(),
                            ft.Divider(height=24, color=ft.Colors.TRANSPARENT),
                            ft.Container(content=self.process_btn, alignment=ft.alignment.Alignment.CENTER),
                            ft.Row([
                                self.overwrite_switch,
                                ft.Text(
                                    "覆盖原文件（不添加「去广告」前缀）",
                                    size=13,
                                    color=theme.TEXT_SECONDARY,
                                ),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
                            self.progress,
                            ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                            self.stats_row,
                            ft.Divider(height=12, color=ft.Colors.TRANSPARENT),
                            self.result_container,
                        ]),
                    ),
                ]),
            )
        )

    def _build_app_bar(self):
        return ft.Container(
            bgcolor=theme.BG_WHITE,
            padding=ft.padding.Padding.only(left=20, top=48, right=20, bottom=16),
            content=ft.Row([
                ft.Column([
                    ft.Text("净播 AdPrune", size=22, weight=ft.FontWeight.W_700, color=theme.TEXT_PRIMARY),
                    ft.Text("m3u8 本地广告清理 · 不转码不损画质", size=12, color=theme.TEXT_HINT),
                ]),
            ]),
        )

    def _build_file_section(self):
        return ft.Container(
            bgcolor=theme.BG_WHITE,
            border_radius=theme.RADIUS,
            padding=ft.padding.Padding.all(16),
            content=ft.Column([
                ft.Text("选择文件", size=14, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                ft.Divider(height=12, color=ft.Colors.TRANSPARENT),
                ft.Row([
                    ft.Icon(ft.Icons.VIDEO_FILE_OUTLINED, color=theme.PRIMARY_LIGHT, size=20),
                    ft.Column([self.file_path_text, self.file_info_text], spacing=2, expand=True),
                    self.file_picker_btn,
                ]),
            ]),
        )

    def _bind_events(self):
        self.file_picker_btn.on_click = lambda e: asyncio.ensure_future(
            self._pick_file(),
        )
        self.process_btn.on_click = lambda e: asyncio.ensure_future(self._on_process(e))
        self.save_all_btn.on_click = lambda e: asyncio.ensure_future(self._on_save_all(e))
        self.change_dir_btn.on_click = lambda e: asyncio.ensure_future(self._on_change_dir(e))

    async def _pick_file(self):
        result = await self.file_picker.pick_files(
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["m3u8", "zip"],
            allow_multiple=True,
        )
        if result and len(result) > 0:
            self.selected_files = [f.path for f in result if f.path]
            total_size = sum(f.size or 0 for f in result)
            first_name = result[0].name

            if len(result) == 1:
                self.file_path_text.value = first_name
            else:
                self.file_path_text.value = f"{first_name} 等 {len(result)} 个文件"

            self.file_path_text.color = theme.TEXT_PRIMARY
            self.file_info_text.value = f"{len(result)} 个文件 · 共 {total_size / 1024:.1f} KB"
            self.page.update()

    async def _on_process(self, e):
        if not self.selected_files:
            return

        self.progress.visible = True
        self.process_btn.disabled = True
        self.page.update()

        try:
            await asyncio.sleep(0.1)

            rule = AdDetectionRule()
            all_ad_groups: list[dict] = []
            aggregated = ProcessResult(
                source_path=f"{len(self.selected_files)} 个文件",
                output_path="—",
            )
            output_paths: list[str] = []
            self.pending_saves = []
            overwrite = self.overwrite_switch.value

            for filepath in self.selected_files:
                info = parse_m3u8(filepath)
                detect_ads(info, rule)
                ad_groups = analyze_ads(info)
                if self.page.platform.is_mobile():
                    content = build_m3u8_content(info)
                    filename = Path(filepath).name if overwrite else f"[去广告]{Path(filepath).name}"
                    self.pending_saves.append((filename, content))
                else:
                    if overwrite:
                        output = fix_m3u8(info, output_path=str(filepath))
                    else:
                        output = fix_m3u8(info)
                    if output:
                        output_paths.append(output)

                for g in ad_groups:
                    g["source_file"] = Path(filepath).name
                all_ad_groups.extend(ad_groups)

                aggregated.total_segments += len(info.segments)
                aggregated.ad_segments += len(info.ad_segments)
                aggregated.ad_groups += len(ad_groups)
                aggregated.removed_duration += round(sum(s.duration for s in info.ad_segments), 1)
                aggregated.remaining_duration += round(sum(s.duration for s in info.clean_segments), 1)

            aggregated.output_path = output_paths[0] if len(output_paths) == 1 else "—"
            self.process_result = aggregated
            self._show_result(aggregated, all_ad_groups, output_paths)

        except Exception as ex:
            self._show_error(str(ex))
        finally:
            self.progress.visible = False
            self.process_btn.disabled = False
            self.page.update()

    def _show_result(self, result: ProcessResult, ad_groups: list[dict], output_paths: list[str] | None = None):
        self.stats_row.visible = True
        self.stat_widgets["总分片"].value = str(result.total_segments)
        self.stat_widgets["广告段"].value = str(result.ad_groups)
        self.stat_widgets["移除时长"].value = f"{result.removed_duration:.2f}s"
        self.stat_widgets["剩余时长"].value = f"{result.remaining_duration:.2f}s"

        if result.ad_groups > 0:
            self.stat_widgets["广告段"].color = theme.AD_TAG
        else:
            self.stat_widgets["广告段"].color = theme.SUCCESS

        self.result_container.visible = True
        self.result_title.visible = True
        self.result_output_path.visible = True
        self.result_output_path.color = theme.TEXT_SECONDARY

        if result.ad_groups > 0:
            if self.page.platform.is_mobile():
                self.result_title.value = f"✓ 已发现 {result.ad_groups} 段广告"
            else:
                self.result_title.value = f"✓ 已移除 {result.ad_groups} 段广告"
            self.result_title.color = theme.SUCCESS
        else:
            self.result_title.value = "未检测到广告"
            self.result_title.color = theme.TEXT_SECONDARY

        if self.page.platform.is_mobile():
            if self.save_dir:
                self.result_output_path.value = (
                    f"待保存 {len(self.pending_saves)} 个文件 · 保存到: {self.save_dir}"
                )
            else:
                self.result_output_path.value = f"待保存 {len(self.pending_saves)} 个文件"
            self._render_save_list()
            self.save_all_btn.visible = True
            self.change_dir_btn.visible = True
        else:
            self.save_all_btn.visible = False
            self.change_dir_btn.visible = False
            self.save_list_column.visible = False
            if output_paths and len(output_paths) > 1:
                parent = str(Path(output_paths[0]).parent)
                self.result_output_path.value = f"输出目录: {parent} ({len(output_paths)} 个文件)"
            else:
                self.result_output_path.value = f"输出: {result.output_path}"

        self.log_column.visible = True
        self.log_column.controls.clear()

        if ad_groups:
            file_summaries: dict[str, dict] = {}
            for group in ad_groups:
                key = group.get("source_file", "未知文件")
                if key not in file_summaries:
                    file_summaries[key] = {"groups": 0, "segments": 0, "duration": 0.0}
                file_summaries[key]["groups"] += 1
                file_summaries[key]["segments"] += group["count"]
                file_summaries[key]["duration"] += group["duration"]

            for filename, summary in file_summaries.items():
                self.log_column.controls.append(
                    ft.Container(
                        bgcolor=theme.BG_SURFACE,
                        border_radius=theme.RADIUS_SM,
                        padding=ft.padding.Padding.symmetric(horizontal=12, vertical=8),
                        content=ft.Column([
                            ft.Text(filename, size=12, weight=ft.FontWeight.W_600, color=theme.TEXT_PRIMARY),
                            ft.Text(
                                f"移除 {summary['groups']} 段广告 · 共 {summary['segments']} 个分片 · {summary['duration']:.1f}s",
                                size=12,
                                color=theme.TEXT_SECONDARY,
                            ),
                        ], spacing=2),
                    )
                )
        else:
            self.log_column.controls.append(
                ft.Text("所有分片均通过检测，未发现广告。", size=13, color=theme.TEXT_HINT)
            )

        self.page.update()

    def _render_save_list(self):
        self.save_list_column.visible = True
        self.save_list_column.controls.clear()
        for filename, _ in self.pending_saves:
            self.save_list_column.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, color=theme.TEXT_HINT, size=16),
                    ft.Text(filename, size=13, color=theme.TEXT_PRIMARY),
                ], spacing=8)
            )

    async def _on_save_all(self, e):
        if not self.pending_saves:
            return

        target_dir = self.save_dir
        if not target_dir:
            # 首次保存：弹目录选择器让用户定位目标文件夹
            target_dir = await self.file_picker.get_directory_path(
                dialog_title="选择保存文件夹",
            )
            if not target_dir:
                return

        try:
            saved_count = 0
            for filename, content in self.pending_saves:
                dest = Path(target_dir) / filename
                dest.write_text(content, encoding="utf-8")
                saved_count += 1

            # 记住本次保存目录，下次直接写入不再弹选择器
            self.save_dir = target_dir
            self._store_save_dir(target_dir)

            self.result_output_path.value = f"已保存 {saved_count} 个文件到: {target_dir}"
            self.result_output_path.color = theme.SUCCESS
            if self.process_result and self.process_result.ad_groups > 0:
                self.result_title.value = f"✓ 已移除 {self.process_result.ad_groups} 段广告"
                self.result_title.color = theme.SUCCESS
            self.save_all_btn.visible = False
            self.page.update()
        except Exception as ex:
            err = str(ex).lower()
            if any(k in err for k in ("permission", "eacces", "operation not permitted", "read-only")):
                self._show_permission_error()
            else:
                self._show_error(f"保存失败: {ex}")

    async def _on_change_dir(self, e):
        target_dir = await self.file_picker.get_directory_path(
            dialog_title="选择保存文件夹",
        )
        if not target_dir:
            return

        self.save_dir = target_dir
        self._store_save_dir(target_dir)

        self.result_output_path.visible = True
        self.result_output_path.value = (
            f"已选择保存文件夹: {target_dir}（待保存 {len(self.pending_saves)} 个文件）"
        )
        self.result_output_path.color = theme.TEXT_SECONDARY
        self.page.update()

    def _config_path(self) -> Path:
        data_dir = os.environ.get("FLET_APP_STORAGE_DATA")
        base = Path(data_dir) if data_dir else Path.cwd()
        return base / "adprune_config.json"

    def _load_save_dir(self) -> str | None:
        try:
            cfg = self._config_path()
            if cfg.exists():
                data = json.loads(cfg.read_text(encoding="utf-8"))
                return data.get("save_dir")
        except Exception:
            pass
        return None

    def _store_save_dir(self, path: str):
        try:
            cfg = self._config_path()
            cfg.write_text(
                json.dumps({"save_dir": path}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _show_error(self, message: str):
        self.result_container.visible = True
        self.result_title.visible = True
        self.result_title.value = "✗ 处理失败"
        self.result_title.color = theme.ERROR
        self.result_output_path.visible = False
        self.log_column.visible = True
        self.log_column.controls.clear()
        self.log_column.controls.append(ft.Text(message, size=13, color=theme.ERROR))
        self.page.update()

    def _show_permission_error(self):
        self.result_container.visible = True
        self.result_title.visible = True
        self.result_title.value = "✗ 保存失败"
        self.result_title.color = theme.ERROR
        self.result_output_path.visible = False
        self.log_column.visible = True
        self.log_column.controls.clear()
        self.log_column.controls.append(
            ft.Text("未获得「所有文件访问」权限，无法写入所选文件夹。", size=13, color=theme.ERROR)
        )
        self.log_column.controls.append(
            ft.Text("点击下方按钮前往系统设置开启，返回后再点「保存全部」重试。", size=12, color=theme.TEXT_HINT)
        )
        self.log_column.controls.append(
            ft.FilledButton(
                content="去系统设置开启",
                icon=ft.Icons.SETTINGS_OUTLINED,
                on_click=lambda e: asyncio.ensure_future(self._on_open_settings()),
                style=ft.ButtonStyle(
                    bgcolor=theme.PRIMARY,
                    color=theme.TEXT_ON_PRIMARY,
                    shape=ft.RoundedRectangleBorder(radius=theme.RADIUS),
                ),
            )
        )
        self.page.update()

    async def _on_open_settings(self):
        try:
            await ft.UrlLauncher().launch_url("package:com.flet.adprune")
        except Exception:
            self._show_error("请手动前往 系统设置 → 应用 → AdPrune → 所有文件访问 开启权限。")


def main(page: ft.Page):
    AdPruneApp(page)
    page.update()