/*
	Pressure: the gauge in the middle of the status bar (game-ideas idea 25).

	It fills as the stoker fights (every hit landed, more for a kill) and
	bleeds off when the fighting stops. Spend it on a Bellows dash or a
	weapon's Overpressure shot. A full gauge is in the red: stay there and it
	scalds, a point a second. Steam vents throw a jumping stoker high for free.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later, as the rest of the
	game code.
*/

#define PRESSURE_MAX		100
#define STAT_PRESSURE		32	// the engine's Sbar_DrawPressure reads it
#define IMPULSE_DASH		20
#define IMPULSE_OVERPRESSURE	21

#define PRESSURE_PER_DAMAGE	0.3	// for each point of damage dealt to a creature
#define PRESSURE_PER_KILL	8
#define PRESSURE_BLEED		6	// a second, once the fighting stops
#define PRESSURE_BLEED_AFTER	4	// seconds after the last gain
#define PRESSURE_RED_GRACE	3	// seconds in the red before it scalds

#define DASH_COST		25
#define DASH_SPEED		640
#define DASH_LIFT		160
#define DASH_COOLDOWN		0.35

.float pressure;		// 0 to PRESSURE_MAX
.float pressure_fed;		// when it last rose
.float pressure_red;		// when it went into the red, or 0
.float pressure_scald;		// when it may scald next
.float dash_finished;		// when the next dash is allowed
.float vent_finished;		// when a vent may throw this player again

void(float num, float type, .float fld) clientstat = #232;

float(float a, float b) Pressure_Min = { if (a < b) return a; return b; };
float(float a, float b) Pressure_Max = { if (a > b) return a; return b; };

void() Pressure_Init =
{
	clientstat (STAT_PRESSURE, 2, pressure);	// 2 is EV_FLOAT
	precache_sound ("cinder/dash.wav");
	precache_sound ("cinder/vent.wav");
	precache_sound ("cinder/scald.wav");
	precache_sound ("cinder/empty.wav");
	precache_sound ("cinder/redline.wav");
};

void(entity p, float amount) Pressure_Add =
{
	local float before;

	if (p.classname != "player" || p.health <= 0)
		return;
	before = p.pressure;
	p.pressure = Pressure_Min (PRESSURE_MAX, p.pressure + amount);
	p.pressure_fed = time;
	if (before < PRESSURE_MAX && p.pressure >= PRESSURE_MAX)
		sound (p, CHAN_ITEM, "cinder/redline.wav", 0.7, ATTN_NORM);
};

// Called by T_Damage once the damage is done.
void(entity targ, entity attacker, float take) Pressure_Damage =
{
	if (attacker.classname != "player" || targ == attacker || !(targ.flags & FL_MONSTER))
		return;
	Pressure_Add (attacker, take * PRESSURE_PER_DAMAGE);
	if (targ.health <= 0)
		Pressure_Add (attacker, PRESSURE_PER_KILL);
};

// Takes cost from the gauge, or hisses and returns FALSE when there isn't enough.
float(entity p, float cost) Pressure_Spend =
{
	if (p.pressure < cost)
	{
		sound (p, CHAN_ITEM, "cinder/empty.wav", 0.6, ATTN_NORM);
		return FALSE;
	}
	p.pressure = p.pressure - cost;
	if (p.pressure < PRESSURE_MAX)
		p.pressure_red = 0;
	return TRUE;
};

void(vector org, vector dir, float count) Pressure_Steam =
{
	particle (org, dir, 12, count);
};

/*
	The Bellows dash: a burst a few metres the way the stoker is moving
	(forward when standing still), on the ground or in the air.
*/
void() Pressure_Dash =
{
	local vector dir;

	if (time < self.dash_finished || self.waterlevel >= 2)
		return;
	if (!Pressure_Spend (self, DASH_COST))
		return;

	dir = self.velocity;
	dir_z = 0;
	if (vlen (dir) < 60)
	{
		makevectors ([0, self.v_angle_y, 0]);
		dir = v_forward;
	}
	else
		dir = normalize (dir);

	self.velocity = dir * DASH_SPEED;
	self.velocity_z = Pressure_Max (self.velocity_z, DASH_LIFT);
	self.flags = self.flags - (self.flags & FL_ONGROUND);
	self.dash_finished = time + DASH_COOLDOWN;
	sound (self, CHAN_BODY, "cinder/dash.wav", 1, ATTN_NORM);
	Pressure_Steam (self.origin - '0 0 16', dir * -60, 24);
};

void() W_Overpressure;

/*
	Every frame for a living player, from PlayerPostThink before the weapon
	frame, so a dash isn't held up by a weapon's refire time.
*/
void() Pressure_Frame =
{
	if (self.impulse == IMPULSE_DASH)
	{
		Pressure_Dash ();
		self.impulse = 0;
	}
	else if (self.impulse == IMPULSE_OVERPRESSURE)
	{
		if (time >= self.attack_finished)
		{
			W_Overpressure ();
			self.impulse = 0;
		}
	}

	if (self.pressure >= PRESSURE_MAX)
	{
		if (!self.pressure_red)
			self.pressure_red = time;
		else if (time > self.pressure_red + PRESSURE_RED_GRACE && time >= self.pressure_scald)
		{
			self.pressure_scald = time + 1;
			sound (self, CHAN_ITEM, "cinder/scald.wav", 0.8, ATTN_NORM);
			Pressure_Steam (self.origin, '0 0 40', 12);
			self.deathtype = "scald";
			T_Damage (self, world, world, 1);
		}
		return;
	}
	self.pressure_red = 0;

	if (self.pressure > 0 && time > self.pressure_fed + PRESSURE_BLEED_AFTER)
		self.pressure = Pressure_Max (0, self.pressure - PRESSURE_BLEED * frametime);
};

void() Pressure_Reset =
{
	self.pressure = 0;
	self.pressure_red = 0;
	self.dash_finished = 0;
	self.vent_finished = 0;
};

/*QUAKED trigger_vent (.5 .5 .5) ?
A steam vent: a stoker who jumps while touching it is thrown up at "speed"
(720 by default). Make it a floor grate's size and about 32 units tall.
*/
void() vent_touch =
{
	if (other.classname != "player" || other.health <= 0)
		return;
	if (!other.button2 || time < other.vent_finished)
		return;
	other.velocity_z = self.speed;
	other.flags = other.flags - (other.flags & FL_ONGROUND);
	other.vent_finished = time + 0.5;
	sound (other, CHAN_BODY, "cinder/vent.wav", 1, ATTN_NORM);
	Pressure_Steam (other.origin - '0 0 24', '0 0 200', 32);
};

void() vent_puff =
{
	local vector org;

	org_x = self.absmin_x + random () * (self.absmax_x - self.absmin_x);
	org_y = self.absmin_y + random () * (self.absmax_y - self.absmin_y);
	org_z = self.absmin_z + 2;
	Pressure_Steam (org, '0 0 120', 3);
	self.nextthink = time + 0.08;
};

void() trigger_vent =
{
	InitTrigger ();
	if (!self.speed)
		self.speed = 720;
	self.touch = vent_touch;
	self.think = vent_puff;
	self.nextthink = time + random () * 0.1;
	if (!self.noise)
		self.noise = "cinder/vent_loop.wav";
	precache_sound (self.noise);
	ambientsound ((self.absmin + self.absmax) * 0.5, self.noise, 0.4, ATTN_STATIC);
};
