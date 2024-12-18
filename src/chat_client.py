import socket         
import threading     
import time          

class ChatClient:
    """
    A Client Object that connects to a server and enables sending/receiving messages.
    """
    def __init__(self, host='127.0.0.1', port=65000):
        #initialize the chat client with appropriate connection 
        self.host = host
        self.port = port
        self.username = ""                    
        self.running = True   
        #create TCP/IP socket for client-server communication
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        """
        Start the chat client: connect to server, set username, and begin message handling.
        """
        try:
            #establish connection with the chat server
            self.client_socket.connect((self.host, self.port))
            
            #handle initial server interaction for username setup
            prompt = self.client_socket.recv(1024).decode('utf-8').strip()
            print(prompt, end='')
            
            #create a thread to handle username input
            username_thread = threading.Thread(target=self.set_username)
            username_thread.start()
            
            #wait for the username to be set before proceeding
            username_thread.join()
            
            #receive and display server's welcome message
            welcome = self.client_socket.recv(1024).decode('utf-8')
            print(welcome.strip())
            
            #create and start thread for receiving messages
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True #thread will exit when main program exits
            receive_thread.start()
            #handles sending messages
            self.send_messages()
            
        except Exception as e:
            print(f"[!] Connection error: {e}")
            self.shutdown()

    def set_username(self):
        """
        Set the username for the client.
        """
        self.username = input().strip()
        self.client_socket.send(self.username.encode('utf-8'))

    def receive_messages(self):
        """
        Continuously receive and display messages from the server.
        (Runs in a separate thread to handle incoming messages asynchronously)
        """
        while self.running:
            try:                
                #wait for and receive message from server
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    #empty message indicates server disconnection
                    print("\n[!] Connection lost.")
                    self.shutdown()
                    break
                
                #dsplay received message and restore user input prompt
                print(f"\r{message.strip()}")
                print(f"{self.username}: ", end='', flush=True)
            
            except Exception as e:
                if self.running:
                    print(f"\n[!] Receive error: {e}")
                break
        
        self.shutdown()

    def send_messages(self):
        """
        Handle user input and send messages to the server.
        """
        print(f"{self.username}: ", end='', flush=True)
        while self.running:
            try:
                #get user input
                message = input()
                if message.lower() == 'quit':
                    self.shutdown()
                    break
                
                #send message to server
                self.client_socket.send(message.encode('utf-8'))
                #restore prompt for next message (just better chat interface)
                print(f"{self.username}: ", end='', flush=True)
            
            except Exception as e:
                if self.running:
                    print(f"[!] Send error: {e}")
                break
        
        self.shutdown()

    def shutdown(self):
        """
        Cleanup method to properly close the client connection.
        """
        self.running = False
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)  # close both send/receive
            self.client_socket.close()
        except:
            pass


def main():
    """
    Main entry point: create and start a chat client instance.
    """
    client = ChatClient()
    client.start()

if __name__ == "__main__":
    main()