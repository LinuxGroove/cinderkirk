/*
	The Foundry's own creatures (game-ideas idea 25):

	Gaugers, foundry workers who stayed, with steam lances: the valve hisses
	and the nozzle smokes for most of a second before the jet comes, so a
	stoker who's listening has time to step out of line.

	Crucible Brutes, huge furnace hands with a crucible of slag in a pair of
	tongs: they pour it in a line along the floor that keeps burning for a
	few seconds, and swing the whole crucible at anything close.

	Clinkers, crusts of slag on six legs that hang from ceilings until
	something walks under them, drop, scuttle in and burst. Killed, they burst
	anyway, so keep them at a distance.

	Their models are assets_src/models/creatures.py's; frames come in the
	order listed here.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

// ----------------------------------------------------------- Gaugers

$framevalue 0
$frame gstand1 gstand2 gstand3 gstand4 gstand5 gstand6 gstand7 gstand8
$frame gwalk1 gwalk2 gwalk3 gwalk4 gwalk5 gwalk6 gwalk7 gwalk8 gwalk9 gwalk10 gwalk11 gwalk12
$frame grun1 grun2 grun3 grun4 grun5 grun6 grun7 grun8
$frame gaim1 gaim2 gaim3 gaim4 gaim5 gaim6 gaim7 gaim8
$frame gfire1 gfire2 gfire3 gfire4 gfire5
$frame gjab1 gjab2 gjab3 gjab4 gjab5 gjab6 gjab7 gjab8
$frame gpain1 gpain2 gpain3 gpain4 gpain5 gpain6
$frame gdeath1 gdeath2 gdeath3 gdeath4 gdeath5 gdeath6 gdeath7 gdeath8 gdeath9 gdeath10

void() gauger_idle =
{
	if (random () < 0.1)
		sound (self, CHAN_VOICE, "cinder/gauger_idle.wav", 0.7, ATTN_IDLE);
};

// Where the lance's nozzle is, for the steam and the jet.
vector() Gauger_Nozzle =
{
	makevectors (self.angles);
	return self.origin + v_forward * 44 + v_right * 4 + '0 0 12';
};

void() steam_jet_touch =
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
		other.deathtype = "steam";
		T_Damage (other, self, self.owner, 9);
	}
	Pressure_Steam (self.origin, '0 0 20', 10);
	remove (self);
};

void() steam_jet_think =
{
	Pressure_Steam (self.origin, self.velocity * -0.05, 4);
	if (time > self.attack_finished)
	{
		remove (self);
		return;
	}
	self.nextthink = time + 0.04;
};

// One gout of the jet: fast, straight, and gone after a few hundred units.
void(float spread) Gauger_Jet =
{
	local vector org, dir;

	org = Gauger_Nozzle ();
	dir = normalize (self.enemy.origin + self.enemy.view_ofs * 0.5 - org);
	dir = normalize (dir + v_right * crandom () * spread + v_up * crandom () * spread * 0.5);
	newmis = spawn ();
	newmis.owner = self;
	newmis.classname = "steam_jet";
	newmis.movetype = MOVETYPE_FLYMISSILE;
	newmis.solid = SOLID_BBOX;
	newmis.touch = steam_jet_touch;
	newmis.think = steam_jet_think;
	newmis.nextthink = time + 0.02;
	newmis.attack_finished = time + 0.7;
	setsize (newmis, '-2 -2 -2', '2 2 2');
	setorigin (newmis, org);
	newmis.velocity = dir * 900;
};

void() gauger_stand1 =[ $gstand1, gauger_stand2 ] { ai_stand (); gauger_idle (); };
void() gauger_stand2 =[ $gstand2, gauger_stand3 ] { ai_stand (); };
void() gauger_stand3 =[ $gstand3, gauger_stand4 ] { ai_stand (); };
void() gauger_stand4 =[ $gstand4, gauger_stand5 ] { ai_stand (); };
void() gauger_stand5 =[ $gstand5, gauger_stand6 ] { ai_stand (); };
void() gauger_stand6 =[ $gstand6, gauger_stand7 ] { ai_stand (); };
void() gauger_stand7 =[ $gstand7, gauger_stand8 ] { ai_stand (); };
void() gauger_stand8 =[ $gstand8, gauger_stand1 ] { ai_stand (); };
void() gauger_walk1 =[ $gwalk1, gauger_walk2 ] { ai_walk (4); gauger_idle (); };
void() gauger_walk2 =[ $gwalk2, gauger_walk3 ] { ai_walk (5); };
void() gauger_walk3 =[ $gwalk3, gauger_walk4 ] { ai_walk (4); };
void() gauger_walk4 =[ $gwalk4, gauger_walk5 ] { ai_walk (3); };
void() gauger_walk5 =[ $gwalk5, gauger_walk6 ] { ai_walk (4); };
void() gauger_walk6 =[ $gwalk6, gauger_walk7 ] { ai_walk (5); };
void() gauger_walk7 =[ $gwalk7, gauger_walk8 ] { ai_walk (4); };
void() gauger_walk8 =[ $gwalk8, gauger_walk9 ] { ai_walk (3); };
void() gauger_walk9 =[ $gwalk9, gauger_walk10 ] { ai_walk (4); };
void() gauger_walk10 =[ $gwalk10, gauger_walk11 ] { ai_walk (5); };
void() gauger_walk11 =[ $gwalk11, gauger_walk12 ] { ai_walk (4); };
void() gauger_walk12 =[ $gwalk12, gauger_walk1 ] { ai_walk (3); };
void() gauger_run1 =[ $grun1, gauger_run2 ] { ai_run (12); gauger_idle (); };
void() gauger_run2 =[ $grun2, gauger_run3 ] { ai_run (16); };
void() gauger_run3 =[ $grun3, gauger_run4 ] { ai_run (14); };
void() gauger_run4 =[ $grun4, gauger_run5 ] { ai_run (10); };
void() gauger_run5 =[ $grun5, gauger_run6 ] { ai_run (12); };
void() gauger_run6 =[ $grun6, gauger_run7 ] { ai_run (16); };
void() gauger_run7 =[ $grun7, gauger_run8 ] { ai_run (14); };
void() gauger_run8 =[ $grun8, gauger_run1 ] { ai_run (10); };
void() gauger_aim1 =[ $gaim1, gauger_aim2 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 3); sound (self, CHAN_WEAPON, "cinder/gauger_hiss.wav", 1, ATTN_NORM); };
void() gauger_aim2 =[ $gaim2, gauger_aim3 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 4); };
void() gauger_aim3 =[ $gaim3, gauger_aim4 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 5); };
void() gauger_aim4 =[ $gaim4, gauger_aim5 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 6); };
void() gauger_aim5 =[ $gaim5, gauger_aim6 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 7); };
void() gauger_aim6 =[ $gaim6, gauger_aim7 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 8); };
void() gauger_aim7 =[ $gaim7, gauger_aim8 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 9); };
void() gauger_aim8 =[ $gaim8, gauger_fire1 ] { ai_face (); Pressure_Steam (Gauger_Nozzle (), v_forward * 40, 10); };
void() gauger_fire1 =[ $gfire1, gauger_fire2 ] { sound (self, CHAN_WEAPON, "cinder/gauger_fire.wav", 1, ATTN_NORM); Gauger_Jet (0.02); };
void() gauger_fire2 =[ $gfire2, gauger_fire3 ] { Gauger_Jet (0.06); };
void() gauger_fire3 =[ $gfire3, gauger_fire4 ] { Gauger_Jet (0.06); };
void() gauger_fire4 =[ $gfire4, gauger_fire5 ] { ai_face (); };
void() gauger_fire5 =[ $gfire5, gauger_run1 ] { ai_face (); };

// The jab with the lance when something's in reach.
void() Gauger_Jab =
{
	if (!self.enemy || vlen (self.enemy.origin - self.origin) > 96 || !CanDamage (self.enemy, self))
		return;
	sound (self, CHAN_WEAPON, "cinder/gauger_jab.wav", 1, ATTN_NORM);
	makevectors (self.angles);
	Pressure_Steam (self.enemy.origin + '0 0 16', v_forward * 60, 12);
	self.enemy.deathtype = "steam";
	T_Damage (self.enemy, self, self, 10 + random () * 6);
};

void() gauger_jab1 =[ $gjab1, gauger_jab2 ] { ai_face (); };
void() gauger_jab2 =[ $gjab2, gauger_jab3 ] { ai_charge (2); };
void() gauger_jab3 =[ $gjab3, gauger_jab4 ] { ai_charge (4); };
void() gauger_jab4 =[ $gjab4, gauger_jab5 ] { ai_charge (6); };
void() gauger_jab5 =[ $gjab5, gauger_jab6 ] { Gauger_Jab (); };
void() gauger_jab6 =[ $gjab6, gauger_jab7 ] { ai_face (); };
void() gauger_jab7 =[ $gjab7, gauger_jab8 ] { ai_face (); };
void() gauger_jab8 =[ $gjab8, gauger_run1 ] { ai_face (); };
void() gauger_pain1 =[ $gpain1, gauger_pain2 ] { };
void() gauger_pain2 =[ $gpain2, gauger_pain3 ] { ai_pain (2); };
void() gauger_pain3 =[ $gpain3, gauger_pain4 ] { ai_pain (2); };
void() gauger_pain4 =[ $gpain4, gauger_pain5 ] { };
void() gauger_pain5 =[ $gpain5, gauger_pain6 ] { };
void() gauger_pain6 =[ $gpain6, gauger_run1 ] { };

void(entity attacker, float damage) gauger_pain =
{
	if (self.pain_finished > time)
		return;
	if (random () * 60 > damage)
		return;		// a light hit doesn't stop the jet once it's coming
	self.pain_finished = time + 1.5;
	sound (self, CHAN_VOICE, "cinder/gauger_pain.wav", 1, ATTN_NORM);
	gauger_pain1 ();
};

void() gauger_death1 =[ $gdeath1, gauger_death2 ] { };
void() gauger_death2 =[ $gdeath2, gauger_death3 ] { };
void() gauger_death3 =[ $gdeath3, gauger_death4 ] { self.solid = SOLID_NOT; };
void() gauger_death4 =[ $gdeath4, gauger_death5 ] { };
void() gauger_death5 =[ $gdeath5, gauger_death6 ] { Pressure_Steam (self.origin, '0 0 60', 30); sound (self, CHAN_BODY, "cinder/vent.wav", 0.7, ATTN_NORM); };
void() gauger_death6 =[ $gdeath6, gauger_death7 ] { };
void() gauger_death7 =[ $gdeath7, gauger_death8 ] { };
void() gauger_death8 =[ $gdeath8, gauger_death9 ] { };
void() gauger_death9 =[ $gdeath9, gauger_death10 ] { };
void() gauger_death10 =[ $gdeath10, gauger_death10 ] { };

void() gauger_die =
{
	if (self.health < -40)
	{
		sound (self, CHAN_VOICE, "player/udeath.wav", 1, ATTN_NORM);
		ThrowHead ("progs/h_player.mdl", self.health);
		ThrowGib ("progs/gib1.mdl", self.health);
		ThrowGib ("progs/gib2.mdl", self.health);
		ThrowGib ("progs/gib3.mdl", self.health);
		Pressure_Steam (self.origin, '0 0 80', 40);
		return;
	}
	sound (self, CHAN_VOICE, "cinder/gauger_death.wav", 1, ATTN_NORM);
	gauger_death1 ();
};

/*QUAKED monster_gauger (1 0 0) (-16 -16 -24) (16 16 40) Ambush
A Gauger: a foundry worker with a steam lance that hisses before it fires.
*/
void() monster_gauger =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/gauger.md3");
	precache_model ("progs/h_player.mdl");
	precache_sound ("cinder/gauger_sight.wav");
	precache_sound ("cinder/gauger_idle.wav");
	precache_sound ("cinder/gauger_hiss.wav");
	precache_sound ("cinder/gauger_fire.wav");
	precache_sound ("cinder/gauger_jab.wav");
	precache_sound ("cinder/gauger_pain.wav");
	precache_sound ("cinder/gauger_death.wav");
	precache_sound ("cinder/vent.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/gauger.md3");
	setsize (self, '-16 -16 -24', '16 16 40');
	self.noise = "cinder/gauger_sight.wav";
	self.netname = "Gauger";
	self.killstring = " was scalded by a Gauger";
	self.health = 90;
	self.max_health = self.health;

	self.th_stand = gauger_stand1;
	self.th_walk = gauger_walk1;
	self.th_run = gauger_run1;
	self.th_melee = gauger_jab1;
	self.th_missile = gauger_aim1;
	self.th_pain = gauger_pain;
	self.th_die = gauger_die;

	walkmonster_start ();
};

