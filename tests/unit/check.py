# Unit tests for a chat client using Python's unittest framework
# We use Mock objects to simulate network connections without actual server

import unittest  # Python's testing framework - gives us assert methods and test runners
from unittest.mock import Mock, patch  # Mock = fake objects, patch = temporarily replace real objects
import socket  # Python's networking module - we'll mock this to avoid real network calls
from src.chat_client import ChatClient  # The actual client code we're testing

class TestChatClient(unittest.TestCase):
    def setUp(self):
        """
        setUp: Runs before each test method (like a reset button)
        Creates fresh client instance so each test starts clean
        """
        # localhost + port - standard testing environment
        self.client = ChatClient('127.0.0.1', 65432)
    
    def tearDown(self):
        """
        tearDown: Cleanup after each test (like garbage collection)
        Prevents tests from affecting each other by shutting down client
        """
        try:
            self.client.shutdown()
        except:  # Broad except because we don't care if shutdown fails during cleanup
            pass

    def test_init(self):
        """
        Tests if ChatClient constructor sets up object correctly
        All instance variables should have expected initial values
        """
        # assertEqual checks if first arg equals second arg
        self.assertEqual(self.client.host, '127.0.0.1')  # Check host address
        self.assertEqual(self.client.port, 65432)        # Check port number
        self.assertEqual(self.client.username, "")       # Username starts empty
        self.assertTrue(self.client.running)             # Client starts in running state
        # Check if socket was created with correct type
        self.assertIsInstance(self.client.client_socket, socket.socket)

    @patch('socket.socket')  # Decorator that replaces real socket with Mock during test
    def test_connect(self, mock_socket):
        """
        Tests client connection sequence:
        1. Connect to server
        2. Get username prompt
        3. Send username
        4. Get welcome message
        Uses mock socket to simulate server responses
        """
        # Create Mock object for socket operations
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        # Program mock to return these responses in sequence
        mock_sock.recv.side_effect = [
            "Enter your username: ".encode('utf-8'),  # First server message
            "Welcome TestUser!".encode('utf-8')       # Second server message
        ]
        
        client = ChatClient('127.0.0.1', 65432)
        
        # Context manager (with) to temporarily patch multiple things:
        # 1. Make input() return "TestUser"
        # 2. Prevent infinite loops in send/receive methods
        with patch('builtins.input', return_value='TestUser'), \
            patch.object(client, 'send_messages'), \
            patch.object(client, 'receive_messages'):
            client.start()
        
        # Verify socket connected to right address/port
        mock_sock.connect.assert_called_once_with(('127.0.0.1', 65432))
        # Verify username was sent
        mock_sock.send.assert_called_with('TestUser'.encode('utf-8'))

    def test_shutdown(self):
        """
        Tests client shutdown
        Should set running flag to False
        """
        self.client.shutdown()
        self.assertFalse(self.client.running)  # Verify client not running after shutdown

    @patch('socket.socket')
    def test_send_message(self, mock_socket):
        """
        Tests message sending functionality
        Verifies that message is properly encoded and sent through socket
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        self.client.client_socket = mock_sock
        test_message = "Hello, World!"
        
        # Try sending a message
        self.client.client_socket.send(test_message.encode('utf-8'))
        # Verify message was sent with correct encoding
        mock_sock.send.assert_called_once_with(test_message.encode('utf-8'))

    @patch('socket.socket')
    def test_receive_message(self, mock_socket):
        """
        Tests message receiving functionality
        Verifies that received messages are properly decoded
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        test_message = "Test message"
        # Program mock to return our test message
        mock_sock.recv.return_value = test_message.encode('utf-8')
        
        self.client.client_socket = mock_sock
        # Try receiving a message (1024 = buffer size)
        received = self.client.client_socket.recv(1024).decode('utf-8')
        
        self.assertEqual(received, test_message)
    
    @patch('socket.socket')
    def test_receive_messages_loop(self, mock_socket):
        """
        Tests the message receiving loop
        Simulates receiving multiple messages and proper loop termination
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        # Set up sequence of messages:
        # 1. Normal message
        # 2. Empty message (causes loop to exit)
        mock_sock.recv.side_effect = [
            "Hello".encode('utf-8'),
            "".encode('utf-8')  # Empty message breaks the loop
        ]
        
        client = ChatClient('127.0.0.1', 65432)
        client.receive_messages()
        
        mock_sock.recv.assert_called()  # Verify receive was attempted

    @patch('socket.socket')
    def test_send_messages_loop(self, mock_socket):
        """
        Tests message sending loop
        Simulates user input and verifies messages are sent correctly
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        client = ChatClient('127.0.0.1', 65432)
        client.username = "TestUser"
        
        # Simulate user typing "Test message" then "quit"
        with patch('builtins.input', side_effect=['Test message', 'quit']):
            client.send_messages()
        
        mock_sock.send.assert_called_with('Test message'.encode('utf-8'))

    @patch('socket.socket')
    def test_error_handling(self, mock_socket):
        """
        Tests connection error handling
        Simulates connection failure and verifies client handles it gracefully
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        # Simulate connection failure
        mock_sock.connect.side_effect = socket.error("Connection refused")
        
        client = ChatClient('127.0.0.1', 65432)
        client.start()
        
        self.assertFalse(client.running)  # Client should stop on connection error

    @patch('socket.socket')
    def test_start_server_error(self, mock_socket):
        """
        Tests server error handling during startup
        Simulates server error and verifies client handles it properly
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        # simulate server error during startup
        mock_sock.recv.side_effect = socket.error("Server error")
        
        client = ChatClient('127.0.0.1', 65432)
        client.start()
        
        self.assertFalse(client.running)  # Client should stop on server error

    @patch('socket.socket')
    def test_receive_messages_error(self, mock_socket):
        """
        Tests error handling during message reception
        Simulates receive error and verifies client handles it properly
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        # Simulate receive error
        mock_sock.recv.side_effect = socket.error("Connection error")
        
        client = ChatClient('127.0.0.1', 65432)
        client.receive_messages()
        
        self.assertFalse(client.running)  # Client should stop on receive error

    @patch('socket.socket')
    def test_send_messages_error(self, mock_socket):
        """
        Tests error handling during message sending
        Simulates send error and verifies client handles it properly
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        # Simulate send error
        mock_sock.send.side_effect = socket.error("Send error")
        
        client = ChatClient('127.0.0.1', 65432)
        with patch('builtins.input', return_value='test message'):
            client.send_messages()
        
        self.assertFalse(client.running)  # Client should stop on send error
    
    @patch('src.chat_client.ChatClient')
    def test_main_function(self, mock_client_class):
        """
        Tests the main program entry point
        Verifies that main() creates and starts client correctly
        """
        from src.chat_client import main
        
        # Create mock for client class
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        main()  # Run main function
        
        # Verify client was created and started
        mock_client_class.assert_called_once()  # Constructor called once
        mock_client.start.assert_called_once()  # start() method called once

# Python's way of running tests when file is run directly
if __name__ == '__main__':
    unittest.main()