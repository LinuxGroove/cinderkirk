/*  Copyright (C) The LinuxGroove team. GPL-2.0-or-later.

	Rumble: asks the engine to play one of its named patterns (rumble.c) on
	this player's pad. Only real clients get it; the pattern is the client's
	own, so in co-op each player feels only their own shots and hits.
*/

void(entity p, string pattern) Rumble =
{
	if (!(p.flags & FL_CLIENT))
		return;
	stuffcmd (p, "rumble ");
	stuffcmd (p, pattern);
	stuffcmd (p, "\n");
};
