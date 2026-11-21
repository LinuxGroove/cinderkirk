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

// records.c -- Cinderkirk: each map's best finish per skill (time, kills,
// secrets), kept in records.txt in the write root and shown at the end of a
// map, and the marks on the Pithead's cages for shafts whose every map was
// finished with all its secrets (the _shaft_marks cvar, which the game reads).

#include "quakedef.h"

#define MAX_RECORDS 256

typedef struct
{
	char map[32];
	int	 skill;
	int	 time;		// seconds, the fastest
	int	 kills;		// the most
	int	 secrets;	// the most
	int	 all;		// finished at least once with every secret
} record_t;

static record_t records[MAX_RECORDS];
static int		num_records;
static qboolean loaded;

// What the end of the map just now beat, for the intermission to say so.
static struct
{
	record_t before;
	qboolean had;
	qboolean valid;
} last;

cvar_t shaft_marks = {"_shaft_marks", "0", CVAR_ROM};

static const char *shafts[] = {"foundry", "cisterns", "kilns", "vein"};

static const char *Records_Path (void)
{
	return va ("%s/records.txt", COM_GetWriteRoot ());
}

static record_t *Records_Find (const char *map, int skill, qboolean create)
{
	for (int i = 0; i < num_records; i++)
		if (records[i].skill == skill && !strcmp (records[i].map, map))
			return &records[i];
	if (!create || num_records == MAX_RECORDS)
		return NULL;
	record_t *r = &records[num_records++];
	memset (r, 0, sizeof (*r));
	q_strlcpy (r->map, map, sizeof (r->map));
	r->skill = skill;
	return r;
}

// A shaft's mark: each of its five maps finished with every secret, at any skill.
static void Records_UpdateMarks (void)
{
	int marks = 0;
	for (int s = 0; s < 4; s++)
	{
		qboolean all = true;
		for (int m = 1; m <= 5 && all; m++)
		{
			const char *map = va ("%s%d", shafts[s], m);
			qboolean got = false;
			for (int i = 0; i < num_records; i++)
				if (records[i].all && !strcmp (records[i].map, map))
					got = true;
			all = got;
		}
		if (all)
			marks |= 1 << s;
	}
	Cvar_SetROM ("_shaft_marks", va ("%d", marks));
}

static void Records_Load (void)
{
	FILE *f;
	char  line[256];

	loaded = true;
	num_records = 0;
	f = Sys_fopen (Records_Path (), "r");
	if (f)
	{
		while (fgets (line, sizeof (line), f) && num_records < MAX_RECORDS)
		{
			record_t r;
			memset (&r, 0, sizeof (r));
			if (sscanf (line, "%31s %d %d %d %d %d", r.map, &r.skill, &r.time, &r.kills, &r.secrets, &r.all) == 6)
				records[num_records++] = r;
		}
		fclose (f);
	}
	Records_UpdateMarks ();
}

static void Records_Save (void)
{
	FILE *f = Sys_fopen (Records_Path (), "w");
	if (!f)
	{
		Con_Printf ("Couldn't write %s\n", Records_Path ());
		return;
	}
	for (int i = 0; i < num_records; i++)
		fprintf (
			f, "%s %d %d %d %d %d\n", records[i].map, records[i].skill, records[i].time, records[i].kills, records[i].secrets, records[i].all);
	fclose (f);
}

/*
==================
Records_Finish

The local player reached the end of a Story map: keep anything it beat.
==================
*/
void Records_Finish (void)
{
	char map[32];

	last.valid = false;
	if (cl.gametype == GAME_DEATHMATCH || !cl.worldmodel || cls.demoplayback)
		return;
	if (!loaded)
		Records_Load ();
	COM_StripExtension (COM_SkipPath (cl.worldmodel->name), map, sizeof (map));
	if (!strncmp (map, "pit", 3))
		return;

	int		  sk = CLAMP (0, (int)(skill.value + 0.5f), 3);
	record_t *r = Records_Find (map, sk, false);
	last.had = r != NULL;
	if (r)
		last.before = *r;
	else
		r = Records_Find (map, sk, true);
	if (!r)
		return;
	last.valid = true;

	int time = cl.completed_time;
	if (!last.had || time < r->time)
		r->time = time;
	r->kills = q_max (r->kills, cl.stats[STAT_MONSTERS]);
	r->secrets = q_max (r->secrets, cl.stats[STAT_SECRETS]);
	if (cl.stats[STAT_SECRETS] >= cl.stats[STAT_TOTALSECRETS])
		r->all = 1;
	Records_Save ();
	Records_UpdateMarks ();
}

/*
==================
Records_Line

What to say under the end of a map's numbers: a new best, or the best to beat.
==================
*/
const char *Records_Line (void)
{
	if (!last.valid)
		return NULL;
	if (!last.had)
		return "Your first finish at this skill";
	int time = cl.completed_time;
	if (time < last.before.time)
		return va ("A new best time! It was %d:%02d", last.before.time / 60, last.before.time % 60);
	return va ("Best: %d:%02d  %d kills  %d secrets", last.before.time / 60, last.before.time % 60, last.before.kills, last.before.secrets);
}

void Records_Init (void)
{
	Cvar_RegisterVariable (&shaft_marks);
	Records_Load ();
}
