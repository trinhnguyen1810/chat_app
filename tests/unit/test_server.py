# tests/unit/test_server.py
import unittest
from unittest.mock import Mock, patch
import socket
import threading
from src.chat_server import ChatServer

class TestChatServer(unittest.TestCase):
    def setUp(self):
        """
        Setup runs before each test
        """
        self.server = ChatServer('127.0.0.1', 65432)
    
    def tearDown(self):
        """
        Cleanup runs after each test
        """
        try:
            self.server.shutdown()
        except:
            pass

    def test_init(self):
        """
        Test server initialization
        """
        #check for initialization with correct host and port value
        self.assertEqual(self.server.host, '127.0.0.1')
        self.assertEqual(self.server.port, 65432)
        self.assertIsInstance(self.server.server_socket, socket.socket)
        self.assertIsInstance(self.server.clients, dict)
        
        #check handle locking for shared object
        self.assertTrue(hasattr(self.server.clients_lock, 'acquire'))
        self.assertTrue(hasattr(self.server.clients_lock, 'release'))

    def test_socket_options(self):
        """
        Test socket configuration
        """
        #test the socket is configured with the SO_REUSEADDR option
        sock = self.server.server_socket
        reuse_addr = sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
        self.assertNotEqual(reuse_addr, 0)

    @patch('socket.socket')
    def test_start(self, mock_socket):
        """
        Test server start process
        """
        #create a mock socket to avoid actual socket binding during the test
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        #create a new ChatServer instance and start it
        server = ChatServer('127.0.0.1', 65432)
        server.start()
        
        #check that bind and listen were called with the expected arguments
        mock_sock.bind.assert_called_once_with(('127.0.0.1', 65432))
        mock_sock.listen.assert_called_once_with(5)

    def test_broadcast(self):
        """
        Test message broadcasting
        """
        # create mock clients
        mock_client1 = Mock()
        mock_client2 = Mock()
        
        # add to server's client list
        with self.server.clients_lock:
            self.server.clients[mock_client1] = "User1"
            self.server.clients[mock_client2] = "User2"
        
        # test broadcasting a message to all clients
        test_message = "Test message"
        self.server.broadcast(test_message, None)
        
        # check that both mock clients received the broadcast message
        mock_client1.send.assert_called_once_with(test_message.encode('utf-8'))
        mock_client2.send.assert_called_once_with(test_message.encode('utf-8'))

    def test_broadcast_exclude_sender(self):
        """Making sure to broadcast excluding the sender (and avoid duplication)"""
        # create mock sender and receiver clients
        mock_sender = Mock()
        mock_receiver1 = Mock()
        mock_receiver2 = Mock()
        
        # add clients to the server
        with self.server.clients_lock:
            self.server.clients[mock_sender] = "Sender"
            self.server.clients[mock_receiver1] = "Receiver"
            self.server.clients[mock_receiver2] = "Receiver"
        
        # test broadcasting a message, excluding the sender
        test_message = "Test message"
        self.server.broadcast(test_message, mock_sender)
        
        # ensure the sender doesn't receive the message but the receiver does
        mock_sender.send.assert_not_called()
        mock_receiver1.send.assert_called_once_with(test_message.encode('utf-8'))
        mock_receiver2.send.assert_called_once_with(test_message.encode('utf-8'))
        
    def test_send_private_message_success(self):
        """
        Test successful sending of a private message
        """
        # create mock clients
        mock_sender = Mock()
        mock_recipient = Mock()
        
        # add clients to the server
        with self.server.clients_lock:
            self.server.clients[mock_sender] = "Sender"
            self.server.clients[mock_recipient] = "Recipient"
        
        # send a private message
        message = "Test private message"
        self.server.send_private_message("Recipient", "[Private] Sender: " + message, mock_sender)
        
        # verify the message was sent to the recipient
        mock_recipient.send.assert_called_once_with("[Private] Sender: Test private message".encode('utf-8'))
        
        # verify the sender received a confirmation message
        mock_sender.send.assert_called_once_with("[Private message has been sent to Recipient]".encode('utf-8'))

    def test_send_private_message_user_not_found(self):
        """
        Test sending a private message to a non-existent user
        """
        # create a mock sender client
        mock_sender = Mock()
        
        # add the sender to the server
        with self.server.clients_lock:
            self.server.clients[mock_sender] = "Sender"
        
        # attempt to send a private message to a non-existent user
        self.server.send_private_message("NonExistentUser", "Test message", mock_sender)
        
        # verify the sender received a user not found message
        mock_sender.send.assert_called_once_with("User 'NonExistentUser' not found.\n".encode('utf-8'))

    def test_send_private_message_send_failure(self):
        """
        Test error handling when sending a private message fails
        """
        # create mock clients
        mock_sender = Mock()
        mock_recipient = Mock()
        mock_recipient.send.side_effect = Exception("Send failed")
        
        # add clients to the server
        with self.server.clients_lock:
            self.server.clients[mock_sender] = "Sender"
            self.server.clients[mock_recipient] = "Recipient"
        
        # attempt to send a private message
        self.server.send_private_message("Recipient", "Test message", mock_sender)
        
        # verify the sender received a failure message
        mock_sender.send.assert_called_once_with("Failed to send private message to Recipient\n".encode('utf-8'))


    def test_client_disconnect(self):
        """
        Test client disconnection handling when an exception occurs
        """
        # create a mock client that simulates a disconnection error
        mock_client = Mock()
        mock_client.recv.side_effect = Exception("Connection lost")
        
        # add the mock client to the server's client list
        with self.server.clients_lock:
            self.server.clients[mock_client] = "DisconnectedUser"
        
        # check the handling the disconnection
        # ensure that the client was removed from the server's clients
        self.server.handle_client(mock_client)
        self.assertNotIn(mock_client, self.server.clients)

    @patch('socket.socket')
    def test_client_thread_creation(self, mock_socket):
        """
        Test client thread creation
        """
        #create mock objects
        mock_client = Mock()
        mock_address = ('127.0.0.1', 12345)
        
        # setup mock socket
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        mock_sock.accept.side_effect = [
            (mock_client, mock_address),  # first call succeeds
            socket.error  # second call raises error to break the loop
        ]
        mock_client.recv.return_value = "TestUser".encode('utf-8')
        
        # create new server instance with mocked socket
        server = ChatServer('127.0.0.1', 65432)
        
        with patch('threading.Thread') as mock_thread:
            server.receive()  # exit after one iteration
            
            # verify thread creation
            mock_thread.assert_called_once()
            mock_thread.return_value.start.assert_called_once()
    
    def test_broadcast_error_handling(self):
        """
        Test error handling during broadcast
        """
        mock_client = Mock()
        mock_client.send.side_effect = Exception("Send failed")
        
        # add the mock client to the server's client list
        with self.server.clients_lock:
            self.server.clients[mock_client] = "ErrorUser"
        
        # broadcast the message
        self.server.broadcast("Test message", None)
        
        # verify client was removed after error
        self.assertNotIn(mock_client, self.server.clients)

    def test_client_cleanup(self):
        """
        Test client cleanup on disconnection
        """
        mock_client = Mock()
        # configure the mock to raise an exception after first receive
        mock_client.recv.side_effect = [
            b"",  # empty message to trigger cleanup
            Exception("Connection closed")  # backup to ensure loop breaks
        ]
        
        with self.server.clients_lock:
            self.server.clients[mock_client] = "CleanupUser"
        
        self.server.handle_client(mock_client)
        
        # verify client was cleaned up
        self.assertNotIn(mock_client, self.server.clients)
        mock_client.close.assert_called_once()

    @patch('signal.signal')
    def test_shutdown_signal_handling(self, mock_signal):
        """
        Test shutdown signal handling
        """
        server = ChatServer()
        self.assertEqual(mock_signal.call_count, 2)  
    
    @patch('signal.signal')
    def test_signal_handler_error(self, mock_signal):
        """
        Test error handling in the signal handler
        """
        mock_signal.side_effect = ValueError("Invalid signal")
        try:
            server = ChatServer()
        except ValueError:
            pass  #the test should pass if ValueError is raised

    def test_handle_client_error(self):
        """
        Test error handling in handle_client
        """
        # add the mock client to the clients dictionary before testing
        mock_client = Mock()
        mock_client.recv.side_effect = Exception("Unexpected error")
        
        #simulate error
        with self.server.clients_lock:
            self.server.clients[mock_client] = "ErrorUser"
        
        #handle client removal check
        self.server.handle_client(mock_client)
        self.assertNotIn(mock_client, self.server.clients)

    @patch('socket.socket')
    @patch('sys.exit') 
    def test_shutdown_error_handling(self, mock_exit, mock_socket):
        """
        Test error handling during shutdown
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        mock_sock.close.side_effect = Exception("Close error")
        
        server = ChatServer()
        server.shutdown()  # Should not raise exception
        
        # terminate server
        mock_exit.assert_called_once_with(0)

    @patch('signal.signal')
    def test_signal_handler_error(self, mock_signal):
        """
        Test signal handler initialization
        """
        #verify it was called correctly
        ChatServer()
        
        #verify signal.signal was called twice (for SIGINT and SIGTERM)
        self.assertEqual(mock_signal.call_count, 2)
        
        # get the actual calls made and verify
        calls = mock_signal.call_args_list
        for call in calls:
            self.assertEqual(len(call[0]), 2)
            self.assertTrue(callable(call[0][1]))

    @patch('socket.socket')
    def test_start_error_handling(self, mock_socket):
        """
        Test server start error handling
        """
        mock_sock = Mock()
        mock_socket.return_value = mock_sock
        
        mock_sock.bind.side_effect = Exception("Bind error")
        
        # create server and attempt to start it
        server = ChatServer()
        
        # mock shutdown to prevent system exit
        with patch.object(server, 'shutdown') as mock_shutdown:
            server.start()
            mock_shutdown.assert_called_once()

    @patch('socket.socket')
    def test_client_close_during_shutdown(self, mock_socket):
        """
        Test client closure during shutdown
        """
        # create server with mock clients
        server = ChatServer()
        
        # create mock clients that raise exception on close
        mock_client1 = Mock()
        mock_client1.close.side_effect = Exception("Close error")
        mock_client2 = Mock()
        
        # add mock clients to server
        with server.clients_lock:
            server.clients[mock_client1] = "User1"
            server.clients[mock_client2] = "User2"
        
        # mock sys.exit to prevent actual exit
        with patch('sys.exit'):
            server.shutdown()
        
        # verify both clients had close() called
        mock_client1.close.assert_called_once()
        mock_client2.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()