/*
	Slag hounds (game-ideas idea 25): lean dogs of cooled slag with their ribs
	open and molten. They hunt in packs: they close fast, circle the prey at a
	distance, and take turns to lunge. Killed, one cools and cracks; hit hard
	enough, it bursts in a spray of slag.

	The model is assets_src/models/creatures.py's; its frames come in this
	order.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

$framevalue 0
$frame hstand1 hstand2 hstand3 hstand4 hstand5 hstand6 hstand7 hstand8 hstand9 hstand10
$frame hwalk1 hwalk2 hwalk3 hwalk4 hwalk5 hwalk6 hwalk7 hwalk8
$frame hrun1 hrun2 hrun3 hrun4 hrun5 hrun6
$frame hbite1 hbite2 hbite3 hbite4 hbite5 hbite6 hbite7 hbite8
$frame hleap1 hleap2 hleap3 hleap4 hleap5 hleap6 hleap7 hleap8 hleap9
$frame hpain1 hpain2 hpain3 hpain4 hpain5
$frame hdeath1 hdeath2 hdeath3 hdeath4 hdeath5 hdeath6 hdeath7 hdeath8 hdeath9 hdeath10

#define HOUND_HEALTH	35
#define HOUND_BURST	-30

.float	hound_circle;	// circling the prey until this time
float	hound_lunged;	// when any hound last lunged: the pack takes turns

void() hound_run1;
void() hound_leap1;

void() hound_idle =
{
	if (random () < 0.1)
		sound (self, CHAN_VOICE, "cinder/hound_idle.wav", 0.8, ATTN_IDLE);
};

void() hound_stand1 =[ $hstand1, hound_stand2 ] { ai_stand (); hound_idle (); };
void() hound_stand2 =[ $hstand2, hound_stand3 ] { ai_stand (); };
void() hound_stand3 =[ $hstand3, hound_stand4 ] { ai_stand (); };
void() hound_stand4 =[ $hstand4, hound_stand5 ] { ai_stand (); };
void() hound_stand5 =[ $hstand5, hound_stand6 ] { ai_stand (); };
void() hound_stand6 =[ $hstand6, hound_stand7 ] { ai_stand (); };
void() hound_stand7 =[ $hstand7, hound_stand8 ] { ai_stand (); };
void() hound_stand8 =[ $hstand8, hound_stand9 ] { ai_stand (); };
void() hound_stand9 =[ $hstand9, hound_stand10 ] { ai_stand (); };
void() hound_stand10 =[ $hstand10, hound_stand1 ] { ai_stand (); };

void() hound_walk1 =[ $hwalk1, hound_walk2 ] { ai_walk (8); hound_idle (); };
void() hound_walk2 =[ $hwalk2, hound_walk3 ] { ai_walk (8); };
void() hound_walk3 =[ $hwalk3, hound_walk4 ] { ai_walk (8); };
void() hound_walk4 =[ $hwalk4, hound_walk5 ] { ai_walk (8); };
void() hound_walk5 =[ $hwalk5, hound_walk6 ] { ai_walk (8); };
void() hound_walk6 =[ $hwalk6, hound_walk7 ] { ai_walk (8); };
void() hound_walk7 =[ $hwalk7, hound_walk8 ] { ai_walk (8); };
void() hound_walk8 =[ $hwalk8, hound_walk1 ] { ai_walk (8); };

// Faster than a stoker on foot, so running away doesn't work; circling slows them.
void(float dist) hound_run =
{
	if (self.attack_state == AS_SLIDING)
		dist = dist * 0.6;
	ai_run (dist);
};

void() hound_run1 =[ $hrun1, hound_run2 ] { hound_run (24); hound_idle (); };
void() hound_run2 =[ $hrun2, hound_run3 ] { hound_run (40); };
void() hound_run3 =[ $hrun3, hound_run4 ] { hound_run (48); };
void() hound_run4 =[ $hrun4, hound_run5 ] { hound_run (24); };
void() hound_run5 =[ $hrun5, hound_run6 ] { hound_run (40); };
void() hound_run6 =[ $hrun6, hound_run1 ] { hound_run (44); };

void() hound_snap =
{
	local float dmg;

	if (!self.enemy || vlen (self.enemy.origin - self.origin) > 90)
		return;
	if (!CanDamage (self.enemy, self))
		return;
	dmg = 6 + random () * 8;
	sound (self, CHAN_WEAPON, "cinder/hound_bite.wav", 1, ATTN_NORM);
	makevectors (self.angles);
	SpawnBlood (self.enemy.origin + v_forward * -8 + '0 0 8', '0 0 0', dmg);
	T_Damage (self.enemy, self, self, dmg);
};

void() hound_bite1 =[ $hbite1, hound_bite2 ] { ai_charge (8); };
void() hound_bite2 =[ $hbite2, hound_bite3 ] { ai_charge (8); };
void() hound_bite3 =[ $hbite3, hound_bite4 ] { ai_charge (10); };
void() hound_bite4 =[ $hbite4, hound_bite5 ] { ai_charge (10); };
void() hound_bite5 =[ $hbite5, hound_bite6 ] { hound_snap (); };
void() hound_bite6 =[ $hbite6, hound_bite7 ] { ai_charge (4); };
void() hound_bite7 =[ $hbite7, hound_bite8 ] { ai_face (); };
void() hound_bite8 =[ $hbite8, hound_run1 ] { ai_face (); };

// The lunge lands once on whoever it hits, then the hound finds its feet.
void() hound_leap_touch =
{
	local float dmg;

	if (self.health <= 0)
		return;
	if (other.takedamage && vlen (self.velocity) > 300 && self.count < time)
	{
		dmg = 12 + random () * 8;
		sound (self, CHAN_WEAPON, "cinder/hound_bite.wav", 1, ATTN_NORM);
		T_Damage (other, self, self, dmg);
		self.count = time + 0.5;
	}
	if (!checkbottom (self))
	{
		if (self.flags & FL_ONGROUND)
		{
			self.touch = __NULL__;
			self.think = hound_leap1;
			self.nextthink = time + 0.1;
		}
		return;
	}
	self.touch = __NULL__;
	self.think = hound_run1;
	self.nextthink = time + 0.1;
};

void() hound_leap1 =[ $hleap1, hound_leap2 ] { ai_face (); };
void() hound_leap2 =[ $hleap2, hound_leap3 ]
{
	ai_face ();
	sound (self, CHAN_VOICE, "cinder/hound_leap.wav", 1, ATTN_NORM);
};
void() hound_leap3 =[ $hleap3, hound_leap4 ]
{
	ai_face ();
	self.touch = hound_leap_touch;
	makevectors (self.angles);
	self.origin_z = self.origin_z + 1;
	self.velocity = v_forward * 440 + '0 0 210';
	if (self.flags & FL_ONGROUND)
		self.flags = self.flags - FL_ONGROUND;
};
void() hound_leap4 =[ $hleap4, hound_leap5 ] { };
void() hound_leap5 =[ $hleap5, hound_leap6 ] { };
void() hound_leap6 =[ $hleap6, hound_leap7 ] { };
void() hound_leap7 =[ $hleap7, hound_leap8 ] { };
void() hound_leap8 =[ $hleap8, hound_leap9 ] { };
void() hound_leap9 =[ $hleap9, hound_leap9 ] { };

void() hound_pain1 =[ $hpain1, hound_pain2 ] { };
void() hound_pain2 =[ $hpain2, hound_pain3 ] { ai_back (6); };
void() hound_pain3 =[ $hpain3, hound_pain4 ] { ai_back (4); };
void() hound_pain4 =[ $hpain4, hound_pain5 ] { };
void() hound_pain5 =[ $hpain5, hound_run1 ] { };

void(entity attacker, float damage) hound_pain =
{
	if (self.pain_finished > time)
		return;
	self.pain_finished = time + 1;
	sound (self, CHAN_VOICE, "cinder/hound_pain.wav", 1, ATTN_NORM);
	// Hurt, it breaks off circling and comes straight in.
	self.hound_circle = 0;
	if (self.attack_state == AS_SLIDING)
		self.attack_state = AS_STRAIGHT;
	hound_pain1 ();
};

void() hound_die1 =[ $hdeath1, hound_die2 ] { };
void() hound_die2 =[ $hdeath2, hound_die3 ] { };
void() hound_die3 =[ $hdeath3, hound_die4 ] { self.solid = SOLID_NOT; };
void() hound_die4 =[ $hdeath4, hound_die5 ] { };
void() hound_die5 =[ $hdeath5, hound_die6 ] { };
void() hound_die6 =[ $hdeath6, hound_die7 ] { W_SlagBurst (self.origin, 12); };
void() hound_die7 =[ $hdeath7, hound_die8 ] { };
void() hound_die8 =[ $hdeath8, hound_die9 ] { };
void() hound_die9 =[ $hdeath9, hound_die10 ] { };
void() hound_die10 =[ $hdeath10, hound_die10 ] { };

void() hound_die =
{
	if (self.health < HOUND_BURST)
	{
		sound (self, CHAN_VOICE, "cinder/hound_burst.wav", 1, ATTN_NORM);
		ThrowGib ("progs/gib3.mdl", self.health);
		ThrowGib ("progs/gib3.mdl", self.health);
		W_SlagBurst (self.origin, 30);
		remove (self);
		return;
	}
	sound (self, CHAN_VOICE, "cinder/hound_death.wav", 1, ATTN_NORM);
	hound_die1 ();
};

/*
	Bite when close; lunge from a few strides out when no other hound has
	just lunged; otherwise, now and then, circle at a distance for a while.
*/
float() HoundCheckAttack =
{
	local vector	delta;
	local float	d;

	if (enemy_range == RANGE_MELEE)
	{
		self.attack_state = AS_MELEE;
		return TRUE;
	}
	if (time < self.attack_finished)
		return FALSE;

	delta = self.enemy.origin - self.origin;
	delta_z = 0;
	d = vlen (delta);
	if (d > 90 && d < 240
		&& self.origin_z + self.mins_z < self.enemy.origin_z + self.enemy.mins_z + 0.75 * self.enemy.size_z
		&& self.origin_z + self.maxs_z > self.enemy.origin_z + self.enemy.mins_z + 0.25 * self.enemy.size_z
		&& time > hound_lunged + 0.7 && random () < 0.5)
	{
		hound_lunged = time;
		self.hound_circle = 0;
		self.attack_state = AS_MISSILE;
		self.attack_finished = time + 1.5 + random ();
		return TRUE;
	}

	if (self.attack_state == AS_SLIDING)
	{
		if (time > self.hound_circle || d < 90 || d > 420)
			self.attack_state = AS_STRAIGHT;
		return FALSE;
	}
	if (d > 140 && d < 380 && random () < 0.15)
	{
		self.attack_state = AS_SLIDING;
		self.hound_circle = time + 0.8 + random () * 1.4;
		self.lefty = random () < 0.5;
	}
	return FALSE;
};

/*QUAKED monster_slag_hound (1 0 0) (-16 -16 -24) (16 16 24) Ambush
A slag hound: hunts in packs, circles and lunges.
*/
void() monster_slag_hound =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/hound.md3");
	precache_model ("progs/gib3.mdl");
	precache_sound ("cinder/hound_sight.wav");
	precache_sound ("cinder/hound_idle.wav");
	precache_sound ("cinder/hound_bite.wav");
	precache_sound ("cinder/hound_leap.wav");
	precache_sound ("cinder/hound_pain.wav");
	precache_sound ("cinder/hound_death.wav");
	precache_sound ("cinder/hound_burst.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/hound.md3");
	setsize (self, '-16 -16 -24', '16 16 24');
	self.noise = "cinder/hound_sight.wav";
	self.netname = "slag hound";
	self.killstring = " was run down by slag hounds";
	self.health = HOUND_HEALTH;
	self.max_health = self.health;

	self.th_stand = hound_stand1;
	self.th_walk = hound_walk1;
	self.th_run = hound_run1;
	self.th_melee = hound_bite1;
	self.th_missile = hound_leap1;
	self.th_pain = hound_pain;
	self.th_die = hound_die;

	walkmonster_start ();
};
