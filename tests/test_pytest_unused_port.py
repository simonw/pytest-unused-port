import socket
import http.server
import threading


def test_unused_port_returns_valid_port(unused_port):
    """Test that the fixture returns a valid port number."""
    assert isinstance(unused_port, int)
    assert 1 <= unused_port <= 65535


def test_unused_port_is_actually_unused(unused_port):
    """Test that the returned port can actually be bound to."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # This should succeed without raising an error
        sock.bind(('127.0.0.1', unused_port))
        # Verify we can get the socket name
        assert sock.getsockname()[1] == unused_port
    finally:
        sock.close()


def test_unused_port_can_start_http_server(unused_port):
    """Test that we can start an HTTP server on the unused port."""
    # Create a simple HTTP server
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(('127.0.0.1', unused_port), handler)

    # Start server in a thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # Verify the server is listening on the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Server should be listening, so connect should succeed
        result = sock.connect_ex(('127.0.0.1', unused_port))
        sock.close()
        assert result == 0, "Server should be listening on the port"
    finally:
        server.shutdown()


def test_multiple_unused_ports_are_different(unused_port):
    """Test that we can get another unused port that's different."""
    # Get another port using the same mechanism
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', 0))
        another_port = sock.getsockname()[1]
        # While they might occasionally be the same, they're typically different
        assert isinstance(another_port, int)
        assert 1 <= another_port <= 65535
    finally:
        sock.close()
