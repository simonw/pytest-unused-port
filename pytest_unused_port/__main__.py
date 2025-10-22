"""
Command-line interface for pytest-unused-port.

This module allows running pytest-unused-port as a standalone tool to serve
directories on an unused port using Python's http.server.
"""
import argparse
import sys
from pytest_unused_port import find_unused_port, StaticServer


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Serve a directory on an unused port using Python's http.server"
    )
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Directory to serve (default: current directory)'
    )

    args = parser.parse_args()

    # Get an unused port
    port = find_unused_port()

    # Create and start the server
    server = StaticServer(port)

    print(f"Serving {args.directory} on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop the server")

    try:
        server.start(args.directory)
        # Keep the server running until interrupted
        while True:
            try:
                server._process.wait()
                break
            except KeyboardInterrupt:
                print("\nShutting down server...")
                break
    finally:
        server.stop()


if __name__ == '__main__':
    main()