// ----------------------------------------------------------- Crucible Brutes

$framevalue 0
$frame bstand1 bstand2 bstand3 bstand4 bstand5 bstand6 bstand7 bstand8 bstand9 bstand10
$frame bwalk1 bwalk2 bwalk3 bwalk4 bwalk5 bwalk6 bwalk7 bwalk8 bwalk9 bwalk10 bwalk11 bwalk12
$frame bpour1 bpour2 bpour3 bpour4 bpour5 bpour6 bpour7 bpour8 bpour9 bpour10 bpour11 bpour12
$frame bswing1 bswing2 bswing3 bswing4 bswing5 bswing6 bswing7 bswing8 bswing9 bswing10
$frame bpain1 bpain2 bpain3 bpain4 bpain5 bpain6
$frame bdeath1 bdeath2 bdeath3 bdeath4 bdeath5 bdeath6 bdeath7 bdeath8 bdeath9 bdeath10 bdeath11 bdeath12

.float pour_step;	// how far along its line the Brute's pour has reached
.vector pour_dir;	// and which way the line runs

void() brute_idle =
{
	if (random () < 0.1)
		sound (self, CHAN_VOICE, "cinder/brute_idle.wav", 0.8, ATTN_IDLE);
};

void() brute_step =
{
	sound (self, CHAN_BODY, "cinder/brute_step.wav", 0.6, ATTN_NORM);
};

