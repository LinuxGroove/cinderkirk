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

// rumble.c -- named rumble patterns the game asks for. vkQuake rumbles the
// pad by how loud the sound is, so everything that makes a noise shakes it;
// Cinderkirk's game code instead sends "rumble <pattern>" to the player it
// happens to (each weapon's shot, a hit taken, the dash, a vent, a pickup),
// and only that plays. joy_rumble scales it as before, and joy_rumble_sound 1
// brings back the loudness rumble between patterns. Upstream could take the
// command and the table's format.

#include "quakedef.h"

static cvar_t joy_rumble_sound = {"joy_rumble_sound", "0", CVAR_ARCHIVE}; // 1: rumble with loud sounds too

typedef struct
{
	float low, high; // motor strengths, 0..1 (low: the heavy motor, high: the light one)
	int	  ms;
} rumble_step_t;

typedef struct
{
	const char	*name;
	rumble_step_t steps[4];
} rumble_pattern_t;

// Short and clear: a shot is a knock, a hit taken is heavier, nothing lasts.
static const rumble_pattern_t patterns[] = {
	{"pick", {{0.55f, 0.25f, 70}}},
	{"scattergun", {{0.85f, 0.45f, 80}, {0.35f, 0.10f, 70}}},
	{"steam", {{1.00f, 0.55f, 110}, {0.45f, 0.15f, 110}}},
	{"spitter", {{0.15f, 0.35f, 35}}},
	{"bolt", {{0.25f, 0.55f, 45}}},
	{"crucible", {{0.90f, 0.25f, 120}, {0.40f, 0.05f, 140}}},
	{"mortar", {{1.00f, 0.30f, 130}, {0.45f, 0.05f, 200}}},
	{"toll", {{0.35f, 0.60f, 110}}},
	{"dash", {{0.40f, 0.15f, 90}, {0.15f, 0.05f, 90}}},
	{"overpressure", {{0.90f, 0.85f, 160}, {0.30f, 0.20f, 120}}},
	{"vent", {{0.30f, 0.20f, 250}, {0.10f, 0.05f, 150}}},
	{"hurt", {{0.55f, 0.30f, 110}}},
	{"hurt_big", {{1.00f, 0.60f, 200}, {0.40f, 0.15f, 150}}},
	{"pickup", {{0.00f, 0.30f, 45}}},
	{"key", {{0.20f, 0.50f, 70}, {0.00f, 0.00f, 60}, {0.20f, 0.50f, 70}}},
	{"secret", {{0.10f, 0.40f, 80}, {0.00f, 0.00f, 80}, {0.10f, 0.40f, 80}, {0.00f, 0.00f, 80}}},
	{"land", {{0.45f, 0.10f, 60}}},
	{"death", {{0.90f, 0.30f, 250}, {0.40f, 0.10f, 300}}},
	{NULL}};

static rumble_step_t custom[1];
static const rumble_step_t *playing;
static int					playing_count;
static double				playing_start;

static void Rumble_f (void)
{
	const rumble_pattern_t *p;
	int						i;
	if (Cmd_Argc () == 4)
	{
		custom[0].low = CLAMP (0.f, atof (Cmd_Argv (1)), 1.f);
		custom[0].high = CLAMP (0.f, atof (Cmd_Argv (2)), 1.f);
		custom[0].ms = CLAMP (0, atoi (Cmd_Argv (3)), 2000);
		playing = custom;
		playing_count = 1;
		playing_start = realtime;
		return;
	}
	if (Cmd_Argc () != 2)
	{
		Con_Printf ("rumble <pattern> | rumble <low> <high> <ms>\npatterns:");
		for (p = patterns; p->name; p++)
			Con_Printf (" %s", p->name);
		Con_Printf ("\n");
		return;
	}
	for (p = patterns; p->name; p++)
		if (!q_strcasecmp (p->name, Cmd_Argv (1)))
		{
			for (i = 0; i < 4 && p->steps[i].ms; i++)
				;
			playing = p->steps;
			playing_count = i;
			playing_start = realtime;
			return;
		}
	Con_DPrintf ("rumble: no pattern %s\n", Cmd_Argv (1));
}

void Rumble_Init (void)
{
	Cvar_RegisterVariable (&joy_rumble_sound);
	Cmd_AddCommand ("rumble", Rumble_f);
}

/*
================
Rumble_Level

The motors' strengths now. Returns false when no pattern is playing and the
loudness rumble is off, so the caller stops the motors.
================
*/
qboolean Rumble_Level (float *low, float *high, qboolean *from_sound)
{
	*from_sound = false;
	if (playing)
	{
		double t = (realtime - playing_start) * 1000.0;
		int	   i;
		for (i = 0; i < playing_count; i++)
		{
			if (t < playing[i].ms)
			{
				*low = playing[i].low;
				*high = playing[i].high;
				return true;
			}
			t -= playing[i].ms;
		}
		playing = NULL;
	}
	*low = *high = 0.f;
	*from_sound = joy_rumble_sound.value != 0.f;
	return *from_sound;
}
