import time
import os
import threading
import pandas as pd
import serial

excel_path = 'data.xlsx'
com_port = 'COM10'
baudrate = 115200
check_interval = 2
send_delay = 1.5

ser = serial.Serial(com_port, baudrate)
time.sleep(2)

column_index, row_index = 0, 0
monitor_mode, last_modified_time, last_sent_text = 'column', None, None
running, first_run = True, True
lock = threading.Lock()


def get_column_index(letter): return ord(letter.upper()) - ord('A')


def read_excel_safe():
    try:
        return pd.read_excel(excel_path, header=None)
    except Exception as e:
        print(f"[ERROR] Gagal membaca file: {e}")
        return None


def send_last_from_excel():
    global last_sent_text, first_run
    df = read_excel_safe()
    if df is None:
        return
    with lock:
        data = (df.iloc[:, column_index] if monitor_mode ==
                'column' else df.iloc[row_index]).dropna().astype(str).tolist()
    if not data:
        print("[INFO] Data kosong.")
        return
    last_item = data[-1]
    if first_run:
        last_sent_text, first_run = last_item, False
    elif last_item != last_sent_text:
        ser.write((last_item + '\n').encode())
        print(f"[KIRIM OTOMATIS] {last_item}")
        last_sent_text = last_item
    else:
        print("[INFO] Tidak ada perubahan isi.")


def monitor_excel():
    global last_modified_time
    while running:
        try:
            mtime = os.path.getmtime(excel_path)
            if last_modified_time is None or mtime != last_modified_time:
                print("[INFO] Perubahan terdeteksi...")
                send_last_from_excel()
                last_modified_time = mtime
        except FileNotFoundError:
            print("[WARNING] File tidak ditemukan. Menunggu...")
        time.sleep(check_interval)


def input_listener():
    global column_index, row_index, monitor_mode, last_sent_text
    while running:
        try:
            cmd = input(">> ").strip()
            if cmd.lower().startswith(("monitor", "tampil")):
                parts = cmd.split()
                if len(parts) != 2:
                    print(
                        "[ERROR] Format salah. Gunakan: monitor/tampil <kolom/baris>")
                    continue
                action, target = parts[0].lower(), parts[1].upper()
                df = read_excel_safe()
                if df is None:
                    continue
                if target.isalpha() and len(target) == 1:
                    idx = get_column_index(target)
                    data = df.iloc[:, idx].dropna().astype(str).tolist()
                    if action == "monitor":
                        with lock:
                            column_index, monitor_mode, last_sent_text = idx, 'column', None
                        print(f"[INFO] Monitoring kolom {target}")
                    else:
                        print(f"\n[DATA Kolom {target}]")
                        for i, val in enumerate(data, 1):
                            print(f"{i}. {val}")
                elif target.isdigit():
                    idx = int(target) - 1
                    if idx >= len(df):
                        print(f"[ERROR] Baris {target} tidak tersedia.")
                        continue
                    data = df.iloc[idx].dropna().astype(str).tolist()
                    if action == "monitor":
                        with lock:
                            row_index, monitor_mode, last_sent_text = idx, 'row', None
                        print(f"[INFO] Monitoring baris {target}")
                    else:
                        print(f"\n[DATA Baris {target}]")
                        for i, val in enumerate(data):
                            print(f"{chr(ord('A')+i)}: {val}")
                else:
                    print("[ERROR] Format tidak valid.")
            elif len(cmd) == 1 and cmd.isalpha():
                df = read_excel_safe()
                col = get_column_index(cmd)
                if df is None or col >= len(df.columns):
                    continue
                data = df.iloc[:, col].dropna().astype(str).tolist()
                print(f"[KIRIM MANUAL] Kolom {cmd.upper()}:")
                for v in data:
                    ser.write((v + '\n').encode())
                    print(f"  -> {v}")
                    time.sleep(send_delay)
            elif cmd.isdigit():
                df = read_excel_safe()
                row = int(cmd)-1
                if df is None or row >= len(df):
                    continue
                data = df.iloc[row].dropna().astype(str).tolist()
                print(f"[KIRIM MANUAL] Baris {cmd}:")
                for v in data:
                    ser.write((v + '\n').encode())
                    print(f"  -> {v}")
                    time.sleep(send_delay)
            elif len(cmd) >= 2 and cmd[0].isalpha() and cmd[1:].isdigit():
                df = read_excel_safe()
                col, row = get_column_index(cmd[0]), int(cmd[1:])-1
                if df is None or row >= len(df):
                    continue
                val = df.iat[row, col]
                if pd.notna(val):
                    ser.write((str(val) + '\n').encode())
                    print(f"[KIRIM MANUAL] {cmd.upper()}: {val}")
                else:
                    print(f"[INFO] Sel {cmd.upper()} kosong.")
            else:
                print(
                    "[PERINTAH] Gunakan 'monitor <kolom/baris>', 'tampil <kolom/baris>', atau langsung: 'A', '3', 'B5', ...")
        except EOFError:
            break


print("=== Monitoring Excel ===")
print("Perintah:")
print("  monitor <kolom>     → Monitoring kolom tertentu (contoh: monitor A)")
print("  monitor <baris>     → Monitoring baris tertentu (contoh: monitor 2)")
print("  tampil <kolom>      → Lihat isi kolom di terminal (contoh: tampil A)")
print("  tampil <baris>      → Lihat isi baris di terminal (contoh: tampil 2)")
print("  A, B, ...           → Kirim semua isi kolom ke Arduino")
print("  1, 2, ...           → Kirim semua isi baris ke Arduino")
print("  A2, B4, ...         → Kirim isi sel tertentu ke Arduino")
print("Tekan Ctrl+C untuk keluar.\n")

threading.Thread(target=monitor_excel, daemon=True).start()
threading.Thread(target=input_listener, daemon=True).start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[STOP] Program dihentikan.")
    running = False
    ser.close()
