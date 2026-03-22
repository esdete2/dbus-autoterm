from __future__ import annotations

import os
import pty
import select
from dataclasses import dataclass


class ByteStream:
    def read(self, size: int, timeout: float) -> bytes:
        raise NotImplementedError

    def write(self, data: bytes) -> int:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class SerialByteStream(ByteStream):
    def __init__(self, device: str, baudrate: int) -> None:
        try:
            import serial
        except ModuleNotFoundError as exc:
            raise RuntimeError("pyserial is required for serial transport") from exc
        self._serial = serial.Serial(
            device,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0,
            write_timeout=1,
        )

    def read(self, size: int, timeout: float) -> bytes:
        readable, _, _ = select.select([self._serial.fileno()], [], [], timeout)
        if not readable:
            return b""
        return self._serial.read(size)

    def write(self, data: bytes) -> int:
        return int(self._serial.write(data))

    def close(self) -> None:
        self._serial.close()


class FDByteStream(ByteStream):
    def __init__(self, fd: int) -> None:
        self._fd = fd

    def read(self, size: int, timeout: float) -> bytes:
        readable, _, _ = select.select([self._fd], [], [], timeout)
        if not readable:
            return b""
        return os.read(self._fd, size)

    def write(self, data: bytes) -> int:
        return os.write(self._fd, data)

    def close(self) -> None:
        os.close(self._fd)


@dataclass
class PtyEndpoint:
    stream: FDByteStream
    slave_path: str


def open_pty_endpoint() -> PtyEndpoint:
    master_fd, slave_fd = pty.openpty()
    slave_path = os.ttyname(slave_fd)
    os.close(slave_fd)
    return PtyEndpoint(stream=FDByteStream(master_fd), slave_path=slave_path)


class MemoryByteStream(ByteStream):
    # Small test-only full duplex endpoint.

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.peer: "MemoryByteStream | None" = None

    def connect(self, peer: "MemoryByteStream") -> None:
        self.peer = peer

    def read(self, size: int, timeout: float) -> bytes:
        del timeout
        if not self._buffer:
            return b""
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data

    def write(self, data: bytes) -> int:
        if self.peer is None:
            raise RuntimeError("memory transport is not connected")
        self.peer._buffer.extend(data)
        return len(data)

    def close(self) -> None:
        self._buffer.clear()


def memory_stream_pair() -> tuple[MemoryByteStream, MemoryByteStream]:
    a = MemoryByteStream()
    b = MemoryByteStream()
    a.connect(b)
    b.connect(a)
    return a, b
