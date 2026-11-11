# 净播 AdPrune

m3u8 本地广告清理器 —— 不转码、不损画质。

纯文本处理工具：读取本地 m3u8 → 按三层规则识别广告分片 → 删掉对应索引行并修正元标签 → 生成新的 m3u8。
全程不缝合、不重编码、不动物理分片。

## 功能特性

- **三层广告识别规则**
  1. 关键词匹配：命中 `ad`、`promo`、`vip`、`advert`、`广告`、`片花` 等关键词的分片
  2. 时长校验：以 `#EXT-X-DISCONTINUITY` 为边界，识别时长异常的广告块；无断点时退化为滑动窗口扫描
  3. 断点锚定：结合 DISCONTINUITY 结构确认前两层标记
- **覆盖原文件**：可选直接覆盖原文件，或另存为 `[去广告]xxx.m3u8`
- **实时统计**：识别后显示「已发现 N 段广告」，保存完成后显示「已移除 N 段广告」

## 环境要求

- Python 3.11+
- Flet 1.x

## 本地运行

```bash
pip install flet
flet run
```

## 打包 Android APK

```bash
# 打包前先应用跳转补丁（幂等，可重复运行）
python patch_url_launcher.py

# 模拟器（x86_64）
flet build apk --arch x86_64

# 真机（多架构）
flet build apk
```

> ⚠️ 每次重新下载依赖或更换构建环境后，需重新运行 `python patch_url_launcher.py`。
> 该补丁修复了 Android 11+ 上「去系统设置开启」按钮无法跳转到权限页面的问题。

## Android 权限说明

本应用需要「所有文件访问权限」（`MANAGE_EXTERNAL_STORAGE`）才能读取任意目录下的 m3u8 文件。
该权限属于特殊权限，系统不会自动弹窗请求，需在应用内点击按钮后手动开启。

## 项目结构

```
AdPrune/
├── main.py                  # 入口
├── pyproject.toml           # Flet 项目配置
├── patch_url_launcher.py    # url_launcher_android 跳转补丁
└── src/
    ├── core/
    │   ├── m3u8_parser.py    # m3u8 解析
    │   ├── ad_detector.py    # 三层广告识别
    │   └── m3u8_fixer.py     # 索引修复
    ├── models/
    │   └── segment.py        # 数据模型
    └── ui/
        ├── app.py            # 主界面
        └── theme.py          # 主题
```

## License

[MIT](./LICENSE)