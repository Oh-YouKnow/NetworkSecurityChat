
import socket
import threading
import sys
import json

HOST = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9009

clients_lock = threading.Lock()
clients = {}  # username -> socket

def handle_client(conn, addr):
    username = None
    buffer = b""
    try:
        # --- Registration ---
        while b'\n' not in buffer:
            chunk = conn.recv(1024)
            if not chunk:
                conn.close()
                return
            buffer += chunk
        line, buffer = buffer.split(b'\n', 1)
        line = line.decode('utf-8', errors='replace')
        msg = json.loads(line)

        username = msg.get("sender")
        if not username:
            conn.sendall(json.dumps({"status": 0, "reason": "No Username Given"}).encode() + b"\n")
            conn.close()
            return

        with clients_lock:
            if username in clients:
                conn.sendall(json.dumps({"status": 0}, "reason", "Username Taken").encode() + b"\n")
                conn.close()
                return
            clients[username] = conn

        conn.sendall(json.dumps({"status": 1}).encode() + b"\n")
        print(f"Add new client: {username}")
        print(clients)

        # --- Messages ---
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                break
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                line = line.decode('utf-8', errors='replace')
                msg = json.loads(line)


                sender = msg.get("sender")
                recipient = msg.get("receiver")
                with clients_lock:
                    fromDest = clients.get(sender)
                    dest = clients.get(recipient)
                if dest and fromDest:
                    forward = msg
                    try:
                        dest.sendall(json.dumps(forward).encode() + b'\n')
                        print(f"Send from: {sender} to: {recipient}")
                    except Exception:
                        # remove disconnected client
                        with clients_lock:
                            if recipient in clients and clients[recipient] is dest:
                                try:
                                    clients[recipient].close()
                                except:
                                    pass
                                del clients[recipient]
                
                else:
                    err = {"status": "ERR", "error": f"No connected client named {recipient}"}
                    conn.sendall(json.dumps(err).encode() + b'\n')

    except Exception as e:
        print(f"[!] Exception for {addr}: {e}")
    finally:
        if username:
            with clients_lock:
                if username in clients and clients[username] is conn:
                    del clients[username]
            print(f"[-] {username} disconnected")
        try:
            conn.close()
        except:
            pass

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(50)
    print(f"[+] Server listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[!] Shutting down server.")
    finally:
        with clients_lock:
            for u, c in list(clients.items()):
                try:
                    c.close()
                except:
                    pass
            clients.clear()
        s.close()

if __name__ == "__main__":
    start_server()