// A splash of slag where the pour lands: it scalds at once, then burns.
void(vector org) Brute_Splash =
{
	local entity e, pool;

	traceline (org + '0 0 24', org - '0 0 96', TRUE, self);
	if (trace_fraction == 1.0 || trace_inwater)
		return;
	org = trace_endpos + '0 0 4';
	W_SlagBurst (org, 20);
	for (e = findradius (org, 44); e; e = e.chain)
		if (e.takedamage && e.health > 0 && e != self)
		{
			e.deathtype = "slag";
			T_Damage (e, self, self, 10);
		}
	pool = spawn ();
	pool.classname = "slag_pool";
	pool.owner = self;
	setorigin (pool, org);
	pool.attack_finished = time + 3.5;
	pool.think = slag_burn_think;
	pool.nextthink = time + 0.3;
};

void() Brute_PourStart =
{
	ai_face ();
	makevectors (self.angles);
	self.pour_dir = v_forward;
	self.pour_step = 0;
	sound (self, CHAN_WEAPON, "cinder/brute_pour.wav", 1, ATTN_NORM);
};

// Each frame of the pour lays the next splash further along the line.
void() Brute_PourOn =
{
	local vector org;

	self.pour_step = self.pour_step + 1;
	org = self.origin + self.pour_dir * (40 + self.pour_step * 52) - '0 0 16';
	traceline (self.origin, org, TRUE, self);
	if (trace_fraction < 1.0)
		return;
	Brute_Splash (org);
};

