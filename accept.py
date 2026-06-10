import tkinter as tk
import threading
import time
import win32api, win32con
import os
import requests
import psutil
import websocket
import json
import ssl
import base64
import urllib3

urllib3.disable_warnings()

# ─── LCU Helpers ──────────────────────────────────────────

def get_lcu_credentials():
    lockfile_path = r"C:\Riot Games\League of Legends\lockfile"
    if not os.path.exists(lockfile_path):
        print("Lockfile not found — is League open?")
        return None, None
    with open(lockfile_path) as f:
        parts = f.read().split(":")
        port, password = parts[2], parts[3]
        return port, password

def get_champion_name(champ_id):
    try:
        ver = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json", timeout=5
        ).json()[0]
        champs = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json",
            timeout=5
        ).json()["data"]
        for name, info in champs.items():
            if int(info["key"]) == champ_id:
                return name
    except Exception as e:
        print(f"Champion lookup failed: {e}")
    return f"Champion #{champ_id}"

def get_aram_champions(port, password):
    """Poll until FINALIZATION phase, then return assigned + bench champions."""
    try:
        for _ in range(20):
            resp = requests.get(
                f"https://127.0.0.1:{port}/lol-champ-select/v1/session",
                auth=("riot", password),
                verify=False,
                timeout=3
            )
            if resp.status_code != 200:
                time.sleep(2)
                continue

            data = resp.json()
            phase = data.get("timer", {}).get("phase", "")

            if phase == "FINALIZATION":
                local_id = data.get("localPlayerCellId")
                assigned_id = None
                for player in data.get("myTeam", []):
                    if player.get("cellId") == local_id:
                        assigned_id = player.get("championId")
                        break

                bench_ids = [c["championId"] for c in data.get("benchChampions", [])]
                assigned = get_champion_name(assigned_id) if assigned_id else None
                bench = [get_champion_name(cid) for cid in bench_ids if cid]
                return assigned, bench

            print(f"Phase: {phase} — waiting for FINALIZATION...")
            time.sleep(2)

    except Exception as e:
        print(f"Champ select query failed: {e}")
    return None, []

# ─── Notifications ────────────────────────────────────────

def send_notification(topic, title, message, tags="white_check_mark"):
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": "high", "Tags": tags},
            timeout=5
        )
    except Exception as e:
        print(f"Notification failed: {e}")

# ─── Misc ─────────────────────────────────────────────────

def is_process_running(name):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == name.lower():
            return True
    return False

# ─── GUI ──────────────────────────────────────────────────

class QueueAccepterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Queue Accepter")
        self.root.geometry("360x440")
        self.root.configure(bg="#0A0E13")
        self.root.resizable(False, False)
        self.running = False
        self.ws = None
        self.build_ui()

    def build_ui(self):
        tk.Label(self.root, text="QUEUE ACCEPTER", fg="#C89B3C", bg="#0A0E13",
                 font=("Courier", 13, "bold")).pack(pady=(20, 2))
        tk.Label(self.root, text="─" * 36, fg="#463714", bg="#0A0E13").pack()

        tk.Label(self.root, text="GAME MODE", fg="#785A28", bg="#0A0E13",
                 font=("Courier", 8)).pack(pady=(14, 5))
        self.mode = tk.StringVar(value="ARAM")
        frame = tk.Frame(self.root, bg="#0A0E13")
        frame.pack()
        for m in ["ARAM", "TFT"]:
            tk.Radiobutton(frame, text=m, variable=self.mode, value=m,
                           fg="#C89B3C", bg="#0A0E13", selectcolor="#463714",
                           activebackground="#0A0E13", font=("Courier", 11)).pack(side="left", padx=16)

        tk.Label(self.root, text="OPTIONS", fg="#785A28", bg="#0A0E13",
                 font=("Courier", 8)).pack(pady=(14, 5))
        self.notif_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.root, text="Send phone notifications", variable=self.notif_var,
                       fg="#C8AA6E", bg="#0A0E13", selectcolor="#0D1117",
                       activebackground="#0A0E13", font=("Courier", 10)).pack()
        self.silent_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.root, text="Auto-accept only (no notification)", variable=self.silent_var,
                       fg="#C8AA6E", bg="#0A0E13", selectcolor="#0D1117",
                       activebackground="#0A0E13", font=("Courier", 10)).pack()

        tk.Label(self.root, text="NTFY TOPIC", fg="#785A28", bg="#0A0E13",
                 font=("Courier", 8)).pack(pady=(14, 5))
        self.topic_var = tk.StringVar(value="lol-accept-ntfy-topic")
        tk.Entry(self.root, textvariable=self.topic_var, bg="#0D1117", fg="#C8AA6E",
                 insertbackground="#C89B3C", font=("Courier", 11),
                 width=28, relief="flat").pack(ipady=4)

        tk.Label(self.root, text="─" * 36, fg="#463714", bg="#0A0E13").pack(pady=(16, 0))
        self.status_var = tk.StringVar(value="Idle")
        tk.Label(self.root, textvariable=self.status_var, fg="#5B5B5B",
                 bg="#0A0E13", font=("Courier", 9)).pack(pady=(6, 10))

        self.btn = tk.Button(self.root, text="LAUNCH", command=self.toggle,
                             bg="#0D1117", fg="#C89B3C", activebackground="#463714",
                             font=("Courier", 12, "bold"), width=20,
                             relief="flat", bd=1, cursor="hand2")
        self.btn.pack(pady=(0, 20))

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def toggle(self):
        if not self.running:
            self.running = True
            self.btn.config(text="STOP", fg="#E84057")
            self.set_status("Connecting to LCU...")
            threading.Thread(target=self.run_accepter, daemon=True).start()
        else:
            self.running = False
            if self.ws:
                self.ws.close()
            self.btn.config(text="LAUNCH", fg="#C89B3C")
            self.set_status("Idle")

    def run_accepter(self):
        port, password = get_lcu_credentials()

        if not port:
            self.set_status("Lockfile not found — is League open?")
            self.root.after(0, lambda: self.btn.config(text="LAUNCH", fg="#C89B3C"))
            self.running = False
            return

        topic = self.topic_var.get()
        notify = self.notif_var.get() and not self.silent_var.get()
        mode = self.mode.get()
        auth = base64.b64encode(f"riot:{password}".encode()).decode()

        def on_open(ws):
            ws.send(json.dumps([5, "OnJsonApiEvent"]))
            self.set_status(f"Listening for {mode} queue...")

        # add this flag before on_message to prevent repeated notifications
        queue_notified = False
        queue_accepted_notified = False

        def on_message(ws, message):
            nonlocal queue_notified, queue_accepted_notified
            try:
                data = json.loads(message)
                if len(data) < 3:
                    return

                event = data[2]
                uri = event.get("uri", "")

                # ── Queue pop ──────────────────────────────────────────
                if "ready-check" in uri:
                    state = event.get("data", {}).get("state")
                    if state == "InProgress":
                        self.set_status("Queue popped! Accepting...")
                        requests.post(
                            f"https://127.0.0.1:{port}/lol-matchmaking/v1/ready-check/accept",
                            auth=("riot", password), verify=False
                        )

                        if mode == "ARAM" and notify and not queue_accepted_notified:
                            queue_accepted_notified = True

                            # Immediate notification on accept
                            send_notification(topic, "ARAM Queue Accepted",
                                            "Queue accepted! Waiting for champion... 🎮",
                                            tags="white_check_mark")
                            self.set_status("Accepted — waiting for champion...")

                        elif mode == "TFT":
                            self.set_status("TFT queue accepted — waiting for game launch...")
                    
                    if state in ["None", "Declined", "Accepted"]:
                        queue_accepted_notified = False
                

                # ── ARAM champ select FINALIZATION ────────────────────
                if mode == "ARAM" and "champ-select" in uri and not queue_notified:
                    phase = event.get("data", {}).get("timer", {}).get("phase", "")
                    if phase == "FINALIZATION" and notify:
                        queue_notified = True  # prevent repeated notifications
                        assigned, bench = get_aram_champions(port, password)
                        bench_str = ", ".join(bench) if bench else "none"
                        msg = f"Your champion: {assigned or 'TBD'}\nBench: {bench_str} 🎮"
                        send_notification(topic, "Champion Assigned", msg,
                                        tags="rotating_light")
                        self.set_status(f"Notified — {assigned or 'unknown'}")

                # ── Game start — TFT only ──────────────────────────────
                if mode == "TFT" and "gameflow" in uri:
                    phase = event.get("data", {}).get("phase") or event.get("data")
                    if phase == "InProgress":
                        self.set_status("TFT game detected!")
                        if notify:
                            send_notification(topic, "TFT Game Starting",
                                              "Your TFT game is loading! Get back to your PC 🎮",
                                              tags="rotating_light, chess_pawn")
                        time.sleep(1)
                        os._exit(0)

            except Exception as e:
                print(f"Event error: {e}")

        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            self.set_status("WebSocket error — is League open?")

        def on_close(ws, *args):
            if self.running:
                self.set_status("Disconnected — retrying in 5s...")
                time.sleep(5)
                if self.running:
                    threading.Thread(target=self.run_accepter, daemon=True).start()

        self.ws = websocket.WebSocketApp(
            f"wss://127.0.0.1:{port}",
            header={"Authorization": f"Basic {auth}"},
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# ─── Entry point ──────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = QueueAccepterApp(root)
    root.mainloop()