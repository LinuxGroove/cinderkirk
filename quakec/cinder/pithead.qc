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

/*QUAKED func_lift_mark (0 .5 .8) ? FOUNDRY CISTERNS OSSUARY UNDERVEIN
The mark over a shaft's cage: shown once every map down that shaft has been
finished with all its secrets, at any skill. The engine keeps those finishes
(records.txt) and says which shafts have earned it in _shaft_marks.
*/
void() func_lift_mark =
{
	if (deathmatch || !(cvar ("_shaft_marks") & self.spawnflags & 15))
	{
		remove (self);
		return;
	}
	self.solid = SOLID_BSP;
	self.movetype = MOVETYPE_PUSH;
	setmodel (self, self.model);
};

/*QUAKED misc_seal_trophy (0 .5 .8) (-16 -16 -24) (16 16 32) FOUNDRY CISTERNS OSSUARY UNDERVEIN
A Seal on the Pithead's shelf: shown, turning slowly, once its shaft is
beaten (the same spawnflag as the shaft's item_sigil), and gone until then.
*/
void() misc_seal_trophy =
{
	string m;

	if (deathmatch || !(serverflags & self.spawnflags & 15))
	{
		remove (self);
		return;
	}
	if (self.spawnflags & 1)
		m = "progs/end1.mdl";
	else if (self.spawnflags & 2)
		m = "progs/end2.mdl";
	else if (self.spawnflags & 4)
		m = "progs/end3.mdl";
	else
		m = "progs/end4.mdl";
	precache_model (m);
	setmodel (self, m);
	self.solid = SOLID_NOT;
	self.movetype = MOVETYPE_NOCLIP;
	self.avelocity = '0 30 0';
};
