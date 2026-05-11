from pyautogui import *
import pyautogui
import time
import keyboard
import random
import win32api, win32con
import os
import requests
import psutil

time.sleep(1)

NTFY_TOPIC = "lol-accept-name-01"  # REPLACE with ntfy subscribed topic

def click(x,y):
    win32api.SetCursorPos((x,y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)

# Sends notification to phone through ntfy topic sub
def send_notification(title, message, tags="white_check_mark"):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": tags
            },
            timeout=5  # don't hang if network is slow
        )
    except Exception as e:
        print(f"Notification failed: {e}")  # fail silently so script still exits

# Checks if a process is running (our case - league of legends.exe)
def is_process_running(name):
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == name.lower():
            return True
    return False

# Waits for League of Legends.exe to start running to indicate game is loading
def wait_for_game_start():
    """Wait until League of Legends.exe is running."""
    print("Queue accepted! Waiting for game to start...")

    # While game isn't loading
    while not is_process_running("League of Legends.exe"):
        time.sleep(2)

    print("Game detected!")
    send_notification("Queue Accepted", "Game loading... Get back to your PC! 🎮✔", tags="rotating_light, white_check_mark")


queue_accepted = False

# Main logic
while True:
    pic = pyautogui.screenshot(region=(871, 695, 20, 10))

    width, height = pic.size

    for x in range(0, width, 2):
        for y in range(0, height, 1):

            r, g, b = pic.getpixel((x, y))

            if r == 30 and g == 37 and b == 42 and not queue_accepted:
                click(x+871, y+695)
                queue_accepted = True
                # send_notification("Queue Accepted", "Game loading... Get back to your PC! 🎮✔",  tags="rotating_light, white_check_mark")

    if queue_accepted:
        wait_for_game_start()
        time.sleep(1)
        os._exit(0)

    time.sleep(0.5) # small sleep interval to reduce CPU load