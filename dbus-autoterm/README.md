# dbus-autoterm

`dbus-autoterm` is a Venus OS D-Bus generator-style plugin for integrating an Autoterm AIR 2D heater with a Victron GX device. The current plugin is dummy-complete: the full Venus OS service shell, config handling, and D-Bus publication path are in place, while the runtime backend still uses deterministic dummy values by default.

## Current status

- Production-style Venus OS plugin shell is implemented.
- Default backend is `dummy`, so the plugin can be installed and tested on a Cerbo GX without heater hardware.
- Runtime is direct Python execution via `python3 app.py`; Cerbo installation does not depend on `pip install -e`, PyPI, or internet access.
- `velib_python` is bundled under `ext/velib_python`.
- The future `serial` backend remains in the tree for later hardware integration, but it is not part of the default install path.

## Runtime contract

- Install path: `/data/apps/dbus-autoterm`
- Config path: `/data/apps/dbus-autoterm/config.ini`
- Service path: `/service/dbus-autoterm`
- D-Bus service: `com.victronenergy.generator.autoterm_air2d`
- Service entrypoint: `python3 app.py -c /data/apps/dbus-autoterm/config.ini`

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
- validates the Python files with `python3 -m py_compile`
- creates or refreshes `/service/dbus-autoterm`
- adds a reinstall hook to `/data/rc.local`
- restarts the runit service if `svc` is available

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
  - future serial backend device path
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
- generator-style D-Bus service publication
- runit service scripts
- offline Cerbo installation flow

What is still deferred:

- real serial transport validation on Cerbo hardware
- confirmed GX Touch UI validation against the final D-Bus path set
- production heater integration with the AIR 2D protocol backend
