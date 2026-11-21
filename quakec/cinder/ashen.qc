/*
	The Ashen: the dead risen from the ash (game-ideas idea 25). Slow, in
	crowds, clawing and grabbing. Killed, one crumbles to a pile of ash that
	a Deacon's bell can raise again; hit hard enough, it bursts and stays down.

	The model is assets_src/models/creatures.py's; its frames come in this
	order.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

$framevalue 0
$frame stand1 stand2 stand3 stand4 stand5 stand6 stand7 stand8 stand9 stand10
$frame walk1 walk2 walk3 walk4 walk5 walk6 walk7 walk8 walk9 walk10 walk11 walk12
$frame run1 run2 run3 run4 run5 run6 run7 run8
$frame atta1 atta2 atta3 atta4 atta5 atta6 atta7 atta8
$frame attb1 attb2 attb3 attb4 attb5 attb6 attb7 attb8 attb9
$frame pain1 pain2 pain3 pain4 pain5 pain6
$frame death1 death2 death3 death4 death5 death6 death7 death8 death9 death10 death11 death12
$frame rise1 rise2 rise3 rise4 rise5 rise6 rise7 rise8 rise9 rise10 rise11 rise12

#define ASHEN_HEALTH	60
#define ASHEN_BURST	-35	// health below this bursts the body: no pile to raise

void() ashen_idle =
{
	if (random () < 0.08)
		sound (self, CHAN_VOICE, "cinder/ashen_idle.wav", 0.8, ATTN_IDLE);
};

void() ashen_stand1 =[ $stand1, ashen_stand2 ] { ai_stand (); ashen_idle (); };
void() ashen_stand2 =[ $stand2, ashen_stand3 ] { ai_stand (); };
void() ashen_stand3 =[ $stand3, ashen_stand4 ] { ai_stand (); };
void() ashen_stand4 =[ $stand4, ashen_stand5 ] { ai_stand (); };
void() ashen_stand5 =[ $stand5, ashen_stand6 ] { ai_stand (); };
void() ashen_stand6 =[ $stand6, ashen_stand7 ] { ai_stand (); };
void() ashen_stand7 =[ $stand7, ashen_stand8 ] { ai_stand (); };
void() ashen_stand8 =[ $stand8, ashen_stand9 ] { ai_stand (); };
void() ashen_stand9 =[ $stand9, ashen_stand10 ] { ai_stand (); };
void() ashen_stand10 =[ $stand10, ashen_stand1 ] { ai_stand (); };

void() ashen_walk1 =[ $walk1, ashen_walk2 ] { ai_walk (3); ashen_idle (); };
void() ashen_walk2 =[ $walk2, ashen_walk3 ] { ai_walk (2); };
void() ashen_walk3 =[ $walk3, ashen_walk4 ] { ai_walk (1); };
void() ashen_walk4 =[ $walk4, ashen_walk5 ] { ai_walk (2); };
void() ashen_walk5 =[ $walk5, ashen_walk6 ] { ai_walk (3); };
void() ashen_walk6 =[ $walk6, ashen_walk7 ] { ai_walk (2); };
void() ashen_walk7 =[ $walk7, ashen_walk8 ] { ai_walk (3); };
void() ashen_walk8 =[ $walk8, ashen_walk9 ] { ai_walk (2); };
void() ashen_walk9 =[ $walk9, ashen_walk10 ] { ai_walk (1); };
void() ashen_walk10 =[ $walk10, ashen_walk11 ] { ai_walk (2); };
void() ashen_walk11 =[ $walk11, ashen_walk12 ] { ai_walk (3); };
void() ashen_walk12 =[ $walk12, ashen_walk1 ] { ai_walk (2); };

void() ashen_run1 =[ $run1, ashen_run2 ] { ai_run (7); ashen_idle (); };
void() ashen_run2 =[ $run2, ashen_run3 ] { ai_run (5); };
void() ashen_run3 =[ $run3, ashen_run4 ] { ai_run (4); };
void() ashen_run4 =[ $run4, ashen_run5 ] { ai_run (6); };
void() ashen_run5 =[ $run5, ashen_run6 ] { ai_run (7); };
void() ashen_run6 =[ $run6, ashen_run7 ] { ai_run (5); };
void() ashen_run7 =[ $run7, ashen_run8 ] { ai_run (4); };
void() ashen_run8 =[ $run8, ashen_run1 ] { ai_run (6); };

// A blow that lands if the enemy is still in reach.
void(float reach, float dmg) ashen_hit =
{
	if (!self.enemy || vlen (self.enemy.origin - self.origin) > reach)
		return;
	if (!CanDamage (self.enemy, self))
		return;
	sound (self, CHAN_WEAPON, "cinder/ashen_hit.wav", 1, ATTN_NORM);
	makevectors (self.angles);
	SpawnBlood (self.enemy.origin + v_forward * -8 + '0 0 16', '0 0 0', dmg);
	T_Damage (self.enemy, self, self, dmg);
};

// The claw: a wide swipe.
void() ashen_atta1 =[ $atta1, ashen_atta2 ] { ai_face (); };
void() ashen_atta2 =[ $atta2, ashen_atta3 ] { ai_face (); sound (self, CHAN_WEAPON, "cinder/ashen_swipe.wav", 1, ATTN_NORM); };
void() ashen_atta3 =[ $atta3, ashen_atta4 ] { ai_charge (4); };
void() ashen_atta4 =[ $atta4, ashen_atta5 ] { ai_charge (4); };
void() ashen_atta5 =[ $atta5, ashen_atta6 ] { ai_charge (2); ashen_hit (68, 8 + random () * 6); };
void() ashen_atta6 =[ $atta6, ashen_atta7 ] { ai_charge (0); };
void() ashen_atta7 =[ $atta7, ashen_atta8 ] { ai_face (); };
void() ashen_atta8 =[ $atta8, ashen_run1 ] { ai_face (); };

// The grab: both hands, a lunge forward.
void() ashen_attb1 =[ $attb1, ashen_attb2 ] { ai_face (); sound (self, CHAN_VOICE, "cinder/ashen_sight.wav", 0.8, ATTN_NORM); };
void() ashen_attb2 =[ $attb2, ashen_attb3 ] { ai_charge (2); };
void() ashen_attb3 =[ $attb3, ashen_attb4 ] { ai_charge (6); };
void() ashen_attb4 =[ $attb4, ashen_attb5 ] { ai_charge (10); };
void() ashen_attb5 =[ $attb5, ashen_attb6 ] { ai_charge (8); };
void() ashen_attb6 =[ $attb6, ashen_attb7 ] { ai_charge (2); ashen_hit (72, 12 + random () * 6); };
void() ashen_attb7 =[ $attb7, ashen_attb8 ] { ai_charge (0); };
void() ashen_attb8 =[ $attb8, ashen_attb9 ] { ai_face (); };
void() ashen_attb9 =[ $attb9, ashen_run1 ] { ai_face (); };

void() ashen_melee =
{
	if (random () < 0.6)
		ashen_atta1 ();
	else
		ashen_attb1 ();
};

void() ashen_pain1 =[ $pain1, ashen_pain2 ] { ai_painforward (-4); };
void() ashen_pain2 =[ $pain2, ashen_pain3 ] { ai_painforward (-2); };
void() ashen_pain3 =[ $pain3, ashen_pain4 ] { };
void() ashen_pain4 =[ $pain4, ashen_pain5 ] { };
void() ashen_pain5 =[ $pain5, ashen_pain6 ] { };
void() ashen_pain6 =[ $pain6, ashen_run1 ] { };

void(entity attacker, float damage) ashen_pain =
{
	if (self.pain_finished > time)
		return;
	sound (self, CHAN_VOICE, "cinder/ashen_pain.wav", 1, ATTN_NORM);
	self.pain_finished = time + 1 + random ();
	if (random () * 40 < damage)
		ashen_pain1 ();
};

// The pile it leaves: it lies there until a Deacon's bell raises it.
void() ashen_pile =
{
	self.classname = "ash_pile";
	// A trigger, not SOLID_NOT: findradius skips those, and the Deacons look for piles with it.
	self.solid = SOLID_TRIGGER;
	setsize (self, '-16 -16 -24', '16 16 -12');
	self.nextthink = -1;
};

void() ashen_die1 =[ $death1, ashen_die2 ] { };
void() ashen_die2 =[ $death2, ashen_die3 ] { };
void() ashen_die3 =[ $death3, ashen_die4 ] { self.solid = SOLID_NOT; };
void() ashen_die4 =[ $death4, ashen_die5 ] { W_SlagBurst (self.origin + '0 0 20', 6); };
void() ashen_die5 =[ $death5, ashen_die6 ] { };
void() ashen_die6 =[ $death6, ashen_die7 ] { W_SlagBurst (self.origin, 6); };
void() ashen_die7 =[ $death7, ashen_die8 ] { };
void() ashen_die8 =[ $death8, ashen_die9 ] { };
void() ashen_die9 =[ $death9, ashen_die10 ] { };
void() ashen_die10 =[ $death10, ashen_die11 ] { };
void() ashen_die11 =[ $death11, ashen_die12 ] { };
void() ashen_die12 =[ $death12, ashen_die12 ] { ashen_pile (); };

void() ashen_die =
{
	if (self.health < ASHEN_BURST)
	{
		sound (self, CHAN_VOICE, "cinder/ashen_burst.wav", 1, ATTN_NORM);
		particle (self.origin + '0 0 10', '0 0 60', 4, 160);
		particle (self.origin + '0 0 10', '0 0 30', 234, 40);
		self.solid = SOLID_NOT;
		self.modelindex = 0;
		self.think = SUB_Remove;
		self.nextthink = time + 0.1;
		return;
	}
	sound (self, CHAN_VOICE, "cinder/ashen_death.wav", 1, ATTN_NORM);
	ashen_die1 ();
};

// Back up from the pile, raised by a Deacon (self is the pile).
void() ashen_up =
{
	self.classname = "monster_ashen";
	self.solid = SOLID_SLIDEBOX;
	setsize (self, '-16 -16 -24', '16 16 40');
	self.health = ASHEN_HEALTH * 0.7;
	self.takedamage = DAMAGE_AIM;
	self.deadflag = DEAD_NO;
	self.ash_raised = TRUE;
	self.pain_finished = 0;
	if (self.enemy && self.enemy.health > 0 && self.enemy.classname == "player")
	{
		self.goalentity = self.enemy;
		self.th_run ();
	}
	else
	{
		self.enemy = world;
		self.th_stand ();
	}
};

void() ashen_rise1 =[ $rise1, ashen_rise2 ] { sound (self, CHAN_VOICE, "cinder/ashen_rise.wav", 1, ATTN_NORM); };
void() ashen_rise2 =[ $rise2, ashen_rise3 ] { W_SlagBurst (self.origin, 4); };
void() ashen_rise3 =[ $rise3, ashen_rise4 ] { };
void() ashen_rise4 =[ $rise4, ashen_rise5 ] { };
void() ashen_rise5 =[ $rise5, ashen_rise6 ] { W_SlagBurst (self.origin + '0 0 16', 4); };
void() ashen_rise6 =[ $rise6, ashen_rise7 ] { };
void() ashen_rise7 =[ $rise7, ashen_rise8 ] { };
void() ashen_rise8 =[ $rise8, ashen_rise9 ] { };
void() ashen_rise9 =[ $rise9, ashen_rise10 ] { };
void() ashen_rise10 =[ $rise10, ashen_rise11 ] { };
void() ashen_rise11 =[ $rise11, ashen_rise12 ] { };
void() ashen_rise12 =[ $rise12, ashen_run1 ] { ashen_up (); };

// Raises the pile p if nothing stands on it; foe is who it goes after.
float(entity p, entity foe) Ashen_Raise =
{
	local entity e, oself;

	if (p.classname != "ash_pile")
		return FALSE;
	for (e = findradius (p.origin, 40); e; e = e.chain)
		if (e != p && e.solid == SOLID_SLIDEBOX && e.health > 0)
			return FALSE;
	oself = self;
	self = p;
	self.classname = "ash_rising";
	self.enemy = foe;
	ashen_rise1 ();
	self = oself;
	return TRUE;
};

/*QUAKED monster_ashen (1 0 0) (-16 -16 -24) (16 16 40) Ambush
The dead risen from the ash. Slow, and they come in crowds.
*/
void() monster_ashen =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/ashen.md3");
	precache_sound ("cinder/ashen_idle.wav");
	precache_sound ("cinder/ashen_sight.wav");
	precache_sound ("cinder/ashen_pain.wav");
	precache_sound ("cinder/ashen_death.wav");
	precache_sound ("cinder/ashen_burst.wav");
	precache_sound ("cinder/ashen_rise.wav");
	precache_sound ("cinder/ashen_swipe.wav");
	precache_sound ("cinder/ashen_hit.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/ashen.md3");
	setsize (self, '-16 -16 -24', '16 16 40');
	self.noise = "cinder/ashen_sight.wav";
	self.netname = "Ashen";
	self.killstring = " was torn apart by the Ashen";
	self.health = ASHEN_HEALTH;
	self.max_health = ASHEN_HEALTH;

	self.th_stand = ashen_stand1;
	self.th_walk = ashen_walk1;
	self.th_run = ashen_run1;
	self.th_melee = ashen_melee;
	self.th_pain = ashen_pain;
	self.th_die = ashen_die;

	walkmonster_start ();
};
