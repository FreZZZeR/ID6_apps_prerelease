# N57 data availability and validation

Status: 2026-11-24.

This describes the identity-pinned N57 source profile. One observed configuration
uses DDE SGBD `0F1F70` and EGS SGBD `0F14B0`. This is limited compatibility evidence,
not a compatibility claim for every N57 DDE, vehicle or head-unit firmware.
An exact identity match, accepted reply length, plausible value and fresh sample
are still required. The pinned profile does not substitute gasoline definitions
or fall back to OBD mode 01 when a DDE channel is unavailable.

The current N57 bundle has seven applications: BoostDeck, ShiftDeck, LaunchDeck,
PowerDeck and Engine Fault Codes, plus optional xDrive Control and HUD Gauges.
Supply voltage, fuel volume, coolant and oil temperature are configurable in
BoostDeck. The former standalone BaseDiagnostik app is not shipped; the historical
six-app no-ENET observations below include it and predate this scope reduction.

## What the evidence establishes

**Implemented** means that a decoder and polling route exist. **Live** means that
a value was received in a parked check. Neither establishes engineering accuracy,
sensor fitment or correct operation of the associated vehicle system. An
independent reference check is identified separately below.

A parked, engine-idling check reported fresh data in all six applications with
ENET completely removed from OBD:

| Application | Functional observation | Limit |
| --- | --- | --- |
| BoostDeck | Selected DDE gauges updated; RPM agreed with the instrument cluster. | Engine load was unavailable. Transmission temperature was unavailable on the current MOST route. |
| ShiftDeck | DDE RPM/speed data were received. | RPM intermittently alternated between numbers and dashes. Reception is not a claim of continuous display quality. |
| LaunchDeck | Speed data were received while stationary. | No acceleration timing or nonzero-speed calibration was established. |
| PowerDeck | RPM, DDE torque and calculated power were received. | This batch did not test recording, file saving or a power curve under load. |
| BaseDiagnostik (former app) | Voltage, fuel-volume and temperature fields were received in the earlier candidate. | Not shipped now; those fields remain in BoostDeck. This did not validate SoC/service/tyre fields. |
| Engine Fault Codes | A new engine-code read completed. | Code clearing was not tested. |

For BoostDeck, runtime observations before and after unplugging identified the
same worker process: an established HSFZ connection before the change, then DSI
and diagnostic MOST ownership without the gateway connection, together with fresh
displayed data. This is functional evidence of an automatic **HSFZ to MOST**
transition in that run. The other five historical results are owner-observed no-ENET
functionality, without equivalent per-application transport snapshots.

The MOST session did not include a raw F303 request/response trace or an
independent decoder/timing audit. A new vehicle/head-unit session starting without
ENET, concurrent physical AAD/HUD operation, and calibration under load remain
unverified. Current source follow-ups include a 24-logical-unit right gutter (about 21 panel
pixels on a 1280-pixel display), grouped F303 RPM/speed reads and their freshness
handling, and explicit-recording-only PowerDeck preview collection. These changes
are offline-only and require another vehicle check; the earlier functional
observation does not validate them.

## Implemented dashboard readings

The units below describe the current decoder/worker representation. Display-unit
selection can convert pressure, temperature, distance, torque and power. The
transport column describes code support, not a promise that every ECU returns the
channel. All DDE entries use the existing identity-pinned F303 path on both
HSFZ and MOST.