void() brute_stand1 =[ $bstand1, brute_stand2 ] { ai_stand (); brute_idle (); };
void() brute_stand2 =[ $bstand2, brute_stand3 ] { ai_stand (); };
void() brute_stand3 =[ $bstand3, brute_stand4 ] { ai_stand (); };
void() brute_stand4 =[ $bstand4, brute_stand5 ] { ai_stand (); };
void() brute_stand5 =[ $bstand5, brute_stand6 ] { ai_stand (); };
void() brute_stand6 =[ $bstand6, brute_stand7 ] { ai_stand (); };
void() brute_stand7 =[ $bstand7, brute_stand8 ] { ai_stand (); };
void() brute_stand8 =[ $bstand8, brute_stand9 ] { ai_stand (); };
void() brute_stand9 =[ $bstand9, brute_stand10 ] { ai_stand (); };
void() brute_stand10 =[ $bstand10, brute_stand1 ] { ai_stand (); };
void() brute_walk1 =[ $bwalk1, brute_walk2 ] { ai_walk (3); brute_step (); };
void() brute_walk2 =[ $bwalk2, brute_walk3 ] { ai_walk (5); };
void() brute_walk3 =[ $bwalk3, brute_walk4 ] { ai_walk (6); };
void() brute_walk4 =[ $bwalk4, brute_walk5 ] { ai_walk (4); };
void() brute_walk5 =[ $bwalk5, brute_walk6 ] { ai_walk (3); };
void() brute_walk6 =[ $bwalk6, brute_walk7 ] { ai_walk (5); };
void() brute_walk7 =[ $bwalk7, brute_walk8 ] { ai_walk (3); brute_step (); };
void() brute_walk8 =[ $bwalk8, brute_walk9 ] { ai_walk (5); };
void() brute_walk9 =[ $bwalk9, brute_walk10 ] { ai_walk (6); };
void() brute_walk10 =[ $bwalk10, brute_walk11 ] { ai_walk (4); };
void() brute_walk11 =[ $bwalk11, brute_walk12 ] { ai_walk (3); };
void() brute_walk12 =[ $bwalk12, brute_walk1 ] { ai_walk (5); };

// It never runs: chasing is the same heavy walk.

void() brute_run1 =[ $bwalk1, brute_run2 ] { ai_run (4); brute_step (); brute_idle (); };
void() brute_run2 =[ $bwalk2, brute_run3 ] { ai_run (6); };
void() brute_run3 =[ $bwalk3, brute_run4 ] { ai_run (7); };
void() brute_run4 =[ $bwalk4, brute_run5 ] { ai_run (5); };
void() brute_run5 =[ $bwalk5, brute_run6 ] { ai_run (4); };
void() brute_run6 =[ $bwalk6, brute_run7 ] { ai_run (6); };
void() brute_run7 =[ $bwalk7, brute_run8 ] { ai_run (4); brute_step (); };
void() brute_run8 =[ $bwalk8, brute_run9 ] { ai_run (6); };
void() brute_run9 =[ $bwalk9, brute_run10 ] { ai_run (7); };
void() brute_run10 =[ $bwalk10, brute_run11 ] { ai_run (5); };
void() brute_run11 =[ $bwalk11, brute_run12 ] { ai_run (4); };
void() brute_run12 =[ $bwalk12, brute_run1 ] { ai_run (6); };
void() brute_pour1 =[ $bpour1, brute_pour2 ] { ai_face (); };
void() brute_pour2 =[ $bpour2, brute_pour3 ] { ai_face (); };
void() brute_pour3 =[ $bpour3, brute_pour4 ] { ai_face (); };
void() brute_pour4 =[ $bpour4, brute_pour5 ] { Brute_PourStart (); };
void() brute_pour5 =[ $bpour5, brute_pour6 ] { Brute_PourOn (); };
void() brute_pour6 =[ $bpour6, brute_pour7 ] { Brute_PourOn (); };
void() brute_pour7 =[ $bpour7, brute_pour8 ] { Brute_PourOn (); };
void() brute_pour8 =[ $bpour8, brute_pour9 ] { Brute_PourOn (); };
void() brute_pour9 =[ $bpour9, brute_pour10 ] { Brute_PourOn (); };
void() brute_pour10 =[ $bpour10, brute_pour11 ] { Brute_PourOn (); };
void() brute_pour11 =[ $bpour11, brute_pour12 ] { };
void() brute_pour12 =[ $bpour12, brute_run1 ] { };

// The crucible brought down on whatever's in front: it hurts, and it throws you.
void() Brute_Smash =
{
	local vector d;

	if (!self.enemy || vlen (self.enemy.origin - self.origin) > 120 || !CanDamage (self.enemy, self))
		return;
	sound (self, CHAN_WEAPON, "cinder/brute_hit.wav", 1, ATTN_NORM);
	W_SlagBurst (self.enemy.origin + '0 0 16', 24);
	d = normalize (self.enemy.origin - self.origin);
	self.enemy.velocity = self.enemy.velocity + d * 380 + '0 0 220';
	if (self.enemy.flags & FL_ONGROUND)
		self.enemy.flags = self.enemy.flags - FL_ONGROUND;
	self.enemy.deathtype = "slag";
	T_Damage (self.enemy, self, self, 28 + random () * 10);
};

