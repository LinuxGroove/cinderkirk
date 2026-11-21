/*
	The cult (game-ideas idea 25): Censer-bearers, its foot soldiers, who
	swing burning censers up close and throw coals in an arc; and Deacons,
	who ring hand bells to raise the Ashen from their ash and throw their
	censers. Kill the Deacons first.

	Their models are assets_src/models/creatures.py's; frames come in the
	order listed here.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

.float ring_finished;	// when a Deacon may ring again
.float coal_dmg;		// what a thrown coal does

// A lob that lands at the target from org, flying across at speed.
vector(vector org, vector target, float speed) Cult_Lob =
{
	local vector d, v;
	local float flat, flight;

	d = target - org;
	v = d;
	v_z = 0;
	flat = vlen (v);
	flight = flat / speed;
	if (flight < 0.25)
		flight = 0.25;
	v = v * (1 / flight);
	v_z = d_z / flight + 0.5 * cvar ("sv_gravity") * flight;
	return v;
};

void() coal_touch =
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
		other.deathtype = "coal";
		T_Damage (other, self, self.owner, self.coal_dmg);
	}
	T_RadiusDamage (self, self.owner, self.coal_dmg * 0.8, other, "coal");
	sound (self, CHAN_WEAPON, "cinder/coal_hit.wav", 1, ATTN_NORM);
	W_SlagBurst (self.origin, 16 + self.coal_dmg);
	remove (self);
};

// A burning coal (or a whole censer) thrown at the enemy in an arc.
void(vector org, float dmg, float spread) Cult_ThrowCoal =
{
	local vector aimat;

	aimat = self.enemy.origin + [crandom () * spread, crandom () * spread, 0];
	newmis = spawn ();
	newmis.owner = self;
	newmis.classname = "cult_coal";
	newmis.movetype = MOVETYPE_TOSS;
	newmis.solid = SOLID_BBOX;
	newmis.coal_dmg = dmg;
	newmis.touch = coal_touch;
	newmis.think = SUB_Remove;
	newmis.nextthink = time + 5;
	setmodel (newmis, "progs/lavaball.mdl");
	setsize (newmis, VEC_ORIGIN, VEC_ORIGIN);
	setorigin (newmis, org);
	newmis.velocity = Cult_Lob (org, aimat, 520 + random () * 80);
	newmis.avelocity = '300 300 300';
	newmis.angles = vectoangles (newmis.velocity);
};

// A blow from the censer if the enemy is in reach.
void(float reach, float dmg) Cult_Strike =
{
	if (!self.enemy || vlen (self.enemy.origin - self.origin) > reach || !CanDamage (self.enemy, self))
		return;
	sound (self, CHAN_WEAPON, "cinder/coal_hit.wav", 1, ATTN_NORM);
	W_SlagBurst (self.enemy.origin + '0 0 16', 12);
	self.enemy.deathtype = "coal";
	T_Damage (self.enemy, self, self, dmg);
};

// ----------------------------------------------------------- Censer-bearers

$framevalue 0
$frame cstand1 cstand2 cstand3 cstand4 cstand5 cstand6 cstand7 cstand8
$frame cwalk1 cwalk2 cwalk3 cwalk4 cwalk5 cwalk6 cwalk7 cwalk8 cwalk9 cwalk10 cwalk11 cwalk12
$frame crun1 crun2 crun3 crun4 crun5 crun6 crun7 crun8
$frame cswing1 cswing2 cswing3 cswing4 cswing5 cswing6 cswing7 cswing8 cswing9 cswing10
$frame cthrow1 cthrow2 cthrow3 cthrow4 cthrow5 cthrow6 cthrow7 cthrow8 cthrow9
$frame cpain1 cpain2 cpain3 cpain4 cpain5 cpain6
$frame cdeath1 cdeath2 cdeath3 cdeath4 cdeath5 cdeath6 cdeath7 cdeath8 cdeath9 cdeath10

void() censer_stand1 =[ $cstand1, censer_stand2 ] { ai_stand (); };
void() censer_stand2 =[ $cstand2, censer_stand3 ] { ai_stand (); };
void() censer_stand3 =[ $cstand3, censer_stand4 ] { ai_stand (); };
void() censer_stand4 =[ $cstand4, censer_stand5 ] { ai_stand (); };
void() censer_stand5 =[ $cstand5, censer_stand6 ] { ai_stand (); };
void() censer_stand6 =[ $cstand6, censer_stand7 ] { ai_stand (); };
void() censer_stand7 =[ $cstand7, censer_stand8 ] { ai_stand (); };
void() censer_stand8 =[ $cstand8, censer_stand1 ] { ai_stand (); };

void() censer_walk1 =[ $cwalk1, censer_walk2 ] { ai_walk (4); };
void() censer_walk2 =[ $cwalk2, censer_walk3 ] { ai_walk (4); };
void() censer_walk3 =[ $cwalk3, censer_walk4 ] { ai_walk (3); };
void() censer_walk4 =[ $cwalk4, censer_walk5 ] { ai_walk (4); };
void() censer_walk5 =[ $cwalk5, censer_walk6 ] { ai_walk (4); };
void() censer_walk6 =[ $cwalk6, censer_walk7 ] { ai_walk (3); };
void() censer_walk7 =[ $cwalk7, censer_walk8 ] { ai_walk (4); };
void() censer_walk8 =[ $cwalk8, censer_walk9 ] { ai_walk (4); };
void() censer_walk9 =[ $cwalk9, censer_walk10 ] { ai_walk (3); };
void() censer_walk10 =[ $cwalk10, censer_walk11 ] { ai_walk (4); };
void() censer_walk11 =[ $cwalk11, censer_walk12 ] { ai_walk (4); };
void() censer_walk12 =[ $cwalk12, censer_walk1 ] { ai_walk (3); };

void() censer_run1 =[ $crun1, censer_run2 ] { ai_run (14); };
void() censer_run2 =[ $crun2, censer_run3 ] { ai_run (10); };
void() censer_run3 =[ $crun3, censer_run4 ] { ai_run (8); };
void() censer_run4 =[ $crun4, censer_run5 ] { ai_run (12); };
void() censer_run5 =[ $crun5, censer_run6 ] { ai_run (14); };
void() censer_run6 =[ $crun6, censer_run7 ] { ai_run (10); };
void() censer_run7 =[ $crun7, censer_run8 ] { ai_run (8); };
void() censer_run8 =[ $crun8, censer_run1 ] { ai_run (12); };

void() censer_swing1 =[ $cswing1, censer_swing2 ] { ai_face (); };
void() censer_swing2 =[ $cswing2, censer_swing3 ] { ai_face (); sound (self, CHAN_WEAPON, "cinder/censer_swing.wav", 1, ATTN_NORM); };
void() censer_swing3 =[ $cswing3, censer_swing4 ] { ai_charge (4); };
void() censer_swing4 =[ $cswing4, censer_swing5 ] { ai_charge (6); };
void() censer_swing5 =[ $cswing5, censer_swing6 ] { ai_charge (4); Cult_Strike (80, 14 + random () * 8); };
void() censer_swing6 =[ $cswing6, censer_swing7 ] { ai_charge (2); };
void() censer_swing7 =[ $cswing7, censer_swing8 ] { ai_charge (0); };
void() censer_swing8 =[ $cswing8, censer_swing9 ] { ai_face (); };
void() censer_swing9 =[ $cswing9, censer_swing10 ] { ai_face (); };
void() censer_swing10 =[ $cswing10, censer_run1 ] { ai_face (); };

void() censer_throw1 =[ $cthrow1, censer_throw2 ] { ai_face (); };
void() censer_throw2 =[ $cthrow2, censer_throw3 ] { ai_face (); };
void() censer_throw3 =[ $cthrow3, censer_throw4 ] { ai_face (); };
void() censer_throw4 =[ $cthrow4, censer_throw5 ] { ai_face (); };
void() censer_throw5 =[ $cthrow5, censer_throw6 ] { ai_face (); };
void() censer_throw6 =[ $cthrow6, censer_throw7 ] {
	local float i;

	ai_face ();
	sound (self, CHAN_WEAPON, "cinder/coal_throw.wav", 1, ATTN_NORM);
	makevectors (self.angles);
	for (i = 0; i < 3; i++)
		Cult_ThrowCoal (self.origin + v_forward * 12 + v_right * 10 + '0 0 30', 9, 40);
};
void() censer_throw7 =[ $cthrow7, censer_throw8 ] { };
void() censer_throw8 =[ $cthrow8, censer_throw9 ] { };
void() censer_throw9 =[ $cthrow9, censer_run1 ] { ai_face (); };

void() censer_pain1 =[ $cpain1, censer_pain2 ] { ai_painforward (-3); };
void() censer_pain2 =[ $cpain2, censer_pain3 ] { ai_painforward (-2); };
void() censer_pain3 =[ $cpain3, censer_pain4 ] { };
void() censer_pain4 =[ $cpain4, censer_pain5 ] { };
void() censer_pain5 =[ $cpain5, censer_pain6 ] { };
void() censer_pain6 =[ $cpain6, censer_run1 ] { };

void(entity attacker, float damage) censer_pain =
{
	if (self.pain_finished > time)
		return;
	sound (self, CHAN_VOICE, "cinder/censer_pain.wav", 1, ATTN_NORM);
	self.pain_finished = time + 1;
	if (random () * 50 < damage)
		censer_pain1 ();
};

void() censer_die1 =[ $cdeath1, censer_die2 ] { };
void() censer_die2 =[ $cdeath2, censer_die3 ] { };
void() censer_die3 =[ $cdeath3, censer_die4 ] { self.solid = SOLID_NOT; };
void() censer_die4 =[ $cdeath4, censer_die5 ] { };
void() censer_die5 =[ $cdeath5, censer_die6 ] { };
void() censer_die6 =[ $cdeath6, censer_die7 ] { };
void() censer_die7 =[ $cdeath7, censer_die8 ] { };
void() censer_die8 =[ $cdeath8, censer_die9 ] { W_SlagBurst (self.origin, 20); };
void() censer_die9 =[ $cdeath9, censer_die10 ] { };
void() censer_die10 =[ $cdeath10, censer_die10 ] { };

void() censer_die =
{
	if (self.health < -40)
	{
		sound (self, CHAN_VOICE, "player/udeath.wav", 1, ATTN_NORM);
		ThrowGib ("progs/gib1.mdl", self.health);
		ThrowGib ("progs/gib2.mdl", self.health);
		ThrowGib ("progs/gib3.mdl", self.health);
		W_SlagBurst (self.origin, 40);
		remove (self);
		return;
	}
	sound (self, CHAN_VOICE, "cinder/censer_death.wav", 1, ATTN_NORM);
	censer_die1 ();
};

/*QUAKED monster_censer (1 0 0) (-16 -16 -24) (16 16 40) Ambush
A Censer-bearer: swings a censer of live coals and throws them.
*/
void() monster_censer =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/censer.md3");
	precache_model ("progs/lavaball.mdl");
	precache_model ("progs/gib1.mdl");
	precache_model ("progs/gib2.mdl");
	precache_model ("progs/gib3.mdl");
	precache_sound ("player/udeath.wav");
	precache_sound ("cinder/censer_sight.wav");
	precache_sound ("cinder/censer_pain.wav");
	precache_sound ("cinder/censer_death.wav");
	precache_sound ("cinder/censer_swing.wav");
	precache_sound ("cinder/coal_throw.wav");
	precache_sound ("cinder/coal_hit.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/censer.md3");
	setsize (self, '-16 -16 -24', '16 16 40');
	self.noise = "cinder/censer_sight.wav";
	self.netname = "Censer-bearer";
	self.killstring = " was burned by a Censer-bearer";
	self.health = 90;
	self.max_health = 90;

	self.th_stand = censer_stand1;
	self.th_walk = censer_walk1;
	self.th_run = censer_run1;
	self.th_melee = censer_swing1;
	self.th_missile = censer_throw1;
	self.th_pain = censer_pain;
	self.th_die = censer_die;

	walkmonster_start ();
};

