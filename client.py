
import socket
import select
import sys
import threading
import json
import uuid


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
                print(f"<{msg.get('sender')}>: {msg.get('text')}")

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
        try:
            line = input()

            if not line:
                continue

            parts = line.split(':', 1)

            if len(parts) < 2:
                print("Usage: <recipient_username>:<message>")
                continue

            recipient = parts[0].strip()
            message = parts[1]

            msg = {
                "status": 1,
                "sender": USERNAME,
                "receiver": recipient,
                "text": message
            }

            sock.sendall(json.dumps(msg).encode() + b'\n')

        except (EOFError, KeyboardInterrupt):
            break
        except OSError:
            print("[!] Failed to send (server may have disconnected).")
            break


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((HOST, PORT))

        # Authenticate
        request_id = uuid.uuid4().hex

        msg = {
            "type": "AUTH_REQUEST",
            "user_id": USERNAME,
            "request_id": request_id
        }
        sock.sendall(json.dumps(msg).encode() + b'\n')

        data = b""
        while b'\n' not in data:
            chunk = sock.recv(1024)
            if not chunk:
                print("[!] Connection closed before registration response")
                return
            data += chunk

        first_line, rest = data.split(b'\n', 1)
        response = json.loads(first_line.decode('utf-8'))

        if (
            response.get("type") == "AUTH_REQUEST_RECEIVED"
            and response.get("request_id") == request_id
        ):
            print("[*] Authentication request received by server.")
        else:
            print("[!] Unexpected response:", response)
            return

        # Start receiver thread
        t_out = threading.Thread(
            target=output_thread,
            args=(sock,),
            daemon=True
        )
        t_out.start()

        # Run input in main thread
        input_thread(sock)

    except KeyboardInterrupt:
        print("\n[!] Disconnecting...")

    except Exception as e:
        print(f"[!] Client error: {e}")

    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        sock.close()
        print("[*] Client shut down.")


if __name__ == "__main__":
    main()
