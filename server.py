
import socket
import threading
import sys
import json
import uuid
from cryptography.hazmat.primitives import serialization

HOST = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9009

clients_lock = threading.Lock()

def load_public_keys():
    public_keys = {}

    for username in ["Alice", "Bob"]:
        with open(f"keys/{username}_public.pem", "rb") as f:
            public_keys[username] = serialization.load_pem_public_key(
                f.read()
            )

    return public_keys

users = {}             # user_id -> user information
username_to_id = {}    # username -> user_id
public_keys = load_public_keys()



def handle_client(conn, addr):
    username = None
    user_id = None
    registered = False
    buffer = b""
    try:
        #region Registration
        while b'\n' not in buffer:
            chunk = conn.recv(1024)
            if not chunk:
                conn.close()
                return
            buffer += chunk
        line, buffer = buffer.split(b'\n', 1)
        line = line.decode('utf-8', errors='replace')
        msg = json.loads(line)
        #region Authentication


        if msg.get("type") != "AUTH_REQUEST":
            conn.sendall(json.dumps({
                "type": "AUTH_FAILURE",
                "reason": "Expected authentication request"
            }).encode() + b"\n")
            conn.close()
            return

        username = msg.get("user_id")
        request_id = msg.get("request_id")

        if not username or not request_id:
            conn.sendall(json.dumps({
                "type": "AUTH_FAILURE",
                "reason": "Missing UserID or Request ID"
            }).encode() + b"\n")
            conn.close()
            return

        if not username:
            conn.sendall(json.dumps({
                "type": "REGISTER_RESPONSE",
                "success": False,
                "reason": "No username given"
            }).encode() + b"\n")
            conn.close()
            return
        if username not in public_keys:
            conn.sendall(json.dumps({
                "type": "REGISTER_RESPONSE",
                "success": False,
                "reason": "Unknown username"
            }).encode() + b"\n")
            conn.close()
            return

        with clients_lock:
            if username in username_to_id:
                conn.sendall(json.dumps({
                    "type": "REGISTER_RESPONSE",
                    "success": False,
                    "reason": "Username taken"
                }).encode() + b"\n")
                conn.close()
                return

            user_id = uuid.uuid4().hex

            users[user_id] = {
                "username": username,
                "connection": conn,
                "address": addr,
                "available": True,
                "active_session": None
            }

            username_to_id[username] = user_id
            registered = True

        conn.sendall(json.dumps({
            "type": "AUTH_REQUEST_RECEIVED",
            "request_id": request_id,
            "user_id": user_id
        }).encode() + b"\n")

        print(f"[*] Registered {username} with ID {user_id}")

        # endregion
        #endregion


        while True:
            data = conn.recv(1024)

            if not data:
                break

            # We will handle protocol messages here later.
            print(f"[!] Received data from {username}: {data}")

        

    except Exception as e:
        print(f"[!] Exception for {addr}: {e}")
    finally:
        if registered:
            with clients_lock:
                if user_id in users and users[user_id]["connection"] is conn:
                    del users[user_id]
                    del username_to_id[username]

            print(f"[-] {username} disconnected")

        try:
            conn.close()
        except OSError:
            pass

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.settimeout(1.0)
    s.bind((HOST, PORT))
    s.listen(50)

    print(f"[+] Server listening on {HOST}:{PORT}")

    try:
        while True:
            try:
                conn, addr = s.accept()

                threading.Thread(
                    target=handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()

            except socket.timeout:
                continue

    except KeyboardInterrupt:
        print("\n[!] Shutting down server.")

    finally:
        with clients_lock:
            for user_id, user in list(users.items()):
                try:
                    user["connection"].shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

                try:
                    user["connection"].close()
                except OSError:
                    pass

            users.clear()
            username_to_id.clear()

        s.close()
        print("[+] Server shut down.")

if __name__ == "__main__":
    start_server()
