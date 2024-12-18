import socket       
import threading   
import sys         
import signal      

class ChatServer:
    """
    Chat server that accepts multiple client connections and broadcasts messages.
    """
    def __init__(self, host='127.0.0.1', port=65000):
        
        #initialize the chat server with network settings and data structures.
        self.host = host
        self.port = port
        
        #create TCP/IP socket for server 
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #allows reuse of local addresses if server restart
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        #dictionary to track connected clients: {socket: username} with locks for safety access
        self.clients = {}
        self.clients_lock = threading.Lock()
        
        #register handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)  
        signal.signal(signal.SIGTERM, self.shutdown) 

    def start(self):
        """
        Start the server: bind to port and begin listening for connections.
        """
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[*] Server listening on {self.host}:{self.port}")
    
        except Exception as e:
            print(f"[!] Server start error: {e}")
            self.shutdown()

    def receive(self):
        """
        - Accept new client connections and create handler threads
        - Runs until an error occurs or server is shut down
        """
        while True:
            try:
                # accept incoming client connection
                client_socket, address = self.server_socket.accept()
                print(f"[+] New connection from {address}")
                
                #handle initial client setup (get username_
                client_socket.send("Enter your username: ".encode('utf-8'))
                username = client_socket.recv(1024).decode('utf-8').strip()
                
                #add new client to tracking dictionary
                with self.clients_lock:
                    self.clients[client_socket] = username
                
                #notify all clients about new user
                self.broadcast(f"{username} has joined the chat!\n", client_socket)
                print(f"[*] Nickname of client is {username}")
                client_socket.send("Connected to the server\n".encode('utf-8'))

                #create and start thread to handle this client's messages
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
            
            except Exception as e:
                print(f"[!] Connection accept error: {e}")
                break

    def handle_client(self, client):
        """
        Handle messages from a specific client 
        """
        username = self.clients[client]
        
        try:
            while True:
                # Receive message from client
                message = client.recv(1024).decode('utf-8').strip()
                if not message:
                    break

                # Check for private message format '@username <message>'
                if message.startswith('@'):
                    parts = message.split(' ', 1)
                    if len(parts) > 1:
                        recipient_name = parts[0][1:]  # Extract the username after '@'
                        private_message = parts[1]
                        self.send_private_message(recipient_name, f"[Private] {username}: {private_message}", client)
                    else:
                        client.send("Invalid private message format.\n".encode('utf-8'))
                else:
                    # Broadcast message to all other clients
                    self.broadcast(f"{username}: {message}\n", client)
                    
        except Exception as e:
            print(f"[!] Client handling error for {username}: {e}")
        
        # clean up when client disconnects
        with self.clients_lock:
            del self.clients[client]
        
        #notify others that user has left
        self.broadcast(f"{username} has left the chat.\n", None)
        client.close()

    def send_private_message(self, recipient_name, message, sender_socket):
        """
        Send a private message to a specific client.
        """
        with self.clients_lock:
            for client_socket, name in self.clients.items():
                if name == recipient_name:
                    try:
                        client_socket.send(message.encode('utf-8'))
                        sender_socket.send(f"[Private message has been sent to {recipient_name}]".encode('utf-8'))
                    except Exception:
                        sender_socket.send(f"Failed to send private message to {recipient_name}\n".encode('utf-8'))
                    return
            
        sender_socket.send(f"User '{recipient_name}' not found.\n".encode('utf-8'))

    def broadcast(self, message, sender_socket):
        """
        Send a message to all connected clients except the sender.
        """
        with self.clients_lock:
            for client in list(self.clients.keys()):
                if client != sender_socket:  # avoid achoing back to sender
                    try:
                        client.send(message.encode('utf-8'))
                    except:
                        # remove client if sending fails (connection dead)
                        client.close()
                        del self.clients[client]


    def shutdown(self, signum=None, frame=None):
        """
        Gracefully shut down the server: close all client connections and server socket.
        """
        print("\n[*] Shutting down server...")
        
        #close all client connections
        with self.clients_lock:
            for client in list(self.clients.keys()):
                try:
                    client.close()
                except:
                    pass
        
        #close the server socket
        try:
            self.server_socket.close()
        except:
            pass
            
        sys.exit(0)

def main():
    """
    Entry point: create and start the chat server.
    """
    server = ChatServer()
    server.start()    
    server.receive()  

if __name__ == "__main__":
    main()