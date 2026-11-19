# DeskBuddy 桌面陪伴助手

Python / PySide6 桌面应用，支持 GIF 助手、定时提醒、局域网握手和消息。

## 开发运行

建议使用 Python 3.12（本次验证版本）。在本目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python main.py
```

启动第二个实例可使用 `python main.py --port 9001`。端口须在 1–65535 内；新端口配置继承默认配置并获得独立用户 ID。也可使用 `--config /absolute/path/config.yaml` 指定配置。端口占用或配置错误会显示启动错误，详细原因写入日志。

源码运行默认使用 `main.py` 所在目录的配置，不依赖当前工作目录。打包应用在首次启动时生成干净的默认配置，不会携带开发者的头像、IP、用户 ID 或测试配置。

## macOS 构建和安装

目标为 macOS 13+，分别构建 Apple Silicon（arm64）和 Intel（x86_64）版本。最低系统版本依据 [Qt 6.10 支持范围](https://doc.qt.io/qt-6.10/supported-platforms.html)，实际兼容性仍需在目标系统验收。

必须在 macOS 上构建；[PyInstaller 的产物与构建操作系统相关](https://www.pyinstaller.org/en/stable/operating-mode.html)。在 Mac 上安装 Python 3.12 和 Xcode Command Line Tools 后，在本目录执行：

```bash
bash scripts/build_macos.sh
```

如需指定 Python：

```bash
PYTHON_BIN=python3.12 bash scripts/build_macos.sh
```

脚本会安装依赖、运行回归测试、打包 GIF 资源和 Python 运行时、从临时工作目录启动实际应用验证握手/提醒/退出、检查签名结构，最后生成：

- `dist/DeskBuddy.app`
- `dist/DeskBuddy-macOS-arm64.zip` 或 `dist/DeskBuddy-macOS-x86_64.zip`

将 `.app` 拖入 Applications 后启动，无须另装 Python。脚本生成的是 PyInstaller 默认的临时签名应用，尚未使用 Apple Developer ID 签名和公证；从网络下载后可能受到 Gatekeeper 拦截。正式分发前应完成开发者签名、公证并在干净的 Mac 上安装验收，签名结构检查不等同于 Gatekeeper 放行。

仓库的 [macOS 构建工作流](../.github/workflows/macos-build.yml) 配置了两种架构的 runner。代码推送到 GitHub 后，可在 Actions → Build macOS app 中运行，并从成功任务的 Artifacts 下载 ZIP。工作流只有在回归测试、打包、产物启动检查及签名结构检查通过后才上传产物。

## 配置和日志

macOS 打包版本的配置、头像缓存和日志位于：

```text
~/Library/Application Support/DeskBuddy/
  config.yaml
  cache/
  deskbuddy.log
```

配置按原子替换方式保存，日志自动轮转。修改定时提醒、服务器地址等配置后需重启。配置缺失或为空时自动补全默认值；格式和关键字段不合法时明确报错。

```yaml
server:
  host: 0.0.0.0
  port: 9000
reminders:
  - type: interval
    minutes: 30
    text: 该起来活动一下啦 🧘
target_ip: ''
my_avatar: ''
```

`0.0.0.0` 用于局域网互联；仅本机使用可改为 `127.0.0.1`。当前 HTTP 为明文通信，默认没有口令，适用于可信局域网。不要直接映射至公网。可在双方配置的 `server.token` 中填入相同 ASCII 共享口令（不含空格），应用会发送/验证 `Authorization: Bearer <token>`。该口令不能替代 HTTPS 加密。

输入对方的 `IP:端口`，点击 🔗 连接；连接后点击对方头像可重新编辑地址。默认端口 9000，支持 IPv6（指定端口时用 `[::1]:9000`）。选择头像时使用有效且不超过 2 MiB 的图片。消息上限 10000 字符，聊天界面最多保留最近 500 条；消息目前仅保存在内存中。

首次跨设备连接时，macOS 的本地网络访问和防火墙设置须允许应用通信。睡眠期间提醒不会唤醒电脑；窗口、输入法和休眠恢复行为需按下方清单在实机验收。

HTTP 调用示例：

```bash
curl -X POST http://127.0.0.1:9000/remind \
  -H 'Content-Type: application/json' \
  -d '{"text":"喝水时间到啦 💧"}'
```

## 检查结果与验证范围

本次检查覆盖全部应用源码、配置、依赖和打包入口，已修复：

- 打包未收集 GIF、缺少 macOS `.app` bundle，导致应用资源和产物不完整。
- 配置及头像缓存使用当前目录，造成双击启动、切换目录、只读 app bundle 下读写失败。
- 空配置、部分配置及错误类型导致的启动异常；保存配置时存在写入中断损坏风险。
- HTTP 接收的字段缺少类型与大小校验；头像用户 ID 被直接拼入文件路径。
- 后台线程更新头像状态；聊天内容被 QLabel 当作富文本解释。
- 发送消息未检查 HTTP 错误状态；连接后无法在界面重新选择对方。
- 网络工作线程无上限且会阻止进程退出；HTTP 服务没有显式关闭流程；端口绑定失败未反馈给主界面。
- 提醒隐藏定时器重复触发；聊天控件长期积累；屏幕定位未考虑可用区域起点；macOS 中文字体缺少优先项。

验证命令：

```bash
python -m pytest -q
python scripts/smoke.py .venv/bin/python main.py
```

`smoke.py` 支持传入打包后的可执行文件，使用独立配置、临时工作目录和有限超时（Linux 30 秒，macOS 首次启动 90 秒，30 秒时记录堆栈诊断），验证启动、GIF、真实 HTTP 握手与提醒、Qt 信号处理和服务退出。Linux 使用 offscreen 插件；macOS 使用原生 Cocoa 插件。

本次已在 Linux / Python 3.12 上运行回归测试，完成 PyInstaller 实际构建，并验证源码及打包程序的启动和 HTTP/GUI 链路。macOS 构建工作流已配置但尚未执行，当前工作环境没有 Mac，不能据此声称 macOS 稳定性已通过验收。

Mac 实机待验收：

1. 两种芯片分别构建并从 Finder 双击启动，移动到 Applications 后仍能读写配置并播放 GIF。
2. 中文输入法、Retina 显示、多显示器、窗口关闭后进程退出。
3. 两台机器互发消息与头像，网络中断提示、重连、端口冲突反馈。
4. 定时提醒、睡眠唤醒后继续工作、至少数小时运行的内存和日志增长。
5. 正式签名、公证和干净系统安装；macOS 13 最低版本兼容性。

仓库历史上提交了 Linux `build/`、`dist/`、缓存和字节码。这些旧文件保留原样，不能当成本次构建产物；新增 `.gitignore` 用于防止继续引入生成文件，后续建议将已跟踪的生成物从版本库移除。