void() brute_swing1 =[ $bswing1, brute_swing2 ] { ai_face (); };
void() brute_swing2 =[ $bswing2, brute_swing3 ] { ai_face (); };
void() brute_swing3 =[ $bswing3, brute_swing4 ] { ai_face (); sound (self, CHAN_WEAPON, "cinder/brute_swing.wav", 1, ATTN_NORM); };
void() brute_swing4 =[ $bswing4, brute_swing5 ] { ai_charge (4); };
void() brute_swing5 =[ $bswing5, brute_swing6 ] { ai_charge (6); };
void() brute_swing6 =[ $bswing6, brute_swing7 ] { Brute_Smash (); };
void() brute_swing7 =[ $bswing7, brute_swing8 ] { };
void() brute_swing8 =[ $bswing8, brute_swing9 ] { };
void() brute_swing9 =[ $bswing9, brute_swing10 ] { };
void() brute_swing10 =[ $bswing10, brute_run1 ] { };
void() brute_pain1 =[ $bpain1, brute_pain2 ] { };
void() brute_pain2 =[ $bpain2, brute_pain3 ] { };
void() brute_pain3 =[ $bpain3, brute_pain4 ] { };
void() brute_pain4 =[ $bpain4, brute_pain5 ] { };
void() brute_pain5 =[ $bpain5, brute_pain6 ] { };
void() brute_pain6 =[ $bpain6, brute_run1 ] { };

void(entity attacker, float damage) brute_pain =
{
	if (self.pain_finished > time)
		return;
	if (random () * 200 > damage)
		return;
	self.pain_finished = time + 3;
	sound (self, CHAN_VOICE, "cinder/brute_pain.wav", 1, ATTN_NORM);
	brute_pain1 ();
};

void() brute_death1 =[ $bdeath1, brute_death2 ] { };
void() brute_death2 =[ $bdeath2, brute_death3 ] { };
void() brute_death3 =[ $bdeath3, brute_death4 ] { self.solid = SOLID_NOT; };
void() brute_death4 =[ $bdeath4, brute_death5 ] { };
void() brute_death5 =[ $bdeath5, brute_death6 ] { };
void() brute_death6 =[ $bdeath6, brute_death7 ] { };
void() brute_death7 =[ $bdeath7, brute_death8 ] { };
void() brute_death8 =[ $bdeath8, brute_death9 ] { Brute_Splash (self.origin + v_forward * 48); sound (self, CHAN_BODY, "cinder/brute_fall.wav", 1, ATTN_NORM); };
void() brute_death9 =[ $bdeath9, brute_death10 ] { };
void() brute_death10 =[ $bdeath10, brute_death11 ] { };
void() brute_death11 =[ $bdeath11, brute_death12 ] { };
void() brute_death12 =[ $bdeath12, brute_death12 ] { };

void() brute_die =
{
	sound (self, CHAN_VOICE, "cinder/brute_death.wav", 1, ATTN_NORM);
	makevectors (self.angles);
	brute_death1 ();
};

/*
	Swing when close; pour from a few strides out, where the line will reach.
*/
float() BruteCheckAttack =
{
	local float d;

	if (enemy_range == RANGE_MELEE)
	{
		self.attack_state = AS_MELEE;
		return TRUE;
	}
	if (time < self.attack_finished)
		return FALSE;
	d = vlen (self.enemy.origin - self.origin);
	if (d < 360 && fabs (self.enemy.origin_z - self.origin_z) < 64 && random () < 0.4)
	{
		self.attack_state = AS_MISSILE;
		self.attack_finished = time + 2.5 + random ();
		return TRUE;
	}
	return FALSE;
};

