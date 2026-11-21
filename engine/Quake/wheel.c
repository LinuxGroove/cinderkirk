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

// wheel.c -- Cinderkirk's weapon wheel. Holding +wheel (LB, or Q) opens it
// and slows the game to a third in single player; the right stick, the gyro
// or the mouse points at a slot, and letting go sends that slot's impulse, so
// the game code needs nothing new. A quick tap goes back to the last weapon.
// Nothing here is Cinderkirk's own but the art and the slot order, so it
// could go upstream with a cvar for the slots.

#include "quakedef.h"
#include "hud_svg.h"

#define WHEEL_R0	104.0f
#define WHEEL_R1	262.0f
#define WHEEL_TAP	0.25 // seconds: a shorter hold is a tap
#define WHEEL_REACH 100.0f // how far the mouse moves the pointer

int		 Sbar_FoundrySlotItem (int slot);
qboolean IN_GamepadInUse (void);
extern cvar_t hud_scale;

static cvar_t wheel_slowmo = {"wheel_slowmo", "0.33", CVAR_ARCHIVE_GAME};

static qboolean wheel_down;
static double	wheel_opened;
static int		wheel_sel; // 1 to 8, 0 for none yet
static float	wheel_x, wheel_y;
static qboolean wheel_mouse_last;
static int		wheel_active, wheel_previous; // item bits

qboolean Wheel_Open (void)
{
	return wheel_down && key_dest == key_game && cls.state == ca_connected && !cl.intermission && cl.stats[STAT_HEALTH] > 0;
}

float Wheel_TimeScale (void)
{
	if (!Wheel_Open () || !sv.active || svs.maxclients != 1 || cls.demoplayback)
		return 1.0f;
	return CLAMP (0.1f, wheel_slowmo.value, 1.0f);
}

static int Wheel_SlotAt (float x, float y)
{
	float a = atan2f (y, x) + M_PI / 2; // 0 at the top, clockwise
	while (a < 0)
		a += 2 * M_PI;
	return ((int)floorf ((a + M_PI / 8) / (M_PI / 4)) % 8) + 1;
}

static int Wheel_SlotOf (int item)
{
	int slot;
	for (slot = 1; slot <= 8; slot++)
		if (Sbar_FoundrySlotItem (slot) == item)
			return slot;
	return 0;
}

void Wheel_Stick (float x, float y)
{
	if (x * x + y * y > 0.45f * 0.45f)
	{
		wheel_sel = Wheel_SlotAt (x, y);
		wheel_mouse_last = false;
	}
}

void Wheel_Mouse (float dx, float dy)
{
	float len;

	wheel_x += dx * 0.5f;
	wheel_y += dy * 0.5f;
	len = sqrtf (wheel_x * wheel_x + wheel_y * wheel_y);
	if (len > WHEEL_REACH)
	{
		wheel_x *= WHEEL_REACH / len;
		wheel_y *= WHEEL_REACH / len;
	}
	if (len > WHEEL_REACH * 0.3f)
		wheel_sel = Wheel_SlotAt (wheel_x, wheel_y);
	if (dx || dy)
		wheel_mouse_last = true;
}

// Called every frame: remembers the weapon before this one, for a tap.
void Wheel_Frame (void)
{
	int active = cl.stats[STAT_ACTIVEWEAPON];
	if (active != wheel_active)
	{
		wheel_previous = wheel_active;
		wheel_active = active;
	}
}

static void Wheel_Down_f (void)
{
	if (wheel_down)
		return;
	wheel_down = true;
	wheel_opened = realtime;
	wheel_sel = 0;
	wheel_x = wheel_y = 0;
	wheel_mouse_last = !IN_GamepadInUse ();
}

static void Wheel_Up_f (void)
{
	int slot = 0;

	if (!wheel_down)
		return;
	if (Wheel_Open ())
	{
		if (wheel_sel)
			slot = wheel_sel;
		else if (realtime - wheel_opened < WHEEL_TAP && wheel_previous)
			slot = Wheel_SlotOf (wheel_previous);
		if (slot && (cl.items & Sbar_FoundrySlotItem (slot)) && Sbar_FoundrySlotItem (slot) != cl.stats[STAT_ACTIVEWEAPON])
			Cbuf_AddText (va ("impulse %d\n", slot));
	}
	wheel_down = false;
}

// wheel_select N: points the open wheel at slot N, for binding keys to it.
static void Wheel_Select_f (void)
{
	int slot = atoi (Cmd_Argv (1));
	if (slot >= 1 && slot <= 8)
		wheel_sel = slot;
}

void Wheel_Init (void)
{
	Cmd_AddCommand ("wheel_select", Wheel_Select_f);
	Cmd_AddCommand ("+wheel", Wheel_Down_f);
	Cmd_AddCommand ("-wheel", Wheel_Up_f);
	Cvar_RegisterVariable (&wheel_slowmo);
}

// The ammo each slot uses: its stat, and its label on the HUD.
static void Wheel_Ammo (int slot, int *stat, const char **label)
{
	static const int		 stats[8] = {-1, STAT_SHELLS, STAT_NAILS, STAT_NAILS, STAT_ROCKETS, STAT_SHELLS, STAT_ROCKETS, STAT_CELLS};
	static const char *const labels[8] = {NULL, "lab_shells", "lab_slag", "lab_slag", "lab_iron", "lab_shells", "lab_iron", "lab_clappers"};
	*stat = stats[slot - 1];
	*label = labels[slot - 1];
}