// ------------------------------------------------------------------ Deacons

$framevalue 0
$frame dstand1 dstand2 dstand3 dstand4 dstand5 dstand6 dstand7 dstand8 dstand9 dstand10
$frame dwalk1 dwalk2 dwalk3 dwalk4 dwalk5 dwalk6 dwalk7 dwalk8 dwalk9 dwalk10 dwalk11 dwalk12
$frame dring1 dring2 dring3 dring4 dring5 dring6 dring7 dring8 dring9 dring10 dring11 dring12
$frame dthrow1 dthrow2 dthrow3 dthrow4 dthrow5 dthrow6 dthrow7 dthrow8 dthrow9 dthrow10
$frame dpain1 dpain2 dpain3 dpain4 dpain5 dpain6
$frame ddeath1 ddeath2 ddeath3 ddeath4 ddeath5 ddeath6 ddeath7 ddeath8 ddeath9 ddeath10 ddeath11 ddeath12

#define DEACON_RAISE_RANGE	640
#define DEACON_RAISE_MAX	3
#define DEACON_RING_EVERY	8

// TRUE when an ash pile lies within the bell's reach and sight.
float() Deacon_PileNear =
{
	local entity e;

	for (e = findradius (self.origin, DEACON_RAISE_RANGE); e; e = e.chain)
		if (e.classname == "ash_pile")
		{
			traceline (self.origin + '0 0 40', e.origin, TRUE, self);
			if (trace_fraction == 1.0)
				return TRUE;
		}
	return FALSE;
};