/*QUAKED monster_crucible_brute (1 0 0) (-32 -32 -24) (32 32 64) Ambush
A Crucible Brute: pours slag along the floor and swings the crucible close up.
*/
void() monster_crucible_brute =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/brute.md3");
	precache_sound ("cinder/brute_sight.wav");
	precache_sound ("cinder/brute_idle.wav");
	precache_sound ("cinder/brute_step.wav");
	precache_sound ("cinder/brute_pour.wav");
	precache_sound ("cinder/brute_swing.wav");
	precache_sound ("cinder/brute_hit.wav");
	precache_sound ("cinder/brute_pain.wav");
	precache_sound ("cinder/brute_death.wav");
	precache_sound ("cinder/brute_fall.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/brute.md3");
	setsize (self, VEC_HULL2_MIN, VEC_HULL2_MAX);
	self.noise = "cinder/brute_sight.wav";
	self.netname = "Crucible Brute";
	self.killstring = " was poured out by a Crucible Brute";
	self.health = 450;
	self.max_health = self.health;

	self.th_stand = brute_stand1;
	self.th_walk = brute_walk1;
	self.th_run = brute_run1;
	self.th_melee = brute_swing1;
	self.th_missile = brute_pour1;
	self.th_pain = brute_pain;
	self.th_die = brute_die;

	walkmonster_start ();
};

// ----------------------------------------------------------- Clinkers

$framevalue 0
$frame kstand1 kstand2 kstand3 kstand4 kstand5 kstand6
$frame krun1 krun2 krun3 krun4
$frame kburst1 kburst2 kburst3 kburst4 kburst5 kburst6 kburst7 kburst8
$frame kpain1 kpain2 kpain3 kpain4
$frame kdeath1 kdeath2 kdeath3 kdeath4 kdeath5 kdeath6 kdeath7 kdeath8

#define CLINKER_CEILING	2

void() Clinker_Burst =
{
	if (self.deadflag == DEAD_DEAD)
		return;
	self.deadflag = DEAD_DEAD;
	self.takedamage = DAMAGE_NO;
	sound (self, CHAN_VOICE, "cinder/clinker_burst.wav", 1, ATTN_NORM);
	W_SlagBurst (self.origin, 50);
	self.deathtype = "clinker";
	T_RadiusDamage (self, self, 34, world, "clinker");
	traceline (self.origin, self.origin - '0 0 64', TRUE, self);
	W_SlagPool (trace_endpos + '0 0 4');
	ThrowGib ("progs/gib3.mdl", -40);
	remove (self);
};

void() clinker_stand1 =[ $kstand1, clinker_stand2 ] { ai_stand (); };
void() clinker_stand2 =[ $kstand2, clinker_stand3 ] { ai_stand (); };
void() clinker_stand3 =[ $kstand3, clinker_stand4 ] { ai_stand (); };
void() clinker_stand4 =[ $kstand4, clinker_stand5 ] { ai_stand (); };
void() clinker_stand5 =[ $kstand5, clinker_stand6 ] { ai_stand (); };
void() clinker_stand6 =[ $kstand6, clinker_stand1 ] { ai_stand (); };
void() clinker_walk1 =[ $krun1, clinker_walk2 ] { ai_walk (6); };
void() clinker_walk2 =[ $krun2, clinker_walk3 ] { ai_walk (6); };
void() clinker_walk3 =[ $krun3, clinker_walk4 ] { ai_walk (6); };
void() clinker_walk4 =[ $krun4, clinker_walk1 ] { ai_walk (6); };
void() clinker_run1 =[ $krun1, clinker_run2 ] { ai_run (22); sound (self, CHAN_BODY, "cinder/clinker_skitter.wav", 0.5, ATTN_NORM); };
void() clinker_run2 =[ $krun2, clinker_run3 ] { ai_run (18); };
void() clinker_run3 =[ $krun3, clinker_run4 ] { ai_run (22); };
void() clinker_run4 =[ $krun4, clinker_run1 ] { ai_run (18); };
void() clinker_burst1 =[ $kburst1, clinker_burst2 ] { sound (self, CHAN_VOICE, "cinder/clinker_swell.wav", 1, ATTN_NORM); ai_face (); };
void() clinker_burst2 =[ $kburst2, clinker_burst3 ] { ai_charge (6); };
void() clinker_burst3 =[ $kburst3, clinker_burst4 ] { ai_charge (6); };
void() clinker_burst4 =[ $kburst4, clinker_burst5 ] { ai_charge (6); };
void() clinker_burst5 =[ $kburst5, clinker_burst6 ] { ai_charge (6); };
void() clinker_burst6 =[ $kburst6, clinker_burst7 ] { ai_charge (6); };
void() clinker_burst7 =[ $kburst7, clinker_burst8 ] { ai_charge (6); };
void() clinker_burst8 =[ $kburst8, clinker_burst8 ] { Clinker_Burst (); };
void() clinker_pain1 =[ $kpain1, clinker_pain2 ] { };
void() clinker_pain2 =[ $kpain2, clinker_pain3 ] { };
void() clinker_pain3 =[ $kpain3, clinker_pain4 ] { };
void() clinker_pain4 =[ $kpain4, clinker_run1 ] { };

