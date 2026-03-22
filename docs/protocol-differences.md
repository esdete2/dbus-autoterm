# Protocol Source Differences

This file lists the observed differences between:

- `autoterm-air-2d-serial-control`
- `AutotermHeaterController`

For this project, `autoterm-air-2d-serial-control` is the preferred source when the two repos disagree, because it targets `AIR 2D`, while `AutotermHeaterController` is based on `4D/44D + PU-27`.

## Likely Causes Of Differences

These differences may be caused by one or more of:

- AIR 2D vs 4D / 44D heater family differences
- no-panel direct heater interaction vs PU-27 controller traffic
- different firmware revisions
- controller protocol vs diagnostic protocol captures
- raw direct-heater capture vs passthrough capture setup

The repos alone do not prove which explanation applies to each difference, so the list below stays descriptive.

## Differences

### Serial baud rate

- AIR 2D repo: `9600 8N1`
- 4D repo: `2400 8N1`

Impact:
- transport configuration cannot be assumed portable across heater families or capture methods

Working choice for this project:
- use `9600 8N1` as the AIR 2D normative default

### Settings / start payload prefix bytes

AIR 2D repo:

```text
0x01 / 0x02 payload: use_time work_time temp_source temp wait_mode level
example: 01 00 04 10 00 08
```

4D repo:

```text
request:  FF FF md ts vt pl
response: 00 78 md ts vt pl
```

Impact:
- the first two payload bytes have incompatible meanings across the repos

Working choice:
- AIR 2D interpretation is normative

### Ventilation / fan-only command `0x23`

AIR 2D repo:

```text
request:  FF FF level FF
response: FF FF level 43
example:  FF FF 08 FF
```

4D repo:

```text
request:  FF FF power 0F
response: 00 78 power 32 / 3B
example:  FF FF 02 0F
```

Impact:
- byte `3` differs in both request and response
- response prefix bytes differ completely

Working choice:
- AIR 2D `0x23` shape is normative

### Status payload length for `0x0F`

AIR 2D repo:

- response length `0x13` = `19` payload bytes

4D repo:

- response length `0x0A` = `10` payload bytes

Impact:
- parser shape, field map, and state decoding differ materially

Working choice:
- AIR 2D 19-byte status layout is normative

### Status model

AIR 2D repo:

- detailed two-part status codes such as `0.1`, `2.3`, `3.35`

4D repo:

- simplified phase values:
  - `00` off
  - `01` starting
  - `02` warming up
  - `03` running
  - `04` shutting down

Impact:
- UI and domain model can either preserve detailed AIR 2D state or collapse everything to coarse phases

Working choice:
- preserve the AIR 2D two-part code, derive coarse phases secondarily

### Temperature and telemetry field map in `0x0F`

AIR 2D repo:

- internal temperature at byte `3`
- external temperature at byte `4`
- voltage at byte `6`
- heater temp at byte `8` with `-15` offset
- fan rpm set / actual at bytes `11` and `12`
- fuel pump frequency at byte `14`

4D repo:

- heater temperature at byte `3`
- external temperature at byte `4`
- voltage at byte `6`
- flame temperature at bytes `7..8`

Impact:
- bytes `7..18` are interpreted differently, not just extended

Working choice:
- use AIR 2D field meanings when available

### Software version example for `0x06`

AIR 2D repo:

- example payload `02 01 03 04 03`
- version `2.1.3.4`

4D repo:

- example payload `03 01 0E 02 03`
- version `3.1.14.2`

Impact:
- no protocol shape conflict, but examples should not be mixed when testing fixtures

Working choice:
- keep fixture sets source-specific

### `0x11` controller / panel temperature examples

AIR 2D repo:

- example payload `0x14` = `20 C`

4D repo:

- example payload `0x1A` = `26 C`

Impact:
- no shape conflict, example values differ only by capture

Working choice:
- no special handling required

### `0x1C` meaning

AIR 2D repo:

- listed once as `Start`
- listed once as `Unknown`

4D repo:

- shown in initialization traffic only

Impact:
- command purpose is unresolved

Working choice:
- treat `0x1C` as initialization-related until AIR 2D capture proves otherwise

### Diagnostic coverage

AIR 2D repo:

- only names diagnostic message types `0x00` and `0x01`

4D repo:

- provides a substantial diagnostic capture set and field map

Impact:
- diagnostic mode is much better documented for 4D than for AIR 2D

Working choice:
- diagnostic decoding can borrow from 4D as a secondary aid, but it is not normative for AIR 2D controller replacement

## Agreements

Despite the differences, both repos agree on:

- preamble `0xAA`
- 5-byte header shape
- device/message-class usage around `0x02`, `0x03`, `0x04`
- CRC16 / Modbus algorithm with polynomial `0xA001`
- high-byte-first checksum encoding in the published examples
- command ids `0x01`, `0x02`, `0x03`, `0x06`, `0x07`, `0x0F`, `0x11`, and `0x23`

## Resulting Project Policy

- `docs/protocol.md` uses AIR 2D values as the normative baseline.
- 4D repo data is kept as secondary context and for future compatibility work.
- Code should be made tolerant of 4D-style variants where practical, but not documented as if those variants define AIR 2D behavior.
