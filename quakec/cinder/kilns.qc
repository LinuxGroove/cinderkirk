/*
	The Ossuary Kilns' creatures (game-ideas idea 25): ash wraiths and bell-ringers.

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

/*
	Bell-ringers: giants of ash with a bronze bell for a ribcage. They toll
	it with a ringer's mallet, and the toll runs out along the floor as a
	ring of force: anything standing on the floor when it passes is thrown
	and hurt, so jump it. Close up they lash out with the other arm.
*/

$framevalue 0
$frame rstand1 rstand2 rstand3 rstand4 rstand5 rstand6 rstand7 rstand8
$frame rwalk1 rwalk2 rwalk3 rwalk4 rwalk5 rwalk6 rwalk7 rwalk8 rwalk9 rwalk10 rwalk11 rwalk12
$frame rtoll1 rtoll2 rtoll3 rtoll4 rtoll5 rtoll6 rtoll7 rtoll8 rtoll9 rtoll10 rtoll11 rtoll12 rtoll13 rtoll14
$frame rswing1 rswing2 rswing3 rswing4 rswing5 rswing6 rswing7 rswing8 rswing9 rswing10
$frame rpain1 rpain2 rpain3 rpain4 rpain5
$frame rdeath1 rdeath2 rdeath3 rdeath4 rdeath5 rdeath6 rdeath7 rdeath8 rdeath9 rdeath10 rdeath11 rdeath12

.entity	toll_hit;	// on a player: the last toll ring that struck them

// The ring: grows along the floor, striking whoever stands on it as it passes.
void() toll_ring_think =
{
	local entity p;
	local vector d;
	local float r, i, a;

	self.cnt = self.cnt + 26;
	r = self.cnt;
	if (r > 1100)
	{
		remove (self);
		return;
	}
	for (i = 0; i < 16; i = i + 1)
	{
		a = (i / 16) * 360 + r * 0.3;
		makevectors ([0, a, 0]);
		particle (self.origin + v_forward * r + '0 0 4', '0 0 20', 104, 2);
	}
	for (p = find (world, classname, "player"); p; p = find (p, classname, "player"))
	{
		if (p.health <= 0 || p.toll_hit == self || !(p.flags & FL_ONGROUND))
			continue;
		if (fabs (p.absmin_z - self.origin_z) > 24)
			continue;
		d = p.origin - self.origin;
		d_z = 0;
		if (fabs (vlen (d) - r) > 30)
			continue;
		traceline (self.origin + '0 0 12', [p.origin_x, p.origin_y, self.origin_z + 12], TRUE, self);
		if (trace_fraction < 1)
			continue;
		p.toll_hit = self;
		p.deathtype = "toll";
		T_Damage (p, self, self.owner, 20);
		p.velocity = p.velocity + normalize (d) * 300 + '0 0 260';
		p.flags = p.flags - (p.flags & FL_ONGROUND);
		Rumble (p, "hurt_big");
	}
	self.nextthink = time + 0.05;
};

void() Ringer_Toll =
{
	local entity ring, p;

	sound (self, CHAN_WEAPON, "cinder/ringer_toll.wav", 1, ATTN_NONE);
	ring = spawn ();
	ring.owner = self;
	ring.classname = "toll_ring";
	setorigin (ring, self.origin + [0, 0, self.mins_z + 2]);
	ring.cnt = 40;
	ring.think = toll_ring_think;
	ring.nextthink = time + 0.05;
	// Everyone near enough feels the toll in their hands.
	for (p = find (world, classname, "player"); p; p = find (p, classname, "player"))
		if (vlen (p.origin - self.origin) < 1200)
			Rumble (p, "mortar");
};

void() Ringer_Lash =
{
	local vector dir;

	sound (self, CHAN_WEAPON, "cinder/ringer_swing.wav", 1, ATTN_NORM);
	if (!self.enemy || vlen (self.enemy.origin - self.origin) > 140 || !CanDamage (self.enemy, self))
		return;
	self.enemy.deathtype = "ringer";
	T_Damage (self.enemy, self, self, 30 + random () * 10);
	makevectors (self.angles);
	dir = v_right * -1;
	self.enemy.velocity = self.enemy.velocity + dir * 340 + '0 0 180';
	Rumble (self.enemy, "hurt_big");
};

