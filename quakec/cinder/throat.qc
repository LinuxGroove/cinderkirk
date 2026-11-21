/*
	Cinderkirk: the finale, the Throat and the Great Bell.

	The Throat is the pit itself, risen out of its slag under the casting
	floor. Nothing you carry can hurt it. The cracked bell hangs over it on
	four chains, each held by a brake at a corner of the floor: knock a
	brake off (a button that targets the bell) and the bell drops a stage
	and tolls, the toll running out across the floor (jump it) and the
	Throat roaring under it, angrier each time. Knock off the fourth and the
	bell comes down into the Throat and stops it for good, and the game
	ends.

	misc_great_bell: "targetname" for the brakes; "height" how far it falls
	in all (default 640). monster_throat: rises when a player comes within
	1400 of it.
*/

$framevalue 0
$frame bswing1 bswing2 bswing3 bswing4 bswing5 bswing6 bswing7 bswing8 bswing9 bswing10 bswing11 bswing12
$frame bswing13 bswing14 bswing15 bswing16 bswing17 bswing18 bswing19 bswing20 bswing21 bswing22 bswing23 bswing24
$frame bring1 bring2 bring3 bring4 bring5 bring6 bring7 bring8 bring9 bring10 bring11 bring12 bring13 bring14 bring15 bring16

$framevalue 0
$frame trise1 trise2 trise3 trise4 trise5 trise6 trise7 trise8 trise9 trise10 trise11 trise12 trise13 trise14 trise15 trise16
$frame tidle1 tidle2 tidle3 tidle4 tidle5 tidle6 tidle7 tidle8 tidle9 tidle10 tidle11 tidle12
$frame tspit1 tspit2 tspit3 tspit4 tspit5 tspit6 tspit7 tspit8 tspit9 tspit10
$frame troar1 troar2 troar3 troar4 troar5 troar6 troar7 troar8 troar9 troar10 troar11 troar12
$frame tdeath1 tdeath2 tdeath3 tdeath4 tdeath5 tdeath6 tdeath7 tdeath8 tdeath9 tdeath10 tdeath11 tdeath12
$frame tdeath13 tdeath14 tdeath15 tdeath16 tdeath17 tdeath18 tdeath19 tdeath20 tdeath21 tdeath22 tdeath23 tdeath24

void(entity attacker, float damage) throat_pain;

.float bell_stage;	// on the bell: brakes knocked off so far; on the Throat: tolls taken
.float bell_floor;	// on the bell: where its lip stops, the Throat's mouth
.entity throat_bell;	// on the Throat: the bell over it

entity() Throat_Find =
{
	return find (world, classname, "monster_throat");
};

// ------------------------------------------------------------ the bell

void() bell_swing =
{
	self.frame = self.frame + 1;
	if (self.frame < $bswing1 || self.frame > $bswing24)
		self.frame = $bswing1;
	self.nextthink = time + 0.1;
	self.think = bell_swing;
};

void() bell_ringing =
{
	self.frame = self.frame + 1;
	if (self.frame > $bring16)
	{
		self.frame = $bswing1;
		self.think = bell_swing;
	}
	self.nextthink = time + 0.1;
};

// The toll: the bell rings, the ring runs along the floor, the Throat feels it.
void() Bell_Toll =
{
	local entity ring, p, t;

	sound (self, CHAN_VOICE, "cinder/ringer_toll.wav", 1, ATTN_NONE);
	self.frame = $bring1;
	self.think = bell_ringing;
	self.nextthink = time + 0.1;
	ring = spawn ();
	ring.owner = self;
	ring.classname = "toll_ring";
	setorigin (ring, [self.origin_x, self.origin_y, self.dmg + 2]);
	ring.cnt = 360;
	ring.think = toll_ring_think;
	ring.nextthink = time + 0.05;
	for (p = find (world, classname, "player"); p; p = find (p, classname, "player"))
		Rumble (p, "mortar");
	t = Throat_Find ();
	if (t && t.health > 0 && t.takedamage)
	{
		t.bell_stage = self.bell_stage;
		p = self;
		self = t;
		throat_pain (p, 0);
		self = p;
	}
};

