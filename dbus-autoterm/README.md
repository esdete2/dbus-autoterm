# dbus-autoterm

`dbus-autoterm` is a Venus OS D-Bus plugin for integrating an Autoterm AIR 2D heater with a Victron GX device. The current plugin publishes a dedicated `heater` service for a custom GX Touch UI. The runtime backend is still dummy-first by default, so the full Venus service shell, config handling, and D-Bus publication path can be validated without heater hardware.

For real serial testing on a Cerbo GX, the important operational detail is that Venus OS runs `serial-starter`, which probes generic USB serial adapters and can attach competing services to `/dev/ttyUSB*`. A stock FT232R adapter is additionally classified by the default Venus rule set as `FT232R_USB_UART`, which marks it as `rs485:default`. Removing that stock FT232R classification alone is not sufficient, because generic `serial-starter` probing still continues unless the adapter is explicitly marked with `VE_SERVICE="ignore"`. Those probes can interfere with `dbus-autoterm` when both processes try to use the same underlying tty.

## Current status

- Production-style Venus OS plugin shell is implemented.
- Default backend is `dummy`, so the plugin can be installed and tested on a Cerbo GX without heater hardware.
- Runtime is direct Python execution via `python3 app.py`; Cerbo installation does not depend on `pip install -e`, PyPI, or internet access.
- `velib_python` is bundled under `ext/velib_python`.
- Primary UX comes from a dedicated `com.victronenergy.heater.autoterm_air2d` service plus installed custom GUI-v2 heater pages.
- The future `serial` backend remains in the tree for later hardware integration, but it is not part of the default install path.
- Serial unplug/replug recovery is implemented in the provider so the service can recover when the tty disappears and later returns.

## Runtime contract

- Install path: `/data/apps/dbus-autoterm`
- Config path: `/data/apps/dbus-autoterm/config.ini`
- Service path: `/service/dbus-autoterm`
- Primary D-Bus service: `com.victronenergy.heater.autoterm_air2d`
- Service entrypoint: `python3 app.py -c /data/apps/dbus-autoterm/config.ini`

The runtime uses one primary service:

- `com.victronenergy.heater.autoterm_air2d` is the source of truth for the custom heater page, live heater telemetry, timer placeholders, and heater-specific writable controls.

## Cerbo serial setup

The recommended Cerbo setup uses a dedicated FT232R adapter whose USB product string has been changed from:

```text
FT232R USB UART
```

to:

```text
Autoterm UART
```

while keeping the normal FTDI UART VID/PID `0403:6001`.

Why this matters:

- the stock Venus rule:
  ```udev
  ACTION=="add", ENV{ID_BUS}=="usb", ENV{ID_MODEL}=="FT232R_USB_UART", ENV{VE_SERVICE}="rs485:default"
  ```
  makes `serial-starter` treat an unmodified FT232R as a generic RS485 adapter
- Venus still enrolls generic USB serial tty devices into `serial-starter`, so removing the FT232R-specific match is not enough by itself
- changing only the USB product string keeps normal `/dev/ttyUSB*` behavior, but gives the adapter a unique identity that can be opted out cleanly with a dedicated `VE_SERVICE="ignore"` rule

With the adapter flashed to `Autoterm_UART`, `install.sh` appends this adapter-specific rule to the official Venus file `/etc/udev/rules.d/serial-starter.rules` if it is missing:

```udev
ACTION=="add", SUBSYSTEM=="tty", SUBSYSTEMS=="platform|usb-serial", ENV{ID_BUS}=="usb", ENV{ID_MODEL}=="Autoterm_UART", ENV{VE_SERVICE}="ignore", SYMLINK+="ttyAUTOTERM"
```

This achieves the intended behavior:

- `serial-starter` remains enabled globally
- only the Autoterm adapter is ignored
- the adapter gets a stable `/dev/ttyAUTOTERM` symlink
- `dbus-autoterm` can keep using the same device path even if the kernel renames the underlying port from `ttyUSB0` to `ttyUSB1`

The stable `serial_device` setting for Cerbo deployments is therefore:

```ini
serial_device = /dev/ttyAUTOTERM
```

The underlying kernel-assigned `/dev/ttyUSB*` number is intentionally not used directly.

## Offline installation on a Cerbo GX

The Cerbo does not need internet access. The files only need to be copied onto the device first, for example by SCP from a laptop on the same LAN or by copying them from removable media.

