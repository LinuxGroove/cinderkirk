/*
	Cinderkirk: the Undervein's master, the Founder.

	The man who cast the bell, grown into his own last mould. He pours iron
	from his hands along the floor at you, flings gouts of it that burn
	where they land, and brings his fists down when you're close so the
	floor rings out round him (jump it, as with the bell-ringers' toll).
	Below half his health the mould's iron runs out of the roof over you as
	well, and he works faster. His death fires his target, so the map's
	cope over the Vein Seal lifts.
*/

$framevalue 0
$frame fstand1 fstand2 fstand3 fstand4 fstand5 fstand6 fstand7 fstand8 fstand9 fstand10
$frame fwalk1 fwalk2 fwalk3 fwalk4 fwalk5 fwalk6 fwalk7 fwalk8 fwalk9 fwalk10 fwalk11 fwalk12
$frame fpour1 fpour2 fpour3 fpour4 fpour5 fpour6 fpour7 fpour8 fpour9 fpour10 fpour11 fpour12 fpour13 fpour14 fpour15 fpour16
$frame fhurl1 fhurl2 fhurl3 fhurl4 fhurl5 fhurl6 fhurl7 fhurl8 fhurl9 fhurl10 fhurl11 fhurl12
$frame fslam1 fslam2 fslam3 fslam4 fslam5 fslam6 fslam7 fslam8 fslam9 fslam10 fslam11 fslam12
$frame fpain1 fpain2 fpain3 fpain4 fpain5 fpain6
$frame fdeath1 fdeath2 fdeath3 fdeath4 fdeath5 fdeath6 fdeath7 fdeath8 fdeath9 fdeath10
$frame fdeath11 fdeath12 fdeath13 fdeath14 fdeath15 fdeath16 fdeath17 fdeath18 fdeath19 fdeath20

.float founder_move;	// which ranged attack he chose: 1 pour, 2 hurl
.float founder_rain;	// when the roof next drips iron, once he's past half health

void() founder_run1;

void() founder_idle =
{
	if (random () < 0.08)
		sound (self, CHAN_VOICE, "cinder/founder_idle.wav", 1, ATTN_NORM);
};

float() Founder_Angry =
{
	return self.health < self.max_health * 0.5;
};

// A gout of iron: it burns what it hits and leaves a pool where it lands.
void() founder_gout_touch =
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
		T_Damage (other, self, self.owner, 22);
	}
	T_RadiusDamage (self, self.owner, 24, other, "slag");
	sound (self, CHAN_WEAPON, "cinder/coal_hit.wav", 1, ATTN_NORM);
	W_SlagBurst (self.origin, 30);
	W_SlagPool (self.origin);
	remove (self);
};

void(vector org, vector aimat, float speed) Founder_Gout =
{
	newmis = spawn ();
	newmis.owner = self;
	newmis.classname = "founder_gout";
	newmis.movetype = MOVETYPE_TOSS;
	newmis.solid = SOLID_BBOX;
	newmis.touch = founder_gout_touch;
	newmis.think = SUB_Remove;
	newmis.nextthink = time + 6;
	setmodel (newmis, "progs/lavaball.mdl");
	setsize (newmis, VEC_ORIGIN, VEC_ORIGIN);
	setorigin (newmis, org);
	newmis.velocity = Cult_Lob (org, aimat, speed);
	newmis.avelocity = '200 300 100';
	newmis.angles = vectoangles (newmis.velocity);
};

// The hurl: one gout at you, and more spread round you once he's angry.
void() Founder_Hurl =
{
	local vector org;
	local float i, n;

	if (!self.enemy)
		return;
	makevectors (self.angles);
	org = self.origin + v_forward * 40 - v_right * 40 + '0 0 110';
	sound (self, CHAN_WEAPON, "cinder/founder_hurl.wav", 1, ATTN_NORM);
	Founder_Gout (org, self.enemy.origin, 640);
	n = Founder_Angry () ? 4 : 2;
	for (i = 0; i < n; i = i + 1)
		Founder_Gout (org, self.enemy.origin + [crandom () * 160, crandom () * 160, 0], 560 + random () * 120);
};

