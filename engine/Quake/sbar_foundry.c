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

// sbar_foundry.c -- Cinderkirk's status bar (scr_style 3): the full width of
// the screen in iron and brass, with armour and health on the left, the
// Pressure dial in the middle, ammo, keys and secrets on the right, and the
// eight weapons in a row above it. Every piece is an SVG from
// tools/hud_svg.py, drawn at the screen's own resolution.
//
// Positions are in the units of the mockup's 1280x720 screen (the bar is 72
// tall), measured from the left edge, the middle or the right edge.

#include "quakedef.h"
#include "hud_svg.h"

#define STAT_PRESSURE 32

// The numeral atlas (tools/hud_svg.py): cells of 27 x 46 at size 54, baseline 41 down.
#define HUD_DIGITS		  "0123456789/-:"
#define HUD_DIGIT_W		  27.0f
#define HUD_DIGIT_H		  46.0f
#define HUD_DIGIT_BASE	  41.0f
#define HUD_DIGIT_SIZE	  54.0f
#define HUD_DIAL_A0		  (M_PI * 1.08)
#define HUD_DIAL_A1		  (M_PI * 1.92)

extern cvar_t	 scr_viewsize;
extern qboolean sb_showscores;
void			 Sbar_DeathmatchOverlay (cb_context_t *cbx);
cvar_t		  hud_scale = {"hud_scale", "1", CVAR_ARCHIVE_GAME};

static float hud_k; // pixels per unit
static float hud_w, hud_h;

static float Left (float x)
{
	return x * hud_k;
}
static float Mid (float x)
{
	return hud_w / 2 + (x - 640) * hud_k;
}
static float Right (float x)
{
	return hud_w - (1280 - x) * hud_k;
}
static float Y (float y)
{
	return hud_h - (720 - y) * hud_k;
}

/*
================
Hud_Pic

Draws an SVG at (x, y) in pixels, scale times its own size.
================
*/
static void Hud_Pic (cb_context_t *cbx, const char *name, float x, float y, float scale, float alpha)
{
	float	w, h;
	qpic_t *pic;

	if (!HudSvg_Size (name, &w, &h))
		return;
	pic = HudSvg_Pic (name, h * scale * hud_k);
	if (pic)
		Draw_SubPicLinearBlend (cbx, floorf (x + 0.5f), floorf (y + 0.5f), pic->width, pic->height, pic, 0, 0, 1, 1, NULL, alpha);
}

/*
================
Hud_Number

Draws text of numerals (HUD_DIGITS) at size (54 is the big numbers) with
its baseline at y. align: 0 from x, 1 centred on x, 2 ending at x. Returns
the width in pixels.
================
*/
static float Hud_Number (cb_context_t *cbx, const char *atlas, const char *str, float x, float y, float size, int align)
{
	const int n = (int)strlen (HUD_DIGITS);
	float	  h = HUD_DIGIT_H * size / HUD_DIGIT_SIZE * hud_k;
	qpic_t	 *pic = HudSvg_Pic (atlas, h);
	float	  cw, width;
	int		  len = (int)strlen (str);

	if (!pic)
		return 0;
	cw = (float)pic->width / n;
	width = cw * len;
	if (align == 1)
		x -= width / 2;
	else if (align == 2)
		x -= width;
	x = floorf (x + 0.5f);
	y = floorf (y - pic->height * HUD_DIGIT_BASE / HUD_DIGIT_H + 0.5f);
	for (; *str; str++, x += cw)
	{
		const char *c = strchr (HUD_DIGITS, *str);
		if (!c || !*str)
			continue;
		int	  i = (int)(c - HUD_DIGITS);
		float s0 = floorf (i * cw + 0.5f), s1 = floorf ((i + 1) * cw + 0.5f);
		Draw_SubPicLinearBlend (cbx, floorf (x + 0.5f), y, s1 - s0, pic->height, pic, s0 / pic->width, 0, (s1 - s0) / pic->width, 1, NULL, 1.0f);
	}
	return width;
}

static float Hud_Int (cb_context_t *cbx, const char *atlas, int value, float x, float y, float size, int align)
{
	char str[16];
	q_snprintf (str, sizeof (str), "%d", value);
	return Hud_Number (cbx, atlas, str, x, y, size, align);
}

/*
================
Sbar_FoundryScale

Pixels per unit: the bar is a tenth of a 16:9 screen's height, kept to the
mockup's 1280 units across on narrower screens, times hud_scale.
================
*/
static float Sbar_FoundryScale (void)
{
	float k = q_min ((float)glheight / 720.0f, (float)glwidth / 1280.0f);
	return k * CLAMP (0.5f, hud_scale.value, 1.5f);
}

float Sbar_FoundryHeight (void)
{
	if (scr_viewsize.value >= 120.0f || cl.intermission)
		return 0;
	return 88.0f * Sbar_FoundryScale ();
}

