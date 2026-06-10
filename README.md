# LoL Queue Accepter

A lightweight desktop app that automatically accepts League of Legends queue pops and sends phone notifications via [ntfy](https://ntfy.sh). Supports **ARAM** and **TFT** game modes with mode-specific notification behaviour.

# Author
Gabriel Nge

---

## Features

- Auto-accepts queue pops via the League Client LCU API (WebSocket)
- Sends phone notifications through ntfy when your game is ready
- **ARAM** — notifies on queue acceptance with your assigned champion and bench options
- **TFT** — notifies only when the game actually launches
- Toggle notifications on/off without stopping the app
- Silent mode — auto-accepts without sending any notification
- Clean GUI with a status indicator and stop button

---

## Requirements

- Windows 10/11
- Python 3.8+
- League of Legends installed at `C:\Riot Games\League of Legends\`
- [ntfy](https://ntfy.sh) app installed on your phone (free, no account needed)

---

## Installation

**1. Clone or download the project**
```
lol_queue_acceptor/
├── accept.py
└── launch.vbs
```

**2. Install Python dependencies**
```cmd
pip install requests psutil websocket-client urllib3
```

> `tkinter` and `win32api` come pre-installed with standard Python on Windows. If you get a `win32api` error run:
> ```cmd
> pip install pywin32
> ```

**3. Set up ntfy on your phone**
- Download the **ntfy** app (iOS or Android)
- Open the app and subscribe to a topic name of your choice (e.g. `lol-queue-yourname`)
- Make it unique so others can't accidentally subscribe to it

---

## Usage

**Option A — run directly**
```cmd
python accept.py
```

**Option B — launch silently from taskbar (recommended) - WINDOWS**

1. Right click Desktop → New → Shortcut
2. Set the location to:
   ```
   wscript.exe "C:\Users\YOUR_USERNAME\Desktop\lol_queue_acceptor\launch.vbs"
   ```
3. Name it `Queue Accepter`
4. Right click the shortcut → Pin to taskbar

---

## Configuration

When you open the app you'll see the following options:

| Setting | Description |
|---|---|
| **Game Mode** | Select ARAM or TFT — controls notification behaviour |
| **Send phone notifications** | Toggle ntfy notifications on or off |
| **Auto-accept only** | Accepts the queue but skips the notification |
| **Ntfy Topic** | Your unique ntfy topic name — must match what you subscribed to in the app |

Hit **Launch** once League is open and you're in a queue. The app connects to the League client and listens for a queue pop. Hit **Stop** at any time to disconnect.

---

## How it works

League of Legends runs a local API server (called the **LCU API**) on your machine while the client is open. It writes a `lockfile` to disk containing a port and one-time password that resets each session.

This app reads those credentials from the lockfile and opens a **WebSocket** connection to the LCU. When a queue pops, the LCU pushes a `ready-check` event in real time — the app catches it, calls the accept endpoint, and handles notifications based on your selected mode.

For ARAM champion detection, the app polls `/lol-champ-select/v1/session` and waits until the `FINALIZATION` phase when your champion and bench are assigned, then looks up champion names via Riot's [Data Dragon](https://ddragon.leagueoflegends.com) CDN.

---

## Troubleshooting

**"Lockfile not found — is League open?"**
The app must be launched *after* League of Legends is already open. The lockfile only exists while the client is running.

**Notification not received**
- Double check your ntfy topic matches exactly (case-sensitive)
- Make sure your phone has the ntfy app open and is subscribed to the topic
- Check you don't have "Auto-accept only" ticked

**WebSocket error**
- Make sure League is open and you're logged in
- Try hitting Stop and Launch again to reconnect

**`pythonw` not found when using launch.vbs**
Find your full Python path with:
```cmd
where pythonw
```
Then update `launch.vbs` replacing `pythonw` with the full path e.g:
```vbs
CreateObject("WScript.Shell").Run """C:\Users\YOUR_USERNAME\AppData\Local\Programs\Python\Python312\pythonw.exe"" ""C:\Users\YOUR_USERNAME\Desktop\lol_queue_acceptor\accept.py""", 0, False
```
