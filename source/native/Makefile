CC ?= cc
PYTHON ?= python3
CFLAGS ?= -O2 -std=c99 -Wall -Wextra -Werror
CORE = src/common/gauge_core.c
CORE_LINK = $(CORE) src/common/diag_link.c src/common/n57.c
INCLUDES = -Isrc/common -Isrc/ipc -Isrc/workers -Isrc/plugins
HEADERS = src/common/gauge_core.h src/common/boost_signals.def src/ipc/drive_frame.h src/common/diagnostic_lease.h src/common/diag_link.h src/common/gauge_coexistence.h src/common/n57.h src/common/n57_signals.def src/common/n57_gauge_support.h src/common/n57_gauges.def
# Every host worker carries the HSFZ-then-MOST link, with a fake DSI selected by ID6_FAKE_MOST.
MOST = src/common/most/most_link.c src/common/most/dsi_client.c src/common/most/most_proto.c src/common/most/dsi_bind.c
MOST_HEADERS = src/common/most/most_link.h src/common/most/dsi_client.h src/common/most/most_proto.h src/common/most/dsi_abi.h
FAKE_DSI = tests/fake_dsi.c tests/fake_dme.c tests/fake_dsi.h tests/fake_dme.h
WORKER_COMMON = $(CORE_LINK) $(MOST) tests/fake_most_env.c $(FAKE_DSI) $(HEADERS) $(MOST_HEADERS)
HOST_LINK = $(CC) $(CFLAGS) -pthread -DMOST_HOST $(INCLUDES) -Itests
.PHONY: assets launch-assets boostdeck-layout test

assets: | build
	unzip -p ../../packages/dashboard.zip BoostDeck/BoostDeck_ALL_Images.zip > build/boostdeck-base-images.zip
	$(PYTHON) ../tools/make_boostdeck_extended.py --images build/boostdeck-base-images.zip --images-out manifests/BoostDeck_ALL_Images.zip
	unzip -p ../../packages/dashboard.zip ShiftDeck/ShiftDeck_ALL_Images.zip > build/shiftdeck-base-images.zip
	$(PYTHON) ../tools/extend_shift_n57.py --images build/shiftdeck-base-images.zip --images-out manifests/ShiftDeck_ALL_Images.zip
	unzip -p ../../packages/dashboard.zip EngineCodes/EngineCodes_ALL_Images.zip > build/enginecodes-base-images.zip
	$(PYTHON) ../tools/make_engine_codes_layout.py --images build/enginecodes-base-images.zip --images-out manifests/EngineCodes_ALL_Images.zip
	unzip -p ../../packages/dashboard.zip MhdMaps/MhdMaps_ALL_Images.zip > manifests/MhdMaps_ALL_Images.zip
	$(PYTHON) ../tools/launch_art.py
	$(PYTHON) ../tools/make_n57_dashboards.py
	$(PYTHON) ../tools/content_layout.py
	$(PYTHON) ../tools/make_warmdeck.py
	$(PYTHON) ../tools/make_hybrid_and_mg.py

boostdeck-layout:
	$(PYTHON) ../tools/make_boostdeck_extended.py

build:
	mkdir -p build

build/boost-deck: src/workers/boost_deck_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/shift-deck: src/workers/shift_deck_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/mhd-maps: src/workers/mhd_maps_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/engine-codes: src/workers/engine_codes_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/bootmod3: src/workers/bootmod3_suite_worker.c src/workers/bm3_profiles.h $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/mgflasher: src/workers/mg_flasher_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/hybriddeck-collector: src/workers/hybrid_deck_worker.c src/ipc/hybrid_frame.h $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/xdrive-control: src/workers/xdrive_control_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/exhaust-flap: src/workers/exhaust_flap_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/test-core: tests/test_core.c $(CORE) $(HEADERS) | build
	$(CC) $(CFLAGS) -Isrc/common $(filter %.c,$^) -lm -o $@

build/test-most: tests/test_most.c $(MOST) $(FAKE_DSI) $(MOST_HEADERS) | build
	$(CC) $(CFLAGS) -pthread -DMOST_HOST -Isrc/common -Itests $(filter %.c,$^) -o $@

build/test-diag-link: tests/test_diag_link.c $(CORE_LINK) $(MOST) tests/fake_most_env.c $(FAKE_DSI) $(HEADERS) $(MOST_HEADERS) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/test-launch-timer: tests/test_launch_timer.c src/common/launch_timer.c src/common/launch_timer.h | build
	$(CC) $(CFLAGS) -Isrc/common $(filter %.c,$^) -o $@

build/launch_timer.o: src/common/launch_timer.c src/common/launch_timer.h | build
	$(CC) $(CFLAGS) -Isrc/common -c $< -o $@

build/test-launch-records: tests/test_launch_records.cpp build/launch_timer.o src/common/launch_records.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -Isrc/common $(filter %.cpp %.o,$^) -o $@

build/warmdeck-collector: src/workers/warm_deck_worker.c src/ipc/warm_frame.h $(WORKER_COMMON) | build
	$(HOST_LINK) $(filter %.c,$^) -lm -o $@

build/test-warm-progress: tests/test_warm_progress.cpp src/plugins/warm_progress.h src/ipc/warm_frame.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -Isrc/plugins -Isrc/ipc $< -o $@

build/boost-test-core.o: $(CORE) $(HEADERS) | build
	$(CC) $(CFLAGS) -Isrc/common -c $< -o $@

build/test-boost-preferences: tests/test_boost_preferences.cpp build/boost-test-core.o src/plugins/boost_preferences.h src/common/gauge_preferences.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -Isrc/plugins -Isrc/common $(filter %.cpp %.o,$^) -o $@

build/test-n57: tests/test_n57.c src/common/n57.c src/common/n57.h src/common/n57_signals.def | build
	$(CC) $(CFLAGS) $(INCLUDES) $(filter %.c,$^) -lm -o $@

build/test-drive-frame: tests/test_drive_frame.c src/ipc/drive_frame.h | build
	$(CC) $(CFLAGS) $(INCLUDES) $< -o $@

build/test-gauge-coexistence: tests/test_gauge_coexistence.c src/common/gauge_coexistence.h | build
	$(CC) $(CFLAGS) -DMOST_HOST $(INCLUDES) $< -o $@

build/test-hud-dashboard: tests/test_hud_dashboard.cpp src/workers/dashboard_sample.h src/ipc/hud_sample.h src/common/gauge_coexistence.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -DMOST_HOST $(INCLUDES) -Isrc/workers $< -o $@

build/test-hud-menu: tests/test_hud_menu.cpp tests/dashboard_sdk/bmw_list.h src/plugins/hud_menu.cpp src/workers/dashboard_sample.h src/ipc/hud_sample.h src/common/gauge_coexistence.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -DMOST_HOST -Itests/dashboard_sdk $(INCLUDES) -Isrc/workers $< -o $@

build/test-shift-scale: tests/test_shift_scale.cpp src/plugins/shift_scale.h src/plugins/shift_assets.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror $(INCLUDES) $< -o $@

build/test-shift-window: tests/test_shift_window.cpp src/plugins/shift_window.h src/common/gauge_preferences.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror $(INCLUDES) $< -o $@

build/test-shift-deck: tests/test_shift_deck.cpp tests/dashboard_sdk/bmw_list.h src/plugins/shift_deck.cpp src/plugins/shift_window.h src/plugins/shift_assets.h src/plugins/shift_scale.h src/ipc/drive_frame.h src/plugins/hmi_state_activity.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -Itests/dashboard_sdk $(INCLUDES) $< -o $@

build/test-shift-deck-smooth: tests/test_shift_deck.cpp tests/dashboard_sdk/bmw_list.h src/plugins/shift_deck.cpp src/plugins/shift_window.h src/plugins/shift_assets.h src/plugins/shift_scale.h src/ipc/drive_frame.h src/plugins/hmi_state_activity.h | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -DNATIVE_SHIFT_SMOOTH -Itests/dashboard_sdk $(INCLUDES) $< -o $@

build/power-core.o: $(CORE) $(HEADERS) | build
	$(CC) $(CFLAGS) -DPERF_LAB $(INCLUDES) -c $(CORE) -o $@

build/test-power-history: tests/test_power_history.cpp src/plugins/power_history.h src/common/gauge_preferences.h build/power-core.o | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -DPERF_LAB $(INCLUDES) tests/test_power_history.cpp build/power-core.o -lm -o $@

build/test-power-rpm-plot: tests/test_power_rpm_plot.cpp src/plugins/power_rpm_plot.h src/plugins/power_history.h build/power-core.o | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -DPERF_LAB $(INCLUDES) tests/test_power_rpm_plot.cpp build/power-core.o -lm -o $@

build/test-power-deck: tests/test_power_deck.cpp tests/dashboard_sdk/bmw_list.h src/plugins/power_deck.cpp src/plugins/power_rpm_plot.h src/plugins/power_history.h src/plugins/n57_dashboard.h src/plugins/hmi_state_activity.h build/power-core.o | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -DPERF_LAB -Itests/dashboard_sdk $(INCLUDES) tests/test_power_deck.cpp build/power-core.o -lm -o $@

build/test-hud-reader: tests/test_hud_reader.c src/workers/parked_check.c src/ipc/hud_sample.h $(CORE) src/common/n57.c $(HEADERS) | build
	$(CC) $(CFLAGS) $(INCLUDES) -Isrc/workers $(filter %.c,$^) -lm -o $@

build/test-gauges-extended: tests/test_gauges_extended.c $(CORE) $(HEADERS) | build
	$(CC) $(CFLAGS) -DPERF_LAB $(INCLUDES) $(filter %.c,$^) -lm -o $@

build/test-launch-deck: tests/test_launch_deck.cpp tests/dashboard_sdk/bmw_list.h src/plugins/launch_deck.cpp src/common/launch_records.h src/plugins/launch_assets.h src/plugins/hmi_state_activity.h build/launch_timer.o | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -Itests/dashboard_sdk $(INCLUDES) tests/test_launch_deck.cpp build/launch_timer.o -o $@

build/test-boostdeck-assignments: tests/test_boostdeck_assignments.cpp src/plugins/boostdeck_assignments.h src/common/gauge_preferences.h $(HEADERS) | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror -DPERF_LAB $(INCLUDES) $< -o $@

build/boostdeck-collector build/boostdeck-n57: build/boost-deck
	cp $< $@

build/shift-deck-fast: src/workers/shift_deck_worker.c $(WORKER_COMMON) | build
	$(HOST_LINK) -DNATIVE_FAST $(filter %.c,$^) -lm -o $@

build/test-n57-availability: tests/test_n57_availability.cpp src/common/n57_gauge_support.h src/common/n57_gauges.def src/plugins/boostdeck_assignments.h src/common/gauge_preferences.h $(HEADERS) | build
	$(CXX) -O2 -std=gnu++98 -Wall -Wextra -Werror $(INCLUDES) $< -o $@

launch-assets:
	$(PYTHON) ../tools/launch_art.py

test: build/test-n57-availability build/boostdeck-collector build/boostdeck-n57 build/shift-deck-fast build/test-n57 build/test-drive-frame build/test-gauge-coexistence build/test-hud-dashboard build/test-hud-menu build/test-shift-scale build/test-shift-window build/test-shift-deck build/test-shift-deck-smooth build/power-core.o build/test-power-history build/test-power-rpm-plot build/test-power-deck build/test-hud-reader build/test-gauges-extended build/test-launch-deck build/test-boostdeck-assignments build/xdrive-control build/boost-deck build/shift-deck build/mhd-maps build/engine-codes build/test-core build/test-most build/test-diag-link build/bootmod3 build/exhaust-flap build/test-launch-timer build/test-launch-records build/test-boost-preferences build/test-warm-progress build/warmdeck-collector build/mgflasher build/hybriddeck-collector
	./build/test-warm-progress
	./build/test-boost-preferences
	./build/test-launch-timer
	./build/test-launch-records
	./build/test-core
	./build/test-most
	./build/test-diag-link
	$(PYTHON) -B tests/test_drive_apps.py
	$(PYTHON) -B tests/test_oneshot_most.py
	$(PYTHON) -B tests/test_transport.py
	./build/test-n57
	./build/test-drive-frame
	./build/test-shift-scale
	./build/test-shift-window
	./build/test-shift-deck
	./build/test-shift-deck-smooth
	./build/test-power-history
	./build/test-power-rpm-plot
	./build/test-power-deck
	./build/test-hud-reader
	./build/test-gauge-coexistence
	./build/test-hud-dashboard
	./build/test-hud-menu
	./build/test-gauges-extended
	./build/test-launch-deck
	./build/test-boostdeck-assignments
	$(PYTHON) -B tests/test_boostdeck_layout.py
	$(PYTHON) -B tests/test_content_layouts.py
	$(PYTHON) -B tests/test_shift_scale.py
	$(PYTHON) -B tests/test_n57_dashboards.py
	$(PYTHON) -B tests/test_n57.py
	$(PYTHON) -B tests/test_drive_n57.py
	$(PYTHON) -B tests/test_n57_xdrive_gate.py
	$(PYTHON) -B tests/test_n57_most.py
	$(PYTHON) -B tests/test_n57_coexistence.py
	./build/test-n57-availability
	$(PYTHON) -B tests/test_generic_hud_poll.py
