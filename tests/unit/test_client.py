# tests/unit/test_client.py
import unittest
from unittest.mock import Mock, patch
import socket
from src.chat_client import ChatClient

class TestChatClient(unittest.TestCase):
    def setUp(self):
        """
        Setup runs before each test
        """
        self.client = ChatClient('127.0.0.1', 65432)
    
    def tearDown(self):
        """
        Cleanup runs after each test
        """
        try:
            self.client.shutdown()
        except:
            pass

    def test_init(self):
        """
        Test client initialization
        """

        #check if it is the right adress and client in running state
        self.assertEqual(self.client.host, '127.0.0.1')
        self.assertEqual(self.client.port, 65432)
        self.assertEqual(self.client.username, "")
        self.assertTrue(self.client.running)
        self.assertIsInstance(self.client.client_socket, socket.socket)

    @patch('socket.socket')
    def test_connect(self, mock_socket):
        """Test client connection process"""
        # setup mocks
        mock_sock = Mock()
        mock_socket.return_value = mock_sock

        # program mock to return these responses in sequence
        mock_sock.recv.side_effect = [
            "Enter your username: ".encode('utf-8'),  # First recv call
            "Welcome TestUser!".encode('utf-8')       # Second recv call
        ]
        
        # test connection
        client = ChatClient('127.0.0.1', 65432)
        
        # mock input and the send_messages method to prevent infinite loop
        with patch('builtins.input', return_value='TestUser'), \
            patch.object(client, 'send_messages'), \
            patch.object(client, 'receive_messages'):
            client.start()
        
        # verify connection attempt
        mock_sock.connect.assert_called_once_with(('127.0.0.1', 65432))
        # verify username was sent
        mock_sock.send.assert_called_with('TestUser'.encode('utf-8'))

    def test_shutdown(self):
        """
        verify client shutdown process 
        """
        self.client.shutdown()
        self.assertFalse(self.client.running)

    @patch('socket.socket')
    def test_send_message(self, mock_socket):
        """
        Test message sending
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        self.client.client_socket = mock_sock
        test_message = "Hello, World!"
        
        #attempt to send message
        self.client.client_socket.send(test_message.encode('utf-8'))
        #verify message
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
        # program mock to return our test message
        mock_sock.recv.return_value = test_message.encode('utf-8')
        
        self.client.client_socket = mock_sock
        #try receiving a message (1024 = buffer size)
        received = self.client.client_socket.recv(1024).decode('utf-8')
        self.assertEqual(received, test_message)
    
    @patch('socket.socket')
    def test_receive_messages_loop(self, mock_socket):
        """
        Test the message receiving loop
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        # set up a sequence of messages followed by an empty message to break the loop
        mock_sock.recv.side_effect = [
            "Hello".encode('utf-8'),
            "".encode('utf-8')  
        ]
        
        client = ChatClient('127.0.0.1', 65432)
        client.receive_messages()
        
        # verify receive was called
        mock_sock.recv.assert_called()

    @patch('socket.socket')
    def test_send_messages_loop(self, mock_socket):
        """
        Test the message sending loo
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        client = ChatClient('127.0.0.1', 65432)
        client.username = "TestUser"
        
        # mock input to test message sending
        with patch('builtins.input', side_effect=['Test message', 'quit']):
            client.send_messages()
        
        # verify message was sent
        mock_sock.send.assert_called_with('Test message'.encode('utf-8'))

    @patch('socket.socket')
    def test_error_handling(self, mock_socket):
        """
        Test error handling in client
        Simulates connection failure and verifies client handles it gracefully
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        #simulate connection failure
        mock_sock.connect.side_effect = socket.error("Connection refused")
        
        client = ChatClient('127.0.0.1', 65432)
        client.start()
        self.assertFalse(client.running)

    @patch('socket.socket')
    def test_start_server_error(self, mock_socket):
        """
        Test handling of server errors during start
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        # simulate server error during startup
        mock_sock.recv.side_effect = socket.error("Server error")
        
        client = ChatClient('127.0.0.1', 65432)
        client.start()
        
        self.assertFalse(client.running)

    @patch('socket.socket')
    def test_receive_messages_error(self, mock_socket):
        """
        Tests error handling during message reception
        Simulates receive error and verifies client handles it properly
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        # simulate receive error
        mock_sock.recv.side_effect = socket.error("Connection error")
        
        client = ChatClient('127.0.0.1', 65432)
        client.receive_messages()
        
        self.assertFalse(client.running)

    @patch('socket.socket')
    def test_send_messages_error(self, mock_socket):
        """
        Tests error handling during message sending
        Simulates send error and verifies client handles it properly
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        mock_sock.send.side_effect = socket.error("Send error")
        
        client = ChatClient('127.0.0.1', 65432)
        with patch('builtins.input', return_value='test message'):
            client.send_messages()
        
        self.assertFalse(client.running)
    

if __name__ == '__main__':
    unittest.main()