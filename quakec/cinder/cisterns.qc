/*
	The Cisterns' creatures (game-ideas idea 25).

	Cistern leeches: long flat worms in the black water that swim for
	whatever falls in, latch on with a sucker ringed in teeth and drag it
	down, feeding, until it dashes free. The dash works under water while
	one is on you (pressure.qc calls Leech_ShakeOff), and costs the same.

	The model is assets_src/models/creatures.py's; its frames come in this
	order.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

$framevalue 0
$frame lswim1 lswim2 lswim3 lswim4 lswim5 lswim6 lswim7 lswim8
$frame llatch1 llatch2 llatch3 llatch4 llatch5 llatch6
$frame lpain1 lpain2 lpain3 lpain4
$frame ldeath1 ldeath2 ldeath3 ldeath4 ldeath5 ldeath6 ldeath7 ldeath8

.entity	leech_on;	// what this leech is fastened to
.vector	leech_at;	// where on it, from its origin
.float	leech_fed;	// on the prey: when the leeches on it next feed

void() leech_swim1;
void() leech_hold;

void() leech_stand1 =[ $lswim1, leech_stand2 ] { ai_stand (); };
void() leech_stand2 =[ $lswim2, leech_stand3 ] { ai_stand (); };
void() leech_stand3 =[ $lswim3, leech_stand4 ] { ai_stand (); };
void() leech_stand4 =[ $lswim4, leech_stand5 ] { ai_stand (); };
void() leech_stand5 =[ $lswim5, leech_stand6 ] { ai_stand (); };
void() leech_stand6 =[ $lswim6, leech_stand7 ] { ai_stand (); };
void() leech_stand7 =[ $lswim7, leech_stand8 ] { ai_stand (); };
void() leech_stand8 =[ $lswim8, leech_stand1 ] { ai_stand (); };

void() leech_walk1 =[ $lswim1, leech_walk2 ] { ai_walk (6); };
void() leech_walk2 =[ $lswim2, leech_walk3 ] { ai_walk (6); };
void() leech_walk3 =[ $lswim3, leech_walk4 ] { ai_walk (6); };
void() leech_walk4 =[ $lswim4, leech_walk5 ] { ai_walk (6); };
void() leech_walk5 =[ $lswim5, leech_walk6 ] { ai_walk (6); };
void() leech_walk6 =[ $lswim6, leech_walk7 ] { ai_walk (6); };
void() leech_walk7 =[ $lswim7, leech_walk8 ] { ai_walk (6); };
void() leech_walk8 =[ $lswim8, leech_walk1 ] { ai_walk (6); };

void() leech_swim1 =[ $lswim1, leech_swim2 ] { ai_run (14); };
void() leech_swim2 =[ $lswim2, leech_swim3 ] { ai_run (16); };
void() leech_swim3 =[ $lswim3, leech_swim4 ] { ai_run (14); };
void() leech_swim4 =[ $lswim4, leech_swim5 ] { ai_run (12); };
void() leech_swim5 =[ $lswim5, leech_swim6 ] { ai_run (14); };
void() leech_swim6 =[ $lswim6, leech_swim7 ] { ai_run (16); };
void() leech_swim7 =[ $lswim7, leech_swim8 ] { ai_run (14); };
void() leech_swim8 =[ $lswim8, leech_swim1 ] { ai_run (12); };

// Fasten on: the leech rides along with its prey from here on.
void() leech_bite =
{
	local entity p;

	p = self.enemy;
	if (!p || p.health <= 0 || time < self.attack_finished || vlen (p.origin - self.origin) > 128
		|| !(p.flags & FL_CLIENT) || p.waterlevel < 1)
	{
		// Not yet: swim on next frame (calling the swim now would ask
		// ai_run to attack again, and round it goes).
		self.think = leech_swim1;
		self.nextthink = time + 0.1;
		return;
	}
	sound (self, CHAN_VOICE, "cinder/leech_bite.wav", 1, ATTN_NORM);
	self.leech_on = p;
	makevectors ([0, p.angles_y, 0]);
	self.leech_at = [crandom () * 10, crandom () * 10, -8 - random () * 16];
	p.leech_count = p.leech_count + 1;
	self.solid = SOLID_NOT;
	self.movetype = MOVETYPE_NOCLIP;
	self.velocity = '0 0 0';
	Rumble (p, "hurt");
	leech_hold ();
};

void() Leech_Let_Go =
{
	if (self.leech_on)
	{
		self.leech_on.leech_count = self.leech_on.leech_count - 1;
		if (self.leech_on.leech_count < 0)
			self.leech_on.leech_count = 0;
	}
	self.leech_on = world;
	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
};

// Fastened on: feed, and pull down while there's water to pull into.
void() leech_hold =
{
	local entity p;

	p = self.leech_on;
	if (!p || p.health <= 0 || self.health <= 0)
	{
		Leech_Let_Go ();
		self.think = leech_swim1;
		self.nextthink = time + 0.1;
		return;
	}
	self.frame = $llatch1 + (self.walkframe % 6);
	self.walkframe = self.walkframe + 1;
	setorigin (self, p.origin + self.leech_at);
	self.angles = [0, vectoyaw (p.origin - self.origin), 0];
	if (p.waterlevel >= 1)
	{
		p.velocity_x = p.velocity_x * 0.85;
		p.velocity_y = p.velocity_y * 0.85;
		p.velocity_z = p.velocity_z - 26;
	}
	else if (random () < 0.04)
	{
		// Out of the water it soon drops off.
		Leech_Let_Go ();
		self.think = leech_swim1;
		self.nextthink = time + 0.1;
		return;
	}
	// All the leeches on one player feed together, as one hit, so the
	// screen flashes once for them rather than once each.
	if (time >= p.leech_fed)
	{
		p.leech_fed = time + 0.5;
		p.deathtype = "leech";
		T_Damage (p, self, self, 3 * (p.leech_count > 1 ? p.leech_count : 1));
		SpawnBlood (self.origin, '0 0 0', 3);
		if (random () < 0.3)
			sound (self, CHAN_VOICE, "cinder/leech_feed.wav", 0.7, ATTN_NORM);
	}
	self.think = leech_hold;
	self.nextthink = time + 0.1;
};

/*
	The dash shakes every leech off whoever made it: each is thrown clear,
	hurt, and won't bite again for a moment.
*/
void(entity p) Leech_ShakeOff =
{
	local entity e, oself;

	oself = self;
	for (e = find (world, classname, "monster_leech"); e; e = find (e, classname, "monster_leech"))
	{
		if (e.leech_on != p)
			continue;
		self = e;
		Leech_Let_Go ();
		setorigin (self, p.origin + normalize (self.origin - p.origin + '0 0 1') * 40);
		self.velocity = normalize (self.origin - p.origin) * 240;
		self.attack_finished = time + 2.5;
		self = oself;
		T_Damage (e, p, p, 12);
	}
	self = oself;
	p.leech_count = 0;
};