// The bell: raises the nearest ash piles it can see.
void() Deacon_Toll =
{
	local entity e;
	local float raised;

	sound (self, CHAN_WEAPON, "cinder/deacon_bell.wav", 1, 0.5);	// heard across the room and beyond
	for (e = findradius (self.origin, DEACON_RAISE_RANGE); e && raised < DEACON_RAISE_MAX; e = e.chain)
	{
		if (e.classname != "ash_pile")
			continue;
		traceline (self.origin + '0 0 40', e.origin, TRUE, self);
		if (trace_fraction < 1.0)
			continue;
		if (Ashen_Raise (e, self.enemy))
			raised++;
	}
};

void() deacon_stand1 =[ $dstand1, deacon_stand2 ] { ai_stand (); };
void() deacon_stand2 =[ $dstand2, deacon_stand3 ] { ai_stand (); };
void() deacon_stand3 =[ $dstand3, deacon_stand4 ] { ai_stand (); };
void() deacon_stand4 =[ $dstand4, deacon_stand5 ] { ai_stand (); };
void() deacon_stand5 =[ $dstand5, deacon_stand6 ] { ai_stand (); };
void() deacon_stand6 =[ $dstand6, deacon_stand7 ] { ai_stand (); };
void() deacon_stand7 =[ $dstand7, deacon_stand8 ] { ai_stand (); };
void() deacon_stand8 =[ $dstand8, deacon_stand9 ] { ai_stand (); };
void() deacon_stand9 =[ $dstand9, deacon_stand10 ] { ai_stand (); };
void() deacon_stand10 =[ $dstand10, deacon_stand1 ] { ai_stand (); };