void() bell_stop =
{
	self.velocity = '0 0 0';
	if (self.bell_stage >= 4)
	{
		sound (self, CHAN_BODY, "cinder/founder_slam.wav", 1, ATTN_NONE);
		W_SlagBurst (self.origin - [0, 0, self.height], 120);
		self.frame = $bswing1;
		self.think = SUB_Null;
		return;
	}
	Bell_Toll ();
};

// A brake knocked off: drop a stage, or all the way on the last.
void() bell_use =
{
	local float d, speed;

	if (self.bell_stage >= 4)
		return;
	self.bell_stage = self.bell_stage + 1;
	sound (self, CHAN_BODY, "cinder/brute_swing.wav", 1, ATTN_NONE);
	if (self.bell_stage < 4)
	{
		d = self.height * 0.12;
		speed = 90;
	}
	else
	{
		d = self.origin_z - self.bell_floor;
		speed = 420;
		sound (self, CHAN_VOICE, "cinder/ringer_toll.wav", 1, ATTN_NONE);
	}
	self.velocity = [0, 0, -speed];
	self.think = bell_stop;
	self.nextthink = time + d / speed;
};

/*QUAKED misc_great_bell (0 .5 .8) (-16 -16 -16) (16 16 16)
The Great Bell, hung by its crown at this point over the Throat.
"targetname" the brakes; "height" how far down to the Throat's mouth (640);
"dmg" the casting floor's height, for the toll's ring (0).
*/
void() misc_great_bell =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/greatbell.md3");
	precache_sound ("cinder/ringer_toll.wav");
	precache_sound ("cinder/brute_swing.wav");
	precache_sound ("cinder/founder_slam.wav");
	setmodel (self, "progs/greatbell.md3");
	setsize (self, '-16 -16 -16', '16 16 16');
	self.solid = SOLID_NOT;
	self.movetype = MOVETYPE_NOCLIP;
	if (!self.height)
		self.height = 640;
	self.bell_floor = self.origin_z - self.height;
	self.use = bell_use;
	self.frame = $bswing1;
	self.think = bell_swing;
	self.nextthink = time + 0.1 + random ();
};

// ------------------------------------------------------------ the Throat

void() throat_idle1;
void() throat_wait;
void() throat_spit1;

// A gout of live iron up out of the Throat and down on you.
void(entity targ, float spread) Throat_Gout =
{
	local vector org;

	org = self.origin + [crandom () * 64, crandom () * 64, self.maxs_z - 32];
	Founder_Gout (org, targ.origin + [crandom () * spread, crandom () * spread, 0], 700 + random () * 200);
};

entity() Throat_Target =
{
	local entity p, best;
	local float d, bd;

	best = world;
	bd = 99999;
	for (p = find (world, classname, "player"); p; p = find (p, classname, "player"))
	{
		if (p.health <= 0 || (p.flags & FL_NOTARGET))
			continue;
		d = vlen (p.origin - self.origin);
		if (d < bd)
		{
			bd = d;
			best = p;
		}
	}
	return best;
};

void() Throat_Spit =
{
	local entity t;
	local float i, n;

	t = Throat_Target ();
	if (!t)
		return;
	sound (self, CHAN_WEAPON, "cinder/founder_hurl.wav", 1, ATTN_NONE);
	n = 2 + self.bell_stage + skill;
	for (i = 0; i < n; i = i + 1)
		Throat_Gout (t, i == 0 ? 0 : 200);
};

// From the second toll the roof drips iron on whoever is nearest, as the
// Founder's did.
void() Throat_Rain =
{
	local entity t;
	local vector top;

	if (self.bell_stage < 2 || time < self.founder_rain)
		return;
	t = Throat_Target ();
	if (!t)
		return;
	self.founder_rain = time + 3 - self.bell_stage * 0.4 + random ();
	top = t.origin + [crandom () * 128, crandom () * 128, 0];
	traceline (top, top + '0 0 1200', TRUE, t);
	top = trace_endpos - '0 0 8';
	newmis = spawn ();
	newmis.owner = self;
	newmis.classname = "founder_gout";
	newmis.movetype = MOVETYPE_TOSS;
	newmis.solid = SOLID_BBOX;
	newmis.touch = founder_gout_touch;
	newmis.think = SUB_Remove;
	newmis.nextthink = time + 8;
	setmodel (newmis, "progs/lavaball.mdl");
	setsize (newmis, VEC_ORIGIN, VEC_ORIGIN);
	setorigin (newmis, top);
	newmis.velocity = '0 0 -40';
	particle (top, '0 0 -40', 234, 20);
};

void() throat_tick =
{
	Throat_Rain ();
	if (time >= self.attack_finished)
	{
		self.attack_finished = time + 3.2 - self.bell_stage * 0.45 + random ();
		throat_spit1 ();
	}
};

void() throat_idle1 =[ $tidle1, throat_idle2 ] { throat_tick (); };
void() throat_idle2 =[ $tidle2, throat_idle3 ] { throat_tick (); };
void() throat_idle3 =[ $tidle3, throat_idle4 ] { throat_tick (); };
void() throat_idle4 =[ $tidle4, throat_idle5 ] { throat_tick (); };
void() throat_idle5 =[ $tidle5, throat_idle6 ] { throat_tick (); };
void() throat_idle6 =[ $tidle6, throat_idle7 ] { throat_tick (); };
void() throat_idle7 =[ $tidle7, throat_idle8 ] { throat_tick (); };
void() throat_idle8 =[ $tidle8, throat_idle9 ] { throat_tick (); };
void() throat_idle9 =[ $tidle9, throat_idle10 ] { throat_tick (); };
void() throat_idle10 =[ $tidle10, throat_idle11 ] { throat_tick (); };
void() throat_idle11 =[ $tidle11, throat_idle12 ] { throat_tick (); };
void() throat_idle12 =[ $tidle12, throat_idle1 ] { throat_tick (); };

void() throat_spit1 =[ $tspit1, throat_spit2 ] { };
void() throat_spit2 =[ $tspit2, throat_spit3 ] { };
void() throat_spit3 =[ $tspit3, throat_spit4 ] { };
void() throat_spit4 =[ $tspit4, throat_spit5 ] { };
void() throat_spit5 =[ $tspit5, throat_spit6 ] { };
void() throat_spit6 =[ $tspit6, throat_spit7 ] { Throat_Spit (); };
void() throat_spit7 =[ $tspit7, throat_spit8 ] { };
void() throat_spit8 =[ $tspit8, throat_spit9 ] { };
void() throat_spit9 =[ $tspit9, throat_spit10 ] { };
void() throat_spit10 =[ $tspit10, throat_idle1 ] { };

void() throat_roar1 =[ $troar1, throat_roar2 ] { sound (self, CHAN_VOICE, "cinder/founder_pain.wav", 1, ATTN_NONE); };
void() throat_roar2 =[ $troar2, throat_roar3 ] { };
void() throat_roar3 =[ $troar3, throat_roar4 ] { W_SlagBurst (self.origin + [0, 0, self.maxs_z], 60); };
void() throat_roar4 =[ $troar4, throat_roar5 ] { };
void() throat_roar5 =[ $troar5, throat_roar6 ] { };
void() throat_roar6 =[ $troar6, throat_roar7 ] { Throat_Spit (); };
void() throat_roar7 =[ $troar7, throat_roar8 ] { };
void() throat_roar8 =[ $troar8, throat_roar9 ] { };
void() throat_roar9 =[ $troar9, throat_roar10 ] { };
void() throat_roar10 =[ $troar10, throat_roar11 ] { };
void() throat_roar11 =[ $troar11, throat_roar12 ] { };
void() throat_roar12 =[ $troar12, throat_idle1 ] { };

