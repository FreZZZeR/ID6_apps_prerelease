# AgentReadMe

This branch's N57 source profile and validation scope are documented in
[N57.md](source/docs/N57.md) and [N57-DATA.md](source/docs/N57-DATA.md). An earlier
deployment received data in six applications without ENET; only BoostDeck has
direct same-worker HSFZ-to-MOST runtime evidence. Current padding, grouped-drive
freshness and PowerDeck preview changes have not been tested on the vehicle.
The historical six-app data check included the former BaseDiagnostik app, which is not shipped now. Existing upstream ZIPs/installers do not include this work. Read the
[update notes](source/docs/N57-UPDATE.ru.md) and
[installation/rollback guide](source/docs/INSTALL-N57.ru.md) before preparing a
source-built N57 candidate. Published-package instructions below do not turn an
upstream archive into that candidate.

## Select the apps

Ask the owner for their choice of **MHD+ Suite**, **Bootmod3 Suite** or **MG Flasher**, and whether they want **xDrive Control (experimental)** and **HUD Gauges**. Install only the selected tuning menu; N57 dashboards do not require one. Install xDrive Control and HUD only when selected. BoostDeck, ShiftDeck, LaunchDeck and Engine Fault Codes are independent apps. PowerDeck is a source-only N57 dashboard and requires the verified shared DDE pin. The seven-app N57 bundle contains five data apps plus optional xDrive/HUD; voltage, fuel volume and both temperatures remain configurable in BoostDeck.

## Identify the car

