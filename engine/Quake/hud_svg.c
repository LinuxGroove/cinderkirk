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

// hud_svg.c -- Cinderkirk: the HUD's SVG pictures (gfx/hud/<name>.svg),
// rasterised by nanosvg at the size they're drawn, so the status bar and the
// weapon wheel stay sharp at any resolution. Each picture is parsed once and
// rasterised again only when the size it's drawn at changes.

#include "quakedef.h"

#define NANOSVG_IMPLEMENTATION
#define NANOSVGRAST_IMPLEMENTATION
#ifdef __GNUC__
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#pragma GCC diagnostic ignored "-Wsign-compare"
#endif
#include "nanosvg/nanosvg.h"
#include "nanosvg/nanosvgrast.h"
#ifdef __GNUC__
#pragma GCC diagnostic pop
#endif

#include "hud_svg.h"

#define MAX_HUD_SVG	  256
#define MAX_HUD_SIZES 3

typedef struct
{
	int		height;
	qpic_t *pic;
} hud_size_t;

typedef struct
{
	char		name[32];
	NSVGimage  *image; // NULL when the file is missing
	hud_size_t	sizes[MAX_HUD_SIZES];
	int			next; // the size slot to reuse next
} hud_svg_t;

static hud_svg_t	   hud_svgs[MAX_HUD_SVG];
static int			   hud_numsvgs;
static NSVGrasterizer *hud_rast;
static int			   hud_serial;

static hud_svg_t *HudSvg_Find (const char *name)
{
	int	  i;
	char  path[MAX_QPATH];
	byte *data;

	for (i = 0; i < hud_numsvgs; i++)
		if (!strcmp (hud_svgs[i].name, name))
			return &hud_svgs[i];
	if (hud_numsvgs == MAX_HUD_SVG)
		return NULL;

	hud_svg_t *svg = &hud_svgs[hud_numsvgs++];
	memset (svg, 0, sizeof (*svg));
	q_strlcpy (svg->name, name, sizeof (svg->name));
	q_snprintf (path, sizeof (path), "gfx/hud/%s.svg", name);
	data = COM_LoadFile (path, NULL); // ends in a 0
	if (data)
	{
		svg->image = nsvgParse ((char *)data, "px", 96.0f);
		Mem_Free (data);
		if (svg->image && (svg->image->width <= 0 || svg->image->height <= 0))
		{
			nsvgDelete (svg->image);
			svg->image = NULL;
		}
	}
	if (!svg->image)
		Con_Warning ("HUD picture %s is missing\n", path);
	return svg;
}

/*
================
HudSvg_Size

The SVG's own width and height (in the mockup's units), or 0 if missing.
================
*/
qboolean HudSvg_Size (const char *name, float *width, float *height)
{
	hud_svg_t *svg = HudSvg_Find (name);
	if (!svg || !svg->image)
	{
		*width = *height = 0;
		return false;
	}
	*width = svg->image->width;
	*height = svg->image->height;
	return true;
}

/*
================
HudSvg_Pic

The picture rasterised height pixels high (and as wide as its shape), or
NULL if there's no such SVG. The qpic's width and height are in pixels.
================
*/
qpic_t *HudSvg_Pic (const char *name, float height)
{
	int		   i, w, h;
	hud_svg_t *svg = HudSvg_Find (name);
	byte	  *pixels;
	char	   texname[64];

	if (!svg || !svg->image)
		return NULL;
	h = (int)ceilf (q_max (height, 1.0f));
	h = q_min (h, 4096);
	for (i = 0; i < MAX_HUD_SIZES; i++)
		if (svg->sizes[i].pic && svg->sizes[i].height == h)
			return svg->sizes[i].pic;

	float scale = h / svg->image->height;
	w = (int)ceilf (svg->image->width * scale);
	w = CLAMP (1, w, 4096);
	if (!hud_rast)
		hud_rast = nsvgCreateRasterizer ();
	pixels = (byte *)Mem_Alloc ((size_t)w * h * 4);
	nsvgRasterize (hud_rast, svg->image, 0, 0, scale, pixels, w, h, w * 4);

	hud_size_t *slot = &svg->sizes[svg->next];
	svg->next = (svg->next + 1) % MAX_HUD_SIZES;
	Draw_FreePic (slot->pic);
	q_snprintf (texname, sizeof (texname), "hud:%s:%d", svg->name, ++hud_serial);
	slot->pic = Draw_PicFromRGBA (texname, w, h, pixels);
	slot->height = h;
	Mem_Free (pixels);
	return slot->pic;
}

/*
================
HudSvg_Flush

Forgets every SVG and its pictures (after a change of game folder).
================
*/
void HudSvg_Flush (void)
{
	int i, j;

	for (i = 0; i < hud_numsvgs; i++)
	{
		for (j = 0; j < MAX_HUD_SIZES; j++)
			Draw_FreePic (hud_svgs[i].sizes[j].pic);
		if (hud_svgs[i].image)
			nsvgDelete (hud_svgs[i].image);
	}
	hud_numsvgs = 0;
}