// The pour: a broad line of iron along the floor towards you.
void() Founder_PourStart =
{
	ai_face ();
	makevectors (self.angles);
	self.pour_dir = v_forward;
	self.pour_step = 0;
	sound (self, CHAN_WEAPON, "cinder/founder_pour.wav", 1, ATTN_NORM);
};

void() Founder_PourOn =
{
	local vector org, side;

	self.pour_step = self.pour_step + 1;
	side = [-self.pour_dir_y, self.pour_dir_x, 0];
	org = self.origin + self.pour_dir * (56 + self.pour_step * 56) - '0 0 16';
	traceline (self.origin, org, TRUE, self);
	if (trace_fraction < 1.0)
		return;
	Brute_Splash (org);
	if (self.pour_step > 3)
	{
		Brute_Splash (org + side * 56);
		Brute_Splash (org - side * 56);
	}
};

// The slam: a blow if you're close, and the floor rings out round him.
void() Founder_Slam =
{
	local vector d;
	local entity ring, p;

	sound (self, CHAN_WEAPON, "cinder/founder_slam.wav", 1, ATTN_NONE);
	makevectors (self.angles);
	W_SlagBurst (self.origin + v_forward * 80 - '0 0 20', 40);
	if (self.enemy && vlen (self.enemy.origin - self.origin) < 170 && CanDamage (self.enemy, self))
	{
		d = normalize (self.enemy.origin - self.origin);
		self.enemy.velocity = self.enemy.velocity + d * 420 + '0 0 240';
		self.enemy.flags = self.enemy.flags - (self.enemy.flags & FL_ONGROUND);
		self.enemy.deathtype = "slag";
		T_Damage (self.enemy, self, self, 36 + random () * 10);
	}
	ring = spawn ();
	ring.owner = self;
	ring.classname = "toll_ring";
	setorigin (ring, self.origin + [0, 0, self.mins_z + 2]);
	ring.cnt = 64;
	ring.think = toll_ring_think;
	ring.nextthink = time + 0.05;
	for (p = find (world, classname, "player"); p; p = find (p, classname, "player"))
		if (vlen (p.origin - self.origin) < 1200)
			Rumble (p, "mortar");
};

// Past half health the iron runs from the roof onto you while he fights.
void() Founder_Rain =
{
	local vector top;

	if (!Founder_Angry () || !self.enemy || self.enemy.health <= 0 || time < self.founder_rain)
		return;
	self.founder_rain = time + 2.5 + random () * 1.5;
	top = self.enemy.origin + [crandom () * 96, crandom () * 96, 0];
	traceline (top, top + '0 0 800', TRUE, self.enemy);
	top = trace_endpos - '0 0 8';
	newmis = spawn ();
	newmis.owner = self;
	newmis.classname = "founder_gout";
	newmis.movetype = MOVETYPE_TOSS;
	newmis.solid = SOLID_BBOX;
	newmis.touch = founder_gout_touch;
	newmis.think = SUB_Remove;
	newmis.nextthink = time + 6;
	setmodel (newmis, "progs/lavaball.mdl");
	setsize (newmis, VEC_ORIGIN, VEC_ORIGIN);
	setorigin (newmis, top);
	newmis.velocity = '0 0 -40';
	particle (top, '0 0 -40', 234, 20);
	sound (newmis, CHAN_WEAPON, "cinder/founder_hurl.wav", 0.6, ATTN_NORM);
};

