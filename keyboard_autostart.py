#!/usr/bin/python3
import os
import time
import traceback

import btfpy

# Dedicated keyboard daemon for Raspberry Pi (auto-start friendly).
# It keeps the LE server alive and reinitializes on unexpected exits.

CONFIG_FILE = os.environ.get("BTF_KEYBOARD_CONFIG", "keyboard.txt")
LE_WAIT_MS = int(os.environ.get("BTF_LE_WAIT_MS", "30000"))
RESTART_DELAY_SEC = float(os.environ.get("BTF_RESTART_DELAY_SEC", "2"))

# Fixed random LE address (static random address).
# Change this value if clients keep using stale cached identity.
RANDADD = [0xD3, 0x56, 0xD6, 0x74, 0x33, 0x04]

reportmap = [
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01, 0x85, 0x01, 0x05, 0x07, 0x19, 0xE0,
    0x29, 0xE7, 0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
    0x95, 0x01, 0x75, 0x08, 0x81, 0x01, 0x95, 0x06, 0x75, 0x08, 0x15, 0x00,
    0x25, 0x65, 0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00, 0xC0
]
report = [0, 0, 0, 0, 0, 0, 0, 0]

name = "HID"
appear = [0xC1, 0x03]
pnpinfo = [0x02, 0x6B, 0x1D, 0x46, 0x02, 0x37, 0x05]
protocolmode = [0x01]
hidinfo = [0x01, 0x11, 0x00, 0x02]

reportindex = -1
node = 0


def write_local_hid_characteristics():
    uuid = [0x2A, 0x00]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), name, 0)

    uuid = [0x2A, 0x01]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), appear, 0)

    uuid = [0x2A, 0x4E]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), protocolmode, 0)

    uuid = [0x2A, 0x4A]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), hidinfo, 0)

    uuid = [0x2A, 0x4B]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), reportmap, 0)

    uuid = [0x2A, 0x4D]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), report, 0)

    uuid = [0x2A, 0x50]
    btfpy.Write_ctic(node, btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid), pnpinfo, 0)


def send_key(key):
    hidcode = btfpy.Hid_key_code(key)
    if hidcode == 0:
        return

    buf = [0, 0, 0, 0, 0, 0, 0, 0]

    buf[0] = (hidcode >> 8) & 0xFF
    buf[2] = hidcode & 0xFF
    btfpy.Write_ctic(node, reportindex, buf, 0)

    buf[0] = 0
    buf[2] = 0
    btfpy.Write_ctic(node, reportindex, buf, 0)


def lecallback(clientnode, op, cticn):
    if op == btfpy.LE_CONNECT:
        print("Client connected. Keyboard events enabled.")
        print("F10 sends 'Hello' + Enter.")

    elif op == btfpy.LE_KEYPRESS:
        if cticn == 23:
            hello = "Hello\n"
            for ch in hello:
                send_key(ord(ch))
        else:
            send_key(cticn)

    elif op == btfpy.LE_DISCONNECT:
        # Keep process alive and wait for the next connection.
        print("Client disconnected. Waiting for reconnection...")
        return btfpy.SERVER_CONTINUE

    return btfpy.SERVER_CONTINUE


def init_server():
    global node
    global reportindex

    if btfpy.Init_blue(CONFIG_FILE) == 0:
        raise RuntimeError("Init_blue failed")

    if btfpy.Localnode() != 1:
        local_addr = btfpy.Device_address(btfpy.Localnode())
        raise RuntimeError(
            "Local node is not node 1. Edit keyboard.txt ADDRESS with local address: " + local_addr
        )

    node = btfpy.Localnode()

    uuid = [0x2A, 0x4D]
    reportindex = btfpy.Find_ctic_index(node, btfpy.UUID_2, uuid)
    if reportindex < 0:
        raise RuntimeError("Failed to find Report characteristic (UUID 2A4D)")

    write_local_hid_characteristics()

    btfpy.Set_le_random_address(RANDADD)
    btfpy.Keys_to_callback(btfpy.KEY_ON, 0)
    btfpy.Set_le_wait(LE_WAIT_MS)
    btfpy.Le_pair(btfpy.Localnode(), btfpy.JUST_WORKS, 0)


def main():
    print("Starting keyboard auto service with config:", CONFIG_FILE)
    print("LE wait (ms):", LE_WAIT_MS)

    while True:
        try:
            init_server()
            retval = btfpy.Le_server(lecallback, 0)
            print("Le_server finished with code:", retval)
        except KeyboardInterrupt:
            print("Interrupted. Exiting.")
            break
        except Exception as exc:
            print("Server error:", exc)
            traceback.print_exc()
        finally:
            btfpy.Close_all()

        time.sleep(RESTART_DELAY_SEC)


if __name__ == "__main__":
    main()
