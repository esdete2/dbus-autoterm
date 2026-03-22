from __future__ import annotations

from dataclasses import dataclass

PREAMBLE = 0xAA


class ProtocolError(ValueError):
    """Raised when a frame cannot be parsed or validated."""


@dataclass(frozen=True)
class ProtocolProfile:
    name: str
    baudrate: int
    controller_device: int = 0x03
    heater_device: int = 0x04
    diagnostic_device: int = 0x02
    init_device: int = 0x00
    checksum_byteorder: str = "big"


CONTROLLER_PROFILE = ProtocolProfile(name="air2d-9600", baudrate=9600)
DIRECT_PROFILE = ProtocolProfile(name="direct-9600", baudrate=9600)


@dataclass(frozen=True)
class Frame:
    device: int
    message_id2: int
    payload: bytes = b""
    message_id1: int = 0x00

    @property
    def payload_length(self) -> int:
        return len(self.payload)


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            odd = crc & 0x0001
            crc >>= 1
            if odd:
                crc ^= 0xA001
    return crc & 0xFFFF


def encode_frame(frame: Frame, checksum_byteorder: str = "big") -> bytes:
    header = bytes(
        [PREAMBLE, frame.device, frame.payload_length, frame.message_id1, frame.message_id2]
    )
    crc = crc16_modbus(header + frame.payload).to_bytes(2, byteorder=checksum_byteorder)
    return header + frame.payload + crc


def decode_frame(packet: bytes, checksum_byteorder: str = "big") -> Frame:
    if len(packet) < 7:
        raise ProtocolError(f"packet too short: {packet.hex()}")
    if packet[0] != PREAMBLE:
        raise ProtocolError(f"invalid preamble: {packet.hex()}")
    payload_length = packet[2]
    expected_length = payload_length + 7
    if len(packet) != expected_length:
        raise ProtocolError(
            f"invalid packet length {len(packet)} expected {expected_length}: {packet.hex()}"
        )
    expected_crc = crc16_modbus(packet[:-2]).to_bytes(2, byteorder=checksum_byteorder)
    if packet[-2:] != expected_crc:
        raise ProtocolError(
            f"invalid checksum {packet[-2:].hex()} expected {expected_crc.hex()}: {packet.hex()}"
        )
    return Frame(
        device=packet[1],
        message_id1=packet[3],
        message_id2=packet[4],
        payload=packet[5:-2],
    )


class FrameParser:
    """Incremental parser for serial byte streams."""

    def __init__(self, checksum_byteorder: str = "big") -> None:
        self._buffer = bytearray()
        self._checksum_byteorder = checksum_byteorder

    def feed(self, data: bytes) -> list[Frame]:
        self._buffer.extend(data)
        frames: list[Frame] = []
        while True:
            start = self._buffer.find(bytes([PREAMBLE]))
            if start == -1:
                self._buffer.clear()
                return frames
            if start:
                del self._buffer[:start]
            if len(self._buffer) < 7:
                return frames
            payload_length = self._buffer[2]
            frame_length = payload_length + 7
            if len(self._buffer) < frame_length:
                return frames
            packet = bytes(self._buffer[:frame_length])
            try:
                frame = decode_frame(packet, checksum_byteorder=self._checksum_byteorder)
            except ProtocolError:
                # Drop one byte and rescan so line noise does not poison the entire parser state.
                del self._buffer[0]
                continue
            del self._buffer[:frame_length]
            frames.append(frame)
