# A clean Ubuntu lab VM on Windows

Want an isolated Linux machine to run the labs without touching your Windows
setup? A VirtualBox VM gives you exactly that: a clean, disposable Ubuntu
machine you can break and rebuild freely. Plan for about **45–60 minutes**,
most of it hands-off while things download and install. It's **free**.

You don't need to be a Linux expert. Follow the steps in order, copy-paste the
commands, and you'll have a working lab machine at the end.

## 1. Turn on virtualization

Your CPU can run virtual machines, but the feature is sometimes switched off.

1. Open **Task Manager** (`Ctrl+Shift+Esc`).
2. Go to the **Performance** tab → **CPU**.
3. Look for **"Virtualization: Enabled"** near the bottom.

If it says **Disabled**, reboot into your BIOS/UEFI (usually by tapping `Del`,
`F2`, `F10`, or `F12` right after power-on) and enable **Intel VT-x**,
**AMD-V**, or **SVM** — the exact name depends on your CPU. Save and reboot.

## 2. Install VirtualBox

1. Download the **"Windows hosts"** package from
   <https://www.virtualbox.org/wiki/Downloads>.
2. Run the installer — the defaults are fine. Click through and accept the
   network prompt.

Prefer a video walkthrough? Ubuntu's official guide covers this end to end:
<https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox>

## 3. Download Ubuntu

Grab **Ubuntu 26.04 LTS** (long-term support — stable and supported for years):

- Desktop download page: <https://ubuntu.com/download/desktop>
- Direct ISO: <https://releases.ubuntu.com/26.04/ubuntu-26.04-desktop-amd64.iso>

The file is about **6.5 GB**, so start it early. (24.04 LTS also works fine if
you already have it.)

## 4. Create the VM

1. Open VirtualBox → click **New**.
2. Name it `Leapfrog` and select the Ubuntu ISO you downloaded.
3. Leave **"Skip Unattended Installation" unchecked**, then set a username and
   password, and tick **Guest Additions** (this enables copy-paste and a
   resizable screen).
4. Give it **8192 MB** of RAM (4096 minimum), **4** CPUs, and a **40 GB**
   dynamically allocated disk.
5. Click **Finish**, then **Start**.

The VM installs itself in about **10–20 minutes**. Grab a coffee.

## 5. Enable copy-paste

Once Ubuntu is up, in the VM window's menu bar:
**Devices → Shared Clipboard → Bidirectional**.

Now you can copy commands from this guide straight into the VM.

## 6. Update the system

Open a terminal in Ubuntu (`Ctrl+Alt+T`) and run:

```bash
sudo apt update && sudo apt upgrade -y
```

It'll ask for the password you set in step 4.

## 7. Install the toolchain

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

## 8. Get the repo

```bash
git clone <repo-url> && cd leapfrog-labs && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

(Replace `<repo-url>` with this repository's clone URL.)

## 9. Run a model locally — no key needed

Install [Ollama](https://ollama.com) and pull a small model:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

Then point the labs at it:

```bash
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=llama3.2
```

Low on RAM? Use the smaller `llama3.2:1b` instead.

## 10. Run a lab

```bash
python labs/08_trace.py
```

You should see a JSON trace print out. That's it — you have a working lab
machine. 🎉

## Troubleshooting

- **Virtualization still shows Disabled** — you're likely in the wrong BIOS
  screen, or another hypervisor (Hyper-V) is holding the CPU feature. Search
  your PC model + "enable virtualization" for the exact key and menu.
- **The VM feels slow** — give it more RAM and CPUs in **Settings → System**,
  but stay inside the green range on the sliders; going into the red starves
  Windows.
- **Black screen after boot** — **Settings → Display**, raise the video memory
  and enable **3D acceleration**.
- **Copy-paste doesn't work** — make sure Guest Additions installed (step 4)
  and the shared clipboard is set to Bidirectional (step 5).
- **`pip install` or the model download fails** — those steps need internet
  access from inside the VM. Check the VM can reach the web (open Firefox in
  Ubuntu and load a page).