| Reading | Source | Implemented units | Transport | Live evidence and verification still needed |
| --- | --- | --- | --- | --- |
| Engine RPM | DDE `5955` | rpm | HSFZ / MOST | Idle RPM checked against the cluster; the wider operating range remains unverified. |
| Vehicle speed | DDE `4C14` | Fractional km/h | HSFZ / MOST | Stationary zero observed; nonzero scale and unit conversion need an independent reference. |
| Coolant temperature | DDE `461B` | °C | HSFZ / MOST | Live values received; independent temperature calibration outstanding. |
| Oil temperature | DDE `4517` | °C | HSFZ / MOST | Live values received; independent temperature calibration outstanding. |
| Intake-air temperature | DDE `4846` | °C | HSFZ / MOST | Live values received; sensor assignment and temperature accuracy need confirmation. |
| Manifold absolute pressure | DDE `4841` | hPa decoded, kPa gauge representation | HSFZ / MOST | Live values received; absolute-pressure scale needs an independent reference. |
| Barometric pressure | DDE `4CF0` | hPa decoded, kPa gauge representation | HSFZ / MOST | Live values received; absolute-pressure scale needs an independent reference. |
| Boost pressure | DDE `4841` minus `4CF0` | Pressure difference, psi internally | HSFZ / MOST | Live derived values received; accuracy depends on both pressure channels. |
| Air flow | DDE `47DC` | kg/h decoded, converted to g/s | HSFZ / MOST | Live values received; source quantity and conversion need independent comparison. |
| Rail pressure | DDE `4746` | bar | HSFZ / MOST | Live numeric values received; pressure calibration remains outstanding. |
| Control-module supply voltage | DDE `5242` | V | HSFZ / MOST | Live values received; this is not a state-of-charge measurement. |
| Fuel volume | DDE `4458` | L | HSFZ / MOST | Live values received; tank-volume calibration remains outstanding. This is separate from the generic OBD fuel-percentage channel. |
| Outside-air temperature | DDE `50A6` | °C | HSFZ / MOST | Implemented; no accepted live sample in the available channel-level capture. |
| DDE-reported torque | DDE `48A5` | Nm | HSFZ / MOST | Live values received; physical torque accuracy and tune-dependent reporting are unverified. |
| Calculated power | DDE `48A5` and `5955` | kW; PowerDeck also displays metric PS | HSFZ / MOST | Live derived values received; not independently calibrated power. |
| DPF soot | DDE `44BE` | g | HSFZ / MOST | Decoded output received; actual soot mass and stock-system behaviour are unverified. |
| DPF differential pressure | DDE `44F8` | hPa | HSFZ / MOST | Decoded output received; pressure calibration and stock-system behaviour are unverified. |
| Distance since regeneration | DDE `44BF` | m internally; km/mi in the gauge | HSFZ / MOST | Decoder includes the four-byte value; regeneration-event updates, reset semantics and distance calibration are unverified. |
| EGT before DPF | DDE `44EF` | °C | HSFZ / MOST | Decoded output received; sensor assignment, fitment and physical temperature accuracy are unverified. |
| EGT before catalyst | DDE `44F2` | °C | HSFZ / MOST | Decoded output received; sensor assignment, fitment and physical temperature accuracy are unverified. |
| AdBlue level | DDE `5306` | % | HSFZ / MOST | Implemented; no accepted live sample in the available evidence. Needs a stock SCR-equipped configuration. |
| Transmission temperature | EGS `DA12` | °C | HSFZ; not implemented through the current tunnel | A live HSFZ display value was observed; independent temperature calibration remains outstanding. |

The DPF/EGT/AdBlue entries retain source support for stock configurations.
A decoded value, a fixed-looking value or an unavailable channel does not prove
that an emissions component is fitted, healthy, enabled or operating. The display
visibility preference does not change the vehicle's configuration.

The current diagnostic MOST implementation routes these requests to DDE/DME only.
Its lack of an EGS route is a limitation of this implementation, not a statement
that transmission diagnostics over MOST are impossible in general. Reconnecting
ENET does not move an already established MOST worker back to HSFZ; that worker
must end before a new transport selection occurs. See [MOST transport](MOST.md).

## Decoder-only and unimplemented data

The catalogue has 22 DDE definitions. These three have decoders but no dashboard
polling/selection mapping; their presence in the catalogue is not live support:

| Candidate | DID | Decoder units | Current status |
| --- | --- | --- | --- |
| Charge-air temperature | `4843` | °C | Decoder only; no dashboard live-validation claim. |
| Target boost pressure | `42C8` | hPa | Decoder only; no dashboard live-validation claim. |
| Injection quantity | `45D4` | mg/stroke | Decoder only; quantity semantics and scale need independent verification before a gauge is added. |

The following are not implemented by this pinned N57 profile:

| Field | Availability and next step |
| --- | --- |
| Engine load / absolute load | No DDE channel is connected. `464C` is only a metadata candidate for a current-to-maximum torque ratio; its service, byte layout, scale, units and meaning require verification before implementation. It must not silently be presented as SAE calculated engine load. |
| EGR | No gauge or decoder. |
| Battery state of charge / capacity | No supported source. Supply voltage is not converted into these quantities. |
| CBS / brake-pad wear or remaining service distance | No supported source. |
| TPMS tyre pressures | No supported source. |
| Fuel percentage, fuel rate, pedal and throttle fields | The generic OBD choices do not establish a DDE mapping for this profile. |
| AFR, gasoline ignition/timing, oil pressure, ethanol and other generic OBD-only fields | No verified N57 mapping; values must remain unavailable. |

The current pinned-N57 UI and worker share one
[supported-channel map](../native/src/common/n57_gauges.def), checked by
[the availability helper](../native/src/common/n57_gauge_support.h). Unsupported
choices are hidden and excluded from polling. Existing custom assignments are
retained, but unsupported tiles are hidden until a supported reading is selected.
The default N57 layout uses a separately labelled DDE-torque tile in place of the
unimplemented engine-load tile. This layout change does not implement engine load
or turn torque into a load percentage.

Missing, unsupported or stale data must remain unavailable. The app must not
manufacture engine-load percentages from fixed stock torque, pressure or power,
or substitute a differently defined channel merely to fill a tile.

## Torque, power and measurement limits

PowerDeck uses a complete fresh DDE torque/RPM pair and calculates:

```text
kW = torque_Nm × RPM × 2π / 60000
metric_PS = kW / 0.73549875
```

PowerDeck's PS is metric horsepower. BoostDeck's generic imperial power
formatting uses mechanical hp (`kW / 0.7456998716`); those are different units.

This is calculated power from DDE-reported engine torque. It is not a dyno,
wheel-power measurement, independently measured shaft torque or proof of peak
power. A saved curve represents the recorded operating conditions; an idle or
partial-load run does not establish the engine's maximum power.

Recording requires a valid, coherent triple. An RPM number by itself is not
evidence that torque/power are valid or that a recordable sample exists.
Unavailable or stale samples are not extrapolated into measurements.

## Follow-up verification

- Compare pressure channels against an independent diagnostic/reference source,
  keeping hPa, kPa and bar, and absolute versus differential pressure distinct.
- Verify air-flow kg/h to g/s, fuel-volume litres, regeneration-distance metres
  and reset behaviour, temperature sensor identity/offsets, and the EGT locations.
- Validate stock DPF/SCR channel behaviour on a configuration that supplies those
  measurements. Check the source definitions before interpreting static values.
- Check speed across nonzero values and RPM across its intended range. Repeat
  the grouped RPM/speed path over real MOST latency without making old samples
  appear fresh to remove display gaps.
- Independently assess DDE torque semantics before using calculated power for
  quantitative comparisons. Keep load-channel `464C` as an unimplemented
  candidate until its complete definition and meaning are verified.
- Repeat a new vehicle/head-unit session without ENET and a separate physical
  AAD/HUD coexistence check. Preserve the distinction between functional data
  reception, transport evidence and engineering calibration.

## Source references

- [DDE catalogue and decoder](../native/src/common/n57_signals.def),
  [identity and F303 implementation](../native/src/common/n57.c).
- [Shared dashboard channel map](../native/src/common/n57_gauges.def),
  [UI availability](../native/src/common/n57_gauge_support.h),
  [polling and derived pairs](../native/src/workers/boost_deck_worker.c),
  [display units and freshness](../native/src/common/gauge_core.c).
- [ShiftDeck/LaunchDeck worker](../native/src/workers/shift_deck_worker.c),
  [drive IPC](../native/src/ipc/drive_frame.h).
- [PowerDeck sample acceptance and CSV](../native/src/plugins/power_history.h),
  [power graph units](../native/src/plugins/power_rpm_plot.h). The shared gauge map
  above retains the voltage/fuel/temperature channels for BoostDeck.
- [Transport selection and transaction lifetime](../native/src/common/diag_link.c),
  [MOST limitations and coordination](MOST.md).
