"""为 url_launcher_android 插件应用跳转补丁。

背景
----
Flet 的 UrlLauncher.launch_url("package:xxx") 会经由 url_launcher_android 插件
发出 ACTION_VIEW intent。在部分 Android 设备（尤其 Android 11+ 模拟器）上，
package: scheme 没有匹配的 Activity 处理器，导致「去系统设置开启」按钮无响应。

本补丁将 package: scheme 重新路由到系统设置页：
- Android 11+（API 30+）：直接打开「所有文件访问」权限开关页
  （Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION）
- 更早版本：打开应用详情页（Settings.ACTION_APPLICATION_DETAILS_SETTINGS）

用法
----
在每次执行 `flet build apk` 之前运行一次（构建环境或依赖被重置后需重跑）：

    python patch_url_launcher.py

幂等：重复运行不会重复打补丁。
"""

import glob
import io
import os
import sys

PATCH_MARKER = "ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION"

OLD = """    Intent launchIntent =
        new Intent(Intent.ACTION_VIEW)
            .setData(Uri.parse(url))
            .putExtra(Browser.EXTRA_HEADERS, extractBundle(headers));"""

NEW = """    Uri uri = Uri.parse(url);
    Intent launchIntent;
    if ("package".equals(uri.getScheme())) {
      if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
        launchIntent =
            new Intent(
                android.provider.Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, uri);
      } else {
        launchIntent =
            new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS, uri);
      }
    } else {
      launchIntent =
          new Intent(Intent.ACTION_VIEW)
              .setData(uri)
              .putExtra(Browser.EXTRA_HEADERS, extractBundle(headers));
    }"""


def find_plugin_file():
    """在本地 Pub 缓存中定位 UrlLauncher.java。"""
    hosted_roots = []

    # Windows: %LOCALAPPDATA%\Pub\Cache\hosted
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        hosted_roots.append(os.path.join(local_app_data, "Pub", "Cache", "hosted"))

    # Linux / macOS: ~/.pub-cache/hosted
    hosted_roots.append(os.path.expanduser("~/.pub-cache/hosted"))

    for root in hosted_roots:
        pattern = os.path.join(
            root, "*", "url_launcher_android-*",
            "android", "src", "main", "java", "io", "flutter", "plugins",
            "urllauncher", "UrlLauncher.java",
        )
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]  # 存在多个版本时取最后一个

    return None


def main():
    path = find_plugin_file()
    if path is None:
        print("[错误] 未找到 url_launcher_android 插件的 UrlLauncher.java。")
        print("请先运行一次 `flet build apk` 或 `flet run`，使插件被下载到本地缓存。")
        sys.exit(1)

    print("找到插件文件：", path)

    with io.open(path, encoding="utf-8") as f:
        content = f.read()

    if PATCH_MARKER in content:
        print("补丁已存在，跳过。")
        return

    if '"package".equals(uri.getScheme())' in content:
        print("[错误] 检测到旧版补丁，请手动将该段代码更新为带 API 版本判断的版本。")
        sys.exit(1)

    if OLD not in content:
        print("[错误] 未能在插件文件中定位到需要替换的代码段。")
        print("可能原因：url_launcher_android 插件版本与预期不符。")
        print("请手动编辑该文件，或更新本脚本的 OLD 代码段。")
        sys.exit(1)

    content = content.replace(OLD, NEW, 1)

    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    print("补丁应用成功！现在可以运行 `flet build apk` 构建带跳转修复的安装包。")


if __name__ == "__main__":
    main()