import socket

import pytest

from clash_analyzer import __main__ as cli


def test_port_in_use_detects_listener() -> None:
    with socket.socket() as s:
        s.bind((cli.HOST, 0))
        s.listen()
        port = s.getsockname()[1]
        assert cli.port_in_use(port)


def test_main_exits_cleanly_when_port_busy(monkeypatch) -> None:
    with socket.socket() as s:
        s.bind((cli.HOST, 0))
        s.listen()
        port = s.getsockname()[1]
        monkeypatch.setattr("sys.argv", ["clash-analyzer", "--port", str(port)])
        with pytest.raises(SystemExit) as exc:
            cli.main()
    assert "already in use" in str(exc.value)
