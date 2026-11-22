# Cinderkirk: build the engine, the game code, the levels and the pak.
#
#   make            everything: engine, progs.dat, levels, dist/cinder/pak0.pak
#   make run        play it from dist/
#   make map MAP=start   rebuild one level
#   make textures   bake the world textures in Blender (BLENDER=..., see README)
#   make models     build the creatures in Blender
#   make weapons    build the weapons the player holds in Blender
#   make pickups    build the pickups and the weapons on the floor in Blender
#   make actors     build the stoker as others see him, gibs and projectiles in Blender
#   make tarball   dist/cinderkirk-VERSION-linux-ARCH.tar.gz, to unpack and play anywhere
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
LIGHT_FLAGS ?= -extra4 -bounce -lit -lux
VIS_FLAGS   ?=
# World size of each texture, in units (the WAD stand-in's size); 128 unless named.
WAD_SIZES   ?= kirk_glyph1=64,ore_rock1=256,vein_rock1=256

MAPS     := $(patsubst maps_src/%.py,%,$(wildcard maps_src/*.py)) $(patsubst maps_src/%.map,%,$(wildcard maps_src/*.map))
BSPS     := $(patsubst %,$(BUILD)/maps/%.bsp,$(MAPS))
QC       := $(wildcard quakec/*.qc quakec/*/*.qc) quakec/progs.src
TEXTURES := $(filter-out %_norm.png %_gloss.png %_rough.png,$(wildcard assets/textures/*.png))
GLYPHS := $(wildcard assets/glyphs/*/*.svg)
MATERIALS := $(wildcard assets/textures/*_norm.png assets/textures/*_gloss.png)
MODELS   := $(wildcard assets/models/*.md3 assets/models/*.png)

export PATH := $(abspath $(PREFIX))/bin:$(PATH)
export PKG_CONFIG_PATH := $(abspath $(PREFIX))/lib/pkgconfig:$(abspath $(PREFIX))/share/pkgconfig
export LD_LIBRARY_PATH := $(abspath $(PREFIX))/lib
# build/prefix's headers first (the snap's gnome extension adds older Vulkan ones to CFLAGS).
export CFLAGS := -I$(abspath $(PREFIX))/include $(CFLAGS)

.PHONY: all engine game deps tools librequake maps map run clean textures models weapons pickups actors check trenchbroom tarball

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

# A level made in TrenchBroom (maps_src/<map>.map) builds the same way.
$(BUILD)/maps/%.bsp: maps_src/%.map $(BUILD)/maps/cinder.wad $(BIN)/.done
	cp maps_src/$*.map $(BUILD)/maps/$*.map
	cd $(BUILD)/maps && $(abspath $(BIN))/qbsp $*.map
	cd $(BUILD)/maps && $(abspath $(BIN))/vis $(VIS_FLAGS) $*.bsp
	cd $(BUILD)/maps && $(abspath $(BIN))/light $(LIGHT_FLAGS) $*.bsp

maps: $(BSPS)
map:
	$(MAKE) $(BUILD)/maps/$(MAP).bsp

game: $(DIST)/cinder/pak0.pak

$(BUILD)/sound/.done: tools/sfx.py tools/sfx_world.py
	$(PYTHON) tools/sfx.py $(BUILD)/sound
	touch $@

$(BUILD)/menu/.done: tools/menu_art.py assets/textures/bronze1.png assets/textures/kirk_brick1.png assets_src/materials/glyph_mask.png $(LQ)/.done
	$(PYTHON) tools/menu_art.py $(LQ)/gfx/palette.lmp $(BUILD)/menu assets/textures assets_src/materials/glyph_mask.png
	touch $@

$(BUILD)/sprites/.done: tools/sprites.py $(LQ)/.done
	$(PYTHON) tools/sprites.py $(LQ)/gfx/palette.lmp $(BUILD)/sprites
	touch $@

$(BUILD)/hud/.done: tools/hud_svg.py $(wildcard assets_src/fonts/*.woff)
	rm -rf $(BUILD)/hud
	$(PYTHON) tools/hud_svg.py $(BUILD)/hud
	touch $@

# pak0.pak holds everything the game loads: LibreQuake's stand-ins first,
# then Cinderkirk's own files over them.
# Music made by tools/lemonade/generate.py: music/trackNN.ogg, NN a map's worldspawn sounds.
MUSIC := $(wildcard assets_src/music/track*.ogg)

$(DIST)/cinder/pak0.pak: $(LQ)/.done $(BUILD)/menu/.done $(BUILD)/hud/.done $(BUILD)/sound/.done $(BUILD)/sprites/.done $(BUILD)/progs.dat $(BSPS) $(TEXTURES) $(MATERIALS) $(MODELS) $(GLYPHS) gfx/splash.png cinder/default.cfg cinder/quake.rc cinder/particles/cinder.cfg tools/pak.py $(MUSIC)
	rm -rf $(STAGE)
	mkdir -p $(STAGE)/maps $(STAGE)/textures $(STAGE)/gfx
	cp -r $(LQ)/gfx.wad $(LQ)/gfx $(LQ)/progs $(LQ)/sound $(LQ)/maps $(STAGE)/
	cp $(BUILD)/progs.dat $(STAGE)/
	for m in $(MAPS); do cp $(BUILD)/maps/$$m.bsp $(STAGE)/maps/; \
		[ ! -f $(BUILD)/maps/$$m.lit ] || cp $(BUILD)/maps/$$m.lit $(STAGE)/maps/; \
		[ ! -f $(BUILD)/maps/$$m.lux ] || cp $(BUILD)/maps/$$m.lux $(STAGE)/maps/; done
	cp -r $(BUILD)/sound/* $(STAGE)/sound/
	mkdir -p $(STAGE)/music && for f in $(MUSIC); do cp $$f $(STAGE)/music/; done
	cp $(TEXTURES) $(MATERIALS) $(STAGE)/textures/
	cp $(MODELS) $(BUILD)/sprites/*.spr $(STAGE)/progs/
	cp $(BUILD)/menu/gfx/* gfx/splash.png $(STAGE)/gfx/
	mkdir -p $(STAGE)/gfx/hud && cp $(BUILD)/hud/*.svg $(STAGE)/gfx/hud/
	cp -r assets/glyphs $(STAGE)/gfx/hud/g && rm $(STAGE)/gfx/hud/g/License.txt
	cp cinder/default.cfg cinder/quake.rc $(STAGE)/
	mkdir -p $(STAGE)/particles && cp cinder/particles/*.cfg $(STAGE)/particles/
	mkdir -p $(DIST)/cinder
	$(PYTHON) tools/pak.py $@ $(STAGE)

tarball: $(DIST)/cinderkirk $(DIST)/cinder/pak0.pak
	tools/tarball.sh $(DIST) $(BUILD) $(PREFIX)

# TrenchBroom's game config and entity definitions, and the WAD it shows
# textures from (dist/cinder/cinder.wad); see docs/mapping.md.
trenchbroom: $(BUILD)/maps/cinder.wad tools/trenchbroom.py $(wildcard quakec/*.qc quakec/*/*.qc)
	$(PYTHON) tools/trenchbroom.py $(DIST)/trenchbroom
	mkdir -p $(DIST)/cinder && cp $(BUILD)/maps/cinder.wad $(DIST)/cinder/

run: all
	cd $(DIST) && ./cinderkirk -basedir . $(ARGS)

# The art -------------------------------------------------------------------

# Bakes every world texture to assets/textures at TEXRES. With a GPU, Cycles
# uses it (CYCLES_DEVICE=OPTIX or CUDA); without one it takes a few minutes.
textures:
	$(PYTHON) assets_src/materials/glyphs.py assets_src/materials/glyph_mask.png
	$(BLENDER) -b -P assets_src/materials/materials.py -- assets/textures $(TEXRES)

# Builds, rigs, animates and skins the creatures to assets/models at TEXRES.
models:
	$(BLENDER) -b -P assets_src/models/creatures.py -- assets/models $(TEXRES)

# Builds the view models (v_*.md3), one Blender run per weapon (one run for
# all eight runs out of memory). Building and skinning a model is Python on one
# core, so run them side by side: make -j8 weapons (on a GPU the bakes
# themselves take turns, see gpu_turn in creatures.py).
WEAPONS := pick scattergun spitter bolt crucible steam mortar toll
.PHONY: $(addprefix weapon-,$(WEAPONS))
weapons: $(addprefix weapon-,$(WEAPONS))
$(addprefix weapon-,$(WEAPONS)): weapon-%:
	$(BLENDER) -b -P assets_src/models/weapons.py -- assets/models $(TEXRES) only=$*

# Builds the pickups: health, ammo, armour, keys, the backpack (pickups.py) and
# the weapons as they lie on the floor (g_*.md3, weapons.py with WORLD=1), one
# Blender run each, so make -j8 pickups.
PICKUPS := health_small health health_mega shells shells_big slag slag_big iron iron_big \
	clappers clappers_big armour_leather armour_iron armour_bronze key_silver key_gold backpack \
	forge_heart mantle veil quench_suit
GROUND  := steam spitter bolt crucible mortar toll
.PHONY: pickups $(addprefix pickup-,$(PICKUPS)) $(addprefix ground-,$(GROUND))
pickups: $(addprefix pickup-,$(PICKUPS)) $(addprefix ground-,$(GROUND))
$(addprefix pickup-,$(PICKUPS)): pickup-%:
	$(BLENDER) -b -P assets_src/models/pickups.py -- assets/models $(TEXRES) only=$*
$(addprefix ground-,$(GROUND)): ground-%:
	WORLD=1 $(BLENDER) -b -P assets_src/models/weapons.py -- assets/models $(TEXRES) only=$*

# Builds the stoker as others see him (player.md3, its head and the eyes the
# Soot Veil leaves), the gibs and the projectiles (actors.py), one Blender run
# each, so make -j8 actors. The engine loads each in place of LibreQuake's .mdl.
ACTORS := player h_player eyes gib1 gib2 gib3 zom_gib spike s_spike grenade missile lavaball bolt bolt2 bolt3
.PHONY: actors $(addprefix actor-,$(ACTORS))
actors: $(addprefix actor-,$(ACTORS))
$(addprefix actor-,$(ACTORS)): actor-%:
	$(BLENDER) -b -P assets_src/models/actors.py -- assets/models $(TEXRES) only=$*

check:
	$(PYTHON) -m py_compile tools/*.py maps_src/*.py assets_src/models/*.py
	for m in $(MAPS); do grep -q "LEAK" $(BUILD)/maps/$$m.log && { echo "$$m leaks"; exit 1; } || true; done
	$(PYTHON) tools/stuck.py

# Plays every level and the finale with nobody at the keys, on this machine's
# GPU (not in CI): make playtest PLAYTEST="--maps throat2 --skill 3"; see
# tools/playtest/playtest.py. The report goes to build/playtest/report.md.
.PHONY: playtest
playtest: all
	$(PYTHON) tools/playtest/playtest.py $(PLAYTEST)

clean:
	rm -rf $(BUILD)/engine $(BUILD)/maps $(BUILD)/stage $(BUILD)/progs.dat $(BUILD)/progs.lno $(DIST)

FORCE:
