# DeskBuddy 🤖

Python / PySide6 桌面陪伴应用，提供 GIF 助手、定时提醒和局域网聊天。

源码位于 `deskbuddy/`。完整运行说明、配置位置、检查结果与 macOS 构建方式见 [项目说明](deskbuddy/README.md)。

在 macOS 上使用 Python 3.12 运行：

```bash
bash deskbuddy/scripts/build_macos.sh
```

输出 `.app` 及对应芯片的 ZIP。仓库也提供 [Apple Silicon / Intel 自动构建流程](.github/workflows/macos-build.yml)。macOS 实机验证及正式签名、公证状态见项目说明。
