# Autoterm Heater UX for GX Touch

## Summary

This document defines the intended user experience for `Autoterm AIR 2D` on GX Touch, using a dedicated heater device and local GX Touch interaction as the primary target.

The UX is based on the practical jobs of a heater user, not on the temporary genset reuse path. It is aligned with:

- the current dedicated heater D-Bus service: `com.victronenergy.heater.autoterm_air2d`
- the current Venus UI component set in `venus-gui-v2`
- the known AIR 2D control-panel feature model from the modern Autoterm Comfort Control panel

This document is intentionally staged:

- `MVP`: should be implemented and usable in the first complete heater UI
- `Next`: should be designed now, but may follow after the first usable heater UI ships
- `Later`: should only be exposed once backend/protocol semantics are actually validated

## Design Principles

- The heater is its own device, not a genset-shaped UI.
- The root heater page is the daily-use page and must cover the most common tasks without extra navigation.
- Only the root heater page should be a `DevicePage`.
- All heater subpages should be plain `Page`.
- The repeated Device Info footer on every heater page is a UX bug caused by using `DevicePage` for subpages and should be removed.
- D-Bus helper objects such as `VeQuickItem` must stay at page scope, not inside `VisibleItemModel`.
- Unsupported or unavailable functions should be hidden or clearly staged, not shown as broken controls.

## User Needs

### Daily operator

The daily operator needs to:

- see whether the heater is off, starting, heating, ventilating, cooling down, or faulted
- start or stop the heater quickly
- switch between supported operating modes
- adjust temperature or power without leaving the main page
- confirm that the heater actually reacted

### Monitoring

The user needs to:

- check control temperature and heater temperature
- confirm battery voltage is healthy
- see runtime while active
- inspect fan and fuel-pump-related live values when debugging or validating behavior
- distinguish heater fault from communication fault

### Scheduling

The user needs to:

- enable or disable up to three timers
- assign a cycle pattern, start time, duration, and mode per timer
- understand timer summaries without reopening each timer

### Setup

The user needs to:

- choose the relevant sensor source
- verify that the heater behaves according to the installation layout
- adjust basic operating defaults where supported

## Staged Functional Scope

### MVP

- Start / stop heater
- Power mode
- Temperature mode
- Ventilation mode
- Heat + ventilation mode
- Sensor source selection
- Live status and diagnostics
- Timer information architecture and editable timer placeholders

### Next

- Better timer summaries and mode-specific timer editing visibility
- Cleaner status presentation and action wording
- Better live-data labeling and condensed root-page summaries
- Smarter visibility rules for controls based on connection, fault, and phase

### Later

- Thermostat / wait-mode variant, only when protocol semantics are validated
- Any advanced heater behavior that depends on protocol fields still marked uncertain
- Timer execution semantics beyond placeholder editing, if not yet backed by the heater protocol/provider

## UX Structure and Component Map

## Root Device Entry

Ownership: `DeviceListDelegate_heater.qml`

Purpose:

- give the user confidence that the heater exists, is connected, and is in a sensible state
- surface one live thermal signal and the current heater state
- open the root heater page

Content:

- primary text: custom name or product name
- secondary text:
  - current state when available
  - fault text when faulted
  - not connected text when disconnected
- quantity row:
  - `control temperature`

Component mapping:

- `DeviceListDelegate`
- `QuantityObjectModel`
- `VeQuickItem` for:
  - `/StateText`
  - `/Temperatures/Control`

Rules:

- fault/disconnect must override the calm live-summary presentation
- clicking the row always opens the root heater page only

## Root Heater Page

Ownership: `PageHeater.qml`

Page type:

- `DevicePage`

Purpose:

- be the everyday control center for the heater
- support “look, decide, act” without forcing subpage navigation

Order and component mapping:

1. optional page-level warning banner
   - shown only when a real heater fault, communication alarm, or blocking state exists
   - not rendered as a permanent empty list item
2. `ListText`: State
   - source: `/StateText`
3. `ListText`: Runtime
   - source: `/Runtime`
4. `ListButton`: Primary action
   - source/action: `/StartStop`
   - opens a confirmation modal before sending the action
   - label must reflect the action:
     - `Start`
     - `Stop`
     - `Start ventilation`
     - `Stop ventilation`
5. `ListRadioButtonGroup`: Mode selector
   - source: `/Mode`
6. `ListSpinBox`: Target temperature
   - source: `/Settings/TargetTemperature`
   - visible only in temperature-like modes
7. `ListRangeSlider`: Power level
   - source: `/Settings/PowerLevel`
   - visible only in power and ventilation-oriented modes
8. `ListQuantityGroup`: Live values
   - `control temperature`
   - `heater temperature`
