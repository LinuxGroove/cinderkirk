/*
Copyright (C) The LinuxGroove team

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.
*/

// glyph.c -- Cinderkirk's button glyphs. Text that names a command in
// braces, "{+jump}", shows the glyph of the key bound to it on the device
// used last: the keyboard and mouse, or an Xbox, PlayStation, Switch or Steam
// Deck pad. "{@look}" and "{@move}" name the sticks or the mouse and keys.
// The glyphs are Kenney's Input Prompts (CC0), as SVG in gfx/hud/g/<set>/
// named after the engine's keys. Nothing here is Cinderkirk's own but the
// glyphs, so it could go upstream.

#include "quakedef.h"
#include "q_ctype.h"
#include "hud_svg.h"

const char *IN_GamepadGlyphs (void);

static cvar_t glyph_set = {"glyph_set", "", CVAR_NONE}; // kbm, xbox, ps, switch or deck: always that set

static const char *const pad_glyphs[] = {
	"abutton", "bbutton", "xbutton", "ybutton", "lshoulder", "rshoulder", "ltrigger", "rtrigger", "lthumb", "rthumb",
	"back",	   "start",	  "dpad_up", "dpad_down", "dpad_left", "dpad_right", NULL};
static const char *const kbm_glyphs[] = {
	"space",   "enter",	   "escape",  "tab",	 "shift",	  "ctrl",	"alt",	   "backspace", "uparrow",	  "downarrow",
	"leftarrow", "rightarrow", "ins",	"del",	 "home",	  "end",	"pgup",	   "pgdn",		"pause",	  "mouse1",
	"mouse2",  "mouse3",   "mouse4",  "mouse5",	 "mwheelup", "mwheeldown", NULL};

void Glyph_Init (void)
{
	Cvar_RegisterVariable (&glyph_set);
}

/*
================
Glyph_Set

The set of glyphs to show: "kbm" or a pad's.
================
*/
const char *Glyph_Set (void)
{
	const char *pad;
	if (glyph_set.string[0])
		return glyph_set.string;
	pad = IN_GamepadGlyphs ();
	return pad ? pad : "kbm";
}

static qboolean Glyph_IsPadKey (int key)
{
	return key >= K_LTHUMB && key <= K_TOUCHPAD_ALT;
}

static qboolean Glyph_Listed (const char *const *list, const char *name)
{
	for (; *list; list++)
		if (!strcmp (*list, name))
			return true;
	return false;
}

/*
================
Glyph_Name

The HUD picture name of a key's glyph in the set shown ("g/xbox/abutton"),
or NULL when the key has none there.
================
*/
const char *Glyph_Name (int key)
{
	static char name[64];
	char		lower[32];
	const char *set = Glyph_Set ();
	const char *s;
	int			i;
	qboolean	pad = strcmp (set, "kbm") != 0;

	if (key < 0 || pad != Glyph_IsPadKey (key))
		return NULL;
	if (key >= K_LTHUMB_ALT && key <= K_TOUCHPAD_ALT)
		key -= K_LTHUMB_ALT - K_LTHUMB;
	s = Key_KeynumToString (key);
	for (i = 0; s[i] && i < (int)sizeof (lower) - 1; i++)
		lower[i] = q_tolower (s[i]);
	lower[i] = 0;
	if (pad ? !Glyph_Listed (pad_glyphs, lower)
			: !(Glyph_Listed (kbm_glyphs, lower) || (i == 1 && q_isalnum (lower[0])) ||
				(lower[0] == 'f' && atoi (lower + 1) >= 1 && atoi (lower + 1) <= 12)))
		return NULL;
	q_snprintf (name, sizeof (name), "g/%s/%s", set, lower);
	return name;
}

/*
================
Glyph_KeyFor

The key bound to a command on the device used last (the first one found),
or -1 when none is.
================
*/
int Glyph_KeyFor (const char *command)
{
	int		 key;
	qboolean pad = strcmp (Glyph_Set (), "kbm") != 0;

	for (key = 0; key < MAX_KEYS; key++)
		if (keybindings[key] && !q_strcasecmp (keybindings[key], command) && pad == Glyph_IsPadKey (key) &&
			!(key >= K_LTHUMB_ALT && key <= K_TOUCHPAD_ALT))
			return key;
	return -1;
}

// What a token shows: one glyph's picture name, or text when there's none.
static void Glyph_Token (const char *token, int len, const char **pic, char *text, size_t textsize)
{
	char		command[128];
	int			key;
	qboolean	pad = strcmp (Glyph_Set (), "kbm") != 0;
	static char name[64];

	*pic = NULL;
	q_strlcpy (command, token, q_min ((size_t)len + 1, sizeof (command)));
	if (!strcmp (command, "@look") || !strcmp (command, "@move"))
	{
		if (pad)
			q_snprintf (name, sizeof (name), "g/%s/%s", Glyph_Set (), command[1] == 'l' ? "rstick" : "lstick");
		else if (command[1] == 'l')
			q_strlcpy (name, "g/kbm/mouse", sizeof (name));
		else
		{
			q_strlcpy (text, "WASD", textsize);
			return;
		}
		*pic = name;
		return;
	}
	key = Glyph_KeyFor (command);
	if (key >= 0 && (*pic = Glyph_Name (key)))
		return;
	if (key >= 0)
		q_snprintf (text, textsize, "[%s]", Key_KeynumToString (key));
	else
		q_snprintf (text, textsize, "[%s]", command);
}

/*
================
Glyph_Text

Draws one line of text in the menu canvas's characters (size units each)
with its {tokens} as glyphs a little over twice as tall, from x and y; with no cbx,
only measures it. Returns the width.
================
*/
float Glyph_Text (cb_context_t *cbx, float x, float y, float size, const char *text, int len)
{
	float		x0 = x, gh = size * 2.2f, w, h, s;
	const char *p, *end = text + len, *close, *pic;
	char		alt[64];
	qpic_t	   *qp;

	s = q_min ((float)glwidth / 320.0f, (float)glheight / 200.0f);
	s = CLAMP (1.0f, M_GetScale (), s);
	for (p = text; p < end; p++)
	{
		if (*p == '{' && (close = memchr (p, '}', end - p)))
		{
			alt[0] = 0;
			Glyph_Token (p + 1, (int)(close - p - 1), &pic, alt, sizeof (alt));
			if (pic && HudSvg_Size (pic, &w, &h))
			{
				w = gh * w / h;
				if (cbx && (qp = HudSvg_Pic (pic, gh * s)))
					Draw_SubPicLinearBlend (cbx, x, y + (size - gh) / 2, w, gh, qp, 0, 0, 1, 1, NULL, 1);
				x += w;
			}
			else
			{
				for (const char *c = alt; *c; c++, x += size)
					if (cbx)
						Draw_Character (cbx, x, y, *c);
			}
			p = close;
			continue;
		}
		if (cbx)
			Draw_Character (cbx, x, y, *p);
		x += size;
	}
	return x - x0;
}