1. Copy the entire `dbus-autoterm/` directory to the Cerbo as `/data/apps/dbus-autoterm`.
2. SSH into the Cerbo.
3. Change into the app directory:

```bash
cd /data/apps/dbus-autoterm
```

4. Run the installer:

```bash
bash install.sh
```

What `install.sh` does:

- creates `config.ini` from `config.sample.ini` if it does not exist
- creates or refreshes `/service/dbus-autoterm`
- ensures the adapter-specific `serial-starter.rules` ignore entry for `Autoterm_UART` exists
- installs the custom GUI-v2 heater delegate and page stack under `/opt/victronenergy/gui-v2/Victron/VenusOS`
- adds a reinstall hook to `/data/rc.local`
- restarts the runit service if `svc` is available

If the Autoterm adapter is already plugged in when the rule is first installed or updated, unplug/replug the adapter or reboot the Cerbo once so the current tty instance picks up the new udev rule.

Cerbo runtime expectations:

- Venus OS should provide `python3`, `dbus`, and `gi.repository.GLib`
- `dbus-autoterm` requires the bundled `velib_python` under `/data/apps/dbus-autoterm/ext/velib_python`

## Configuration

The runtime template is `config.sample.ini`. After installation, edit `/data/apps/dbus-autoterm/config.ini` as needed.

### `[driver]`

- `backend`
  - `dummy` is the default and recommended value for the current plugin state
  - `serial` is reserved for later real-heater integration
- `serial_device`
  - serial backend device path
  - on Cerbo GX this should normally be `/dev/ttyAUTOTERM`
- `poll_interval`
  - poll cadence in seconds
- `log_level`
  - standard Python log level such as `INFO` or `DEBUG`
- `mock_dbus`
  - local-development flag
  - keep this `false` on a Cerbo GX

### `[dbus]`

- `service_name`
- `device_instance`
- `product_name`
- `firmware_version`
- `hardware_version`
- `connection`

## Service control

Install or reinstall:

```bash
cd /data/apps/dbus-autoterm
bash install.sh
```

Enable without reinstalling:

```bash
cd /data/apps/dbus-autoterm
bash enable.sh
```

Disable the service:

```bash
cd /data/apps/dbus-autoterm
bash disable.sh
```

Restart the service:

```bash
cd /data/apps/dbus-autoterm
bash restart.sh
```

Uninstall the service link and rc.local hook:

```bash
cd /data/apps/dbus-autoterm
bash uninstall.sh
```

## Why the serial-starter rule exists

The problem this project must solve on Venus OS is not only "find the adapter" but "stop Venus from auto-probing the adapter as something else".

Without the adapter-specific ignore rule, the adapter can still be claimed or probed by unrelated Venus services, even after the FT232R product string has been renamed. Examples observed during development were:

- `gps-dbus`
- `dbus-modbus-client`
- `dbus-cgwacs`
- `vedirect-interface`

That leads to flaky serial behavior, intermittent timeouts, and split ownership of the same tty.

The current solution is intentionally narrow:

- it does not disable `serial-starter`
- it is not tied to a physical USB port
- it does not affect other serial devices
- it persists across reboots through the normal `install.sh` boot hook in `/data/rc.local`

After a Venus firmware update, `install.sh` is expected to run again and re-apply the ignore rule if the system copy of `serial-starter.rules` was replaced.

## Logs

The runit log service writes to:

```bash
/var/log/dbus-autoterm
```

Typical log inspection:

```bash
tail -f /var/log/dbus-autoterm/current
```

## Local development

Dummy backend with mock D-Bus:

```bash
PYTHONPATH=dbus-autoterm python3 -m app --backend=dummy --mock-dbus
```

Emulation project:

```bash
PYTHONPATH=emulation python3 -m emulator
```

## What dummy-complete means

The plugin is complete around the dummy runtime path:

- direct Python runtime
- config-driven startup
- GLib-based Venus-style polling
- dedicated heater D-Bus service publication
- custom GUI-v2 heater pages installed from the driver repo
- runit service scripts
- offline Cerbo installation flow

What is still deferred:

- long-term productization beyond the current FT232R-based Cerbo test harness
- confirmed GX Touch UI validation against the final heater page set on target hardware
- production heater integration with the AIR 2D protocol backend