// The ending: the players see the bell come down, then the night shift ends.
void() throat_end =
{
	nextmap = "start";
	execute_changelevel ();
	remove (self);
};

void() throat_death1 =[ $tdeath1, throat_death2 ] { sound (self, CHAN_VOICE, "cinder/founder_death.wav", 1, ATTN_NONE); };
void() throat_death2 =[ $tdeath2, throat_death3 ] { };
void() throat_death3 =[ $tdeath3, throat_death4 ] { W_SlagBurst (self.origin + [0, 0, self.maxs_z], 120); };
void() throat_death4 =[ $tdeath4, throat_death5 ] { };
void() throat_death5 =[ $tdeath5, throat_death6 ] { };
void() throat_death6 =[ $tdeath6, throat_death7 ] { };
void() throat_death7 =[ $tdeath7, throat_death8 ] { };
void() throat_death8 =[ $tdeath8, throat_death9 ] { W_SlagBurst (self.origin + [0, 0, self.maxs_z * 0.6], 120); };
void() throat_death9 =[ $tdeath9, throat_death10 ] { };
void() throat_death10 =[ $tdeath10, throat_death11 ] { };
void() throat_death11 =[ $tdeath11, throat_death12 ] { };
void() throat_death12 =[ $tdeath12, throat_death13 ] { };
void() throat_death13 =[ $tdeath13, throat_death14 ] { };
void() throat_death14 =[ $tdeath14, throat_death15 ] { };
void() throat_death15 =[ $tdeath15, throat_death16 ] { };
void() throat_death16 =[ $tdeath16, throat_death17 ] { };
void() throat_death17 =[ $tdeath17, throat_death18 ] { };
void() throat_death18 =[ $tdeath18, throat_death19 ] { };
void() throat_death19 =[ $tdeath19, throat_death20 ] { };
void() throat_death20 =[ $tdeath20, throat_death21 ] { };
void() throat_death21 =[ $tdeath21, throat_death22 ] { };
void() throat_death22 =[ $tdeath22, throat_death23 ] { };
void() throat_death23 =[ $tdeath23, throat_death24 ] { };
void() throat_death24 =[ $tdeath24, throat_death24 ] { self.think = SUB_Null; self.modelindex = 0; };

void() Throat_Dies =
{
	local entity e;

	self.health = 0;
	self.takedamage = DAMAGE_NO;
	self.solid = SOLID_NOT;
	killed_monsters = killed_monsters + 1;
	WriteByte (MSG_ALL, SVC_KILLEDMONSTER);
	SUB_UseTargets ();
	for (e = find (world, classname, "player"); e; e = find (e, classname, "player"))
		Rumble (e, "death");
	throat_death1 ();
	e = spawn ();
	e.think = throat_end;
	e.nextthink = time + 6;
};

// Nothing a player carries hurts it; the bell's tolls do, and the fourth
// stops it.
void(entity attacker, float damage) throat_pain =
{
	self.health = 100000;
	if (attacker.classname != "misc_great_bell")
	{
		if (time > self.pain_finished)
		{
			self.pain_finished = time + 8;
			if (attacker.classname == "player")
				centerprint (attacker, "Nothing you carry can hurt it.\nThe bell hangs over it on four chains.");
		}
		return;
	}
	if (self.bell_stage >= 4)
	{
		Throat_Dies ();
		return;
	}
	throat_roar1 ();
};

