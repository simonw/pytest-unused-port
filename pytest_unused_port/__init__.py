import socket
import pytest


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