void() ringer_stand1 =[ $rstand1, ringer_stand2 ] { ai_stand (); };
void() ringer_stand2 =[ $rstand2, ringer_stand3 ] { ai_stand (); };
void() ringer_stand3 =[ $rstand3, ringer_stand4 ] { ai_stand (); };
void() ringer_stand4 =[ $rstand4, ringer_stand5 ] { ai_stand (); };
void() ringer_stand5 =[ $rstand5, ringer_stand6 ] { ai_stand (); };
void() ringer_stand6 =[ $rstand6, ringer_stand7 ] { ai_stand (); };
void() ringer_stand7 =[ $rstand7, ringer_stand8 ] { ai_stand (); };
void() ringer_stand8 =[ $rstand8, ringer_stand1 ] { ai_stand (); };

void() ringer_walk1 =[ $rwalk1, ringer_walk2 ] { ai_walk (5); };
void() ringer_walk2 =[ $rwalk2, ringer_walk3 ] { ai_walk (5); };
void() ringer_walk3 =[ $rwalk3, ringer_walk4 ] { ai_walk (5); };
void() ringer_walk4 =[ $rwalk4, ringer_walk5 ] { ai_walk (5); };
void() ringer_walk5 =[ $rwalk5, ringer_walk6 ] { ai_walk (5); };
void() ringer_walk6 =[ $rwalk6, ringer_walk7 ] { ai_walk (5); };
void() ringer_walk7 =[ $rwalk7, ringer_walk8 ] { ai_walk (5); };
void() ringer_walk8 =[ $rwalk8, ringer_walk9 ] { ai_walk (5); };
void() ringer_walk9 =[ $rwalk9, ringer_walk10 ] { ai_walk (5); };
void() ringer_walk10 =[ $rwalk10, ringer_walk11 ] { ai_walk (5); };
void() ringer_walk11 =[ $rwalk11, ringer_walk12 ] { ai_walk (5); };
void() ringer_walk12 =[ $rwalk12, ringer_walk1 ] { ai_walk (5); };

void() ringer_run1 =[ $rwalk1, ringer_run2 ] { ai_run (9); };
void() ringer_run2 =[ $rwalk2, ringer_run3 ] { ai_run (9); };
void() ringer_run3 =[ $rwalk3, ringer_run4 ] { ai_run (9); };
void() ringer_run4 =[ $rwalk4, ringer_run5 ] { ai_run (9); };
void() ringer_run5 =[ $rwalk5, ringer_run6 ] { ai_run (9); };
void() ringer_run6 =[ $rwalk6, ringer_run7 ] { ai_run (9); };
void() ringer_run7 =[ $rwalk7, ringer_run8 ] { ai_run (9); };
void() ringer_run8 =[ $rwalk8, ringer_run9 ] { ai_run (9); };
void() ringer_run9 =[ $rwalk9, ringer_run10 ] { ai_run (9); };
void() ringer_run10 =[ $rwalk10, ringer_run11 ] { ai_run (9); };
void() ringer_run11 =[ $rwalk11, ringer_run12 ] { ai_run (9); };
void() ringer_run12 =[ $rwalk12, ringer_run1 ] { ai_run (9); };

void() ringer_toll1 =[ $rtoll1, ringer_toll2 ] { ai_face (); };
void() ringer_toll2 =[ $rtoll2, ringer_toll3 ] { ai_face (); };
void() ringer_toll3 =[ $rtoll3, ringer_toll4 ] { ai_face (); };
void() ringer_toll4 =[ $rtoll4, ringer_toll5 ] { ai_face (); };
void() ringer_toll5 =[ $rtoll5, ringer_toll6 ] { ai_face (); };
void() ringer_toll6 =[ $rtoll6, ringer_toll7 ] { ai_face (); };
void() ringer_toll7 =[ $rtoll7, ringer_toll8 ] { };
void() ringer_toll8 =[ $rtoll8, ringer_toll9 ] { };
void() ringer_toll9 =[ $rtoll9, ringer_toll10 ] { Ringer_Toll (); };
void() ringer_toll10 =[ $rtoll10, ringer_toll11 ] { };
void() ringer_toll11 =[ $rtoll11, ringer_toll12 ] { };
void() ringer_toll12 =[ $rtoll12, ringer_toll13 ] { };
void() ringer_toll13 =[ $rtoll13, ringer_toll14 ] { };
void() ringer_toll14 =[ $rtoll14, ringer_run1 ] { };

