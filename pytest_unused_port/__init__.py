import socket
import subprocess
import sys
import time
import pytest


class StaticServer:
    """
    Manages a static file HTTP server running on a port.

    Provides methods to start and stop the server, with automatic cleanup.
    """

    def __init__(self, port):
        self.port = port
        self._process = None
        self._directory = None

    def start(self, directory='.'):
        """
        Start an HTTP server serving the specified directory.

        Args:
            directory: Path to the directory to serve (default: current directory)
        """
        if self._process is not None:
            raise RuntimeError("Server is already running")

        self._directory = directory
        # Start python -m http.server on the specified port and directory
        self._process = subprocess.Popen(
            [sys.executable, '-m', 'http.server', str(self.port), '--directory', directory],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait a bit for the server to start
        time.sleep(0.1)

        # Verify the server is actually running
        if self._process.poll() is not None:
            # Process died immediately
            stdout, stderr = self._process.communicate()
            raise RuntimeError(f"Server failed to start: {stderr}")

        return self

    def stop(self):
        """Stop the HTTP server if it's running."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure cleanup on context manager exit."""
        self.stop()
        return False


@pytest.fixture
def unused_port():
    """
    Returns an unused port number on localhost.

    This fixture finds an available port by binding to port 0
    (which tells the OS to assign any available port), getting
    the assigned port number, and then closing the socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        return port
    finally:
        sock.close()


@pytest.fixture
def unused_port_server(unused_port):
    """
    Returns a StaticServer instance that can start an HTTP server on an unused port.

    The server automatically stops at the end of the test function.

    Example:
        def test_my_server(unused_port_server):
            unused_port_server.start('/path/to/directory')
            # Test your server at unused_port_server.port
            # Server automatically stops after test
    """
    server = StaticServer(unused_port)
    yield server
    # Automatic cleanup: stop the server if it's still running
    server.stop()