void(entity attacker, float damage) clinker_pain =
{
	clinker_pain1 ();
};

void() clinker_die =
{
	// It bursts as it dies, just a beat late.
	self.solid = SOLID_NOT;
	self.think = Clinker_Burst;
	self.nextthink = time + 0.15;
	self.frame = $kdeath2;
};

void() clinker_fall;

// Hanging from the ceiling: waits for something living to come close below, then drops.
void() clinker_hang =
{
	local entity e;
	local vector d;

	self.nextthink = time + 0.1;
	for (e = find (world, classname, "player"); e; e = find (e, classname, "player"))
	{
		d = e.origin - self.origin;
		d_z = 0;
		if (vlen (d) > 160 || e.health <= 0 || (e.flags & FL_NOTARGET) || !visible (e))
			continue;
		sound (self, CHAN_VOICE, "cinder/clinker_drop.wav", 1, ATTN_NORM);
		self.enemy = e;
		self.movetype = MOVETYPE_TOSS;
		self.velocity = '0 0 -40';
		self.think = clinker_fall;
		return;
	}
};

void() clinker_fall =
{
	self.nextthink = time + 0.05;
	if (!(self.flags & FL_ONGROUND))
		return;
	self.angles_z = 0;
	self.movetype = MOVETYPE_STEP;
	self.goalentity = self.enemy;
	self.ideal_yaw = vectoyaw (self.enemy.origin - self.origin);
	self.th_run ();
};

void() clinker_start_ceiling =
{
	total_monsters = total_monsters + 1;
	traceline (self.origin, self.origin + '0 0 512', TRUE, self);
	setorigin (self, trace_endpos - '0 0 24');
	self.angles_z = 180;
	self.movetype = MOVETYPE_NONE;
	self.takedamage = DAMAGE_AIM;
	self.ideal_yaw = self.angles * '0 1 0';
	self.yaw_speed = 30;
	self.view_ofs = '0 0 0';
	self.use = monster_use;
	self.flags = self.flags | FL_MONSTER;
	self.think = clinker_hang;
	self.nextthink = time + 0.5 + random () * 0.3;
};

/*QUAKED monster_clinker (1 0 0) (-16 -16 -24) (16 16 8) Ambush Ceiling
A clinker: scuttles in and bursts. With Ceiling, it hangs from the ceiling
above until something comes close, then drops.
*/
void() monster_clinker =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/clinker.md3");
	precache_model ("progs/gib3.mdl");
	precache_sound ("cinder/clinker_sight.wav");
	precache_sound ("cinder/clinker_skitter.wav");
	precache_sound ("cinder/clinker_swell.wav");
	precache_sound ("cinder/clinker_burst.wav");
	precache_sound ("cinder/clinker_drop.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/clinker.md3");
	setsize (self, '-16 -16 -24', '16 16 8');
	self.noise = "cinder/clinker_sight.wav";
	self.netname = "clinker";
	self.killstring = " was burst on by a clinker";
	self.health = 20;
	self.max_health = self.health;

	self.th_stand = clinker_stand1;
	self.th_walk = clinker_walk1;
	self.th_run = clinker_run1;
	self.th_melee = clinker_burst1;
	self.th_pain = clinker_pain;
	self.th_die = clinker_die;

	if (self.spawnflags & CLINKER_CEILING)
	{
		self.think = clinker_start_ceiling;
		self.nextthink = time + 0.2;
		return;
	}
	walkmonster_start ();
};