void() founder_stand1 =[ $fstand1, founder_stand2 ] { ai_stand (); founder_idle (); };
void() founder_stand2 =[ $fstand2, founder_stand3 ] { ai_stand (); };
void() founder_stand3 =[ $fstand3, founder_stand4 ] { ai_stand (); };
void() founder_stand4 =[ $fstand4, founder_stand5 ] { ai_stand (); };
void() founder_stand5 =[ $fstand5, founder_stand6 ] { ai_stand (); };
void() founder_stand6 =[ $fstand6, founder_stand7 ] { ai_stand (); };
void() founder_stand7 =[ $fstand7, founder_stand8 ] { ai_stand (); };
void() founder_stand8 =[ $fstand8, founder_stand9 ] { ai_stand (); };
void() founder_stand9 =[ $fstand9, founder_stand10 ] { ai_stand (); };
void() founder_stand10 =[ $fstand10, founder_stand1 ] { ai_stand (); };

void() founder_walk1 =[ $fwalk1, founder_walk2 ] { ai_walk (4); founder_idle (); };
void() founder_walk2 =[ $fwalk2, founder_walk3 ] { ai_walk (5); };
void() founder_walk3 =[ $fwalk3, founder_walk4 ] { ai_walk (5); };
void() founder_walk4 =[ $fwalk4, founder_walk5 ] { ai_walk (4); };
void() founder_walk5 =[ $fwalk5, founder_walk6 ] { ai_walk (4); };
void() founder_walk6 =[ $fwalk6, founder_walk7 ] { ai_walk (5); };
void() founder_walk7 =[ $fwalk7, founder_walk8 ] { ai_walk (4); };
void() founder_walk8 =[ $fwalk8, founder_walk9 ] { ai_walk (5); };
void() founder_walk9 =[ $fwalk9, founder_walk10 ] { ai_walk (5); };
void() founder_walk10 =[ $fwalk10, founder_walk11 ] { ai_walk (4); };
void() founder_walk11 =[ $fwalk11, founder_walk12 ] { ai_walk (4); };
void() founder_walk12 =[ $fwalk12, founder_walk1 ] { ai_walk (5); };

// He grinds forward in his mould, a little quicker once he's angry.
void(float d) founder_go =
{
	if (Founder_Angry ())
		d = d * 1.5;
	ai_run (d);
	Founder_Rain ();
};

void() founder_run1 =[ $fwalk1, founder_run2 ] { founder_go (5); founder_idle (); };
void() founder_run2 =[ $fwalk2, founder_run3 ] { founder_go (6); };
void() founder_run3 =[ $fwalk3, founder_run4 ] { founder_go (6); };
void() founder_run4 =[ $fwalk4, founder_run5 ] { founder_go (5); };
void() founder_run5 =[ $fwalk5, founder_run6 ] { founder_go (5); };
void() founder_run6 =[ $fwalk6, founder_run7 ] { founder_go (6); };
void() founder_run7 =[ $fwalk7, founder_run8 ] { founder_go (5); };
void() founder_run8 =[ $fwalk8, founder_run9 ] { founder_go (6); };
void() founder_run9 =[ $fwalk9, founder_run10 ] { founder_go (6); };
void() founder_run10 =[ $fwalk10, founder_run11 ] { founder_go (5); };
void() founder_run11 =[ $fwalk11, founder_run12 ] { founder_go (5); };
void() founder_run12 =[ $fwalk12, founder_run1 ] { founder_go (6); };

void() founder_pour1 =[ $fpour1, founder_pour2 ] { ai_face (); };
void() founder_pour2 =[ $fpour2, founder_pour3 ] { ai_face (); };
void() founder_pour3 =[ $fpour3, founder_pour4 ] { ai_face (); };
void() founder_pour4 =[ $fpour4, founder_pour5 ] { Founder_PourStart (); };
void() founder_pour5 =[ $fpour5, founder_pour6 ] { Founder_PourOn (); };
void() founder_pour6 =[ $fpour6, founder_pour7 ] { Founder_PourOn (); };
void() founder_pour7 =[ $fpour7, founder_pour8 ] { Founder_PourOn (); };
void() founder_pour8 =[ $fpour8, founder_pour9 ] { Founder_PourOn (); };
void() founder_pour9 =[ $fpour9, founder_pour10 ] { Founder_PourOn (); };
void() founder_pour10 =[ $fpour10, founder_pour11 ] { Founder_PourOn (); };
void() founder_pour11 =[ $fpour11, founder_pour12 ] { Founder_PourOn (); };
void() founder_pour12 =[ $fpour12, founder_pour13 ] { Founder_PourOn (); };
void() founder_pour13 =[ $fpour13, founder_pour14 ] { };
void() founder_pour14 =[ $fpour14, founder_pour15 ] { };
void() founder_pour15 =[ $fpour15, founder_pour16 ] { };
void() founder_pour16 =[ $fpour16, founder_run1 ] { };

