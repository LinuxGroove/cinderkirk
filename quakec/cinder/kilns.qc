/*
	The Ossuary Kilns' creatures (game-ideas idea 25).

	Ash wraiths: the bone ash of the kilns, risen in the shape of what it
	was. They drift as a cloud, thin and grey, and nothing touches them
	then: shots and blasts pass through. To hurt you they have to gather
	and swoop, and while they swoop and rake they are solid and can be hit.
	A stoker waits for the shriek, then fires.

	The model is assets_src/models/creatures.py's; its frames come in this
	order.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

$framevalue 0
$frame wdrift1 wdrift2 wdrift3 wdrift4 wdrift5 wdrift6 wdrift7 wdrift8
$frame wswoop1 wswoop2 wswoop3 wswoop4 wswoop5 wswoop6 wswoop7 wswoop8
$frame wclaw1 wclaw2 wclaw3 wclaw4 wclaw5 wclaw6
$frame wpain1 wpain2 wpain3 wpain4
$frame wdeath1 wdeath2 wdeath3 wdeath4 wdeath5 wdeath6 wdeath7 wdeath8 wdeath9 wdeath10

.float	alpha;		// the engine's: how solid an entity is drawn

void() wraith_run1;
void() wraith_claw1;

// A cloud of ash: nothing hits it, and it sheds a little as it goes.
void() Wraith_Fade =
{
	if (self.solid != SOLID_NOT)
	{
		self.solid = SOLID_NOT;
		self.takedamage = DAMAGE_NO;
		setorigin (self, self.origin);
	}
	self.alpha = 0.45;
	if (random () < 0.5)
		particle (self.origin + [crandom () * 12, crandom () * 12, random () * 40 - 16], '0 0 -10', 5, 3);
};

// Gathered for the swoop: solid, and it can be hurt.
void() Wraith_Gather =
{
	self.solid = SOLID_SLIDEBOX;
	self.takedamage = DAMAGE_AIM;
	self.alpha = 1;
	setorigin (self, self.origin);
};

// Back to a cloud after a swoop, and a while before the next one.
void() Wraith_Recover =
{
	self.movetype = MOVETYPE_STEP;
	self.velocity = '0 0 0';
	self.touch = SUB_Null;
	self.attack_state = AS_SLIDING;
	self.attack_finished = time + 3 + random () * 2;
	Wraith_Fade ();
	wraith_run1 ();
};

void() wraith_idle =
{
	if (random () < 0.1)
		sound (self, CHAN_VOICE, "cinder/wraith_idle.wav", 0.6, ATTN_IDLE);
};

void() wraith_stand1 =[ $wdrift1, wraith_stand2 ] { Wraith_Fade (); ai_stand (); };
void() wraith_stand2 =[ $wdrift2, wraith_stand3 ] { ai_stand (); };
void() wraith_stand3 =[ $wdrift3, wraith_stand4 ] { ai_stand (); };
void() wraith_stand4 =[ $wdrift4, wraith_stand5 ] { ai_stand (); };
void() wraith_stand5 =[ $wdrift5, wraith_stand6 ] { wraith_idle (); ai_stand (); };
void() wraith_stand6 =[ $wdrift6, wraith_stand7 ] { ai_stand (); };
void() wraith_stand7 =[ $wdrift7, wraith_stand8 ] { ai_stand (); };
void() wraith_stand8 =[ $wdrift8, wraith_stand1 ] { ai_stand (); };

void() wraith_walk1 =[ $wdrift1, wraith_walk2 ] { Wraith_Fade (); ai_walk (4); };
void() wraith_walk2 =[ $wdrift2, wraith_walk3 ] { ai_walk (4); };
void() wraith_walk3 =[ $wdrift3, wraith_walk4 ] { ai_walk (4); };
void() wraith_walk4 =[ $wdrift4, wraith_walk5 ] { ai_walk (4); };
void() wraith_walk5 =[ $wdrift5, wraith_walk6 ] { wraith_idle (); ai_walk (4); };
void() wraith_walk6 =[ $wdrift6, wraith_walk7 ] { ai_walk (4); };
void() wraith_walk7 =[ $wdrift7, wraith_walk8 ] { ai_walk (4); };
void() wraith_walk8 =[ $wdrift8, wraith_walk1 ] { ai_walk (4); };

void() wraith_run1 =[ $wdrift1, wraith_run2 ] { Wraith_Fade (); ai_run (10); };
void() wraith_run2 =[ $wdrift2, wraith_run3 ] { Wraith_Fade (); ai_run (10); };
void() wraith_run3 =[ $wdrift3, wraith_run4 ] { Wraith_Fade (); ai_run (10); };
void() wraith_run4 =[ $wdrift4, wraith_run5 ] { Wraith_Fade (); ai_run (10); };
void() wraith_run5 =[ $wdrift5, wraith_run6 ] { Wraith_Fade (); wraith_idle (); ai_run (10); };
void() wraith_run6 =[ $wdrift6, wraith_run7 ] { Wraith_Fade (); ai_run (10); };
void() wraith_run7 =[ $wdrift7, wraith_run8 ] { Wraith_Fade (); ai_run (10); };
void() wraith_run8 =[ $wdrift8, wraith_run1 ] { Wraith_Fade (); ai_run (10); };

void() Wraith_Touch =
{
	if (other == self.enemy && self.health > 0)
	{
		self.touch = SUB_Null;
		self.velocity = self.velocity * 0.2;
		wraith_claw1 ();
	}
};

// Away it goes, straight at where the enemy is now.
void() Wraith_Launch =
{
	local vector to;

	to = self.enemy.origin + '0 0 8' - self.origin;
	self.movetype = MOVETYPE_FLY;
	self.velocity = normalize (to) * 520;
	self.angles_y = vectoyaw (to);
	self.touch = Wraith_Touch;
	setorigin (self, self.origin + '0 0 1');
};

// While swooping: rake whatever it reaches, or give up at the end.
void() Wraith_Reach =
{
	if (self.enemy.health > 0 && vlen (self.enemy.origin - self.origin) < 72)
	{
		self.touch = SUB_Null;
		self.velocity = self.velocity * 0.2;
		wraith_claw1 ();
		return;
	}
	particle (self.origin, self.velocity * -0.1, 5, 4);
};

void() wraith_swoop1 =[ $wswoop1, wraith_swoop2 ] {
	Wraith_Gather ();
	sound (self, CHAN_VOICE, "cinder/wraith_swoop.wav", 1, ATTN_NORM);
	ai_face ();
};
void() wraith_swoop2 =[ $wswoop2, wraith_swoop3 ] { ai_face (); };
void() wraith_swoop3 =[ $wswoop3, wraith_swoop4 ] { ai_face (); Wraith_Launch (); };
void() wraith_swoop4 =[ $wswoop4, wraith_swoop5 ] { Wraith_Reach (); };
void() wraith_swoop5 =[ $wswoop5, wraith_swoop6 ] { Wraith_Reach (); };
void() wraith_swoop6 =[ $wswoop6, wraith_swoop7 ] { Wraith_Reach (); };
void() wraith_swoop7 =[ $wswoop7, wraith_swoop8 ] { Wraith_Reach (); };
void() wraith_swoop8 =[ $wswoop8, wraith_swoop8 ] { Wraith_Reach (); if (self.think == wraith_swoop8) Wraith_Recover (); };

void() Wraith_Rake =
{
	local float d;

	sound (self, CHAN_WEAPON, "cinder/wraith_claw.wav", 1, ATTN_NORM);
	if (!self.enemy || vlen (self.enemy.origin - self.origin) > 90 || !CanDamage (self.enemy, self))
		return;
	d = 12 + random () * 6;
	self.enemy.deathtype = "wraith";
	T_Damage (self.enemy, self, self, d);
	SpawnBlood (self.enemy.origin + '0 0 16', '0 0 0', d);
	if (self.enemy.flags & FL_CLIENT)
		Rumble (self.enemy, "hurt");
};

void() wraith_claw1 =[ $wclaw1, wraith_claw2 ] { self.velocity = self.velocity * 0.3; ai_face (); };
void() wraith_claw2 =[ $wclaw2, wraith_claw3 ] { self.velocity = '0 0 0'; ai_face (); };
void() wraith_claw3 =[ $wclaw3, wraith_claw4 ] { Wraith_Rake (); };
void() wraith_claw4 =[ $wclaw4, wraith_claw5 ] { };
void() wraith_claw5 =[ $wclaw5, wraith_claw6 ] { self.velocity = '0 0 60'; };
void() wraith_claw6 =[ $wclaw6, wraith_run1 ] { Wraith_Recover (); };

void() wraith_pain1 =[ $wpain1, wraith_pain2 ] { self.velocity = '0 0 0'; self.touch = SUB_Null; };
void() wraith_pain2 =[ $wpain2, wraith_pain3 ] { };
void() wraith_pain3 =[ $wpain3, wraith_pain4 ] { };
void() wraith_pain4 =[ $wpain4, wraith_run1 ] { Wraith_Recover (); };

void(entity attacker, float damage) wraith_pain =
{
	if (self.pain_finished > time)
		return;
	self.pain_finished = time + 1.5;
	sound (self, CHAN_VOICE, "cinder/wraith_pain.wav", 1, ATTN_NORM);
	wraith_pain1 ();		// a hit knocks it out of the swoop, back into a cloud
};

void() wraith_death1 =[ $wdeath1, wraith_death2 ] { };
void() wraith_death2 =[ $wdeath2, wraith_death3 ] { };
void() wraith_death3 =[ $wdeath3, wraith_death4 ] { particle (self.origin, '0 0 -30', 5, 30); };
void() wraith_death4 =[ $wdeath4, wraith_death5 ] { };
void() wraith_death5 =[ $wdeath5, wraith_death6 ] { };
void() wraith_death6 =[ $wdeath6, wraith_death7 ] { particle (self.origin, '0 0 -30', 5, 30); };
void() wraith_death7 =[ $wdeath7, wraith_death8 ] { };
void() wraith_death8 =[ $wdeath8, wraith_death9 ] { };
void() wraith_death9 =[ $wdeath9, wraith_death10 ] { };
void() wraith_death10 =[ $wdeath10, wraith_death10 ] { self.think = SUB_Remove; self.nextthink = time + 8; };

void() wraith_die =
{
	self.alpha = 1;
	self.solid = SOLID_NOT;
	self.touch = SUB_Null;
	self.movetype = MOVETYPE_TOSS;		// it falls as a heap of ash
	self.velocity = '0 0 0';
	self.flags = self.flags - (self.flags & FL_FLY);
	sound (self, CHAN_VOICE, "cinder/wraith_death.wav", 1, ATTN_NORM);
	wraith_death1 ();
};

void() wraith_swoop =
{
	wraith_swoop1 ();
};

/*
	Swoop when the last one's long past and it can see its enemy; until then
	circle at a distance, as a cloud.
*/
float() WraithCheckAttack =
{
	if (time < self.attack_finished)
	{
		self.attack_state = AS_SLIDING;
		return FALSE;
	}
	if (vlen (self.enemy.origin - self.origin) > 800)
	{
		self.attack_state = AS_STRAIGHT;
		return FALSE;
	}
	self.attack_state = AS_MISSILE;
	return TRUE;
};

/*QUAKED monster_ash_wraith (1 0 0) (-16 -16 -24) (16 16 40) Ambush
An ash wraith: drifts as a cloud nothing can hit, and is solid only while it swoops.
*/
void() monster_ash_wraith =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/wraith.md3");
	precache_sound ("cinder/wraith_idle.wav");
	precache_sound ("cinder/wraith_sight.wav");
	precache_sound ("cinder/wraith_swoop.wav");
	precache_sound ("cinder/wraith_claw.wav");
	precache_sound ("cinder/wraith_pain.wav");
	precache_sound ("cinder/wraith_death.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/wraith.md3");
	setsize (self, '-16 -16 -24', '16 16 40');
	self.noise = "cinder/wraith_sight.wav";
	self.netname = "Ash Wraith";
	self.killstring = " was raked by an Ash Wraith";
	self.health = 80;
	self.max_health = 80;

	self.th_stand = wraith_stand1;
	self.th_walk = wraith_walk1;
	self.th_run = wraith_run1;
	self.th_missile = wraith_swoop;
	self.th_pain = wraith_pain;
	self.th_die = wraith_die;

	flymonster_start ();
};
