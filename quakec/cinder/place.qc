/*  Copyright (C) The LinuxGroove team
    SPDX-License-Identifier: GPL-2.0-or-later

    Cinderkirk: things placed a little into a wall or a ledge are moved to
    the nearest free spot instead of being dropped. Quake removed an item
    whose box started inside a brush ("fell out of level") and left a
    creature stuck where it stood; a key on a bier went that way once, and
    the level couldn't be finished. tools/spawncheck.py lists what's left.
*/

// Tries self at base + off: true (and left there) if it drops to a floor
// no lower than one step below base and, for creatures, can stand there.
float(vector base, vector off, float creature) Place_Try =
{
	setorigin (self, base + off);
	if (!droptofloor ())
		return FALSE;
	if (self.origin_z < base_z - 24)
		return FALSE;
	if (creature && !walkmove (0, 0))
		return FALSE;
	return TRUE;
};

// Looks round base in growing rings, first lifting it out of a floor or a
// bier top, then sideways. Leaves self at base and returns false if
// nothing nearby is free.
float(vector base, float creature) Place_Nudge =
{
	local float r, a, lift;
	local vector off;

	for (lift = 0; lift <= 32; lift = lift + 16)
		if (Place_Try (base, [0, 0, lift], creature))
			return TRUE;
	for (r = 8; r <= 96; r = r + 8)
		for (a = 0; a < 360; a = a + 45)
			for (lift = 0; lift <= 32; lift = lift + 16)
			{
				makevectors ([0, a, 0]);
				off = v_forward * r + [0, 0, lift];
				if (Place_Try (base, off, creature))
					return TRUE;
			}
	setorigin (self, base);
	return FALSE;
};
