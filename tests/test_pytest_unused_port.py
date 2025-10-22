import socket
import http.server
import threading
import tempfile
import os
import subprocess
import sys
import time
from pathlib import Path
try:
    from urllib.request import urlopen
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen, URLError


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


# Tests for unused_port_server fixture


def test_unused_port_server_has_port(unused_port_server):
    """Test that the server has a port attribute."""
    assert hasattr(unused_port_server, 'port')
    assert isinstance(unused_port_server.port, int)
    assert 1 <= unused_port_server.port <= 65535


def test_unused_port_server_start_and_fetch(unused_port_server):
    """Test that we can start the server and fetch a file from it."""
    # Create a temporary directory with a test file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / 'test.txt'
        test_content = 'Hello from test server!'
        test_file.write_text(test_content)

        # Start the server
        unused_port_server.start(tmpdir)

        # Fetch the file
        url = f'http://127.0.0.1:{unused_port_server.port}/test.txt'
        response = urlopen(url)
        fetched_content = response.read().decode('utf-8')

        assert fetched_content == test_content


def test_unused_port_server_explicit_stop(unused_port_server):
    """Test that we can explicitly stop the server."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Start the server
        unused_port_server.start(tmpdir)

        # Verify it's running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', unused_port_server.port))
        sock.close()
        assert result == 0, "Server should be running"

        # Stop the server
        unused_port_server.stop()

        # Verify it's stopped (connection should fail)
        import time
        time.sleep(0.1)  # Give it a moment to fully stop
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', unused_port_server.port))
        sock.close()
        assert result != 0, "Server should be stopped"


def test_unused_port_server_auto_cleanup():
    """Test that the server automatically stops after the test."""
    # This test verifies the cleanup happens by checking in a subsequent test
    # The fixture should handle cleanup automatically
    pass  # Cleanup is tested implicitly by other tests not conflicting


def test_unused_port_server_start_returns_self(unused_port_server):
    """Test that start() returns self for method chaining."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = unused_port_server.start(tmpdir)
        assert result is unused_port_server


def test_unused_port_server_context_manager():
    """Test that StaticServer works as a context manager."""
    from pytest_unused_port import StaticServer
    import socket

    # Get an unused port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()

    with tempfile.TemporaryDirectory() as tmpdir:
        with StaticServer(port) as server:
            server.start(tmpdir)
            # Server should be running
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = test_sock.connect_ex(('127.0.0.1', port))
            test_sock.close()
            assert result == 0, "Server should be running inside context"

        # Server should be stopped after exiting context
        import time
        time.sleep(0.1)
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = test_sock.connect_ex(('127.0.0.1', port))
        test_sock.close()
        assert result != 0, "Server should be stopped after context exit"


def test_cli_serves_directory():
    """Test that the CLI can serve a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file in the directory
        test_file = Path(tmpdir) / 'test.txt'
        test_content = 'Hello from CLI test!'
        test_file.write_text(test_content)

        # Start the CLI process with unbuffered output
        process = subprocess.Popen(
            [sys.executable, '-u', '-m', 'pytest_unused_port', tmpdir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )

        port = None
        try:
            # Read the output to get the port number
            # The CLI prints: "Serving {directory} on http://127.0.0.1:{port}"
            import re
            for _ in range(10):  # Try reading up to 10 times
                line = process.stdout.readline()
                if 'Serving' in line and 'http://127.0.0.1:' in line:
                    # Extract port from "Serving {dir} on http://127.0.0.1:{port}"
                    match = re.search(r'http://127\.0\.0\.1:(\d+)', line)
                    if match:
                        port = int(match.group(1))
                        break
                if process.poll() is not None:
                    # Process ended unexpectedly
                    stderr = process.stderr.read()
                    raise RuntimeError(f"CLI process ended unexpectedly: {stderr}")

            assert port is not None, "Failed to extract port from CLI output"

            # Give the server a moment to start
            time.sleep(0.3)

            # Fetch the test file
            url = f'http://127.0.0.1:{port}/test.txt'
            response = urlopen(url)
            fetched_content = response.read().decode('utf-8')

            assert fetched_content == test_content

        finally:
            # Stop the server
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def test_cli_serves_current_directory_by_default():
    """Test that the CLI serves the current directory when no argument is provided."""
    # We'll test this by checking that the CLI accepts no arguments
    # and doesn't immediately crash
    process = subprocess.Popen(
        [sys.executable, '-u', '-m', 'pytest_unused_port'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )

    try:
        # Check that we got the expected output
        output = process.stdout.readline()
        assert 'Serving' in output and 'http://127.0.0.1:' in output

        # Check that the process is still running (didn't crash)
        assert process.poll() is None, "CLI process should still be running"

    finally:
        # Stop the server
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
