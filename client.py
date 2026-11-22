
import socket
import select
import sys
import threading
import json


USERNAME = input("input you username:")
HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9009

def output_thread(sock):
    buf = b""
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print("\n[!] Server closed connection")
                break
            buf += data
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                line = line.decode('utf-8', errors='replace')

                msg = json.loads(line)
                if(msg.get("status") != 1):
                    print(msg.get("error"))
                    continue
                print(f"<{msg.get("sender")}>: {msg.get("text")}")

    except Exception as e:
        print(f"[!] Receiver error: {e}")
    finally:
        
        try:
            print("[*] Receiver thread exiting")
            sock.close()
            exit()
        except:
            pass

def input_thread(sock):
    while True:
        if sys.platform == "win32":
            import msvcrt
            if msvcrt.kbhit():
                line = sys.stdin.readline().rstrip("\n")
            else:
                line = None
        else:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                line = rlist[0].readline().rstrip("\n")  
            else: 
                None
        if not line:
            continue
        # split into recipient and message
        parts = line.split(':', 1)
        if len(parts) < 2:
            print("Usage: <recipient_username>:<message>")
            continue
        recipient = parts[0].strip()
        message = parts[1]
        msg = {"status": 1, "sender": USERNAME, "receiver": recipient, "text": message}
        try:
            sock.sendall(json.dumps(msg).encode() + b'\n')
        except Exception:
            print("[!] Failed to send (server may have disconnected).")
            break


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Register
    msg = {"status": 0, "sender": USERNAME}
    reg_line = json.dumps(msg).encode() + b'\n'
    sock.sendall(reg_line)

    data = b""
    while b'\n' not in data:
        chunk = sock.recv(1024)
        if not chunk:
            print("[!] Connection closed before registration response")
            sock.close()
            return
        data += chunk

    
    first_line, rest = data.split(b'\n', 1)
    first_line = first_line.decode('utf-8', errors='replace')

    line = json.loads(first_line)
    if line.get("status") == 1:
        print("[*] Registered successfully.")
    elif line.get("status") == 0:
        print("[!] Registration error:" + line.get("reason"))
        sock.close()
        return
    else:
        print("[!] Unexpected response:", line)
        sock.close()
        return

    t_out = threading.Thread(target=output_thread, args=(sock,))
    t_in = threading.Thread(target=input_thread, args=(sock,))
    t_out.start()
    t_in.start()

    t_in.join()
    sock.close()


if __name__ == "__main__":
    main()
