#!/usr/bin/env python3
"""Copies the button glyphs the game shows from Kenney's Input Prompts (CC0)
into assets/glyphs/<set>/<key>.svg, named by the engine's key names in lower
case, so the engine can find the glyph for any bound key. Run it again only
to change which glyphs are copied; the copies are committed.

    python3 tools/glyphs.py "<kenney-assets>/Icons/Input Prompts" assets/glyphs
"""
import os
import shutil
import string
import sys

# The pad's buttons by position: abutton is the bottom face button, bbutton
# the right one, xbutton the left and ybutton the top, whatever they're called.
PADS = {
    "xbox": ("Xbox Series", {
        "abutton": "xbox_button_color_a", "bbutton": "xbox_button_color_b", "xbutton": "xbox_button_color_x",
        "ybutton": "xbox_button_color_y", "lshoulder": "xbox_lb", "rshoulder": "xbox_rb", "ltrigger": "xbox_lt",
        "rtrigger": "xbox_rt", "lthumb": "xbox_stick_l_press", "rthumb": "xbox_stick_r_press",
        "back": "xbox_button_view", "start": "xbox_button_menu", "lstick": "xbox_stick_l", "rstick": "xbox_stick_r",
    }),
    "ps": ("PlayStation Series", {
        "abutton": "playstation_button_color_cross", "bbutton": "playstation_button_color_circle",
        "xbutton": "playstation_button_color_square", "ybutton": "playstation_button_color_triangle",
        "lshoulder": "playstation_trigger_l1", "rshoulder": "playstation_trigger_r1", "ltrigger": "playstation_trigger_l2",
        "rtrigger": "playstation_trigger_r2", "lthumb": "playstation_button_l3", "rthumb": "playstation_button_r3",
        "back": "playstation5_button_create", "start": "playstation5_button_options",
        "lstick": "playstation_stick_l", "rstick": "playstation_stick_r",
    }),
    # Nintendo's labels sit the other way round: the bottom button is B.
    "switch": ("Nintendo Switch", {
        "abutton": "switch_button_b", "bbutton": "switch_button_a", "xbutton": "switch_button_y",
        "ybutton": "switch_button_x", "lshoulder": "switch_button_l", "rshoulder": "switch_button_r",
        "ltrigger": "switch_button_zl", "rtrigger": "switch_button_zr", "lthumb": "switch_stick_l_press",
        "rthumb": "switch_stick_r_press", "back": "switch_button_minus", "start": "switch_button_plus",
        "lstick": "switch_stick_l", "rstick": "switch_stick_r",
    }),
    "deck": ("Steam Deck", {
        "abutton": "steamdeck_button_a", "bbutton": "steamdeck_button_b", "xbutton": "steamdeck_button_x",
        "ybutton": "steamdeck_button_y", "lshoulder": "steamdeck_button_l1", "rshoulder": "steamdeck_button_r1",
        "ltrigger": "steamdeck_button_l2", "rtrigger": "steamdeck_button_r2", "lthumb": "steamdeck_stick_l_press",
        "rthumb": "steamdeck_stick_r_press", "back": "steamdeck_button_view", "start": "steamdeck_button_options",
        "lstick": "steamdeck_stick_l", "rstick": "steamdeck_stick_r",
    }),
}
DPAD = {"xbox": "xbox_dpad", "ps": "playstation_dpad", "switch": "switch_dpad", "deck": "steamdeck_dpad"}

KEYS = {c: "keyboard_" + c for c in string.ascii_lowercase + string.digits}
KEYS.update({f"f{i}": f"keyboard_f{i}" for i in range(1, 13)})
KEYS.update({
    "space": "keyboard_space", "enter": "keyboard_enter", "escape": "keyboard_escape", "tab": "keyboard_tab",
    "shift": "keyboard_shift", "ctrl": "keyboard_ctrl", "alt": "keyboard_alt", "backspace": "keyboard_backspace",
    "uparrow": "keyboard_arrow_up", "downarrow": "keyboard_arrow_down", "leftarrow": "keyboard_arrow_left",
    "rightarrow": "keyboard_arrow_right", "ins": "keyboard_insert", "del": "keyboard_delete", "home": "keyboard_home",
    "end": "keyboard_end", "pgup": "keyboard_page_up", "pgdn": "keyboard_page_down", "pause": "keyboard_pause",
    "mouse1": "mouse_left", "mouse2": "mouse_right", "mouse3": "mouse_scroll", "mouse4": "mouse_side_back",
    "mouse5": "mouse_side_forward", "mwheelup": "mouse_scroll_up", "mwheeldown": "mouse_scroll_down",
    "mouse": "mouse_move",
})


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    sets = {k: v for k, v in PADS.items()}
    for name, (folder, keys) in sets.items():
        keys = dict(keys)
        for d in ("up", "down", "left", "right"):
            keys["dpad_" + d] = f"{DPAD[name]}_{d}"
        copy(os.path.join(src, folder, "Vector"), os.path.join(out, name), keys)
    copy(os.path.join(src, "Keyboard & Mouse", "Vector"), os.path.join(out, "kbm"), KEYS)
    shutil.copy(os.path.join(src, "License.txt"), os.path.join(out, "License.txt"))


def copy(src, out, keys):
    os.makedirs(out, exist_ok=True)
    for key, stem in keys.items():
        shutil.copy(os.path.join(src, stem + ".svg"), os.path.join(out, key + ".svg"))
    print(out, len(keys))


if __name__ == "__main__":
    main()
