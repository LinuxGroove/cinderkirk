/*  Copyright (C) The LinuxGroove team. GPL-2.0-or-later.

	The Pithead, the hub: the lift lever's notches set the skill, and each
	shaft's cage takes you down to its first map.
*/

string(float s) Pithead_SkillName =
{
	if (s <= 0)
		return "Apprentice";
	if (s == 1)
		return "Journeyman";
	if (s == 2)
		return "Master";
	return "Founder's";
};

/*QUAKED target_skill (.5 .5 .5) (-8 -8 -8) (8 8 8)
A notch of the lift lever: when used, sets the skill to "cnt" (0 Apprentice,
1 Journeyman, 2 Master, 3 Founder's) and says so.
*/
void() target_skill_use =
{
	cvar_set ("skill", ftos (self.cnt));
	if (activator.classname == "player")
	{
		centerprint (activator, Pithead_SkillName (self.cnt));
		Rumble (activator, "key");
	}
};

void() target_skill =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	self.use = target_skill_use;
};