void() founder_hurl1 =[ $fhurl1, founder_hurl2 ] { ai_face (); };
void() founder_hurl2 =[ $fhurl2, founder_hurl3 ] { ai_face (); };
void() founder_hurl3 =[ $fhurl3, founder_hurl4 ] { ai_face (); };
void() founder_hurl4 =[ $fhurl4, founder_hurl5 ] { ai_face (); };
void() founder_hurl5 =[ $fhurl5, founder_hurl6 ] { ai_face (); };
void() founder_hurl6 =[ $fhurl6, founder_hurl7 ] { ai_face (); };
void() founder_hurl7 =[ $fhurl7, founder_hurl8 ] { ai_face (); };
void() founder_hurl8 =[ $fhurl8, founder_hurl9 ] { Founder_Hurl (); };
void() founder_hurl9 =[ $fhurl9, founder_hurl10 ] { };
void() founder_hurl10 =[ $fhurl10, founder_hurl11 ] { };
void() founder_hurl11 =[ $fhurl11, founder_hurl12 ] { };
void() founder_hurl12 =[ $fhurl12, founder_run1 ] { };

void() founder_slam1 =[ $fslam1, founder_slam2 ] { ai_face (); };
void() founder_slam2 =[ $fslam2, founder_slam3 ] { ai_face (); };
void() founder_slam3 =[ $fslam3, founder_slam4 ] { ai_face (); };
void() founder_slam4 =[ $fslam4, founder_slam5 ] { ai_face (); };
void() founder_slam5 =[ $fslam5, founder_slam6 ] { ai_face (); };
void() founder_slam6 =[ $fslam6, founder_slam7 ] { ai_charge (2); };
void() founder_slam7 =[ $fslam7, founder_slam8 ] { ai_charge (4); };
void() founder_slam8 =[ $fslam8, founder_slam9 ] { Founder_Slam (); };
void() founder_slam9 =[ $fslam9, founder_slam10 ] { };
void() founder_slam10 =[ $fslam10, founder_slam11 ] { };
void() founder_slam11 =[ $fslam11, founder_slam12 ] { };
void() founder_slam12 =[ $fslam12, founder_run1 ] { };

void() founder_attack =
{
	if (self.founder_move == 1)
		founder_pour1 ();
	else
		founder_hurl1 ();
};

void() founder_pain1 =[ $fpain1, founder_pain2 ] { };
void() founder_pain2 =[ $fpain2, founder_pain3 ] { };
void() founder_pain3 =[ $fpain3, founder_pain4 ] { };
void() founder_pain4 =[ $fpain4, founder_pain5 ] { };
void() founder_pain5 =[ $fpain5, founder_pain6 ] { };
void() founder_pain6 =[ $fpain6, founder_run1 ] { };

// He hardly flinches: only a heavy blow, and not often.
void(entity attacker, float damage) founder_pain =
{
	if (self.pain_finished > time)
		return;
	if (random () * 300 > damage)
		return;
	self.pain_finished = time + 5;
	sound (self, CHAN_VOICE, "cinder/founder_pain.wav", 1, ATTN_NORM);
	founder_pain1 ();
};

