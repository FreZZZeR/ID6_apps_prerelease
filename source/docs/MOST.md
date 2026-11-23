# MOST fallback

On some cars the head unit has no route to the HSFZ diagnostic gateway. Without it the workers cannot connect, so the gauges stay blank and map or code requests fail. Workers with fallback can then reach the DME through the head unit's own UDS tunnel over MOST.

## Workers

| Worker | DSI client name |
| --- | --- |
| BoostDeck (`boostdeck-collector-qnx`) | `boostdeck` |
| ShiftDeck (`shift-deck-qnx`) | `shiftdeck` |
| MHD Maps (`mhd-maps-qnx`) | `mhdmaps` |
| Engine codes (`engine-codes-qnx`) | `enginecodes` |

PowerDeck reuses the BoostDeck worker as `powerdeck`; LaunchDeck reuses the
ShiftDeck worker as `launchdeck`. The four current N57 dashboards have separate
active/MOST markers. The standalone BaseDiagnostik app is no longer shipped.
Its legacy `basediagnostik` client name, data port and active/MOST markers remain
recognized so an installed older client cannot cause a second HUD poller or
collide with a newly assigned service. Do not reuse those reserved endpoints.
The HUD renderer consumes published dashboard telemetry. Its own sampler is
HSFZ-only so rendering cannot start a second diagnostic MOST client.

Native xDrive (`xdrive-control-qnx`) remains HSFZ-only: its qualified checks require DSC, transfer-case and EGS access. N57 engine telemetry does not extend the compatibility or authorization of any tuning/drivetrain control.

## When a worker switches

- A loop worker (BoostDeck, ShiftDeck) switches after 5 failed HSFZ connects in a row. A one-shot worker (MHD Maps, engine codes) switches after 1.
- With no `--host`, a worker goes straight to MOST. The plugins always pass the gateway address, so on a car the switch follows failed connects.
- Normally, once HSFZ has connected in a process, that process never switches
  to MOST. Pinned N57 live telemetry explicitly opts into fallback after five
  failed connects or failed HSFZ I/O batches, including a lost connection after
  an earlier successful read. A complete valid batch resets that count; a
  positive identity reply alone does not. UDS refusals and malformed values
  do not count as transport failures or bypass their checks.
- A failed MOST open is closed. A loop worker goes back to HSFZ and tries MOST again after 30 s. For a one-shot worker the failure is final.
- Once on MOST, a worker stays there until it is restarted. If the tunnel drops, a loop worker exits and the plugin starts a new one.

The diagnostic workers use automatic fallback by default where supported. The dashboard workers accept a transport override for testing.
An explicit `--transport hsfz` keeps the N57 workers on HSFZ. Both the live
HUD's independent sampler and its parked check remain HSFZ-only.

## Packaged controls

- **Bootmod3 Suite** can switch maps, request exhaust flap position, and set Active Sound over MOST on a recognized CustomROM. Burble presets require HSFZ because the complete write is larger than the tunnel limit.
- **MHD+ Suite → Options → Exhaust Flap** uses the same DME commands as the previous worker and falls back through MOST when the HSFZ connection fails.
- **xDrive Control** requires HSFZ for DSC, transfer case and transmission diagnostics. The shared MOST tunnel reaches only the DME.

The workers switch transport before sending a control request. A rejected or unconfirmed request is reported to the menu.

## What goes over MOST

- This implementation routes diagnostics to DDE/DME (`0x12`). BoostDeck's EGS transmission temperature (`DA12`) stays blank on this MOST route, and so does its ethanol read (`2C 88 01`). This is not a statement that EGS access over MOST is impossible in general.
- Requests use routine `0x0F0B` on FBlock `0x06`, instance `0xF0`, FktID `0x050`, with diagnostic source `0x63`, through `DSYSMOSTServer`.
- A request waits the larger of its own timeout and 2 s. A pending reply extends that up to 5 s in all.
- A reply holds at most 512 bytes, about 127 fault codes. A longer code reply is dropped and shows "No valid code response". A reply that fills all 512 bytes adds "More codes may exist".
- ShiftDeck and the gauges refresh more slowly on MOST. BoostDeck sends each new value as soon as it is read.

