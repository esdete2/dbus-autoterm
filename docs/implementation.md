# dbus-autoterm

## Summary
Build a greenfield project that replaces the Autoterm AIR 2D control panel with a Cerbo GX-hosted D-Bus service over a direct USB-to-TTL UART link. The work is staged across four milestones: protocol documentation, a Raspberry Pi heater emulator, a Cerbo dummy-data driver to validate GX Touch UI reuse, and end-to-end integration between Cerbo and the heater emulation.

Repository layout:
- `emulation/` contains the Raspberry Pi heater emulation project.
- `dbus-autoterm/` contains the Cerbo GX D-Bus driver project.
- `docs/` contains shared project documentation.
- No shared code folder is used; each project keeps its own runtime modules.

## Milestone 1: Protocol Documentation
- Compare the locally cloned `autoterm-air-2d-serial-control` and `AutotermHeaterController` repositories as the primary reverse-engineered protocol sources, then reconcile them against other public references that can be validated.
- Document the controller-replacement scope specifically for `Autoterm AIR 2D` with no physical control panel attached.
- Produce `docs/protocol.md` as the implementation-ready protocol reference:
  - physical layer and wiring assumptions for direct heater UART via USB-to-TTL
  - serial settings, framing, checksums, addressing, request/response timing, retry behavior, and startup sequencing
  - command set required for panel replacement: power on/off, operating mode, setpoint or power changes, status polling, and fault reporting
  - heater state model: boot, idle, preheat, ignition, run, cooldown, fault, and lockout conditions
  - source comparison table showing agreements, disagreements, and unresolved gaps
  - `docs/protocol-differences.md` listing all observed differences between the AIR 2D and 4D reverse-engineered sources
  - confidence labels per command or field plus an explicit "unverified until real-heater capture" section
- Treat `docs/protocol.md` as the normative source for implementation once it exists.

## Milestone 2: Raspberry Pi Fake Heater
- Implement the emulator in Python on Raspberry Pi 5.
- Structure it as a protocol engine plus transport adapter:
  - core state machine that reproduces AIR 2D controller-visible behavior
  - UART transport over a Linux serial device
  - optional PTY or mock transport for automated workstation tests
- Match the heater from the controller's perspective:
  - same frame syntax, checksums, turnaround timing envelope, periodic status traffic, ACK or NACK behavior, and fault responses captured in `docs/protocol.md`
  - realistic startup, ignition, steady-state, cooldown, and error transitions
  - configurable telemetry values for temperature, voltage, pump or fan indicators, and injected faults
- Expose a small operator interface for testing:
  - config file or CLI flags for initial heater state and fault injection
  - structured logs for decoded frames and state transitions
- Acceptance:
  - replay test vectors from public protocol references pass
  - the Cerbo-side driver can complete startup, status, and control flows against the emulator without protocol exceptions
  - "exact heater" means controller-visible protocol fidelity for the documented command set; undocumented or unverified behavior stays explicitly out of scope until real-heater capture is available

## Milestone 3: Cerbo GX Dummy Driver and UI Validation
- Run the production driver on the Cerbo GX as a Venus OS service.
- Implement the driver in Python first, aligned with `velib_python` examples and common Venus OS D-Bus service patterns.
- Publish dummy data through a generator-style D-Bus service so GX Touch 70 can reuse native controllable UI elements for start/stop and status display.
- Separate the driver into three layers from the beginning:
  - Victron D-Bus and UI adapter
  - heater domain model
  - protocol transport and provider interface
- Bind the provider interface to a dummy backend only in this milestone.
- Define the initial public interfaces now so later milestones do not reshape them:
  - D-Bus service compatible with native GX UI reuse
  - internal provider contract for connect, send command, poll or read status, surface faults, and surface transport health
  - driver config for serial device path, transport profile selection, polling intervals, logging level, and service instance naming
- Acceptance:
  - the service starts cleanly on Cerbo boot
  - dummy values render on GX Touch 70
  - native UI controls drive dummy heater state transitions
  - no custom GUI work in this milestone; native UI reuse is validated first

## Milestone 4: Cerbo-to-Fake-Heater Integration
- Replace the dummy backend with the UART protocol backend and connect Cerbo GX to the Raspberry Pi heater emulation over the USB-to-TTL adapter.
- Keep the D-Bus and UI layer unchanged; only the provider implementation switches from dummy to serial.
- Implement serial robustness required for unattended Cerbo operation:
  - startup device detection and configuration
  - frame timeout handling, retries, resynchronization after garbage bytes, and reconnect after USB serial loss
  - health and error mapping from transport or protocol faults into GX-visible alarms and status
- Add observability:
  - raw frame debug logging on demand
  - decoded protocol logs
  - driver health status exposed on D-Bus
- Acceptance:
  - GX Touch controls start, stop, and adjust heater behavior through the Cerbo driver
  - the Pi emulator reflects the expected heater state machine
  - status and fault information round-trip back into the Cerbo UI
  - unplug, replug, and timeout scenarios recover without manual process restarts

## Public Interfaces
- `docs/protocol.md` is the canonical protocol contract once completed.
- The Python emulator package exposes:
  - protocol engine
  - serial and PTY transports
  - test-oriented fault and state injection
- The Cerbo driver exposes:
  - a generator-style D-Bus service for native GX UI reuse
  - a provider abstraction so dummy and serial backends share the same heater domain model
  - config values for serial device, timing profile, service instance, and logging

## Test Plan
- Protocol unit tests for frame encode and decode, checksum handling, and parser recovery on malformed input.
- Fixture tests derived from the two reverse-engineered repositories to ensure the documented command set reproduces known-good traffic.
- Emulator driver-compatibility tests over PTY or a mock transport to validate request or response timing and heater state transitions.
- Cerbo driver smoke tests with the dummy backend to verify D-Bus paths, state changes, and control handling.
- End-to-end hardware tests with Cerbo GX, GX Touch 70, Raspberry Pi 5, and USB-to-TTL.
- Manual UI acceptance on GX Touch 70 for start, stop, status updates, error display, and recovery after serial disconnect.
- Deferred conformance pass, once the real AIR 2D is available, to compare captured traffic against `docs/protocol.md` and tighten any unverified sections.

## Assumptions
- Target device is `Autoterm AIR 2D` with no physical control panel; the Cerbo implementation replaces the panel role directly.
- The first transport target is the direct heater UART via USB-to-TTL, not a diagnostic adapter workflow.
- The production driver runs on the Cerbo GX.
- The first UI target is native Venus OS generator-style controls on GX Touch 70; a custom heater UI is only considered if native reuse proves insufficient.
- The repo is greenfield, so the initial implementation should establish its own project layout for docs, emulator code, Cerbo driver code, and tests.
- Real-heater access is not available during the first pass, so the implementation must distinguish documented controller-visible fidelity from later hardware-backed conformance.
