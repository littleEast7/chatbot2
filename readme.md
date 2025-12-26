# DeskBuddy 🤖

**DeskBuddy** is a lightweight, extensible desktop assistant framework built with Python and PySide6. It features a floating animated avatar that sits on your screen, manages scheduled reminders, and listens for remote commands via HTTP.

Designed with a modular architecture, it serves as a perfect foundation for building advanced AI assistants, VTubers, or productivity companions.

---

## ✨ Key Features

* **🎈 Floating Widget:** A frameless, transparent, always-on-top window that sits quietly in your desktop corner.
* **🎞️ Animated Avatar:** Supports GIF playback (easy to swap with your own assets).
* **⏰ Built-in Scheduler:** Configure recurring reminders (e.g., "Drink water") via a simple YAML file.
* **⚡ Remote Control:** Embedded Flask server allows you to trigger events/reminders from external scripts, webhooks, or other devices.
* **🧩 Modular Design:** Clean separation of concerns (UI, Logic, Server, Config) making it easy to integrate LLMs (OpenAI/Claude), TTS, or Live2D later.

---

## 📂 Project Structure

```text
deskbuddy/
├── main.py                 # Application Entry Point
├── requirements.txt        # Python Dependencies
├── README.md               # Documentation
├── config.yaml             # User Configuration
│
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration Loader
│   ├── scheduler.py        # Background Task Manager (APScheduler)
│   ├── server.py           # HTTP API Server (Flask)
│   └── ui/
│       ├── __init__.py
│       └── assistant.py    # PySide6 Floating Window Logic
│
└── assets/
    └── assistant.gif       # Your Avatar (Replace this!)

```

---

## 🚀 Getting Started

### 1. Prerequisites

* Python 3.8+
* Windows, macOS, or Linux

### 2. Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/your-username/deskbuddy.git
cd deskbuddy
pip install -r requirements.txt

```

### 3. Configuration

Edit `config.yaml` to customize your assistant's position and scheduled tasks:

```yaml
window:
  x: 1600  # Horizontal position on screen
  y: 800   # Vertical position on screen

reminders:
  - type: interval
    minutes: 30
    text: "Time to stretch! 🧘"

server:
  host: 0.0.0.0
  port: 9000

```

### 4. Run

Start the assistant:

```bash
python main.py

```

---

## 📡 Remote Control (API)

DeskBuddy runs a local HTTP server (default port 9000). You can send POST requests to trigger the assistant from anywhere (CI/CD pipelines, smart home devices, or other scripts).

**Endpoint:** `POST /remind`

**Example using cURL:**

```bash
curl -X POST http://127.0.0.1:9000/remind \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting starts in 5 minutes! 📅"}'

```

---

## 🛠️ Customization

### Change the Avatar

Simply replace `assets/assistant.gif` with any transparent GIF of your choice.

### Add Logic

* **UI Logic:** Edit `app/ui/assistant.py` to change window behavior or add animations.
* **Background Tasks:** Edit `app/scheduler.py` to add complex cron jobs.

---

## 🗺️ Roadmap

This project is currently a skeleton. Future updates will include:

* [ ] **Speech Bubbles:** Comic-style dialog boxes for notifications.
* [ ] **System Tray:** Minimize to tray with a right-click context menu.
* [ ] **State Management:** Support for multiple animations (Idle, Talking, Sleeping).
* [ ] **Voice Support:** Integration with TTS (Text-to-Speech) engines.
* [ ] **AI Integration:** Connect to LLMs to make the assistant conversational.
* [ ] **Security:** API Token authentication for remote requests.

---

## 📄 License

MIT License. Feel free to use this as a base for your own projects!