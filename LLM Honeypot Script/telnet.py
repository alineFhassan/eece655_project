import socket
import threading
from datetime import datetime, timedelta
from openai import OpenAI
import re
openai_client = OpenAI(api_key="")
LOG_FILE = "honeypot_logs.txt"

def clean_response(response):
    return re.sub(r"```(?:\w+)?\n?|```", "", response).strip()

def log_connection(client_address, connection_time):

    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{connection_time}] Connection established from IP: {client_address[0]}, Port: {client_address[1]}\n")

def log_interaction(client_address, command, response, timestamp):

    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {client_address[0]}:{client_address[1]} - Command: {command}\n")
        log_file.write(f"[{timestamp}] {client_address[0]}:{client_address[1]} - Response: {response}\n")

def get_openai_response(messages):

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR]."

def handle_client(client_socket, client_address):
    connection_time = datetime.now()
    log_connection(client_address, connection_time)

    messages = [
        {"role": "system", "content": "You are a fake Linux shell environment. Respond only as a shell would. PLease note that I added all messages and responses in order to know the history and be able to continue based on previous commands and responses. So in this way you can reply to last command"},
    ]

    try:
        client_socket.send(b"Welcome to Telnet Honeypot\n\n")
        client_socket.send(b"login: ")
        username = client_socket.recv(1024).decode("utf-8").strip()
        client_socket.send(b"Password: ")
        password = client_socket.recv(1024).decode("utf-8").strip()
        client_socket.send(b"\nLogin successful!\n")
        client_socket.send(b"Welcome to Ubuntu 20.04.6 LTS (GNU/Linux 5.4.0-135-generic x86_64)\n")
        client_socket.send(f"Last login: {connection_time.strftime('%a %b %d %H:%M:%S %Y')} from {client_address[0]}\n\n".encode("utf-8"))
        client_socket.send(b"user@honeypot:~$ ")
        while True:
            command = client_socket.recv(1024).decode("utf-8").strip()
            if command.lower() in ("exit", "logout"):
                client_socket.send(b"logout\nConnection closed.\n")
                break

            print(f"Received command from {client_address}: {command}") 
            messages.append({"role": "user", "content": command})
            raw_response = get_openai_response(messages) 
            response = clean_response(raw_response)
            messages.append({"role": "assistant", "content": response})

            current_time = datetime.now()
            timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
            response_with_timestamp = response

            log_interaction(client_address, command, response_with_timestamp, timestamp)

            client_socket.send(f"{response_with_timestamp}\nuser@honeypot:~$ ".encode("utf-8"))

    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()

def start_honeypot(host="0.0.0.0", port=2228):
    """
    Starts the Telnet Honeypot server.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Honeypot listening on {host}:{port}...")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == "__main__":
    start_honeypot()