void() deacon_walk1 =[ $dwalk1, deacon_walk2 ] { ai_walk (3); };
void() deacon_walk2 =[ $dwalk2, deacon_walk3 ] { ai_walk (3); };
void() deacon_walk3 =[ $dwalk3, deacon_walk4 ] { ai_walk (2); };
void() deacon_walk4 =[ $dwalk4, deacon_walk5 ] { ai_walk (3); };
void() deacon_walk5 =[ $dwalk5, deacon_walk6 ] { ai_walk (3); };
void() deacon_walk6 =[ $dwalk6, deacon_walk7 ] { ai_walk (2); };
void() deacon_walk7 =[ $dwalk7, deacon_walk8 ] { ai_walk (3); };
void() deacon_walk8 =[ $dwalk8, deacon_walk9 ] { ai_walk (3); };
void() deacon_walk9 =[ $dwalk9, deacon_walk10 ] { ai_walk (2); };
void() deacon_walk10 =[ $dwalk10, deacon_walk11 ] { ai_walk (3); };
void() deacon_walk11 =[ $dwalk11, deacon_walk12 ] { ai_walk (3); };
void() deacon_walk12 =[ $dwalk12, deacon_walk1 ] { ai_walk (2); };

// Deacons don't hurry: they come on at a walk.
void() deacon_run1 =[ $dwalk1, deacon_run2 ] { ai_run (6); };
void() deacon_run2 =[ $dwalk2, deacon_run3 ] { ai_run (6); };
void() deacon_run3 =[ $dwalk3, deacon_run4 ] { ai_run (4); };
void() deacon_run4 =[ $dwalk4, deacon_run5 ] { ai_run (6); };
void() deacon_run5 =[ $dwalk5, deacon_run6 ] { ai_run (6); };
void() deacon_run6 =[ $dwalk6, deacon_run7 ] { ai_run (4); };
void() deacon_run7 =[ $dwalk7, deacon_run8 ] { ai_run (6); };
void() deacon_run8 =[ $dwalk8, deacon_run9 ] { ai_run (6); };
void() deacon_run9 =[ $dwalk9, deacon_run10 ] { ai_run (4); };
void() deacon_run10 =[ $dwalk10, deacon_run11 ] { ai_run (6); };
void() deacon_run11 =[ $dwalk11, deacon_run12 ] { ai_run (6); };
void() deacon_run12 =[ $dwalk12, deacon_run1 ] { ai_run (4); };