void() founder_death1 =[ $fdeath1, founder_death2 ] { };
void() founder_death2 =[ $fdeath2, founder_death3 ] { };
void() founder_death3 =[ $fdeath3, founder_death4 ] { };
void() founder_death4 =[ $fdeath4, founder_death5 ] { };
void() founder_death5 =[ $fdeath5, founder_death6 ] { };
void() founder_death6 =[ $fdeath6, founder_death7 ] { self.solid = SOLID_NOT; };
void() founder_death7 =[ $fdeath7, founder_death8 ] { };
void() founder_death8 =[ $fdeath8, founder_death9 ] { };
void() founder_death9 =[ $fdeath9, founder_death10 ] { };
void() founder_death10 =[ $fdeath10, founder_death11 ] { W_SlagBurst (self.origin, 60); };
void() founder_death11 =[ $fdeath11, founder_death12 ] { };
void() founder_death12 =[ $fdeath12, founder_death13 ] { };
void() founder_death13 =[ $fdeath13, founder_death14 ] { };
void() founder_death14 =[ $fdeath14, founder_death15 ] { W_SlagBurst (self.origin, 60); };
void() founder_death15 =[ $fdeath15, founder_death16 ] { };
void() founder_death16 =[ $fdeath16, founder_death17 ] { };
void() founder_death17 =[ $fdeath17, founder_death18 ] { };
void() founder_death18 =[ $fdeath18, founder_death19 ] { };
void() founder_death19 =[ $fdeath19, founder_death20 ] { };
void() founder_death20 =[ $fdeath20, founder_death20 ] { };

void() founder_die =
{
	local entity p;

	sound (self, CHAN_VOICE, "cinder/founder_death.wav", 1, ATTN_NONE);
	for (p = find (world, classname, "player"); p; p = find (p, classname, "player"))
		Rumble (p, "death");
	founder_death1 ();
};

/*
	Slam when you're close; otherwise pour when you're on his level and
	within the line's reach, or hurl. Faster once he's angry.
*/
float() FounderCheckAttack =
{
	local float d, wait;

	d = vlen (self.enemy.origin - self.origin);
	if (d < 170)
	{
		if (time < self.attack_finished - 1)
			return FALSE;
		self.attack_state = AS_MELEE;
		self.attack_finished = time + 1.5;
		return TRUE;
	}
	if (time < self.attack_finished)
		return FALSE;
	wait = Founder_Angry () ? 1.6 : 2.6;
	if (d < 560 && fabs (self.enemy.origin_z - self.origin_z) < 64 && random () < 0.5)
		self.founder_move = 1;
	else if (random () < 0.7)
		self.founder_move = 2;
	else
		return FALSE;
	self.attack_state = AS_MISSILE;
	self.attack_finished = time + wait + random ();
	return TRUE;
};

/*QUAKED monster_founder (1 0 0) (-32 -32 -24) (32 32 64) Ambush
The Founder, the Undervein's master: pours and flings iron, slams the floor.
His target fires when he dies.
*/
void() monster_founder =
{
	if (deathmatch)
	{
		remove (self);
		return;
	}
	precache_model ("progs/founder.md3");
	precache_model ("progs/lavaball.mdl");
	precache_sound ("cinder/founder_sight.wav");
	precache_sound ("cinder/founder_idle.wav");
	precache_sound ("cinder/founder_pour.wav");
	precache_sound ("cinder/founder_hurl.wav");
	precache_sound ("cinder/founder_slam.wav");
	precache_sound ("cinder/founder_pain.wav");
	precache_sound ("cinder/founder_death.wav");
	precache_sound ("cinder/brute_pour.wav");
	precache_sound ("cinder/coal_hit.wav");

	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_STEP;
	setmodel (self, "progs/founder.md3");
	setsize (self, VEC_HULL2_MIN, VEC_HULL2_MAX);
	self.noise = "cinder/founder_sight.wav";
	self.netname = "the Founder";
	self.killstring = " was poured into the Founder's last mould";
	if (!self.health)		// a map may set his health, for testing
		self.health = 2000 + skill * 300;
	self.max_health = self.health;

	self.th_stand = founder_stand1;
	self.th_walk = founder_walk1;
	self.th_run = founder_run1;
	self.th_missile = founder_attack;
	self.th_melee = founder_slam1;
	self.th_pain = founder_pain;
	self.th_die = founder_die;

	walkmonster_start ();
};