1. Confirm the installation is authorized and the car is parked, with iDrive awake. Connect wired ENET and identify the computer's ENET address, diagnostic gateway address, and head-unit SSH address.
2. Use an unlock tool that supports the exact unit, such as [Bavarian SSH Client](https://ssh.bavarian-aa.uk/). Verify the SSH host key and use locally supplied credentials.
3. Read the exact NBTevo software code, the active panel resolution (LayerManager screen 0), and SHA-256 hashes of both files under /opt/hmi/ID5/lib. Use the [read-only capture utility](source/tools/capture_headunit.py) when you need a structured report.

On some units SSH lands on the Jacinto processor (`uname -a` reports `hu-jacinto`), not the HMI OMAP, and `/opt/hmi/ID5/lib` is empty on that node. The HMI files are then reachable read-only over Qnet under `/net/hu-omap/fs/sda0/...`, and OMAP commands run with `on -f hu-omap`. The capture utility detects this and reads the right paths automatically. See [Split-node units](source/docs/PORTING.md#split-node-units).

The reference dashboard build uses **NBTevo_N18032I** at **1280 × 480**. The desktop installer verifies both live framework hashes against an approved pair before staging. It accepts firmware variants that share that pair. See [Dashboard compatibility](source/docs/COMPATIBILITY.md) for the captured profiles and their validation.

| File | SHA-256 |
| --- | --- |
| libAppFramework.A.so | 93f4c7ab7e59c0adf7923b9b491de06165ba9d97bbe7412292e7ddc418ca2123 |
| libCoreFramework.A.so | 64ba154c68c772f9ca779fc18507f5b34715be58ded4a198b8a62b90d16c3ee0 |

Discover the current diagnostic gateway independently of the head-unit SSH address. Put its verified IPv4 address in /var/opt/hmi/data/ID5/gateway-ip.txt on the HMI node when an override is needed. The shared setting overrides app-local gateway-ip.txt files. Without either file, supported workers try the reference fallback and then wired link-local discovery; that does not establish that the fallback is correct for this vehicle. Use the desktop installer to verify both live hashes and select the layout for the active display. If the framework pair has no approved match in the [compatibility matrix](source/docs/COMPATIBILITY.md), follow the [porting workflow](source/docs/PORTING.md) to verify compatibility. Native changes need the QNX SDP 6.5 Linux host tools and ARM GCC 4.4.2. Matching packaged binaries and compatible layout resource changes do not need QNX on the ENET computer.

If you need the toolchain for a native build, the [QNX SDP 6.5 archive](https://archive.org/details/qnxsdp-65.7z) includes the SDK and a license key generator, according to the archive listing. See [Build and deploy](source/docs/BUILD.md) for toolchain setup.

## Stage and verify

Download and extract the selected packages from [packages/](packages/). The dashboard ZIP contains BoostDeck, ShiftDeck, EngineCodes, and MhdMaps. Exhaust Flap is under MHD+ Suite → Options and uses the same gateway-ip.txt setting. When updating MhdMaps, move its earlier standalone ExhaustFlap plugin folder to the backup outside Plugins. Include MhdMaps only for the MHD choice. Bootmod3Suite and XDriveControl are separate ZIPs. MG Flasher (connector 116) and HybridDeck (connector 117) also have separate packages. Read their package notes for module and tune constraints. Source-built N57 candidates also include the selected PowerDeck resources and licences; use their own verified manifests rather than substituting files from an upstream ZIP. **DSC_25 0F1860 with LMV 0F1480 requires the engine running. The supported G-series DSCs require the engine off. All mode changes require confirmed Park and zero speed.** Install neither when the owner declines them.

Inventory /var/opt/hmi/data/ID5/Plugins for conflicting names and connector IDs. Back up any prior version being replaced to a separate directory outside Plugins. Stage complete app folders outside Plugins, upload over confirmed SSH, set the workers executable, and compare each readback with its local file before moving the folders into Plugins. Verify the final paths and bytes, and tell the owner where backups were saved. If anything fails, restore the previous folders before restarting. Do not add a second copy of an app.

An older BaseDiagnostik installation is not automatically removed by omitting it from the new bundle. Remove it only as a separately selected, backed-up app; keep legacy coordination ports reserved.

For N57, preserve the shared pin and saved measurements, leave HUD disabled and do not create an owner-VIN file as part of ordinary gauge installation. After verification, have the owner perform the unit's authorized normal iDrive restart, then check the selected menus while parked. Check live readings and settings. Menu installation alone does not verify an engine or drivetrain command. Get the owner's authorization before testing a command that changes ECU or drivetrain state.

## Optional HUD Gauges

Install the [HUD Gauges package](packages/hud-gauges.zip) when the owner selects it and the car has the matching reference configuration. Verify the reference firmware, framework hashes, resolution, and gateway above. The worker also expects a unique factory MOST HUDTerminal service 82/00 at node 0101. Treat other configurations as porting targets.

Extract and verify SHA256SUMS. Keep the initial hud-enabled flag off; enabling the overlay is a separate parked test. Installed NBT-AAD/CarPlay HUD support blocks this renderer, even while projection is stopped. Stage only the HudTest directory and check for an existing HudTest or an app using connector ID 107. Preserve the prior app outside Plugins if replacing it. If an app-local gateway override is needed, set gateway-ip.txt beside the worker. Set hud-shape-qnx executable, verify the uploaded files, and restart iDrive while parked. Open My Vehicle → HUD Gauges and check Show HUD gauges. Verify the tach and PSI display and that unchecking clears the overlay. Enabling is explicit for the current iDrive session; reopening the menu or restarting HMI must not automatically restore it. If the display fails its parked checks, turn it off and restore the prior app folder or remove HudTest from Plugins, then restart iDrive.

## LaunchDeck

Install [LaunchDeck](packages/launchdeck.zip) as a separate plugin folder with connector ID 120. Use the same firmware and screen checks as BoostDeck. Its packaged diagnostic worker is read-only and measures vehicle speed via OBD. This fork's source additionally supports pinned N57 DDE speed in LaunchDeck, ShiftDeck and HUD Gauges; see [N57 source requirements](source/docs/N57.md#dynamic-reads-and-most). The packaged ZIPs do not include those changes.

## Uninstall

Each app is one folder under /var/opt/hmi/data/ID5/Plugins. Keep each folder intact so its local settings, including gateway-ip.txt, can be restored.

| App | Folder |
| --- | --- |
| BoostDeck | BoostDeck |
| ShiftDeck | ShiftDeck |
| LaunchDeck | LaunchDeck |
| PowerDeck (source N57) | PowerDeck |
| Engine Fault Codes | EngineCodes |
| MHD+ Suite (with Exhaust Flap and Max Cooling) | MhdMaps |
| Exhaust Flap from earlier standalone builds | ExhaustFlap |
| Bootmod3 Suite | Bootmod3Suite |
| MG Flasher | MgFlasher |
| HybridDeck | HybridDeck |
| xDrive Control (experimental) | XDriveControl |
| HUD Gauges | HudTest |

1. Ask the owner which apps to remove. Leave every other folder in Plugins untouched.
2. While the menus still exist, have the owner put the car back in the state they want to keep. Uncheck **My Vehicle → HUD Gauges → Show HUD gauges** and confirm the overlay clears. If a drivetrain mode must be restored, use a separately authorized parked procedure for the verified DSC: F-series DSC_25 requires the engine running; the supported G-series profiles require it off. Read back the intended mode independently. Select the wanted map slot, exhaust flap, Max Cooling, Active Sound, and burble settings. Removing a menu does not undo a setting already sent to the DME or DSC.
3. Park the car, keep iDrive awake, and connect as in [Identify the car](#identify-the-car). On a split-node unit, use the OMAP address or the Qnet write path described in [Split-node units](source/docs/PORTING.md#split-node-units).
4. List Plugins and confirm that each folder to remove is one of the apps above. Move only those folders into a new backup directory outside Plugins, such as /var/opt/hmi/data/ID5/PluginBackups/<timestamp>. Keep the original folder names, avoid overwriting an existing backup, and record the backup path.
5. List Plugins again and verify that the removed folders are gone and the remaining ones are unchanged.
6. Have the owner hold the volume knob until iDrive goes dark. After the restart, check that the removed entries are gone from My Vehicle, the remaining apps still open, and the HUD shows no overlay.

To restore an app, make sure its folder name is available in Plugins, then move the intact folder back from the backup. Restart iDrive while parked and confirm that the restored menu opens.
