from __future__ import annotations

import argparse
import logging
import time

from heater import FakeAir2DHeater
from protocol import FrameParser, ProtocolProfile, encode_frame
from transports import ByteStream, SerialByteStream, open_pty_endpoint

LOG = logging.getLogger(__name__)


def run_loop(heater: FakeAir2DHeater, stream: ByteStream, profile: ProtocolProfile) -> None:
    parser = FrameParser(checksum_byteorder=profile.checksum_byteorder)
    while True:
        data = stream.read(256, timeout=0.2)
        now = time.monotonic()
        for frame in heater.background_frames(now):
            if heater.config.response_delay_s > 0:
                time.sleep(heater.config.response_delay_s)
            stream.write(encode_frame(frame, checksum_byteorder=profile.checksum_byteorder))
        if not data:
            continue
        for frame in parser.feed(data):
            for response in heater.handle_frame(frame):
                if heater.config.response_delay_s > 0:
                    time.sleep(heater.config.response_delay_s)
                stream.write(encode_frame(response, checksum_byteorder=profile.checksum_byteorder))


def build_transport(args: argparse.Namespace, profile: ProtocolProfile) -> ByteStream:
    if args.transport == "serial":
        device = args.device or "/dev/serial0"
        LOG.info(
            "event=startup transport=serial device=%s baudrate=%s profile=%s",
            device,
            args.baudrate or profile.baudrate,
            profile.name,
        )
        return SerialByteStream(device, args.baudrate or profile.baudrate)
    endpoint = open_pty_endpoint()
    LOG.info("event=startup transport=pty slave_path=%s profile=%s", endpoint.slave_path, profile.name)
    print(endpoint.slave_path, flush=True)
    return endpoint.stream