// The landing: the bell's last fall finishes it, whatever the Throat is doing.
void() throat_watcher =
{
	local entity t, oself;

	t = self.owner;
	if (!t || t.health <= 0)
	{
		remove (self);
		return;
	}
	if (!t.throat_bell)
		t.throat_bell = find (world, classname, "misc_great_bell");
	if (t.throat_bell && t.throat_bell.bell_stage >= 4 && t.throat_bell.velocity == '0 0 0')
	{
		oself = self;
		self = t;
		Throat_Dies ();
		self = oself;
		remove (self);
		return;
	}
	self.nextthink = time + 0.1;
};

void() throat_rise1 =[ $trise1, throat_rise2 ] { sound (self, CHAN_VOICE, "cinder/founder_sight.wav", 1, ATTN_NONE); };
void() throat_rise2 =[ $trise2, throat_rise3 ] { };
void() throat_rise3 =[ $trise3, throat_rise4 ] { W_SlagBurst (self.origin + '0 0 32', 100); };
void() throat_rise4 =[ $trise4, throat_rise5 ] { };
void() throat_rise5 =[ $trise5, throat_rise6 ] { };
void() throat_rise6 =[ $trise6, throat_rise7 ] { };
void() throat_rise7 =[ $trise7, throat_rise8 ] { };
void() throat_rise8 =[ $trise8, throat_rise9 ] { };
void() throat_rise9 =[ $trise9, throat_rise10 ] { };
void() throat_rise10 =[ $trise10, throat_rise11 ] { };
void() throat_rise11 =[ $trise11, throat_rise12 ] { };
void() throat_rise12 =[ $trise12, throat_rise13 ] { };
void() throat_rise13 =[ $trise13, throat_rise14 ] { };
void() throat_rise14 =[ $trise14, throat_rise15 ] { };
void() throat_rise15 =[ $trise15, throat_rise16 ] { };
void() throat_rise16 =[ $trise16, throat_idle1 ]
{
	self.solid = SOLID_BBOX;
	self.takedamage = DAMAGE_YES;
	setsize (self, '-128 -128 -24', '128 128 416');
	self.attack_finished = time + 2;
};

// Under the slag, waiting for someone to come near.
void() throat_wait =
{
	local entity p;

	self.nextthink = time + 0.25;
	for (p = find (world, classname, "player"); p; p = find (p, classname, "player"))
		if (p.health > 0 && vlen (p.origin - self.origin) < 1400)
		{
			self.modelindex = self.cnt;
			throat_rise1 ();
			return;
		}
};

/*QUAKED monster_throat (1 0 0) (-128 -128 -24) (128 128 416)
The Throat, the finale's boss, standing in the slag under the casting
floor. Only the Great Bell can stop it. Its target fires when it dies.
*/
void() monster_throat =
{
	local entity watcher;

	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/throat.md3");
	precache_model ("progs/lavaball.mdl");
	precache_sound ("cinder/founder_sight.wav");
	precache_sound ("cinder/founder_hurl.wav");
	precache_sound ("cinder/founder_pain.wav");
	precache_sound ("cinder/founder_death.wav");
	precache_sound ("cinder/coal_hit.wav");
	setmodel (self, "progs/throat.md3");
	self.cnt = self.modelindex;
	self.modelindex = 0;
	setsize (self, '-128 -128 -24', '128 128 416');
	self.solid = SOLID_NOT;
	self.movetype = MOVETYPE_NONE;
	self.takedamage = DAMAGE_NO;
	self.health = 100000;
	self.max_health = 100000;
	self.netname = "the Throat";
	self.th_pain = throat_pain;
	self.th_die = Throat_Dies;
	self.flags = self.flags | FL_MONSTER;
	total_monsters = total_monsters + 1;
	self.think = throat_wait;
	self.nextthink = time + 1;
	// A second eye on the bell, so its last fall finishes the Throat even
	// while it's busy spitting.
	watcher = spawn ();
	watcher.owner = self;
	watcher.think = throat_watcher;
	watcher.nextthink = time + 1;
};
