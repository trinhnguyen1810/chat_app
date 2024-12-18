# Chat Application

## Overview
This is a simple chat application that allows multiple clients to connect to a server and exchange messages in real-time. The application is built using Python's socket programming and threading capabilities.

## Features
- Multiple clients can connect to the server simultaneously.
- Users can send and receive messages in real-time.
- Support for private messaging between users based on username
- Graceful shutdown of the server and clients.

## Requirements
To run this application, you need:
- Python 3.8 or higher
- Required Python packages (install using `requirements.txt`)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/chatapplication.git
   cd chat_app
   ```
   or download the zip file

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Server
To start the chat server, run:

```bash
python src/chat_server.py
```

### Starting the Client
To start a chat client, open another terminal and run:

```bash
python src/chat_client.py
```

You can open multiple terminals and run the client script to simulate multiple users connecting to the server.

### Performance Testing
For performance testing, run the following script and wait for 1-2 minutes to complete the load test. This will provide analytics on how the system performs under increased load:

```bash
python tests/performance/performance_test.py
```

### Unit Testing
To run unit tests for both the client and server, use the following command:

```bash
python -m pytest --cov=src tests/
```
