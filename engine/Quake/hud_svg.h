/*
Copyright (C) The LinuxGroove team

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
*/

#ifndef HUD_SVG_H
#define HUD_SVG_H

// Cinderkirk's HUD: SVG pictures rasterised at the size they're drawn
// (hud_svg.c), the Foundry status bar (sbar_foundry.c) and the weapon wheel
// (wheel.c).

qpic_t	*HudSvg_Pic (const char *name, float height);
qboolean HudSvg_Size (const char *name, float *width, float *height);
void	 HudSvg_Flush (void);

void  Sbar_DrawFoundry (cb_context_t *cbx);
float Sbar_FoundryHeight (void); // pixels the bar covers at the bottom, 0 when hidden

void		Glyph_Init (void);
const char *Glyph_Set (void);
const char *Glyph_Name (int key);
int			Glyph_KeyFor (const char *command);
float		Glyph_Text (cb_context_t *cbx, float x, float y, float size, const char *text, int len);

void  Wheel_Init (void);
void  Wheel_Draw (cb_context_t *cbx);
qboolean Wheel_Open (void);
void  Wheel_Stick (float x, float y);
void  Wheel_Mouse (float dx, float dy);
float Wheel_TimeScale (void);
void  Wheel_Frame (void);

#endif