void() deacon_ring1 =[ $dring1, deacon_ring2 ] { ai_face (); };
void() deacon_ring2 =[ $dring2, deacon_ring3 ] { ai_face (); };
void() deacon_ring3 =[ $dring3, deacon_ring4 ] { ai_face (); };
void() deacon_ring4 =[ $dring4, deacon_ring5 ] { Deacon_Toll (); };
void() deacon_ring5 =[ $dring5, deacon_ring6 ] { };
void() deacon_ring6 =[ $dring6, deacon_ring7 ] { };
void() deacon_ring7 =[ $dring7, deacon_ring8 ] { };
void() deacon_ring8 =[ $dring8, deacon_ring9 ] { };
void() deacon_ring9 =[ $dring9, deacon_ring10 ] { };
void() deacon_ring10 =[ $dring10, deacon_ring11 ] { ai_face (); };
void() deacon_ring11 =[ $dring11, deacon_ring12 ] { ai_face (); };
void() deacon_ring12 =[ $dring12, deacon_run1 ] { ai_face (); };

void() deacon_throw1 =[ $dthrow1, deacon_throw2 ] { ai_face (); };
void() deacon_throw2 =[ $dthrow2, deacon_throw3 ] { ai_face (); sound (self, CHAN_WEAPON, "cinder/deacon_throw.wav", 1, ATTN_NORM); };
void() deacon_throw3 =[ $dthrow3, deacon_throw4 ] { ai_face (); };
void() deacon_throw4 =[ $dthrow4, deacon_throw5 ] { ai_face (); };
void() deacon_throw5 =[ $dthrow5, deacon_throw6 ] { ai_face (); };
void() deacon_throw6 =[ $dthrow6, deacon_throw7 ] {
	makevectors (self.angles);
	Cult_ThrowCoal (self.origin + v_forward * 20 + v_right * 24 + '0 0 56', 28, 16);
};
void() deacon_throw7 =[ $dthrow7, deacon_throw8 ] { };
void() deacon_throw8 =[ $dthrow8, deacon_throw9 ] { };
void() deacon_throw9 =[ $dthrow9, deacon_throw10 ] { ai_face (); };
void() deacon_throw10 =[ $dthrow10, deacon_run1 ] { ai_face (); };

