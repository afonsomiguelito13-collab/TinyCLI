# 🦁 Tiny Cloud CLI

**The Autonomous Programming Agent for the Terminal.**
*Benchmarks are honest.*

[![Version](https://img.shields.io/badge/version-15.0.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

**Languages / Idiomas / 語言 / 言語 / Языки:**
- [🇬🇧 English](#english)
- [🇵🇹 Português (PT)](#português-pt)
- [🇧🇷 Português (BR)](#português-br)
- [🇨🇳 中文](#中文)
- [🇯🇵 日本語](#日本語)
- [🇷🇺 Русский](#русский)

---

## English

The **Tiny Cloud CLI** is a lightweight and intelligent Command Line Interface (CLI) tool designed to transform your terminal (Termux, Linux, Raspberry Pi) into an AI-assisted development environment. It's not just a chat: it has **agent powers** to create files, execute commands, and test Python code in real-time.

### 🚀 Key Features
- **Agent Loop (Self-Correction):** Creates code, executes it, reads error logs, and **corrects itself**.
- **Model Pool & Failover:** DeepSeek, Agnes, GPT-6 Luna, Gemini. Auto-switch on failure.
- **Queue System (iPhone Queue):** Real queue for server stability.
- **Trust Workspace:** Asks permission before accessing new directories.
- **Ban System:** Blocks dangerous commands (like `rm -rf`).

### 🛠️ Installation
```bash
curl -sL https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main/public/install.sh | bash