void() leech_pain1 =[ $lpain1, leech_pain2 ] { };
void() leech_pain2 =[ $lpain2, leech_pain3 ] { ai_pain (6); };
void() leech_pain3 =[ $lpain3, leech_pain4 ] { ai_pain (6); };
void() leech_pain4 =[ $lpain4, leech_swim1 ] { };

void(entity attacker, float damage) leech_pain =
{
	if (self.leech_on)
		return;		// fastened on, it holds whatever hits it
	if (self.pain_finished > time)
		return;
	self.pain_finished = time + 1;
	sound (self, CHAN_VOICE, "cinder/leech_pain.wav", 1, ATTN_NORM);
	leech_pain1 ();
};

void() leech_death1 =[ $ldeath1, leech_death2 ] { };
void() leech_death2 =[ $ldeath2, leech_death3 ] { self.solid = SOLID_NOT; };
void() leech_death3 =[ $ldeath3, leech_death4 ] { };
void() leech_death4 =[ $ldeath4, leech_death5 ] { };
void() leech_death5 =[ $ldeath5, leech_death6 ] { };
void() leech_death6 =[ $ldeath6, leech_death7 ] { };
void() leech_death7 =[ $ldeath7, leech_death8 ] { };
void() leech_death8 =[ $ldeath8, leech_death8 ] { };

void() leech_die =
{
	Leech_Let_Go ();
	self.solid = SOLID_NOT;
	self.movetype = MOVETYPE_STEP;
	sound (self, CHAN_VOICE, "cinder/leech_death.wav", 1, ATTN_NORM);
	SpawnBlood (self.origin, '0 0 0', 20);
	leech_death1 ();
};

/*QUAKED monster_leech (1 0 0) (-16 -16 -24) (16 16 24) Ambush
A cistern leech: swims for you, fastens on and drags you down until you dash free.
*/
void() monster_leech =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/leech.md3");
	precache_sound ("cinder/leech_sight.wav");
	precache_sound ("cinder/leech_bite.wav");
	precache_sound ("cinder/leech_feed.wav");
	precache_sound ("cinder/leech_pain.wav");
	precache_sound ("cinder/leech_death.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/leech.md3");
	setsize (self, '-16 -16 -24', '16 16 24');
	self.noise = "cinder/leech_sight.wav";
	self.netname = "cistern leech";
	self.killstring = " was drained by cistern leeches";
	self.health = 35;
	self.max_health = self.health;

	self.th_stand = leech_stand1;
	self.th_walk = leech_walk1;
	self.th_run = leech_swim1;
	self.th_melee = leech_bite;
	self.th_pain = leech_pain;
	self.th_die = leech_die;

	swimmonster_start ();
};