## Pinned N57 engine telemetry

The experimental N57 source supports DDE `0x12` identity and measured values
through the same tunnel. Each dynamic value or supported group uses
`2C 03 F303` clear, `2C 01 F303` definition and `22 F303` read, with the pinned
DDE identity, response echo, exact data length and decoder limits checked.
There is no fallback to mode 01 or to gasoline signal definitions.

This applies to BoostDeck, PowerDeck, ShiftDeck and LaunchDeck. The shared backend
also retains the old Base client protocol for safe coexistence.
EGS `0x18` is not implemented by the current tunnel route, so
transmission temperature remains unavailable there. The HUD parked check
still requires HSFZ, exact zero speed and the independently verified EGS Park
responses. xDrive retains its HSFZ-only ECU checks, VIN gate and other
interlocks. Engine telemetry is not evidence that a drivetrain mode change
is permitted.

Dynamic slot F303 is shared ECU state. A loop worker holds one diagnostic
lease across identity and the whole clear/define/read group, including both
reads for derived boost or torque/RPM power. On MOST it normally releases that
lease at the end of the group and yields between groups. Requests
from another cooperating worker cannot redefine the slot inside that group.
External diagnostic clients must still be closed for a live check.

A timed-out F303 clear/define/read or pinned N57 group makes the current MOST
client unusable. A late `62 F303` cannot identify which measurement produced it,
so that client sends no further requests. Earlier samples keep their original
observation times. The worker closes it and exits for a fresh process. Its
diagnostic lease and MOST marker stay held until
DSI teardown succeeds; a stuck teardown keeps them until bounded process exit.
An ECU refusal remains a refusal, not a reason to bypass identity or decode checks.

N57 samples keep observation times rather than reply-completion times. The
current ShiftDeck follow-up defines RPM `5955` and fractional speed `4C14` in one
F303 group and accepts exactly four data bytes. LaunchDeck stays speed-only.
These drive timestamps start immediately before the actual `22 F303` read;
identity/clear/define preparation is not a measured-value observation. Lease
contention does not publish a new empty sample. The new grouped-read behaviour
is offline-only and still needs a vehicle retest.

Derived BoostDeck pressure keeps the beginning of its absolute/ambient pair,
so waiting for ambient pressure cannot make the earlier absolute value fresh.
The existing limits remain: ShiftDeck/LaunchDeck 750 ms, HUD RPM 1100 ms and
HUD boost 1200 ms. A slow exchange may leave the display blank; completing a
reply does not make a delayed measurement fresh.

## N57, NBT-AAD and HUD ownership

The N57 engine collector may use diagnostic FBlock `06/F0` while native NBT-AAD
is installed. AAD installation never forces these collectors back to HSFZ.
This differs from the coarse installation veto in upstream `60704f8`.
The collector does not register or draw on HUDTerminal `82/00`.

Our HUD renderer keeps the conservative projection exclusion: an installed
NBT-AAD or CarPlay HUD hook, or an existing projection shown-marker, blocks its
startup and every send. It never removes those markers, stops AAD, or clears
foreign HUD handles. Absence of a marker cannot prove that AAD is idle: AAD
itself yields to foreign HUD traffic, and a marker may lag or fail to write.

Without a projection owner, the renderer holds its arbitration socket until
process exit. A dashboard marks its MOST intent, asks an existing renderer to
clear and exit, and retries after 250 ms. It opens diagnostic MOST only after
the renderer releases ownership. Its MOST marker remains held through DSI
shutdown. OS-owned markers also disappear after an abnormal process exit.

An active dashboard owns polling even when its selected channels contain no
usable RPM. The renderer closes its own reader and consumes only that source's
published data; LaunchDeck and a legacy Base source without RPM leave the gauges blank
instead of causing a second poller. A source change drains former packets and
invalidates the cache. Profile, magic/size, loopback sender and bound source port,
timestamp order, plausibility and separate RPM/boost freshness are checked.
Shared telemetry cannot establish EGS Park.