// Ring when there's ash to raise, otherwise throw the censer.
void() deacon_attack =
{
	if (time >= self.ring_finished && Deacon_PileNear ())
	{
		self.ring_finished = time + DEACON_RING_EVERY;
		deacon_ring1 ();
	}
	else
		deacon_throw1 ();
};

void() deacon_pain1 =[ $dpain1, deacon_pain2 ] { };
void() deacon_pain2 =[ $dpain2, deacon_pain3 ] { };
void() deacon_pain3 =[ $dpain3, deacon_pain4 ] { };
void() deacon_pain4 =[ $dpain4, deacon_pain5 ] { };
void() deacon_pain5 =[ $dpain5, deacon_pain6 ] { };
void() deacon_pain6 =[ $dpain6, deacon_run1 ] { };

void(entity attacker, float damage) deacon_pain =
{
	if (self.pain_finished > time)
		return;
	sound (self, CHAN_VOICE, "cinder/deacon_pain.wav", 1, ATTN_NORM);
	self.pain_finished = time + 2;
	if (random () * 120 < damage)
		deacon_pain1 ();
};

void() deacon_die1 =[ $ddeath1, deacon_die2 ] { };
void() deacon_die2 =[ $ddeath2, deacon_die3 ] { };
void() deacon_die3 =[ $ddeath3, deacon_die4 ] { };
void() deacon_die4 =[ $ddeath4, deacon_die5 ] { self.solid = SOLID_NOT; };
void() deacon_die5 =[ $ddeath5, deacon_die6 ] { };
void() deacon_die6 =[ $ddeath6, deacon_die7 ] { };
void() deacon_die7 =[ $ddeath7, deacon_die8 ] { };
void() deacon_die8 =[ $ddeath8, deacon_die9 ] { };
void() deacon_die9 =[ $ddeath9, deacon_die10 ] { };
void() deacon_die10 =[ $ddeath10, deacon_die11 ] { W_SlagBurst (self.origin, 40); };
void() deacon_die11 =[ $ddeath11, deacon_die12 ] { };
void() deacon_die12 =[ $ddeath12, deacon_die12 ] { };

void() deacon_die =
{
	sound (self, CHAN_VOICE, "cinder/deacon_death.wav", 1, ATTN_NORM);
	deacon_die1 ();
};

/*QUAKED monster_deacon (1 0 0) (-32 -32 -24) (32 32 64) Ambush
A Deacon: rings its bell to raise the Ashen from their ash, and throws its
censer. Kill it first.
*/
void() monster_deacon =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/deacon.md3");
	precache_model ("progs/lavaball.mdl");
	precache_sound ("cinder/deacon_sight.wav");
	precache_sound ("cinder/deacon_pain.wav");
	precache_sound ("cinder/deacon_death.wav");
	precache_sound ("cinder/deacon_bell.wav");
	precache_sound ("cinder/deacon_throw.wav");
	precache_sound ("cinder/coal_hit.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/deacon.md3");
	setsize (self, '-32 -32 -24', '32 32 64');
	self.noise = "cinder/deacon_sight.wav";
	self.netname = "Deacon";
	self.killstring = " was given to the bell by a Deacon";
	self.health = 260;
	self.max_health = 260;

	self.th_stand = deacon_stand1;
	self.th_walk = deacon_walk1;
	self.th_run = deacon_run1;
	self.th_missile = deacon_attack;
	self.th_pain = deacon_pain;
	self.th_die = deacon_die;

	walkmonster_start ();
};