9. `ListNavigation`: Live Data
10. `ListNavigation`: Diagnostics
11. `ListNavigation`: Timers, only when timer UX is actually implemented
12. `ListNavigation`: Heater Settings

Root-page behavior:

- The main page must support the full daily operator workflow.
- The page must not rely on `/StartStop` alone to describe current run state.
- Actual state comes from `/State` and `/StateText`.
- The separate informational `Mode` row is intentionally omitted from the main page because the selector already communicates and controls mode.
- The primary action label should reflect the current mode:
  - `Start` / `Stop`
  - `Start ventilation` / `Stop ventilation`
- Fault presentation should not consume a permanent row in the normal list.
- A top warning/banner area should only appear when there is a real fault or communication issue.

## Subpages

All subpages below must be plain `Page`, not `DevicePage`.

That removes repeated Device Info footer links and makes the root page the clear device entrypoint.

### Timers Page

Ownership: `PageHeaterTimers.qml`

Page type:

- `Page`

Purpose:

- show all timers as an overview and entry point

Component mapping:

- `GradientListView`
- 3x `ListNavigation`

Each timer row summary should show:

- enabled / disabled
- cycle
- start time
- duration
- optionally compact mode summary if space allows

Data sources:

- `/Timers/0..2/Enabled`
- `/Timers/0..2/Cycle`
- `/Timers/0..2/StartHour`
- `/Timers/0..2/StartMinute`
- `/Timers/0..2/DurationMinutes`
- `/Timers/0..2/Mode`

### Timer Detail Page

Ownership: `PageHeaterTimer.qml`

Page type:

- `Page`

Purpose:

- edit one timer in full

Component mapping:

- `ListSwitch`: enabled
- `ListRadioButtonGroup`: cycle
- `ListTimeSelector`: start time
- `ListTimeSelector`: duration
- `ListRadioButtonGroup`: mode
- `ListSpinBox`: target temperature when relevant
- `ListRangeSlider`: power level when relevant

Data sources:

- `/Timers/<n>/Enabled`
- `/Timers/<n>/Cycle`
- `/Timers/<n>/Days`
- `/Timers/<n>/StartHour`
- `/Timers/<n>/StartMinute`
- `/Timers/<n>/DurationMinutes`
- `/Timers/<n>/Mode`
- `/Timers/<n>/TargetTemperature`
- `/Timers/<n>/PowerLevel`

Timer editing rules:

- time-oriented inputs should use time selectors where possible instead of raw numeric hour/minute editing
- power and temperature controls must not be shown together when the chosen timer mode makes one irrelevant
- if timer backend semantics are still placeholder-only, the UX should still be structurally correct and clearly staged as `Next`

### Live Data Page

Ownership: `PageHeaterLiveData.qml`

Page type:

- `Page`

Purpose:

- expose deeper operating telemetry for validation and troubleshooting

Component mapping:

- `ListTemperature`: control temperature
- `ListTemperature`: internal temperature
- `ListTemperature`: heater temperature
- `ListQuantity`: battery voltage
- `ListQuantity`: fan set RPM
- `ListQuantity`: fan actual RPM
- `ListQuantity`: fuel pump frequency

Data sources:

- `/Temperatures/Control`
- `/Temperatures/Internal`
- `/Temperatures/Heater`
- `/Dc/0/Voltage`
- `/Status/FanRpmSet`
- `/Status/FanRpmActual`
- `/Status/FuelPumpFrequency`

### Diagnostics Page

Ownership: `PageHeaterDiagnostics.qml`

Page type:

- `Page`

Purpose:

- let the user distinguish heater fault from communication or integration fault

Component mapping:

- `ListText`: connection state
- `ListText`: heater state text
- `ListText`: heater error code
- `ListText`: heater error text
- `ListText`: communication alarm

Data sources:

- `/Connected`
- `/StateText`
- `/ErrorCode`
- `/ErrorText`
- `/Alarms/Communication`

### Heater Settings Page

Ownership: `PageHeaterSettings.qml`

Page type:

- `Page`

Purpose:

- contain heater-specific preferences, not generic device metadata

Component mapping:

- `ListRadioButtonGroup`: sensor source
- `ListSpinBox`: target temperature, when meaningful
- `ListRangeSlider`: power level, when meaningful

Data sources:

- `/Settings/SensorSource`
- `/Settings/SensorSourceText`
- `/Settings/TargetTemperature`
- `/Settings/PowerLevel`

## D-Bus Contract and UI Semantics

The heater UX depends on these D-Bus paths:

- `/Connected`
- `/State`
- `/StateText`
- `/Mode`
- `/ModeText`
- `/StartStop`
- `/Runtime`
- `/ErrorCode`
- `/ErrorText`
- `/Alarms/Communication`
- `/Dc/0/Voltage`
- `/Temperatures/Internal`
- `/Temperatures/Control`
- `/Temperatures/Heater`
- `/Status/FanRpmSet`
- `/Status/FanRpmActual`
- `/Status/FuelPumpFrequency`
- `/Settings/TargetTemperature`
- `/Settings/PowerLevel`
- `/Settings/SensorSource`
- `/Settings/SensorSourceText`
- `/Timers/0..2/*`

Semantics that the UI must follow:

- `/StartStop` is an action surface, not the sole state source.
- Actual operating truth comes from `/State` and `/StateText`.
- Cooldown, fault, and disconnect must remain visible even if `/StartStop` is already `0`.
- Unsupported controls must be hidden by invalid or missing D-Bus items, not rendered as dead controls.
- Ventilation is a first-class user-visible mode and should not be presented as a hidden protocol quirk.
- Battery voltage is monitoring data and belongs on Live Data, not in the root device-list summary.
- Sensor source is a setup-time setting and belongs on Heater Settings, not the root page.

## Mode Model

### MVP modes

- `Power`
- `Temperature`
- `Ventilation`
- `Heat + ventilation`

### Later modes

- `Thermostat / wait-mode`
  - only after protocol semantics are validated well enough to explain it confidently to the user

## User Flows

### Flow 1: Start heating to a target temperature

1. User opens `Devices`.
2. User sees heater name, current control temperature, and battery voltage.
2. User sees heater name, current control temperature, and current state.
3. User opens the root heater page.
4. User checks `State` and `Mode`.
4. User checks `State`.
5. User selects `Temperature` mode if needed.
6. User sets the target temperature.
7. User presses the primary start button.
8. User confirms the action in the modal.
9. User sees state progress through starting, warming, and running.
10. User sees live values respond.

### Flow 2: Switch to ventilation

1. User opens the root heater page.
2. User selects `Ventilation`.
3. User sets power/fan level using a slider.
4. User presses the primary start button.
5. User confirms the action in the modal.
6. User sees ventilation-specific state text and fan-related live metrics.

### Flow 3: Investigate a problem

1. User sees fault or disconnected feedback in the device list.
2. User opens the heater.
3. If present, user sees a warning banner at the top of the root page.
3. User opens `Diagnostics`.
4. User checks:
   - connection state
   - communication alarm
   - heater error code
   - heater error text
   - current state text
5. User determines whether the issue is a heater-side fault or Cerbo communication/integration issue.

### Flow 4: Configure a timer

1. User opens `Timers`.
2. User selects one timer.
3. User enables it.
4. User selects cycle, start time, duration, and mode.
5. User sets temperature or power depending on mode.
6. User returns to the timer overview and sees a readable summary.

This flow is `Next` unless timer behavior is fully backed by the provider and validated.

### Flow 5: Installer/basic setup

1. User opens `Heater Settings`.
2. User selects the sensor source that matches the installation.
3. User adjusts default target temperature or power if supported.
4. User verifies the expected control behavior.
5. User returns to the root page and tests start/stop.

## Validation and Acceptance

The UX is acceptable when:

- the root page is the only page with the automatic device footer link
- all heater subpages open without device-footer duplication
- the root page supports the daily operator workflow without forcing Diagnostics or Live Data
- mode-specific controls never appear in contradictory combinations
- no not-yet-implemented page or control is visible in the live UI
- faults and disconnects are obvious from both the device list and Diagnostics
- fault UI is absent during normal operation and appears only when an actual issue exists
- the timer page structure exists even if execution semantics are still staged
- the UX document clearly distinguishes:
  - `MVP now`
  - `Next after backend support`
  - `Later after protocol validation`

## Known Rough Edges to Remove

- Heater subpages currently using `DevicePage` should be converted to plain `Page`.
- Timer start time and duration should move from raw spin boxes toward time-oriented controls.
- Root-page action text should reflect actual mode and state more precisely.
- Root-page fault presentation should move to a conditional warning banner instead of a list row.
- Root-page summaries should favor operationally meaningful information over electrical debug values.

## Assumptions and Defaults

- Scope is local GX Touch first.
- Web parity is not a design driver for this document, only a later adaptation concern.
- The document describes the intended AIR 2D user experience, not only current implementation status.
- The heater remains a dedicated heater device, not a genset-shaped UX.
- Current backend support is sufficient for root control, live data, diagnostics, and timer placeholders.
- Timer execution semantics remain staged until real backend support is implemented and verified.
- Any page or control that is not implemented end-to-end should remain hidden.