// Weapons in slot order (game-ideas idea 25): the item bit each slot uses.
static const int foundry_slots[8] = {IT_AXE, IT_SHOTGUN, IT_NAILGUN, IT_SUPER_NAILGUN, IT_GRENADE_LAUNCHER, IT_SUPER_SHOTGUN, IT_ROCKET_LAUNCHER, IT_LIGHTNING};

int Sbar_FoundrySlotItem (int slot)
{
	return (slot >= 1 && slot <= 8) ? foundry_slots[slot - 1] : 0;
}

static void Sbar_FoundryAmmo (const char **icon, const char **label, int *count)
{
	*icon = *label = NULL;
	*count = cl.stats[STAT_AMMO];
	if (cl.items & IT_SHELLS)
		*icon = "ammo_shells", *label = "lab_shells";
	else if (cl.items & IT_NAILS)
		*icon = "ammo_slag", *label = "lab_slag";
	else if (cl.items & IT_ROCKETS)
		*icon = "ammo_iron", *label = "lab_iron";
	else if (cl.items & IT_CELLS)
		*icon = "ammo_clappers", *label = "lab_clappers";
}

static void Sbar_FoundryDial (cb_context_t *cbx)
{
	float p = CLAMP (0.0f, cl.statsf[STAT_PRESSURE], 100.0f);
	float a = HUD_DIAL_A0 + (HUD_DIAL_A1 - HUD_DIAL_A0) * p / 100.0f;
	float cx = Mid (640), cy = Y (690);
	float w, h;

	// In the red the rim glows, slowly, so it never flashes.
	if (p >= 75.0f && HudSvg_Size ("dial_hot", &w, &h))
	{
		float	glow = (p - 75.0f) / 25.0f * (0.75f + 0.25f * sinf (realtime * 3.0f));
		qpic_t *pic = HudSvg_Pic ("dial_hot", h * hud_k);
		if (pic)
			Draw_SubPicLinearBlend (cbx, cx - pic->width / 2.0f, cy - pic->height / 2.0f, pic->width, pic->height, pic, 0, 0, 1, 1, NULL, glow);
	}
	if (HudSvg_Size ("needle", &w, &h))
	{
		qpic_t *pic = HudSvg_Pic ("needle", h * hud_k);
		if (pic)
			Draw_PicRotated (cbx, cx, cy, w * hud_k, h * hud_k, pic, 6.0f / w, 0.5f, a, NULL, 1.0f);
	}
	Hud_Pic (cbx, "dial_cap", cx - 7 * hud_k, cy - 7 * hud_k, 1, 1);
}

static void Sbar_FoundryWeapons (cb_context_t *cbx)
{
	int i;

	for (i = 0; i < 8; i++)
	{
		int		 it = foundry_slots[i];
		qboolean cur = cl.stats[STAT_ACTIVEWEAPON] == it;
		float	 x = Right (836 + i * 54), y = Y (608);
		char	 num[4], icon[16];

		Hud_Pic (cbx, cur ? "slot_cur" : "slot", x - hud_k, y - hud_k, 1, 1);
		q_snprintf (num, sizeof (num), "%d", i + 1);
		Hud_Number (cbx, cur ? "digits" : "digits_dim", num, x + 3 * hud_k, y + 11 * hud_k, 12, 0);
		if (cl.items & it)
		{
			q_snprintf (icon, sizeof (icon), cur ? "w%d" : "w%d_dim", i + 1);
			Hud_Pic (cbx, icon, x + 10 * hud_k, y + (4 - 2 * 0.38f) * hud_k, 0.38f, 1);
		}
	}
}

// Tab in single player: kills, secrets and the time, above the dial.
static void Sbar_FoundryScores (cb_context_t *cbx)
{
	char  str[32];
	float x = Mid (640), y = Y (546);
	int	  t = (int)cl.time;

	Draw_Fill (cbx, x - 260 * hud_k, y - 6 * hud_k, 520 * hud_k, 56 * hud_k, 0, 0.6f);
	Hud_Pic (cbx, "lab_kills", x - 240 * hud_k, y, 1, 1);
	q_snprintf (str, sizeof (str), "%d/%d", cl.stats[STAT_MONSTERS], cl.stats[STAT_TOTALMONSTERS]);
	Hud_Number (cbx, "digits", str, x - 240 * hud_k, y + 42 * hud_k, 30, 0);
	Hud_Pic (cbx, "lab_secrets", x - 60 * hud_k, y, 1, 1);
	q_snprintf (str, sizeof (str), "%d/%d", cl.stats[STAT_SECRETS], cl.stats[STAT_TOTALSECRETS]);
	Hud_Number (cbx, "digits", str, x - 60 * hud_k, y + 42 * hud_k, 30, 0);
	Hud_Pic (cbx, "lab_time", x + 120 * hud_k, y, 1, 1);
	q_snprintf (str, sizeof (str), "%d:%02d", t / 60, t % 60);
	Hud_Number (cbx, "digits", str, x + 120 * hud_k, y + 42 * hud_k, 30, 0);
}

