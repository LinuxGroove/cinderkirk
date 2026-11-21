/*
	Cinderkirk's arsenal on top of the inherited weapon code: the slots,
	cycling through them, and each weapon's Overpressure shot (LT, the right
	mouse button), which spends Pressure.

	Slots (game-ideas idea 25): 1 Pick (IT_AXE), 2 Scattergun (IT_SHOTGUN),
	3 Spitter (IT_NAILGUN), 4 Bolt Caster (IT_SUPER_NAILGUN), 5 Crucible
	(IT_GRENADE_LAUNCHER), 6 Steam Cannon (IT_SUPER_SHOTGUN), 7 Shot Mortar
	(IT_ROCKET_LAUNCHER), 8 Tolling Iron (IT_LIGHTNING). The vertical slice has
	the first three of their own; the rest still fire as their stand-ins.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

#define OP_PICK_COST		34
#define OP_SCATTER_COST		34
#define OP_SPITTER_COST		40

void() player_axe1;
void() player_shot1;

// The item bit in a slot, 1 to 8.
float(float slot) W_SlotItem =
{
	switch (slot)
	{
		case 1: return IT_AXE;
		case 2: return IT_SHOTGUN;
		case 3: return IT_NAILGUN;
		case 4: return IT_SUPER_NAILGUN;
		case 5: return IT_GRENADE_LAUNCHER;
		case 6: return IT_SUPER_SHOTGUN;
		case 7: return IT_ROCKET_LAUNCHER;
		case 8: return IT_LIGHTNING;
	}
	return 0;
};

float(float it) W_ItemSlot =
{
	local float slot;

	for (slot = 1; slot <= 8; slot++)
		if (W_SlotItem (slot) == it)
			return slot;
	return 1;
};

// TRUE when the player has enough ammo to fire what's in the slot.
float(float slot) W_SlotHasAmmo =
{
	switch (W_SlotItem (slot))
	{
		case IT_AXE: return TRUE;
		case IT_SHOTGUN: return self.ammo_shells >= 1;
		case IT_SUPER_SHOTGUN: return self.ammo_shells >= 2;
		case IT_NAILGUN: return self.ammo_nails >= 1;
		case IT_SUPER_NAILGUN: return self.ammo_nails >= 2;
		case IT_GRENADE_LAUNCHER: return self.ammo_rockets >= 1;
		case IT_ROCKET_LAUNCHER: return self.ammo_rockets >= 1;
		case IT_LIGHTNING: return self.ammo_cells >= 1;
	}
	return FALSE;
};

// Steps through the slots one way (1 forward, -1 back) to the next weapon
// that's owned and loaded.
void(float step) W_CycleSlots =
{
	local float slot, tries;

	self.impulse = 0;
	slot = W_ItemSlot (self.weapon);
	for (tries = 0; tries < 8; tries++)
	{
		slot = slot + step;
		if (slot > 8)
			slot = 1;
		if (slot < 1)
			slot = 8;
		if ((self.items & W_SlotItem (slot)) && W_SlotHasAmmo (slot))
		{
			self.weapon = W_SlotItem (slot);
			W_SetCurrentAmmo ();
			return;
		}
	}
};

void(vector org, float count) W_SlagBurst =
{
	particle (org, '0 0 30', 234, count);
};

/*
	The Pick's Overpressure: a steam-driven blow that staggers whatever it
	hits and splits cracked stone.
*/
void() W_OverpressurePick =
{
	local vector source, org;

	if (!Pressure_Spend (self, OP_PICK_COST))
		return;
	player_axe1 ();
	self.attack_finished = time + 0.8;
	makevectors (self.v_angle);
	source = self.origin + '0 0 22';
	sound (self, CHAN_WEAPON, "cinder/dash.wav", 1, ATTN_NORM);
	traceline (source, source + v_forward * 80, FALSE, self);
	if (trace_fraction == 1.0)
		return;
	org = trace_endpos - v_forward * 4;
	Pressure_Steam (org, v_forward * -80, 20);

	if (trace_ent.classname == "func_cracked")
	{
		trace_ent.th_die ();
		return;
	}
	if (trace_ent.takedamage)
	{
		SpawnBlood (org, '0 0 0', 40);
		trace_ent.deathtype = "axe";
		T_Damage (trace_ent, self, self, 80);
		if ((trace_ent.flags & FL_MONSTER) && trace_ent.health > 0 && trace_ent.size_z < 80)	// not the big hull
		{
			trace_ent.velocity = v_forward * 420 + '0 0 180';
			trace_ent.flags = trace_ent.flags - (trace_ent.flags & FL_ONGROUND);
		}
	}
	else
		sound (self, CHAN_AUTO, "player/axhit2.wav", 1, ATTN_NORM);
};

/*
	The Scattergun's Overpressure: a heated slug that goes straight through
	a line of creatures, up to four.
*/
void() W_OverpressureScatter =
{
	local vector src, dir, end;
	local entity ignore;
	local float hits, step;

	if (self.ammo_shells < 1)
	{
		sound (self, CHAN_ITEM, "cinder/empty.wav", 0.6, ATTN_NORM);
		return;
	}
	if (!Pressure_Spend (self, OP_SCATTER_COST))
		return;
	player_shot1 ();
	self.attack_finished = time + 0.9;
	if (!deathmatch_unlimited_ammo ())
		self.currentammo = self.ammo_shells = self.ammo_shells - 1;
	sound (self, CHAN_WEAPON, "weapons/guncock.wav", 1, ATTN_NORM);
	sound (self, CHAN_AUTO, "cinder/vent.wav", 0.7, ATTN_NORM);

	makevectors (self.v_angle);
	dir = aim (self, 100000);
	src = self.origin + v_forward * 10 + '0 0 22';
	ignore = self;
	for (hits = 0; hits < 4; hits++)
	{
		traceline (src, src + dir * 4096, FALSE, ignore);
		end = trace_endpos;
		for (step = 32; step < vlen (end - src); step = step + 48)
			particle (src + dir * step, '0 0 0', 234, 2);
		if (trace_fraction == 1.0 || !trace_ent.takedamage)
		{
			W_SlagBurst (end - dir * 4, 12);
			return;
		}
		SpawnBlood (end, dir * 40, 50);
		trace_ent.deathtype = "shotgun";
		T_Damage (trace_ent, self, self, 50);
		ignore = trace_ent;
		src = end;
	}
};

/*
	A patch of burning slag left on the floor: it hurts what stands in it
	for a few seconds, then cools.
*/
void() slag_burn_think =
{
	local entity e;

	if (time > self.attack_finished)
	{
		remove (self);
		return;
	}
	particle (self.origin + [crandom () * 24, crandom () * 24, 2], '0 0 40', 234, 3);
	if (time >= self.pain_finished)
	{
		self.pain_finished = time + 0.4;
		for (e = findradius (self.origin, 48); e; e = e.chain)
			if (e.takedamage && e.health > 0 && e != self.owner)
			{
				e.deathtype = "slag";
				T_Damage (e, self, self.owner, 4);
			}
	}
	self.nextthink = time + 0.1;
};

void(vector org) W_SlagPool =
{
	local entity pool;

	pool = spawn ();
	pool.classname = "slag_pool";
	pool.owner = self.owner;
	setorigin (pool, org);
	pool.attack_finished = time + 4;
	pool.think = slag_burn_think;
	pool.nextthink = time + 0.05;
};

void() slag_gout_touch =
{
	if (other == self.owner || other.solid == SOLID_TRIGGER)
		return;
	if (pointcontents (self.origin) == CONTENT_SKY)
	{
		remove (self);
		return;
	}
	if (other.takedamage)
	{
		other.deathtype = "slag";
		T_Damage (other, self, self.owner, 30);
	}
	T_RadiusDamage (self, self.owner, 30, other, "slag");
	sound (self, CHAN_WEAPON, "cinder/scald.wav", 1, ATTN_NORM);
	W_SlagBurst (self.origin, 40);
	traceline (self.origin, self.origin - '0 0 128', TRUE, self);
	W_SlagPool (trace_endpos + '0 0 4');
	remove (self);
};

/*
	The Spitter's Overpressure: a gout of slag that bursts where it lands and
	leaves the floor burning.
*/
void() W_OverpressureSpitter =
{
	local vector dir;

	if (self.ammo_nails < 5)
	{
		sound (self, CHAN_ITEM, "cinder/empty.wav", 0.6, ATTN_NORM);
		return;
	}
	if (!Pressure_Spend (self, OP_SPITTER_COST))
		return;
	self.attack_finished = time + 0.7;
	if (!deathmatch_unlimited_ammo ())
		self.currentammo = self.ammo_nails = self.ammo_nails - 5;
	sound (self, CHAN_WEAPON, "cinder/vent.wav", 1, ATTN_NORM);

	makevectors (self.v_angle);
	dir = aim (self, 1000);
	newmis = spawn ();
	newmis.owner = self;
	newmis.movetype = MOVETYPE_TOSS;
	newmis.solid = SOLID_BBOX;
	newmis.classname = "slag_gout";
	newmis.touch = slag_gout_touch;
	newmis.think = SUB_Remove;
	newmis.nextthink = time + 5;
	setmodel (newmis, "progs/lavaball.mdl");
	setsize (newmis, VEC_ORIGIN, VEC_ORIGIN);
	setorigin (newmis, self.origin + v_forward * 8 + '0 0 16');
	newmis.velocity = dir * 800 + '0 0 120';
	newmis.avelocity = '300 300 300';
	newmis.angles = vectoangles (newmis.velocity);
};

void() W_Overpressure =
{
	if (self.health <= 0)
		return;
	makevectors (self.v_angle);
	self.show_hostile = time + 1;
	if (self.weapon == IT_AXE)
		W_OverpressurePick ();
	else if (self.weapon == IT_SHOTGUN)
		W_OverpressureScatter ();
	else if (self.weapon == IT_NAILGUN)
		W_OverpressureSpitter ();
	else
		sound (self, CHAN_ITEM, "cinder/empty.wav", 0.6, ATTN_NORM);
};

/*QUAKED func_cracked (0 .5 .8) ?
Cracked stone: a wall only the Pick's Overpressure blow breaks, often
hiding a secret. "target" is fired when it breaks.
*/
void() func_cracked_die =
{
	local vector mid;

	mid = (self.absmin + self.absmax) * 0.5;
	sound (self, CHAN_AUTO, "player/axhit2.wav", 1, ATTN_NORM);
	particle (mid, '0 0 60', 4, 120);
	particle (mid, '0 0 20', 8, 60);
	activator = self.enemy;
	SUB_UseTargets ();
	remove (self);
};

void() func_cracked =
{
	self.angles = '0 0 0';
	self.movetype = MOVETYPE_PUSH;
	self.solid = SOLID_BSP;
	setmodel (self, self.model);
	self.th_die = func_cracked_die;
};

void() Arsenal_Precache =
{
	precache_model ("progs/lavaball.mdl");
};
