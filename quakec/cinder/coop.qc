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

// Cinderkirk: Co-op Story for 2 to 4. More creatures on each skill (a copy
// of some of a map's creatures stands beside them, more of them the harder
// the skill), and players come in beside the start rather than on it.

void(...) callfunction = #605;

.float	coop_copy;		// a creature co-op added, which isn't copied again
float	coop_seen;		// creatures spawned so far, to pick which get a copy

// Somewhere clear for a body of this size, beside `at`, with floor under it
// and no slag or water: '0 0 0' if there's nowhere.
vector(vector at, vector mn, vector mx, float wide) Coop_Beside =
{
	local float i;
	local vector to;

	at = at + '0 0 8';		// clear of the floor it stands on
	for (i = 0; i < 8; i++)
	{
		to = at;
		if (i == 0) to_x = to_x + wide;
		else if (i == 1) to_x = to_x - wide;
		else if (i == 2) to_y = to_y + wide;
		else if (i == 3) to_y = to_y - wide;
		else if (i == 4) to = to + (wide * '1 1 0');
		else if (i == 5) to = to + (wide * '-1 1 0');
		else if (i == 6) to = to + (wide * '1 -1 0');
		else to = to + (wide * '-1 -1 0');

		tracebox (at, mn, mx, to, TRUE, self);
		if (trace_startsolid || trace_fraction < 1)
			continue;
		traceline (to, to - '0 0 96', TRUE, self);
		if (trace_fraction == 1)
			continue;
		if (pointcontents (trace_endpos + '0 0 4') != CONTENT_EMPTY)
			continue;
		return to;
	}
	return '0 0 0';
};

// Called by walkmonster_start and flymonster_start: in co-op, maybe put a
// second one of this creature beside it. Every third creature on Apprentice,
// every second on Journeyman, and every one on Master and Founder's.
void() Coop_Extra =
{
	local float every;
	local vector to;
	local entity e, was;

	if (!coop || deathmatch || self.coop_copy || self.health > 1000)
		return;
	coop_seen = coop_seen + 1;
	every = 3;
	if (skill >= 2)
		every = 1;
	else if (skill >= 1)
		every = 2;
	if (coop_seen - floor (coop_seen / every) * every != 0)
		return;

	to = Coop_Beside (self.origin, self.mins, self.maxs, self.maxs_x - self.mins_x + 16);
	if (to == '0 0 0')
		return;

	e = spawn ();
	e.classname = self.classname;
	e.origin = to;
	e.angles = self.angles;
	e.spawnflags = self.spawnflags;
	e.targetname = self.targetname;
	e.target = self.target;
	e.coop_copy = TRUE;
	setorigin (e, to);

	was = self;
	self = e;
	callfunction (e.classname);
	self = was;
};

// Where a co-op player comes in: beside the start if someone's on it.
vector(vector at) Coop_Spot =
{
	local entity p;
	local float i, busy;
	local vector to;

	for (i = 0; i < 4; i++)
	{
		if (i == 0)
			to = at;
		else
		{
			to = Coop_Beside (at, VEC_HULL_MIN, VEC_HULL_MAX, 48 * i);
			if (to == '0 0 0')
				continue;
		}
		busy = FALSE;
		p = find (world, classname, "player");
		while (p)
		{
			if (p != self && p.health > 0 && vlen (p.origin - to) < 48)
				busy = TRUE;
			p = find (p, classname, "player");
		}
		if (!busy)
			return to;
	}
	return at;
};
