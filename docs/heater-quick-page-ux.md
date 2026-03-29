# Autoterm Heater Quick Page UX

## Summary

This document defines the ideal native bottom-bar `Heater` quick page for `AUTOTERM AIR` heaters on GX Touch.

It uses the `AUTOTERM Comfort Control V2` user manual as the functional reference and adapts that model to a touch-first GX environment instead of copying the rotary-knob panel literally.

This is a quick-page document, not a full device-page document. The core rule is:

- the quick page is for frequent operational use
- one-time, installer, or commissioning settings stay on the heater device page

Scope defaults:

- `AIR only`
- `Dashboard + sections`
- multi-heater capable, with a `TabBar` only when more than one heater exists

Manual baseline:

- `AUTOTERM Comfort Control V2 User’s manual`, English `10.2023 - v1.23`
- [Official PDF](https://cdn.autoterm.com/Manuals/Control%20panels/Comfort%20Control%20V2/Comfort%20Control%20EN%2010.2023%20-%20v1.23.pdf)

## Design Principles

- The quick page is the heater’s daily-use command center.
- The quick page must be faster than opening the device page for normal operation.
- The device page remains the home for one-time settings and deep configuration.
- Heater control must feel stateful and alive, not like a static settings form.
- Faults and maintenance reminders must interrupt the calm layout clearly, but only when relevant.
- The quick page should surface the most important thermal and state information first.
- The quick page may use custom components when stock Venus components are too settings-like or too weak visually.
- Heater temperature is telemetry, not room temperature.
- The current reference temperature source may be shown on the quick page as context, but not changed there.

## Visual Direction

The quick page should feel like a premium embedded appliance interface, not a recycled settings page and not a generic smart-home dashboard.

Visual goals:

- strong sense of thermal state
- bold, glanceable numbers
- touch-friendly controls that feel like operating hardware, not editing form rows
- one dominant hero area instead of many equal-weight cards
- restrained, purposeful motion

Recommended visual tone:

- dark graphite or warm charcoal base
- warm amber / orange accent for heating
- cool cyan accent for ventilation
- red reserved for faults and blocking warnings
- subtle gradients and soft depth, not flat white cards
- large temperature typography with smaller secondary operational metrics

Avoid:

- generic list-heavy layouts
- flat “settings app” card stacks
- excessive glassmorphism
- purple or neon visual bias
- decorative animation that competes with state readability

## Layout Zones

The page should be designed as a dashboard with a clear visual hierarchy.

### Zone 1: Heater Selection

- top `TabBar` only when more than one heater exists
- tabs should feel compact and hardware-like
- selected tab should be visually obvious without taking over the page

### Zone 2: Hero Status

This is the visual anchor of the page.

It should show:

- heater name
- current state
- current mode
- room/reference temperature as the dominant value
- heater unit temperature as secondary value
- optional compact timer summary
- fault or maintenance banner when relevant

This zone should carry most of the visual identity of the page.

### Zone 3: Primary Operation

This is the main command area directly under the hero section.

It should contain:

- start / stop control
- mode selector
- target control for the current mode
- active-mode quick edit access when inline controls are insufficient

This area should support the full daily-use workflow without requiring the device page.

### Zone 4: Operational Summary

This area should contain compact, supporting operational summaries:

- timers
- battery voltage, if shown
- runtime
- fan / pump highlights, if visually useful
- room temperature source as read-only context

This should feel denser and more compact than the hero zone, but still intentionally designed.

### Zone 5: Secondary Actions

Bottom action area for:

- `Timers`
- `Live data`
- `Diagnostics`
- `Open device page`

These actions should read as secondary destinations, not as the main focus of the page.

## Custom Component Plan

The quick page should be allowed to introduce custom components where stock Venus list controls are too weak visually or too settings-like.

### `HeaterHeroCard`

Purpose:

- create a strong central identity for the heater quick page

Recommended content:

- large room/reference temperature
- smaller heater temperature
- state label
- mode label
- compact source/timer context

Recommended behavior:

- warm glow or accent shift when actively heating
- cool accent treatment in ventilation mode
- stronger alert framing when faulted

### `ModeSegmentedControl`

Purpose:

- replace plain radio-button behavior with a touch-friendly mode switcher

Recommended behavior:

- large pill or segment buttons
- icon + short label per mode
- selected mode gets stronger fill, border, or glow
- unavailable modes are hidden, not disabled placeholders

### `RunTargetCard`

Purpose:

- provide one unified target-editing surface that changes by mode

Variants:

- temperature modes:
  - large setpoint editor
- power mode:
  - stepped power editor
- ventilation mode:
  - fan / power-level editor
- thermostat mode:
  - thermostat-specific target or hysteresis summary, if supported later

### `ThermalDial`

Purpose:

- premium temperature target editor for temperature-regulated modes

Why custom:

- a dial better matches “set the cabin temperature” than a small list spin box

Behavior:

- big numeric target in the center
- ring or arc around the target
- current room temperature can be shown on the same scale

### `PowerArcSlider`

Purpose:

- replace a generic slider for heater power levels

Why custom:

- power levels are stepped and appliance-like, not freeform

Behavior:

- segmented bar or arc
- clearly communicates low-to-high power steps
- selected step should feel tactile

### `TimerSummaryStrip`

Purpose:

- show all 3 timers as compact operational presets

Behavior:

- one chip or tile per timer
- enabled state always visible
- start time and day pattern shown compactly
- tap enters deeper timer flow

### `HeaterAlertBanner`

Purpose:

- handle fault, communication-loss, no-sensor, and maintenance states cleanly

Behavior:

- visually integrated with the page, ideally near the hero card
- strong enough to interrupt, but not so large that it destroys the page layout
- title + short secondary explanation + optional action

### `LiveMetricChips`

Purpose:

- present small supporting metrics without dropping back to a plain list

Good candidates:

- battery voltage
- runtime
- fan RPM
- pump frequency
- room source

### `QuickActionDock`

Purpose:

- group bottom-of-page navigation actions into a designed control strip rather than plain list rows

## Motion and State Feedback

Motion should communicate heater state changes, not decorate the page.

Recommended motion rules:

- gentle fade / slide when switching heater tabs
- subtle glow pulse during active heating
- cooler motion treatment for ventilation
- short highlight pulse when mode or target changes successfully
- visible but brief transition when faults appear

Avoid:

- looping decorative animation with no meaning
- bouncy motion
- excessive parallax
- slow transitions that make the heater feel less responsive

State-specific feedback ideas:

- `Starting`: restrained pulse or breathing highlight
- `Heating`: warm steady glow
- `Ventilating`: cool accent treatment
- `Shutting down`: dimming state ribbon or reduced glow
- `Fault`: alert banner plus strong but static error emphasis

## Visual Component Hierarchy

The page should not give every element equal visual weight.

Recommended hierarchy:

1. hero temperature + heater state
2. start / stop and mode selection
3. current mode target control
4. timer summary
5. compact metrics
6. bottom navigation actions

This hierarchy should remain true on both the single-heater and multi-heater versions of the page.

## Comfort Control Feature Baseline

For `AIR` heaters, the Comfort Control manual establishes these relevant user-facing functions:

- main screen status:
  - time
  - supply voltage
  - temperature
  - active mode
  - active timers
- quick start/stop behavior
- active-mode quick editing
- heating modes:
  - `Temperature`
  - `Power`
  - `Heat + ventilation`
  - `Thermostat`
- `Ventilation`
- up to `3` timers
- temperature source selection:
  - `By panel`
  - `By heater`
  - `External`
- advanced heater settings:
  - shutdown voltage
  - thermostat rise/drop
  - heater/control-unit info
- error reporting
- 30-day maintenance reminder

GX adaptation rules:

- panel-local features such as language, display brightness, sleep mode, LED settings, and time/date are out of scope for heater UX on GX
- quick-button and rotary-knob behavior must be translated into direct touch actions, dialogs, and sheets
- GX quick page is not a “main menu”; it is the operational landing page

## Quick Page vs Device Page

### Quick Page Only

These belong on the bottom-bar `Heater` quick page:

- start / stop
- current mode visibility
- mode switching
- active target adjustment
- active manual run duration, if implemented
- room/reference temperature
- heater unit temperature
- optional battery voltage
- active timers summary
- timer enable / disable
- entry into timer editing
- live heater state and phase feedback
- fault visibility
- maintenance reminder
- shortcuts to diagnostics, live data, and device page

### Device Page Only

These must stay on the heater device page:

- temperature source selection
- shutdown voltage
- thermostat default rise/drop values
- serial numbers
- software / firmware versions
- total operating hours info pages, if treated as device info rather than operational telemetry
- calibration
- installation / commissioning options
- backend-specific configuration
- anything the user would not normally change during operation

Decision rule:

- if a setting is primarily chosen once during installation, setup, or troubleshooting, it belongs on the device page, not the quick page

## Information Architecture

## Page Container

The quick page is the native bottom-bar `Heater` page.

Header behavior:

- page title: `Heater`
- if only one heater exists:
  - no `TabBar`
- if more than one heater exists:
  - show a `TabBar`
  - tab labels use device names
  - each tab switches heater context only

The quick page should never expose cross-heater controls at the same time. One visible heater context per page view.

## Page Layout

Recommended vertical structure:

1. header / tabs
2. hero status card
3. primary control area
4. timer summary strip
5. secondary action cards
6. bottom shortcuts

Recommended layout behavior:

- the top half of the page should be status + control heavy
- the lower half should be summary + navigation heavy
- scrolling is acceptable, but the first screenful should already support the primary operator workflow

## Hero Status Card

Purpose:

- immediately answer “what is the heater doing right now?”

Content:

- heater name
- current state
- current mode
- room/reference temperature
- heater unit temperature
- optional battery voltage
- active timer summary or next timer summary

Banner states inside or above the card:

- active heater fault
- communication fault
- no valid room sensor while temperature-regulated mode is desired
- 30-day maintenance reminder

This card should be visually stronger than a normal list item.

## Primary Control Area

Purpose:

- let the user look, decide, and act without leaving the quick page

Controls:

- primary action button:
  - `Start heater`
  - `Stop heater`
  - `Start ventilation`
  - `Stop ventilation`
- mode selector
- active target editor
- active-mode quick edit entry if extra settings do not fit inline
- optional manual run duration editor

Quick-page control rules:

- controls must adapt to the active mode
- only controls relevant to the selected mode should be visible
- the current state must visibly react to user actions
- start/stop should use clear confirmation where stopping could be disruptive

## Timer Summary Strip

Purpose:

- show that timer automation exists and whether it matters now

Content:

- three compact timer chips or cards
- enabled / disabled state
- start time
- day pattern
- mode summary

Interactions:

- quick enable / disable
- tap to open full timer edit flow

The quick page should show timers as operational automation, not as a buried settings submenu.

## Secondary Action Area

Purpose:

- group less frequent but still operational actions

Entries:

- `Timers`
- `Live data`
- `Diagnostics`
- `Open device page`

No setup/settings card should live here other than `Open device page`.

## Functional Mapping

## Start / Stop

Quick page:

- yes
- primary button in the main control area

Behavior:

- action label reflects the actual action
- visible feedback must reflect phase transitions:
  - starting
  - warming up
  - running
  - shutting down
  - ventilation
  - fault

## Heating Modes

Quick page:

- yes

Modes to include:

- `Temperature`
- `Power`
- `Heat + ventilation`
- `Thermostat`
- `Ventilation`

### Temperature

Visible quick-page controls:

- target temperature
- optional manual run duration

Feedback:

- room/reference temperature
- heater state

### Power

Visible quick-page controls:

- power level
- optional manual run duration

Feedback:

- heater state
- room/reference temperature as monitoring only

### Heat + Ventilation

Visible quick-page controls:

- target temperature
- optional manual run duration

Feedback:

- room/reference temperature
- state transitions between heating and ventilating

### Thermostat

Visible quick-page controls:

- target temperature
- optional manual run duration

Device-page-only related settings:

- thermostat rise/drop defaults

Feedback:

- room/reference temperature
- current on/off cycle state

### Ventilation

Visible quick-page controls:

- power level
- optional manual run duration

Feedback:

- ventilation state
- room/reference temperature and heater temperature as telemetry

## Active Mode Settings

Quick page:

- yes

Approach:

- the most important setting should be inline
- extra mode-specific settings may open a `QuickModeEditorSheet`

Examples:

- Temperature / Heat + ventilation / Thermostat:
  - inline target temperature
- Power / Ventilation:
  - inline power editor
- duration:
  - inline if it fits cleanly, otherwise in quick editor sheet

## Timers

Quick page:

- yes, as overview + entry point

Device page:

- no, unless implementation later decides all timer editing belongs there

Quick-page timer responsibilities:

- show all 3 timers
- allow enable / disable
- show schedule summary
- open full timer editing

Timer editing flow should support:

- start time
- duration
- day pattern:
  - Every day
  - Every workday
  - Selected days
- mode
- temperature or power target as relevant

## Temperature Source Selection

Quick page:

- read-only only

Device page:

- editable

Quick-page behavior:

- show current reference source as context if it adds clarity
- never allow changing it from the quick page

Device-page behavior:

- allow changing the reference source
- current GX-oriented mapping should acknowledge likely source types such as:
  - Cerbo room sensor
  - Heater intake sensor
  - future external heater sensor distinction, if backend support becomes explicit

## Advanced Heater Settings

Quick page:

- no

Device page only:

- shutdown voltage
- thermostat rise/drop defaults
- advanced heater behavior
- configuration-type options

## Heater Info

Quick page:

- no full info section

Quick page may show:

- concise operational context only

Device page only:

- serial number
- software / firmware version
- operating hours if treated as device info

## Faults and Maintenance Reminder

Quick page:

- yes

Behavior:

- use a prominent banner or alert zone
- show only when relevant
- provide a direct path to diagnostics

Maintenance reminder:

- show as an actionable banner
- explain the recommendation briefly
- allow the user to open the recommended run/start flow or dismiss for now, depending on backend support

## Ideal Component Plan

The quick page should not be limited to stock Venus list items.

Recommended custom components:

- `HeaterHeroCard`
  - large state and temperature presentation
- `ModeSegmentedControl`
  - touch-friendly mode selector
- `RunTargetCard`
  - unified target control that switches between temperature and power behavior
- `TimerSummaryStrip`
  - compact 3-timer summary with enable/disable affordance
- `HeaterAlertBanner`
  - fault, communication, no-sensor, and maintenance reminder presentation
- `QuickModeEditorSheet`
  - additional mode-specific settings without leaving the page
- `HeaterInfoStrip`
  - compact operational metadata only, not deep device info

Stock components are still appropriate for:

- bottom-page navigation links
- diagnostics list pages
- live data list pages
- full timer editing forms
- device-page setup forms

## User Flows

### Flow 1: Start heating in Temperature mode

1. User opens `Heater` quick page.
2. User sees current state and room/reference temperature.
3. User selects `Temperature`.
4. User adjusts target temperature.
5. User presses `Start heater`.
6. Hero card changes through starting / warming / running states.

### Flow 2: Start heating in Power mode

1. User opens quick page.
2. User selects `Power`.
3. User adjusts power level.
4. User starts heater.
5. Quick page shows running state and live temperatures.

### Flow 3: Switch to Ventilation

1. User opens quick page.
2. User selects `Ventilation`.
3. User adjusts ventilation power.
4. User starts ventilation.
5. Quick page reflects ventilation-specific state and labeling.

### Flow 4: Edit active mode settings

1. User opens quick page while the heater is already operating.
2. User adjusts the inline target control or opens the quick mode editor.
3. User confirms changes if required.
4. Quick page updates immediately.

### Flow 5: Enable or disable a timer

1. User opens quick page.
2. User sees timer strip with timer states.
3. User toggles timer enabled state.
4. Timer chip updates immediately.

### Flow 6: Open timer editing

1. User taps a timer chip or `Timers`.
2. User enters the timer editing flow.
3. User edits schedule, duration, mode, and target.
4. User returns to quick page and sees updated timer summary.

### Flow 7: Inspect a fault

1. Quick page shows a fault banner.
2. User reads the summary message.
3. User taps through to diagnostics.
4. Diagnostics page shows fault detail and communication state.

### Flow 8: Respond to maintenance reminder

1. Quick page shows maintenance reminder banner.
2. User reads why a maintenance run is recommended.
3. User can start the suggested run or dismiss, depending on implementation support.

### Flow 9: Open device page for setup change

1. User opens quick page.
2. User needs to change a one-time setting such as reference temperature source.
3. User taps `Open device page`.
4. User changes the setting there, not on the quick page.

## Acceptance Criteria

- With one heater:
  - no `TabBar` is shown
- With multiple heaters:
  - `TabBar` is shown
  - each tab switches heater context only
- The first screenful supports the daily-use workflow.
- One-time settings do not appear on the quick page.
- Temperature source may be shown as context, but is not editable on the quick page.
- Temperature source editing exists only on the device page.
- Timer overview is present on the quick page.
- Faults and maintenance reminders are prominent and actionable.
- Each Comfort Control air-heater feature is either:
  - adapted into the quick page,
  - intentionally moved to the device page, or
  - explicitly excluded with rationale

## Notes for Implementation

- This document is intentionally not constrained by the current `HeaterPage.qml` scaffold.
- The quick page should be visually richer than the device page.
- The quick page should feel like a native operational dashboard, while the device page remains a structured control/settings view.
- The current bottom-bar scaffold already supports multi-heater tabs and is the intended container for this UX.