static void Wheel_Pic (cb_context_t *cbx, const char *name, float cx, float cy, float k, float scale, float angle, float alpha)
{
	float	w, h;
	qpic_t *pic;

	if (!HudSvg_Size (name, &w, &h))
		return;
	pic = HudSvg_Pic (name, h * scale * k);
	if (!pic)
		return;
	if (angle)
		Draw_PicRotated (cbx, cx, cy, w * scale * k, h * scale * k, pic, 0.5f, 0.5f, angle, NULL, alpha);
	else
		Draw_SubPicLinearBlend (cbx, floorf (cx - pic->width / 2.0f + 0.5f), floorf (cy - pic->height / 2.0f + 0.5f), pic->width, pic->height, pic, 0, 0, 1, 1, NULL, alpha);
}

static void Wheel_Number (cb_context_t *cbx, const char *atlas, int value, float cx, float base, float k, float size)
{
	// The status bar's numerals: cells of 27 x 46 at size 54, baseline 41 down.
	char	str[16];
	int		i, len;
	qpic_t *pic = HudSvg_Pic (atlas, 46.0f * size / 54.0f * k);
	float	cw, x, y;

	if (!pic)
		return;
	len = q_snprintf (str, sizeof (str), "%d", value);
	cw = pic->width / 13.0f;
	x = floorf (cx - cw * len / 2 + 0.5f);
	y = floorf (base - pic->height * 41.0f / 46.0f + 0.5f);
	for (i = 0; i < len; i++, x += cw)
	{
		int	  d = str[i] == '-' ? 11 : str[i] - '0';
		float s0 = floorf (d * cw + 0.5f), s1 = floorf ((d + 1) * cw + 0.5f);
		Draw_SubPicLinearBlend (cbx, floorf (x + 0.5f), y, s1 - s0, pic->height, pic, s0 / pic->width, 0, (s1 - s0) / pic->width, 1, NULL, 1.0f);
	}
}

/*
================
Wheel_Draw
================
*/
void Wheel_Draw (cb_context_t *cbx)
{
	int		i;
	float	k, cx, cy, w, h;
	char	name[16];
	qpic_t *pic;

	if (!Wheel_Open ())
		return;
	k = q_min ((float)glheight / 720.0f, (float)glwidth / 1280.0f) * CLAMP (0.5f, hud_scale.value, 1.5f);
	cx = glwidth / 2.0f;
	cy = glheight / 2.0f - 10 * k;
	GL_SetCanvas (cbx, CANVAS_DEFAULT);

	if (HudSvg_Size ("vignette", &w, &h) && (pic = HudSvg_Pic ("vignette", 180)))
		Draw_SubPicLinearBlend (cbx, 0, 0, glwidth, glheight, pic, 0, 0, 1, 1, NULL, 1.0f);

	for (i = 0; i < 8; i++)
	{
		int		 slot = i + 1, item = Sbar_FoundrySlotItem (slot);
		qboolean owned = (cl.items & item) != 0, sel = slot == wheel_sel;
		float	 a = -M_PI / 2 + i * M_PI / 4;
		float	 rm = (WHEEL_R0 + WHEEL_R1) / 2 + (sel ? 11 : 4);
		float	 ix = cx + rm * cosf (a) * k, iy = cy + rm * sinf (a) * k;

		Wheel_Pic (cbx, sel ? "wedge_sel" : owned ? "wedge" : "wedge_empty", cx, cy, k, 1, i * M_PI / 4 + 0.0001f, 1);
		q_snprintf (name, sizeof (name), owned ? "w%d" : "w%d_dim", slot);
		Wheel_Pic (cbx, name, ix, iy - 4 * k, k, 0.76f, 0, 1);
		q_snprintf (name, sizeof (name), owned ? "wname%d" : "wname%d_dim", slot);
		Wheel_Pic (cbx, name, ix, iy + 30 * k, k, 1, 0, 1);
		Wheel_Number (
			cbx, sel ? "digits_hot" : "digits_dim", slot, cx + (WHEEL_R1 + 30) * cosf (a) * k, cy + ((WHEEL_R1 + 30) * sinf (a) + 6) * k, k, 15);
	}

	Wheel_Pic (cbx, "wheel_hub", cx, cy, k, 1, 0, 1);
	if (wheel_sel)
	{
		int			stat;
		const char *label;
		float		a = -M_PI / 2 + (wheel_sel - 1) * M_PI / 4;

		Wheel_Pic (cbx, va ("wtitle%d", wheel_sel), cx, cy - 28 * k, k, 1, 0, (cl.items & Sbar_FoundrySlotItem (wheel_sel)) ? 1 : 0.4f);
		Wheel_Ammo (wheel_sel, &stat, &label);
		if (label && HudSvg_Size (label, &w, &h))
		{
			float lx = cx - (w + 8 + 27 * 20 / 54.0f * 3) * k / 2;
			Wheel_Pic (cbx, label, lx + w * k / 2, cy - 1 * k, k, 1, 0, 1);
			Wheel_Number (cbx, "digits_hot", cl.stats[stat], lx + (w + 8 + 15) * k, cy + 4 * k, k, 20);
		}
		Wheel_Pic (cbx, va ("wdesc%d", wheel_sel), cx, cy + 40 * k, k, 1, 0, 1);
		Wheel_Pic (cbx, "wheel_pointer", cx + (WHEEL_R0 + 2) * cosf (a) * k, cy + (WHEEL_R0 + 2) * sinf (a) * k, k, 1, a + M_PI / 2, 1);
	}
	if (Wheel_TimeScale () < 1.0f)
		Wheel_Pic (cbx, "wheel_slow", cx, cy - (WHEEL_R1 + 60) * k, k, 1, 0, 1);
	Wheel_Pic (cbx, wheel_mouse_last ? "wheel_hint_kbm" : "wheel_hint_pad", cx, cy + (WHEEL_R1 + 62) * k, k, 1, 0, 1);
}
