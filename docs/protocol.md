# Autoterm Protocol

This document describes the currently understood UART control protocol for an `Autoterm AIR 2D`.

## Confidence Levels

- `High`: field or frame shape is sufficiently stable for implementation
- `Medium`: behavior is observed and plausible, but still needs real-heater confirmation
- `Low`: command is known to exist, but field semantics are incomplete
- `Unverified`: frame or field is not yet documented well enough to rely on

## Physical Layer

### Wiring assumptions

- Heater-side interface is `5V UART`.
- GND must be shared across heater, USB-to-TTL adapter, and host.
- The red supply wire on the harness is not part of the UART pair and must not be connected to TTL signal pins.

### Serial settings

Current working baseline:

- baud rate: `9600`
- data bits: `8`
- parity: `none`
- stop bits: `1`

Confidence: `High`

## Frame Format

Every message is:

| Byte | Meaning |
| --- | --- |
| 0 | preamble `0xAA` |
| 1 | device / message class |
| 2 | payload length |
| 3 | message id 1, observed as `0x00` |
| 4 | message id 2, command / report type |
| 5..n | payload |
| last 2 | CRC16 checksum |

### Device byte

- `0x02`: diagnostic message class
- `0x03`: request
- `0x04`: response
- `0x00`: observed in at least one initialization-style acknowledgement

Confidence: `High` for `0x02`, `0x03`, `0x04`; `Medium` for `0x00`

### CRC

- CRC type: CRC16 / Modbus
- polynomial: `0xA001`
- initial value: `0xFFFF`
- checksum bytes on the wire: high byte first

Confidence: `High`

Example:

```text
AA 03 00 00 03 5D 7C
```

The checksum bytes `5D 7C` correspond to CRC value `0x5D7C`.

## Session Model

### Request / response

- Traffic is request / response oriented.
- The heater replies with the same `message id 2` as the request.

Confidence: `High`

### Polling behavior

- `0x0F` status polling is periodic during normal operation.
- Exact cadence is not yet fixed in this spec and should stay configurable in code.

Confidence: `Medium`

### Initialization

Observed initialization-style sequence:

```text
C -> H  aa 03 00 00 1c | 95 3d
H -> C  aa 00 00 00 1c | d1 3d
C -> H  aa 03 00 00 04 | 9f 3d
H -> C  aa 04 05 00 04 | 12 9e 00 15 80 | 05 3d
C -> H  aa 03 00 00 06 | 5e bc
H -> C  aa 04 05 00 06 | 02 01 03 04 03 | c1 6e
```

Use this as the current startup baseline. The exact required startup order is still `Medium` confidence.

## Command Set

### `0x01` Turn heater on

Confidence: `High`

Request:

```text
AA 03 06 00 01 | 01 00 04 10 00 08 | B3 EE
```

Response:

```text
AA 04 06 00 01 | 01 00 04 10 00 08 | 69 5F
```

Payload layout:

| Byte | Meaning |
| --- | --- |
| 0 | use work time: `0 = yes`, `1 = no` |
| 1 | work time |
| 2 | temperature source |
| 3 | target temperature |
| 4 | wait mode |
| 5 | level |

Field meanings:

- temperature source:
  - `0x01`: internal sensor
  - `0x02`: panel sensor
  - `0x03`: external sensor
  - `0x04`: no automatic temperature control
- wait mode:
  - `0x01`: on
  - `0x02`: off
- level:
  - `0..9`

### `0x02` Get / set settings

Confidence: `High`

Get settings request:

```text
AA 03 00 00 02 | 9D BD
```

Settings response:

```text
AA 04 06 00 02 | 01 00 04 10 00 08 | 69 6C
```

Set settings request:

```text
AA 03 06 00 02 | use_time work_time temp_source temp wait_mode level | CRC
```

The payload layout is identical to `0x01`.

### `0x03` Turn heater / fan off

Confidence: `High`

```text
AA 03 00 00 03 | 5D 7C
AA 04 00 00 03 | 29 7D
```

### `0x06` Get version

Confidence: `High`

Request:

```text
AA 03 00 00 06 | 5E BC
```

Response example:

```text
AA 04 05 00 06 | 02 01 03 04 03 | C1 6E
```

Payload layout:

| Byte | Meaning |
| --- | --- |
| 0 | version major |
| 1 | version minor |
| 2 | version patch |
| 3 | version build |
| 4 | blackbox version |

Example version: `2.1.3.4`, blackbox version `3`.

### `0x07` Diagnostic control

Confidence: `Medium`

Known enable request:

```text
AA 03 01 00 07 | 01 | 1D 9E
```

Known disable request form:

```text
AA 03 01 00 07 | 00 | CRC
```

The command exists, but the full response behavior is not fully documented here.

### `0x08` Set fan speed

Confidence: `Low`

The command id is known, but its payload and behavior are not yet documented.

### `0x0B` Report

Confidence: `Low`

The command id is known, but its payload and behavior are not yet documented.

### `0x0D` Unlock

Confidence: `Medium`

Observed frame:

```text
AA 03 00 00 0D | 99 FD
AA 00 00 00 0D | DD FD
```

The command likely clears a lockout or unblock condition, but that semantic still needs confirmation.

### `0x0F` Get status

Confidence: `High`

Request:

```text
AA 03 00 00 0F | 58 7C
```

Response example:

```text
AA 04 13 00 0F | 00 01 00 13 7F 00 86 01 24 00 00 00 00 00 00 00 00 00 64 | D9 49
```

Payload layout:

| Byte | Meaning |
| --- | --- |
| 0 | status code high part |
| 1 | status code low part |
| 2 | unknown |
| 3 | internal temp sensor, signed byte |
| 4 | external temp sensor, signed byte |
| 5 | unknown |
| 6 | voltage / 10 |
| 7 | unknown |
| 8 | heater temp sensor minus 15 |
| 9 | unknown |
| 10 | unknown |
| 11 | fan rpm set, scaled |
| 12 | fan rpm actual, scaled |
| 13 | unknown |
| 14 | fuel pump frequency / 100 |
| 15 | unknown |
| 16 | unknown |
| 17 | unknown |
| 18 | unknown |

Status codes:

| Code | Meaning |
| --- | --- |
| `0.1` | standby |
| `1.0` | cooling flame sensor |
| `1.1` | ventilation |
| `2.1` | heating glow plug |
| `2.2` | ignition 1 |
| `2.3` | ignition 2 |
| `2.4` | heating combustion chamber |
| `3.0` | heating |
| `3.35` | only fan |
| `3.4` | cooling down |
| `4.0` | shutting down |

Interpretation rules:

- byte `3` and byte `4` should be interpreted as signed 8-bit temperatures
- byte `6` is voltage in tenths of a volt
- byte `8` is heater temperature sensor value offset by `-15`
- unknown bytes should be preserved in parsing and logs

### `0x11` Set temperature

Confidence: `High`

Request:

```text
AA 03 01 00 11 | 14 | B2 51
```

Response:

```text
AA 04 01 00 11 | 14 | 72 E4
```

Payload:

| Byte | Meaning |
| --- | --- |
| 0 | panel temperature sensor |

### `0x13` Fuel pump

Confidence: `Low`

The command id is known, but its payload and behavior are not yet documented.

### `0x1C` Initialization-related command

Confidence: `Low`

`0x1C` appears to be part of startup or identification flow. Its exact semantics are still unresolved.

### `0x23` Turn only fan on

Confidence: `High`

Request:

```text
AA 03 04 00 23 | FF FF 08 FF | E1 0B
```

Response:

```text
AA 04 04 00 23 | FF FF 08 43 | B6 4B
```

Payload layout:

| Byte | Meaning |
| --- | --- |
| 0 | unknown, example `FF` |
| 1 | unknown, example `FF` |
| 2 | level `0..9` |
| 3 | unknown |

This command is currently the documented fan-only / ventilation control frame.

## Diagnostic Message Types

Known message types:

- `0x00`: connect
- `0x01`: heater

Diagnostic-mode field decoding is incomplete and should remain secondary to controller-replacement work.

## Heater State Model

The current externally visible AIR 2D state model is the two-part status code returned by `0x0F`:

| Code | Meaning |
| --- | --- |
| `0.1` | standby |
| `1.0` | cooling flame sensor |
| `1.1` | ventilation |
| `2.1` | heating glow plug |
| `2.2` | ignition 1 |
| `2.3` | ignition 2 |
| `2.4` | heating combustion chamber |
| `3.0` | heating |
| `3.35` | only fan |
| `3.4` | cooling down |
| `4.0` | shutting down |

Implementation guidance:

- preserve the full two-part status code in the domain model
- derive simplified UI phases from the detailed status code as a secondary mapping
- preserve raw status bytes for later refinement of undocumented fields

## Implementation Rules

- Use `9600 8N1` as the default transport profile.
- Use the 19-byte `0x0F` response layout as the default status model.
- Use the 6-byte settings payload layout for `0x01` and `0x02`.
- Preserve unknown bytes and raw frames in logs.
- Keep parser and emulator code strict enough for known fields but tolerant enough to retain undocumented bytes.

## Still Unverified

- exact startup order before normal control traffic
- meaning of undocumented bytes in `0x0F`
- exact meaning of `0x23` byte `3`
- whether `0x08`, `0x0B`, and `0x13` are needed for full panel replacement
- exact semantics of `0x1C`
- complete diagnostic-mode field map
