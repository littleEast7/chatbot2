# DeskBuddy - 桌面陪伴助手

这是一个基于 Python 的桌面悬浮助手，具备定时提醒和远程控制功能。

## 快速开始

### 1. 安装依赖

确保你已经安装了 Python 3.8+。

```bash
pip install -r requirements.txt
```

### 2. 准备资源

项目默认需要一个 GIF 动图作为助手的形象。
请将你喜欢的 GIF 图片重命名为 `assistant.gif` 并放入 `assets` 文件夹中，替换掉默认的占位文件。

### 3. 运行

```bash
python main.py
```

## 功能

- **桌面悬浮**: 助手会一直显示在桌面最上层。
- **定时提醒**: 在 `config.yaml` 中配置提醒间隔和内容。
- **远程控制**: 可以通过 HTTP 请求触发提醒。

示例：
```bash
curl -X POST http://127.0.0.1:9000/remind \
  -H "Content-Type: application/json" \
  -d '{"text":"喝水时间到啦 💧"}'
```

## 配置

修改 `config.yaml` 文件来调整窗口位置、提醒设置和服务器端口。