/*
================
Sbar_DrawFoundry
================
*/
void Sbar_DrawFoundry (cb_context_t *cbx)
{
	float		w, h, x;
	const char *icon, *label;
	int			count;
	char		str[16];
	float		bar_alpha = 1.0f;

	if (scr_viewsize.value >= 120.0f)
		return;
	hud_k = Sbar_FoundryScale ();
	hud_w = glwidth;
	hud_h = glheight;
	GL_SetCanvas (cbx, CANVAS_DEFAULT);

	if (cl.gametype == GAME_DEATHMATCH && (sb_showscores || cl.stats[STAT_HEALTH] <= 0))
		Sbar_DeathmatchOverlay (cbx);
	GL_SetCanvas (cbx, CANVAS_DEFAULT);

	// The bar, stretched across, and the dial's housing in the middle.
	if (HudSvg_Size ("bar", &w, &h))
	{
		qpic_t *pic = HudSvg_Pic ("bar", h * hud_k);
		if (pic)
			Draw_SubPicLinearBlend (cbx, 0, floorf (Y (640) + 0.5f), hud_w, pic->height, pic, 0, 0, 1, 1, NULL, bar_alpha);
	}
	for (x = 14; Left (x) < Mid (440) - 12 * hud_k; x += 37)
		Hud_Pic (cbx, "rivet", Left (x - 3), Y (649), 1, 1);
	for (x = 1270; Right (x) > Mid (840) + 12 * hud_k; x -= 37)
		Hud_Pic (cbx, "rivet", Right (x - 3), Y (649), 1, 1);
	Hud_Pic (cbx, "housing", Mid (440), Y (620), 1, 1);
	Hud_Pic (cbx, "divider", Left (232), Y (664), 1, 1);
	Hud_Pic (cbx, "divider", Right (1042), Y (664), 1, 1);
	Hud_Pic (cbx, "divider", Right (1166), Y (664), 1, 1);

	// Armour and health.
	Hud_Pic (cbx, "lab_armour", Left (94), Y (659), 1, 1);
	Hud_Pic (cbx, "armour", Left (29), Y (663), 1, cl.stats[STAT_ARMOR] > 0 ? 1 : 0.3f);
	Hud_Int (cbx, cl.stats[STAT_ARMOR] > 0 ? "digits" : "digits_dim", cl.stats[STAT_ARMOR], Left (92), Y (712), 54, 0);
	Hud_Pic (cbx, "lab_health", Left (326), Y (659), 1, 1);
	Hud_Pic (cbx, "health", Left (260), Y (657), 1, 1);
	Hud_Int (cbx, cl.stats[STAT_HEALTH] <= 25 ? "digits_hot" : "digits", cl.stats[STAT_HEALTH], Left (324), Y (712), 54, 0);

	Sbar_FoundryDial (cbx);

	// Ammo for the weapon in hand.
	Sbar_FoundryAmmo (&icon, &label, &count);
	if (icon)
	{
		Hud_Pic (cbx, label, Right (896), Y (659), 1, 1);
		Hud_Pic (cbx, icon, Right (838), Y (663), 1, 1);
		Hud_Int (cbx, (cl.items & IT_NAILS) || count <= 5 ? "digits_hot" : "digits", count, Right (894), Y (712), 54, 0);
	}

	// Keys, then secrets (or frags in Pit fights).
	Hud_Pic (cbx, "lab_keys", Right (1062), Y (659), 1, 1);
	Hud_Pic (cbx, (cl.items & IT_KEY1) ? "key1" : "key1_dim", Right (1060), Y (674), 0.82f, 1);
	Hud_Pic (cbx, (cl.items & IT_KEY2) ? "key2" : "key2_dim", Right (1112), Y (674), 0.82f, 1);
	if (cl.gametype == GAME_DEATHMATCH)
	{
		Hud_Pic (cbx, "lab_frags", Right (1182), Y (659), 1, 1);
		Hud_Int (cbx, "digits", cl.scores[cl.viewentity - 1].frags, Right (1182), Y (712), 42, 0);
	}
	else
	{
		Hud_Pic (cbx, "lab_secrets", Right (1182), Y (659), 1, 1);
		q_snprintf (str, sizeof (str), "%d/%d", cl.stats[STAT_SECRETS], cl.stats[STAT_TOTALSECRETS]);
		Hud_Number (cbx, "digits", str, Right (1182), Y (712), 42, 0);
	}

	if (scr_viewsize.value < 110.0f)
		Sbar_FoundryWeapons (cbx);
	if (cl.gametype != GAME_DEATHMATCH && sb_showscores)
		Sbar_FoundryScores (cbx);
}