void() ringer_swing1 =[ $rswing1, ringer_swing2 ] { ai_face (); };
void() ringer_swing2 =[ $rswing2, ringer_swing3 ] { ai_face (); };
void() ringer_swing3 =[ $rswing3, ringer_swing4 ] { ai_face (); };
void() ringer_swing4 =[ $rswing4, ringer_swing5 ] { ai_face (); };
void() ringer_swing5 =[ $rswing5, ringer_swing6 ] { };
void() ringer_swing6 =[ $rswing6, ringer_swing7 ] { Ringer_Lash (); };
void() ringer_swing7 =[ $rswing7, ringer_swing8 ] { };
void() ringer_swing8 =[ $rswing8, ringer_swing9 ] { };
void() ringer_swing9 =[ $rswing9, ringer_swing10 ] { };
void() ringer_swing10 =[ $rswing10, ringer_run1 ] { };

void() ringer_pain1 =[ $rpain1, ringer_pain2 ] { };
void() ringer_pain2 =[ $rpain2, ringer_pain3 ] { };
void() ringer_pain3 =[ $rpain3, ringer_pain4 ] { };
void() ringer_pain4 =[ $rpain4, ringer_pain5 ] { };
void() ringer_pain5 =[ $rpain5, ringer_run1 ] { };

void(entity attacker, float damage) ringer_pain =
{
	if (self.pain_finished > time || random () * 120 > damage)
		return;		// it takes a lot to stagger one
	self.pain_finished = time + 3;
	sound (self, CHAN_VOICE, "cinder/ringer_pain.wav", 1, ATTN_NORM);
	ringer_pain1 ();
};

void() ringer_death1 =[ $rdeath1, ringer_death2 ] { };
void() ringer_death2 =[ $rdeath2, ringer_death3 ] { };
void() ringer_death3 =[ $rdeath3, ringer_death4 ] { self.solid = SOLID_NOT; };
void() ringer_death4 =[ $rdeath4, ringer_death5 ] { };
void() ringer_death5 =[ $rdeath5, ringer_death6 ] { };
void() ringer_death6 =[ $rdeath6, ringer_death7 ] { };
void() ringer_death7 =[ $rdeath7, ringer_death8 ] { };
void() ringer_death8 =[ $rdeath8, ringer_death9 ] { };
void() ringer_death9 =[ $rdeath9, ringer_death10 ] { };
void() ringer_death10 =[ $rdeath10, ringer_death11 ] { };
void() ringer_death11 =[ $rdeath11, ringer_death12 ] { };
void() ringer_death12 =[ $rdeath12, ringer_death12 ] { };

void() ringer_die =
{
	sound (self, CHAN_VOICE, "cinder/ringer_death.wav", 1, ATTN_NONE);
	ringer_death1 ();
};

float() RingerCheckAttack =
{
	local float d;

	d = vlen (self.enemy.origin - self.origin);
	if (d < 130)
	{
		self.attack_state = AS_MELEE;
		return TRUE;
	}
	if (time < self.attack_finished)
		return FALSE;
	if (d < 900 && random () < 0.5)
	{
		self.attack_state = AS_MISSILE;
		self.attack_finished = time + 3.5 + random () * 1.5;
		return TRUE;
	}
	return FALSE;
};

/*QUAKED monster_bell_ringer (1 0 0) (-32 -32 -24) (32 32 64) Ambush
A bell-ringer: tolls the bell in its chest, and the toll runs along the floor. Jump it.
*/
void() monster_bell_ringer =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/ringer.md3");
	precache_sound ("cinder/ringer_toll.wav");
	precache_sound ("cinder/ringer_sight.wav");
	precache_sound ("cinder/ringer_swing.wav");
	precache_sound ("cinder/ringer_pain.wav");
	precache_sound ("cinder/ringer_death.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/ringer.md3");
	setsize (self, VEC_HULL2_MIN, VEC_HULL2_MAX);
	self.noise = "cinder/ringer_sight.wav";
	self.netname = "Bell-ringer";
	self.killstring = " was tolled under by a Bell-ringer";
	self.health = 700;
	self.max_health = 700;

	self.th_stand = ringer_stand1;
	self.th_walk = ringer_walk1;
	self.th_run = ringer_run1;
	self.th_missile = ringer_toll1;
	self.th_melee = ringer_swing1;
	self.th_pain = ringer_pain;
	self.th_die = ringer_die;

	walkmonster_start ();
};
