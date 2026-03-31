# Project Guidance

- Implementation plan: [`docs/implementation.md`](./docs/implementation.md)
- Protocol reference: [`docs/protocol.md`](./docs/protocol.md)
- Protocol source differences: [`docs/protocol-differences.md`](./docs/protocol-differences.md)

## Working Rules
- Treat [`docs/implementation.md`](./docs/implementation.md) as the milestone source of truth.
- Treat [`docs/protocol.md`](./docs/protocol.md) as the normative protocol reference once it is populated.
- Treat [`docs/protocol-differences.md`](./docs/protocol-differences.md) as the audit trail for AIR 2D vs 4D source conflicts.
- Keep Cerbo GX driver code under `dbus-autoterm/`.
- Keep heater emulation code under `emulation/`.
- Keep the Cerbo driver layered into D-Bus/UI adapter, heater domain model, and protocol provider components.
- Keep transport profiles configurable because the public reverse-engineered sources disagree on some UART details.

## Devbox Commands
- Devbox shell bootstraps a project-local venv at `.devbox/venv` and prepends it to `PATH`, so `python`, `pip`, and installed console scripts come from the same environment.
- `make package`: assemble the offline-installable `dbus-autoterm.tar.gz` artifact in `dist/` and populate ignored `dbus-autoterm/ext/`
- `devbox run emulation:test`: run the emulation tests
- `devbox run dbus-autoterm:test`: run the driver tests, including the driver-to-emulation compatibility test
- `devbox run test`: run both project test suites
- `devbox run emulation:run:pty`: start the heater emulation CLI on a PTY for local development
- `devbox run emulation:run:gpio`: start the heater emulation CLI on Raspberry Pi GPIO UART via `/dev/ttyAMA0`
- `devbox run dbus-autoterm:run:dummy`: start the driver app with the dummy backend and mock D-Bus
- `devbox run emulation:check`: byte-compile the emulation project
- `devbox run dbus-autoterm:check`: byte-compile the driver project
- `devbox run check`: byte-compile both projects
- `devbox run package`: build the default offline package via `make package`
- `devbox run deploy`: build and deploy the default package via `make deploy`
- `devbox run package:native-gui`: build the native GUI variant via `make package:native-gui`
- `devbox run deploy:native-gui`: build and deploy the native GUI variant via `make deploy:native-gui`

## Venus OS Driver Scripts
- `dbus-autoterm/install.sh`: validate the direct-Python runtime, seed `config.ini`, create `/service/dbus-autoterm`, and persist reinstall via `/data/rc.local`
- `dbus-autoterm/service/run`: runit entrypoint that executes `python3 app.py -c /data/apps/dbus-autoterm/config.ini`
- `dbus-autoterm/enable.sh`: ensure the service symlink exists and request service start
- `dbus-autoterm/disable.sh`: request service stop without uninstalling files
- `dbus-autoterm/restart.sh`: restart the runit service
- `dbus-autoterm/uninstall.sh`: remove the service symlink and the `/data/rc.local` reinstall hook
- `dbus-autoterm/config.sample.ini`: template runtime config for the driver service
- `README.md`: project description plus offline Cerbo install, config, service instructions, and current UI/runtime status
- `dbus-autoterm/ext/velib_python`: bundled `velib_python` copy used by the driver for `vedbus`