Existing app IPC stays at Boost `42860`, Shift `42863`, Launch `42871`, Power
`42872`; the old Base data port `42873` remains reserved. The diagnostic lease stays at `42861`.
Coordination uses the separate range below, avoiding upstream's overlapping
`42870`-series markers. Update the HUD library, HUD worker and all dashboard
workers together; mixed coordination versions are not validated.

| Purpose | Port |
| --- | --- |
| Versioned HUD telemetry | 42970 |
| Boost / Shift / Launch active | 42971 / 42972 / 42973 |
| Renderer arbitration and release request | 42974 |
| Boost / Shift / Launch MOST | 42975 / 42976 / 42977 |
| Reserved Warm active / MOST | 42978 / 42979 |
| Power active / MOST | 42980 / 42981 |
| Reserved legacy Base active / MOST | 42982 / 42983 |

Host tests model installed AAD, occupied HUD ownership, current dashboard workers
and the legacy Base client protocol with HSFZ unavailable. They validate separation and handoff,
not the physical DSYSMOSTServer, NBT-AAD or ECU operating together on the car.

## Sharing the tunnel

Workers share the loopback diagnostics lease, as they do on HSFZ. On MOST a loop worker holds it for one request at a time, or for the complete N57 group described above, and waits up to 300 ms for it. A one-shot worker holds it for its whole run and waits up to 3 s for it at startup. When a loop worker sees that another worker is waiting, it steps aside before its next request or group.

## Library and limits

- The DSI library is opened with `dlopen` only when a worker falls back, first by name and then from `/opt/sys/lib`. Nothing links against it. If it or one of its functions is missing, MOST stays off for that process. The plugins add `/opt/sys/lib` to the workers' library path.
- A DSI send has no timeout, so `alarm()` bounds each loop on MOST at 60 s and the stop after SIGTERM at 15 s. On SIGTERM a worker unregisters its target and client before it exits.

## Validation scope

An earlier N57 deployment has one parked functional HSFZ-to-MOST transition:
BoostDeck continued fresh readings in the same worker after ENET was fully
removed from OBD, with runtime transport resources changing from HSFZ to DSI/MOST.
The owner also observed no-ENET data reception in ShiftDeck, LaunchDeck,
PowerDeck and the former BaseDiagnostik app, and a completed Engine Fault Codes
read. This historical six-app batch predates removal of the standalone Base app;
the current bundle has five data apps.
Only BoostDeck has that direct runtime transport correlation.

These results do not provide a raw MOST/F303 trace or independent calibration.
ShiftDeck received data but its RPM display alternated with dashes. The current
grouped-drive/freshness, right-padding and PowerDeck preview changes are offline
follow-ups and have not been checked on the vehicle. See the
[N57 data/verification matrix](N57-DATA.md).

A new vehicle/head-unit session starting without ENET, concurrent physical AAD/HUD
operation, multiple real DSI clients and physical HUD rendering remain unverified.
DTC clearing and tuning/drivetrain commands were not part of the no-ENET check.
An engine-code read result does not establish a confirmed clear or command path.
Host responders and simulator DSI loading test software behaviour, not real ECU
latency, sensor semantics or concurrent projection operation.

## Host tests

Host builds use a fake DSI library selected by `ID6_FAKE_MOST`:

- unset: no library
- `up`: a DME answering every request the workers send
- `drop`: the link is lost at the fifth request
- `no-server`: the library loads but no server answers
- `mhd-refuse`: `up`, but the map request is refused with NRC `31`
- `codes-512`, `codes-513`: `up`, but the code read returns 127 codes in 512 or 513 bytes

`ID6_FAKE_MOST_DELAY_MS` (up to 2000) slows each reply and the close by that many milliseconds. `make -C native test` runs these.

Replace `GATEWAY_IPV4` with the verified gateway for an authorized test. For N57, use the verified shared pin (and Diesel selection); keep external clients closed. These examples do not authorize a live run.

```sh
boostdeck-collector-qnx --host GATEWAY_IPV4 --transport hsfz   # never MOST
boostdeck-collector-qnx --transport most --trace              # MOST only
boostdeck-collector-qnx --host GATEWAY_IPV4                    # auto
```
