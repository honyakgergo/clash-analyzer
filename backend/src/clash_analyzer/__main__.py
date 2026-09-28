"""``uv run clash-analyzer [--port 8000]`` starts the API server."""

import argparse
import logging
import socket
import sys

import uvicorn

HOST = "127.0.0.1"


def port_in_use(port: int, host: str = HOST) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="clash-analyzer")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if port_in_use(args.port):
        sys.exit(
            f"Port {args.port} is already in use. Is the backend already running?\n"
            f"Stop the other process, or start on another port with --port "
            f"(and point frontend/vite.config.ts's proxy at it)."
        )

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    uvicorn.run("clash_analyzer.main:app", host=HOST, port=args.port, reload=False)


if __name__ == "__main__":
    main()
