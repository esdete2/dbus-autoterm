from __future__ import annotations

import argparse
import logging

from domain import HeaterPhase
from heater import EmulatorConfig, FakeAir2DHeater
from protocol import CONTROLLER_PROFILE
from runtime import build_transport, run_loop

LOG = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="dbus-autoterm emulation")
    parser.add_argument("--transport", choices=["serial", "pty"], default="serial")
    parser.add_argument("--device", help="serial device when --transport=serial, default: /dev/serial0")
    parser.add_argument("--baudrate", type=int, default=None)
    parser.add_argument(
        "--initial-phase",
        choices=["off", "starting", "warming_up", "running", "shutting_down"],
        default="off",
    )
    parser.add_argument("--internal-temperature", type=int, default=26)
    parser.add_argument("--external-temperature", type=int, default=None)
    parser.add_argument("--battery-voltage", type=float, default=12.6)
    parser.add_argument("--error-code", type=int, default=0)
    parser.add_argument("--fan-rpm-set", type=int, default=0)
    parser.add_argument("--fan-rpm-actual", type=int, default=0)
    parser.add_argument("--fuel-pump-frequency", type=float, default=0.0)
    parser.add_argument("--response-delay", type=float, default=0.02)
    parser.add_argument("--status-broadcast-interval", type=float, default=1.0)
    parser.add_argument("--startup-sequence-required", action="store_true", default=True)
    parser.add_argument("--no-startup-sequence-required", dest="startup_sequence_required", action="store_false")
    parser.add_argument("--status-code", default=None, help="override initial status code, for example 2.3")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    profile = CONTROLLER_PROFILE
    status_major = None
    status_minor = None
    if args.status_code:
        major_str, minor_str = args.status_code.split(".", 1)
        status_major = int(major_str)
        status_minor = int(minor_str)
    phase_map = {
        "off": HeaterPhase.OFF,
        "starting": HeaterPhase.STARTING,
        "warming_up": HeaterPhase.WARMING_UP,
        "running": HeaterPhase.RUNNING,
        "shutting_down": HeaterPhase.SHUTTING_DOWN,
    }
    heater = FakeAir2DHeater(
        EmulatorConfig(
            profile=profile,
            initial_phase=phase_map[args.initial_phase],
            initial_internal_temperature_c=args.internal_temperature,
            initial_external_temperature_c=args.external_temperature,
            initial_battery_voltage_v=args.battery_voltage,
            initial_error_code=args.error_code,
            initial_status_code_major=status_major,
            initial_status_code_minor=status_minor,
            initial_fan_rpm_set=args.fan_rpm_set,
            initial_fan_rpm_actual=args.fan_rpm_actual,
            initial_fuel_pump_frequency_hz=args.fuel_pump_frequency,
            startup_sequence_required=args.startup_sequence_required,
            response_delay_s=args.response_delay,
            status_broadcast_interval_s=args.status_broadcast_interval,
        )
    )
    LOG.info(
        "event=heater_state phase=%s status_code=%s.%s internal_temp=%s external_temp=%s battery_voltage=%.1f error_code=%s startup_sequence_required=%s response_delay_s=%.3f status_broadcast_interval_s=%.3f",
        heater.snapshot.phase.name.lower(),
        heater.snapshot.telemetry.status_code_major,
        heater.snapshot.telemetry.status_code_minor,
        heater.snapshot.telemetry.internal_temperature_c,
        heater.snapshot.telemetry.external_temperature_c,
        heater.snapshot.telemetry.battery_voltage_v,
        heater.snapshot.telemetry.error_code,
        heater.config.startup_sequence_required,
        heater.config.response_delay_s,
        heater.config.status_broadcast_interval_s,
    )
    stream = build_transport(args, profile)
    try:
        try:
            run_loop(heater, stream, profile)
        except KeyboardInterrupt:
            LOG.info("event=shutdown reason=keyboard_interrupt")
            return 130
    finally:
        stream.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
