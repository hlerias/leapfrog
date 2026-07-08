# The lighter route: WSL (when VirtualBox is blocked)

Can't install VirtualBox? On many corporate machines you can't — installing a
hypervisor needs admin rights and is often blocked. **WSL** (the Windows
Subsystem for Linux) is Microsoft's own, built-in way to run Linux on Windows,
and it's frequently allowed where third-party virtualization isn't.

It's lighter than a full VM, boots in seconds, and shares your files with
Windows. Here's the whole setup.

## 1. Install WSL

Open **PowerShell as Administrator** (right-click the Start menu → **Terminal
(Admin)** or **Windows PowerShell (Admin)**), then run:

```powershell
wsl --install
```

This installs WSL along with Ubuntu automatically on Windows 10 and 11. Reboot
if it asks you to.

## 2. Launch Ubuntu

Open **Ubuntu** from the Start menu. The first launch takes a minute to set up,
then asks you to create a **username and password** — pick anything you'll
remember; this is your Linux account.

## 3. Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

It'll ask for the password you just set.

## 4. Install the toolchain

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

## 5. Get the repo

Same as the VirtualBox guide's step 8:

```bash
git clone https://github.com/hlerias/leapfrog.git && cd leapfrog && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## 6. Run a model locally — no key needed

Install [Ollama](https://ollama.com) and set the environment variables, exactly
as in the VirtualBox guide's step 9 — it works fine inside WSL:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=llama3.2
```

Low on RAM? Use `llama3.2:1b`.

## 7. Run a lab

```bash
python labs/08_trace.py
```

You should see a JSON trace print out. Done. 🎉

## Honest caveat

`wsl --install` needs **admin rights the first time**. If your machine is
locked down hard enough to block *both* VirtualBox and WSL, you still have
options:

- Run the **no-key labs** (`08_trace.py`, `03_eval_gate.py`, and the
  `sentence-transformers` ones) on any machine that already has Python.
- Use a **cloud sandbox** — a [GitHub Codespace](https://github.com/features/codespaces)
  or a Colab-style notebook — which runs Linux in your browser, no local install
  required.

## Tip: edit the labs in VS Code

Install [VS Code](https://code.visualstudio.com/) and its **WSL** extension.
You can then open the repo directly in Linux and edit the lab files with a full
editor — they live under your Linux home at `~/leapfrog`.
