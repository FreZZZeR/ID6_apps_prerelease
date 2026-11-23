# Build and deploy

Run commands from `source/`. Host tests use a C compiler, Make, and Python 3. No car or BMW files are needed for these tests.

```sh
make -C native test
python3 tools/test_probe_signals.py
```

## Native payload

Prepare a licensed QNX SDP 6.5 toolchain. The [SDK archive](https://archive.org/details/qnxsdp-65.7z) is a reference location; use an authorized installation.

1. Prepare a licensed QNX SDP 6.5 Linux x86 toolchain with ARM GCC 4.4.2. Set `QNX_HOST`, `QNX_TARGET`, and `QNX_CONFIGURATION` if your installation differs from the paths in `native/build.sh`.

```sh
mkdir -p native/frameworks
ssh root@HEAD_IP 'cat /opt/hmi/ID5/lib/libAppFramework.A.so' > native/frameworks/libAppFramework.A.so
ssh root@HEAD_IP 'cat /opt/hmi/ID5/lib/libCoreFramework.A.so' > native/frameworks/libCoreFramework.A.so
shasum -a 256 native/frameworks/*.so
```

   Replace `HEAD_IP` with the head-unit SSH IP. Use a binary-safe transfer. If the old SSH server needs a legacy algorithm, configure it for that specific ENET connection. On a split-node unit (`uname -a` reports `hu-jacinto`), `/opt/hmi/ID5/lib` is empty on the SSH node; read the libraries over Qnet under `/net/hu-omap/fs/sda0/...` instead (see [Split-node units](PORTING.md#split-node-units)). Use the head unit's existing library copies as link inputs. Where SDK linker versions differ, set `NBTEVO_RUNTIME_DIR` to a private directory with matching `libm.so.2`, `libsocket.so.3`, and `libstdc++.so.6` from the authorized unit or its reference image. The build also accepts `NBTEVO_FRAMEWORKS_DIR`.
3. Generate the RHMI resources with Python and Pillow. The scripts use host fonts, so image bytes can differ across hosts. DejaVu fonts are the fallback on Linux.

```sh
python3 -m pip install Pillow
sh native/build.sh
```

The script builds the native libraries and diagnostic workers. The dashboard diagnostic workers use the [MOST fallback](MOST.md), which loads the DSI library at runtime. The MHD+ Suite package also includes a dedicated Exhaust Flap worker as `MhdMaps/exhaust-flap-worker-qnx`. It uses the PR #29 commands and the shared HSFZ-to-MOST fallback. Use `tools/merge_exhaust_flap_page.py` to assemble the submenu from the original flap artwork and the MHD+ Suite image archive. The packaged XML and matching image archives must be deployed together.

Run `make -C native assets` from the source directory to regenerate the BoostDeck layout and dial artwork. The target uses the base artwork from the dashboard package and stages the matching MHD and ShiftDeck images alongside their manifests. The alert chime is a separate invocation of the BoostDeck worker and uses the
head unit's preferred QNX PCM playback route.
[QNX PCM playback documentation](https://www.qnx.com/developers/docs/6.5.0SP1/neutrino/audio/pcm.html)

## New firmware

Use the [car identification steps](../../AgentReadMe.md#identify-the-car), the [porting workflow](PORTING.md), and the [read-only capture tool](../tools/capture_headunit.py) to collect the platform, display, and framework evidence before building a candidate profile.

Read `/opt/sys/etc/nbt_version.txt`, `uname -a`, and `/opt/sys/bin/LayerManagerControl get screen 0` over SSH. Record the on-screen version and known iDrive pixel resolution if the corresponding automatic query fails. Compare the two framework hashes with the reference table in `AgentReadMe.md`. A firmware code with an exact match for both framework hashes can reuse the existing installer profile. For a different pair, compare static ABI evidence with the already tested reference using `tools/audit_framework_abi.py` with `pyelftools` and `capstone`. Verify all imported symbols, constructor signatures, and vtable slots, then run a parked load and lifecycle test on that firmware. Static similarity alone does not establish runtime compatibility. Add a firmware entry only with matching evidence. Keep firmware approval separate from the vehicle's DME/EGS signal mapping.

Set `NBT_CAPTURE_DIR`, `NBT_PLUGIN_DIR` and `NBT_ABI_REPORT` to your authorized local inputs/output before using the examples below. Keep those private files outside the repository.

The committed [framework fingerprint](../native/framework-fingerprint.json) lets you run this audit with only your own captured pair. It holds the symbol names, sizes, vtable relocation slots, and SHA-256 digests of the NBTevo_N18032I reference pair for the functions the packaged plugins import. It contains no framework code. Install the two Python packages, extract the plugin libraries from [packages/](../../packages/), and audit all of them in one run:

```sh
python3 -m pip install pyelftools capstone
python3 tools/audit_framework_abi.py \
  --fingerprint native/framework-fingerprint.json \
  --installed-dir "$NBT_CAPTURE_DIR" \
  --plugin "$NBT_PLUGIN_DIR"/lib*.so --report "$NBT_ABI_REPORT"
```

The published ten-build [static comparison](COMPATIBILITY.md#static-framework-checks) used S19221I as its reference. To compare against a reference pair you hold yourself, set `NBT_REFERENCE_DIR` and pass its directory:

```sh
python3 tools/audit_framework_abi.py \
  --reference-dir "$NBT_REFERENCE_DIR" \
  --installed-dir "$NBT_CAPTURE_DIR" \
  --plugin native/out/libBoostDeck.so --report "$NBT_ABI_REPORT"
```

After changing a plugin's framework imports, regenerate the fingerprint from the private reference pair with `--reference-dir`, `--plugin` for every packaged plugin, `--emit-fingerprint native/framework-fingerprint.json`, and `--label`. `native/tests/test_fingerprint.py` checks that the fingerprint covers the packaged plugin imports and expected vtables.

Inspect the report's limitations. The tool checks required imports, function instruction prefixes, and expected vtable relocation slots. It does not simulate HMI calls or prove that a matched framework works at runtime.

## Build HUD Gauges

Set `NBTAAD_SOURCE` to the `milestone-7/src` directory from the licensed
[NBT-AAD reference](https://github.com/Sq00ky/Supra-iDrive6-Android-Auto/tree/47ff0ae89712f2b5cbfe743cc8b7ff413ed235cc/milestone-7).
That revision exposes the `checkNav`, `navTexts` and `navBuffers` configuration
used by `native/src/workers/hud_shape.cpp`. Preserve these navigation-ownership
checks when selecting a different reference; API presence alone is not a build
or vehicle-compatibility result.

Run `sh native/build.sh` to build the optional HUD library and worker. The code
retains the reference handle map and navigation checks, accepts the verified
gateway and shared N57 pin, and leaves the overlay off initially. A cluster that
rejects the reference handles requires its own authorized parked protocol check.
Preserve the NBT-AAD PolyForm Noncommercial licence and Required Notice in any
redistributed source or candidate bundle. No NBT-AAD source, private BMW framework
or factory diagnostic binary is included by these instructions.

## N57 source candidate

The native tree separates `src/common`, `src/plugins`, `src/workers` and `src/ipc`.
Resource generators and packaging/audit tools are under `source/tools`; generated
XML/manifests are under `source/native/manifests`. Build matching libraries,
workers and resources from the same clean revision. Existing upstream ZIPs and
installer downloads do not contain the N57 source changes.

From `source/`, a local bundle can be assembled after supplying actual build
metadata and the matching HUD licence; replace the uppercase path placeholders:

```sh
python3 tools/package_n57.py --output OUTPUT_DIR --binaries native/out \
  --build-info BUILD_INFO_JSON --hud-license HUD_LICENSE_FILE
```

The packaging guard requires a clean source tree and matching source/build
metadata. It does not upload, restart HMI or validate an ECU. Preserve its
checksums, licences/NOTICEs and [data matrix](N57-DATA.md). Review the
[N57 installation/rollback guide](INSTALL-N57.ru.md) before an owner-authorized
installation. Current padding, grouped-drive freshness and PowerDeck preview
changes are offline follow-ups; older functional vehicle results do not validate
the newly built payload. Record the toolchain actually used and all unrun checks
rather than treating a static ABI match or emulator run as a vehicle result.
