from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import socket
import threading
import time
import statistics
from enum import Enum

@dataclass
class ResultTest:
    """
    stores test metricswith key being delivery rate and latency
    use to compare metrics
    """
    num_clients: int               
    connected_clients: int          
    total_messages_sent: int       
    total_messages_received: int    #message recieved
    expected_messages: int   # total messages that is expected
    msgs_per_second: float        
    delivery_rate: float          
    avg_latency_ms: float           

class UserType(Enum):
    """simple user types"""
    ACTIVE = "active"     # sends messages, actively using
    LURKER = "lurker"     # only receives no use to simulate actual behaviour

class ClientTest:
    """
    simulates a chat client for testing
    """
    def __init__(self, host: str, port: int, client_id: str, client_type: UserType):
        #initial address host, clients to mock test
        self.host = host
        self.port = port
        self.client_id = client_id
        self.client_type = client_type
        self.username = f"{client_type.value}_{client_id}"
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.running = True
        self.received_messages = set()  
        self.sent_messages = set()     
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """
        establishes connection to serve
        r"""
        try:
            self.socket.connect((self.host, self.port))
            self.socket.recv(1024)
            self.socket.send(self.username.encode('utf-8'))
            self.socket.recv(1024)
            self.connected = True
            
            self._receiver = threading.Thread(target=self._receive_messages)
            self._receiver.daemon = True
            self._receiver.start()
            return True
        except Exception:
            return False
    
    def _receive_messages(self):
        """
        handles incoming messages
        """
        while self.running:
            try:
                #get message
                message = self.socket.recv(1024).decode('utf-8')
                if not message:
                    break
                
                #check to see the message
                if "TEST_MSG:" in message:
                    msg_id = message.split("TEST_MSG:")[1].split("|")[0]
                    with self._lock:
                        self.received_messages.add(msg_id)
            except Exception:
                if self.running:
                    break
        self.connected = False

    def send_message(self, content: str) -> bool:
        """
        sends a message
        """
        #if it is not connected dont send return False
        if not self.connected:
            return False
        
        # sending a message to approporate socket
        try:
            self.socket.send(content.encode('utf-8'))
            if "TEST_MSG:" in content:
                msg_id = content.split("TEST_MSG:")[1].split("|")[0]
                self.sent_messages.add(msg_id)
            return True
        
        #exception if its not connected
        except Exception:
            self.connected = False
            return False

    def cleanup(self):
        """
        cleans up resources
        """
        self.running = False
        try:
            self.socket.close()
        except:
            pass

class LoadTest:
    """
    manages chat server load testing
    """
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: Dict[str, ClientTest] = {}
        self.start_times: Dict[str, float] = {}  # track when each message was sent
        self._lock = threading.Lock()

    def _send_test_message(self, client: ClientTest) -> None:
        """
        sends a test message and tracks timing
        """
        msg_id = f"{time.time()}_{client.client_id}"
        content = f"TEST_MSG:{msg_id}|test_content"
        
        if client.send_message(content):
            with self._lock:
                self.start_times[msg_id] = time.time()

    def _calculate_metrics(self, start_time: float) -> ResultTest:
        """
        calculates test metrics
        """
        #calulate duration to see messages sent per second 
        #didnt include in report though as I realized its not super appropriate for analysis
        test_duration = time.time() - start_time
        active_clients = len([c for c in self.clients.values() if c.connected])

        # collect all messages
        total_sent = sum(len(client.sent_messages) for client in self.clients.values())
        total_received = sum(len(client.received_messages) for client in self.clients.values())
        expected_messages = total_sent * (active_clients - 1)  # each message should go to n-1 clients

        # calculate latencies
        latencies = []
        for client in self.clients.values():
            for msg_id in client.received_messages:
                if msg_id in self.start_times:
                    latency = (time.time() - self.start_times[msg_id]) * 1000
                    latencies.append(latency)

        #return the test result so we would calculate and comapre later on
        return ResultTest(
            num_clients=len(self.clients),
            connected_clients=active_clients,
            total_messages_sent=total_sent,
            total_messages_received=total_received,
            expected_messages=expected_messages,
            msgs_per_second=total_sent / test_duration if test_duration > 0 else 0,
            delivery_rate=(total_received / expected_messages * 100) if expected_messages > 0 else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0
        )

    def run_test(self, num_clients: int, duration: float = 5.0) -> ResultTest:
        """runs a complete test with specified number of clients"""
        print(f"\n=== Testing with {num_clients} clients ===")
        
        # connect clients
        for i in range(num_clients):
            client_type = UserType.LURKER if i % 5 == 0 else UserType.ACTIVE
            client = ClientTest(self.host, self.port, str(i), client_type)
            
            if client.connect():
                self.clients[str(i)] = client
                time.sleep(0.1)  
                
        connected = len([c for c in self.clients.values() if c.connected])
        print(f"Connected clients: {connected}/{num_clients}")
        
        if not connected:
            return None

        # run message test
        print(f"\nSending messages for {duration} seconds...")
        start_time = time.time()
        last_status = start_time
        
        try:
            while time.time() - start_time < duration:
                current_time = time.time()
                
                # status update every second
                if current_time - last_status >= 1.0:
                    metrics = self._calculate_metrics(start_time)
                    print(f"\rMessages sent: {metrics.total_messages_sent}, "
                          f"received: {metrics.total_messages_received}", end='')
                    last_status = current_time

                # send messages from active clients
                for client in self.clients.values():
                    if client.connected and client.client_type == UserType.ACTIVE:
                        self._send_test_message(client)
                
                # control send rate based on client count
                time.sleep(0.1 if num_clients < 50 else 0.3)
                
        except Exception as e:
            print(f"\nTest error: {str(e)}")
            
        return self._calculate_metrics(start_time)

    def cleanup(self):
        """cleanup test resources"""
        for client in self.clients.values():
            client.cleanup()
        self.clients.clear()

def print_results(results: Dict[int, ResultTest]):
    """
    prints formatted test results
    """
    print("\n" + "="*80)
    print(" CHAT SERVER LOAD TEST RESULTS ")
    print("="*80)
    
    header = f"{'Clients':>7} | {'Connected':>9} | {'Messages':>9} | {'Received':>9} | {'Expected':>9} | {'Delivery%':>9} | {'Latency(ms)':>10}"
    print(header)
    print("-" * len(header))
    
    for num_clients, r in sorted(results.items()):
        print(f"{r.num_clients:7d} | "
              f"{r.connected_clients:9d} | "
              f"{r.total_messages_sent:9d} | "
              f"{r.total_messages_received:9d} | "
              f"{r.expected_messages:9d} | "
              f"{r.delivery_rate:8.1f}% | "
              f"{r.avg_latency_ms:10.1f}")

def main():
    """
    runs load tests with different client counts
    """
    #with different test counts, we see the result
    test_configs = [2, 5, 20, 50, 200]
    all_results = {}
    
    for num_clients in test_configs:
        test = LoadTest('127.0.0.1', 65000)
        try:
            duration = 5.0 if num_clients < 100 else 8.0
            result = test.run_test(num_clients, duration)
            if result:
                all_results[num_clients] = result
        finally:
            test.cleanup()
            time.sleep(1)
    
    print_results(all_results)

if __name__ == "__main__":
    main()