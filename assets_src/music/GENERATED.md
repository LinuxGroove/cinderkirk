# Generated audio

Made with [Lemonade](https://lemonade-server.ai)'s models and acestep.cpp's ace-server by `tools/lemonade/generate.py` from `tools/lemonade/audio.json`; `tools/lemonade/generated.json` has the full record, including every take's numbers. Released under CC0. Make them again with

```sh
python3 tools/lemonade/generate.py --force [--only music|voices|sfx] [name ...]
```

Every file is 44.1 kHz Ogg Vorbis (music stereo, the rest mono), trimmed of silence and peaking at about -3 dBFS. Loops were cut where their end matches their start and crossfaded there. Music and sounds were made in several takes (seeds counting up from the first); the take kept is the one whose length, loudness, ending and loop seam fit best (for sounds, also how many separate sounds it has and how quiet its background is) unless the table says it was picked by hand. The other takes were not kept.

## Music

Model `ACE-Step-Music` (`acestep-v15-xl-sft-Q8_0.gguf, vae-BF16.gguf, Qwen3-Embedding-0.6B-BF16.gguf`). Instrumental (no lyrics), the server's default steps. Rendered by `ace-server f65b160 (2026-10-28) --vae-chunk 256`, given the request Lemonade's ACE-Step backend sends it (the prompt as the caption, `[Instrumental]` as the lyrics, 24-bit WAV) rather than through Lemonade (`--ace-server`).

| File | Prompt | Seed | Takes | Length | Settings |
|---|---|---|---|---|---|
| `assets_src/music/track02.ogg` | dark ambient drone, deep low cello drone, distant cracked church bell tolling slowly, wind in a mine shaft, faint metallic creaks, cold and still, abandoned industrial chapel, sparse, no drums, 60 bpm, instrumental, loopable | 98162 | 3 | 150.1 s | asked for 180 s; loop 21.50 to 171.65 s of the take, 1.5 s crossfade; -19.1 LUFS |
| `assets_src/music/track03.ogg` | quiet dark ambient interlude, warm low organ drone, soft bowed metal, slow single bell, embers cooling, a breath after a fight, no drums, 60 bpm, instrumental, loopable | 79458 | 3 | 52.2 s | asked for 72 s; loop 9.00 to 61.20 s of the take, 1.5 s crossfade; -15.1 LUFS |
| `assets_src/music/track04.ogg` | dark industrial ambient, foundry at night, slow heavy hammer on anvil far away, furnace roar, low brass drone, metallic clangs with long reverb, grinding chains, ominous, 70 bpm, instrumental, loopable | 61585 | 3 | 146.4 s | asked for 180 s; loop 8.16 to 154.55 s of the take, 1.5 s crossfade; -17.6 LUFS |
| `assets_src/music/track05.ogg` | dark ambient, flooded underground cistern, water dripping in huge stone vaults, deep sub bass drone, distant muffled pump thuds, eerie bowed glass, cold green gloom, sparse, no drums, 60 bpm, instrumental, loopable | 65921 | 3 | 148.5 s | asked for 180 s; loop 11.09 to 159.60 s of the take, 1.5 s crossfade; -16.2 LUFS |
| `assets_src/music/track06.ogg` | dark ambient, ossuary crypt and bone kilns, low wordless male choir drone, hollow wooden bone percussion, crackling fire, slow hand bells, ash and dread, sacred and wrong, 65 bpm, instrumental, loopable | 64658 | 3 | 151.2 s | asked for 180 s; loop 15.59 to 166.79 s of the take, 1.5 s crossfade; -16.4 LUFS |
| `assets_src/music/track07.ogg` | dark industrial ambient, deep mine tunnels, rumbling earth, slow steam engine pistons, metal pings of pickaxes far away, low detuned synth drone, creaking timber, claustrophobic, 70 bpm, instrumental, loopable | 5345 | 3 | 150.8 s | asked for 180 s; loop 21.15 to 171.92 s of the take, 1.5 s crossfade; -20.4 LUFS |
| `assets_src/music/track08.ogg` | doom dark ambient, descending into an endless pit, huge slow cracked bell tolls, sub bass swells, distorted low strings, heat haze, dread building, no drums, 55 bpm, instrumental, loopable | 54929 | 3 | 148.9 s | asked for 180 s; loop 13.35 to 162.25 s of the take, 1.5 s crossfade; -15.7 LUFS |
| `assets_src/music/track09.ogg` | heavy industrial doom metal, crushing slow distorted baritone guitars, pounding taiko and anvil percussion, church bells, low brass, boss fight in a burning foundry, 90 bpm, instrumental, loopable | 2050 | 3 | 119.1 s | asked for 144 s; loop 7.86 to 126.97 s of the take, 1.5 s crossfade; -15.3 LUFS |
| `assets_src/music/track10.ogg` | driving dark industrial, fast mechanical drum machine, anvil hits, distorted bass synth, steam hisses, metal clangs, arena fight in a foundry, aggressive, 130 bpm, instrumental, loopable | 73687 | 3 | 121.3 s | asked for 144 s; loop 13.02 to 134.37 s of the take, 1.5 s crossfade; -15.9 LUFS |
