# Cinderkirk: build the engine, the game code, the levels and the pak.
#
#   make            everything: engine, progs.dat, levels, dist/cinder/pak0.pak
#   make run        play it from dist/
#   make map MAP=start   rebuild one level
#   make textures   bake the world textures in Blender (BLENDER=..., see README)
#   make clean      remove build/ and dist/ (keeps fetched sources in build/src)
#
# The game runs from dist/: dist/cinderkirk is the engine, dist/cinder/ the game.

BUILD    ?= build
DIST     ?= dist
PREFIX   ?= $(BUILD)/prefix
BIN      ?= $(BUILD)/bin
LQ       ?= $(BUILD)/librequake
STAGE    := $(BUILD)/stage
PYTHON   ?= python3
export PYTHON
BLENDER  ?= blender
TEXRES   ?= 1024
LIGHT_FLAGS ?= -extra4 -bounce -lit
VIS_FLAGS   ?=
# World size of each texture, in units (the WAD stand-in's size); 128 unless named.
WAD_SIZES   ?= kirk_glyph1=64

MAPS     := $(patsubst maps_src/%.py,%,$(wildcard maps_src/*.py))
BSPS     := $(patsubst %,$(BUILD)/maps/%.bsp,$(MAPS))
QC       := $(wildcard quakec/*.qc quakec/*/*.qc) quakec/progs.src
TEXTURES := $(filter-out %_norm.png %_gloss.png %_rough.png,$(wildcard assets/textures/*.png))

export PATH := $(abspath $(PREFIX))/bin:$(PATH)
export PKG_CONFIG_PATH := $(abspath $(PREFIX))/lib/pkgconfig:$(abspath $(PREFIX))/share/pkgconfig
export LD_LIBRARY_PATH := $(abspath $(PREFIX))/lib
# build/prefix's headers first (the snap's gnome extension adds older Vulkan ones to CFLAGS).
export CFLAGS := -I$(abspath $(PREFIX))/include $(CFLAGS)

.PHONY: all engine game deps tools librequake maps map run clean textures models check

all: engine game

# The engine ----------------------------------------------------------------

deps: $(PREFIX)/.done
$(PREFIX)/.done: tools/deps.sh tools/versions.sh
	tools/deps.sh $(PREFIX)
	touch $@

engine: $(DIST)/cinderkirk
# ninja decides what to rebuild, so this always asks it.
$(DIST)/cinderkirk: $(PREFIX)/.done FORCE
	[ -d $(BUILD)/engine ] || meson setup $(BUILD)/engine engine --buildtype=release
	ninja -C $(BUILD)/engine
	mkdir -p $(DIST)
	install -m 755 $(BUILD)/engine/vkquake $@

# The game ------------------------------------------------------------------

tools: $(BIN)/.done
$(BIN)/.done: tools/tools.sh tools/versions.sh
	tools/tools.sh $(BIN)
	touch $@

librequake: $(LQ)/.done
$(LQ)/.done: tools/librequake.sh tools/versions.sh tools/wad.py $(BIN)/.done
	tools/librequake.sh $(LQ) $(BIN)
	touch $@

$(BUILD)/progs.dat: $(QC) $(BIN)/.done
	mkdir -p $(BUILD)
	cd quakec && $(abspath $(BIN))/fteqcc -srcfile progs.src

$(BUILD)/maps/cinder.wad: tools/wad.py $(TEXTURES) $(LQ)/.done
	mkdir -p $(BUILD)/maps
	$(PYTHON) tools/wad.py $(LQ)/gfx/palette.lmp $@ assets/textures --sizes $(WAD_SIZES)

# Each level: the script writes the .map, then qbsp, vis and light.
$(BUILD)/maps/%.bsp: maps_src/%.py tools/mapkit.py $(BUILD)/maps/cinder.wad $(BIN)/.done
	$(PYTHON) maps_src/$*.py $(BUILD)/maps/$*.map
	cd $(BUILD)/maps && $(abspath $(BIN))/qbsp $*.map
	cd $(BUILD)/maps && $(abspath $(BIN))/vis $(VIS_FLAGS) $*.bsp
	cd $(BUILD)/maps && $(abspath $(BIN))/light $(LIGHT_FLAGS) $*.bsp

maps: $(BSPS)
map:
	$(MAKE) $(BUILD)/maps/$(MAP).bsp

game: $(DIST)/cinder/pak0.pak

$(BUILD)/sound/.done: tools/sfx.py
	$(PYTHON) tools/sfx.py $(BUILD)/sound
	touch $@

$(BUILD)/menu/.done: tools/menu_art.py assets/textures/bronze1.png assets/textures/kirk_brick1.png assets_src/materials/glyph_mask.png $(LQ)/.done
	$(PYTHON) tools/menu_art.py $(LQ)/gfx/palette.lmp $(BUILD)/menu assets/textures assets_src/materials/glyph_mask.png
	touch $@

# pak0.pak holds everything the game loads: LibreQuake's stand-ins first,
# then Cinderkirk's own files over them.
$(DIST)/cinder/pak0.pak: $(LQ)/.done $(BUILD)/menu/.done $(BUILD)/sound/.done $(BUILD)/progs.dat $(BSPS) $(TEXTURES) gfx/splash.png cinder/default.cfg cinder/quake.rc tools/pak.py
	rm -rf $(STAGE)
	mkdir -p $(STAGE)/maps $(STAGE)/textures $(STAGE)/gfx
	cp -r $(LQ)/gfx.wad $(LQ)/gfx $(LQ)/progs $(LQ)/sound $(LQ)/maps $(STAGE)/
	cp $(BUILD)/progs.dat $(STAGE)/
	for m in $(MAPS); do cp $(BUILD)/maps/$$m.bsp $(STAGE)/maps/; \
		[ ! -f $(BUILD)/maps/$$m.lit ] || cp $(BUILD)/maps/$$m.lit $(STAGE)/maps/; done
	cp -r $(BUILD)/sound/cinder $(STAGE)/sound/
	cp $(TEXTURES) $(STAGE)/textures/
	cp $(BUILD)/menu/gfx/* gfx/splash.png $(STAGE)/gfx/
	cp cinder/default.cfg cinder/quake.rc $(STAGE)/
	mkdir -p $(DIST)/cinder
	$(PYTHON) tools/pak.py $@ $(STAGE)

run: all
	cd $(DIST) && ./cinderkirk -basedir . $(ARGS)

# The art -------------------------------------------------------------------

# Bakes every world texture to assets/textures at TEXRES. With a GPU, Cycles
# uses it (CYCLES_DEVICE=OPTIX or CUDA); without one it takes a few minutes.
textures:
	$(PYTHON) assets_src/materials/glyphs.py assets_src/materials/glyph_mask.png
	$(BLENDER) -b -P assets_src/materials/materials.py -- assets/textures $(TEXRES)

models:
	$(BLENDER) -b -P assets_src/models/models.py -- assets/models

check:
	$(PYTHON) -m py_compile tools/*.py maps_src/*.py
	for m in $(MAPS); do grep -q "LEAK" $(BUILD)/maps/$$m.log && { echo "$$m leaks"; exit 1; } || true; done

clean:
	rm -rf $(BUILD)/engine $(BUILD)/maps $(BUILD)/stage $(BUILD)/progs.dat $(BUILD)/progs.lno $(DIST)

FORCE:
