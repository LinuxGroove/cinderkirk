/*
	Bots for Pit fights: stokers played by the game, so a Pit fight works
	with one player or a few. They're real clients (the engine's botclients),
	so they score, die and respawn as players do; the engine steers them with
	.movement as it would a player's controls.

	There are no waypoints. A bot goes for an enemy it can see, else for the
	nearest thing worth picking up that it can see, else to where it last saw
	someone, else it wanders. It feels ahead for walls, drops and slag, jumps
	what it can, and turns away from what it can't. Its aim is the skill's:
	slower to turn and wider of the mark at Apprentice than at Founder's.

	The bots cvar says how many join; StartFrame keeps that many in a Pit
	fight and none anywhere else.

	Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
*/

entity() spawnclient = #454;
float(float a) sin = #60;
float(float a) cos = #61;
string(string s1, string s2, ...) strcat = #115;
string(string s, float start, float length) substring = #116;
void(vector start, vector mins, vector maxs, vector end, float nomonsters, entity ent) tracebox = #90;
float(entity client) clienttype = #455;
void(entity player) dropclient = #453;
void(entity e, string s) clientcommand = #440;

#define CLIENTTYPE_BOT	2
#define M_PI			3.14159265

.vector movement;			// read by the engine for botclients: forward, side, up
.entity bot_goal;			// what it's going for: a player, an item, or nothing
.float bot_next_goal;		// when to look round again
.vector bot_last_seen;		// where it last saw its enemy
.float bot_last_seen_time;
.float bot_saw_since;		// when it first saw the enemy it's fighting (reaction time)
.float bot_yaw;				// the way it wants to walk
.vector bot_aim_err;		// how far off its aim wanders
.float bot_aim_next;
.float bot_strafe;			// -1 or 1
.float bot_strafe_next;
.vector bot_check_pos;		// stuck check
.float bot_check_time;
.float bot_unstick;			// until when it walks the way it picked to get unstuck
.float bot_jump_next;
.float bot_name_index;

void() ClientConnect;
void() PutClientInServer;
void() W_SetCurrentAmmo;

string(float n) Bot_Name =
{
	switch (n)
	{
		case 0: return "Bellows";
		case 1: return "Old Pour";
		case 2: return "Ladle";
		case 3: return "Sprue";
		case 4: return "Tapper";
		case 5: return "Furnace Meg";
		case 6: return "Gauge";
	}
	return "Clinker";
};

float(float n) Bot_Bit =
{
	local float b;

	for (b = 1; n > 0; n--)
		b = b * 2;
	return b;
};

float(entity e) Bot_IsBot =
{
	return clienttype (e) == CLIENTTYPE_BOT;
};

// A bot's skill, 0 to 3: the server's skill.
float() Bot_Skill =
{
	if (skill < 0)
		return 0;
	if (skill > 3)
		return 3;
	return skill;
};

float(entity targ) Bot_CanSee =
{
	traceline (self.origin + self.view_ofs, targ.origin + targ.view_ofs * 0.5, TRUE, self);
	return trace_fraction == 1;
};

// What a pickup is worth to this bot now (0 if nothing).
float(entity it) Bot_ItemWorth =
{
	if (it.model == string_null || it.solid != SOLID_TRIGGER)
		return 0;
	if (it.classname == "item_health")
		return self.health < 100 ? 120 - self.health : 0;
	if (substring (it.classname, 0, 11) == "item_armor")
		return self.armorvalue < 100 ? 60 : 0;
	if (substring (it.classname, 0, 7) == "weapon_")
	{
		if (self.items & it.weapon)
			return 10;
		return 90;
	}
	if (substring (it.classname, 0, 14) == "item_artifact_")
		return 100;
	if (it.classname == "item_shells" || it.classname == "item_spikes" || it.classname == "item_rockets"
		|| it.classname == "item_cells")
		return 20;
	return 0;
};

void() Bot_PickGoal =
{
	local entity e, best;
	local float d, score, best_score;

	self.bot_next_goal = time + 0.3 + random () * 0.2;

	// An enemy in sight beats anything.
	best = world;
	best_score = 0;
	e = find (world, classname, "player");
	while (e)
	{
		if (e != self && e.health > 0 && !(e.flags & FL_NOTARGET)
			&& !(teamplay && e.team == self.team) && !(e.items & IT_INVISIBILITY && vlen (e.origin - self.origin) > 200))
		{
			if (Bot_CanSee (e))
			{
				d = vlen (e.origin - self.origin);
				score = 4000 - d;
				if (e == self.enemy)
					score = score + 400;		// don't flick between two
				if (score > best_score)
				{
					best = e;
					best_score = score;
				}
			}
		}
		e = find (e, classname, "player");
	}
	if (best)
	{
		if (self.enemy != best)
			self.bot_saw_since = time;
		self.enemy = best;
		self.bot_goal = best;
		self.bot_last_seen = best.origin;
		self.bot_last_seen_time = time;
		return;
	}
	self.enemy = world;

	// Else the best pickup in sight, nearer is better.
	e = findradius (self.origin, 1200);
	while (e)
	{
		if (e.flags & FL_ITEM)
		{
			score = Bot_ItemWorth (e);
			if (score > 0 && Bot_CanSee (e))
			{
				score = score * 1000 / (vlen (e.origin - self.origin) + 200);
				if (score > best_score)
				{
					best = e;
					best_score = score;
				}
			}
		}
		e = e.chain;
	}
	self.bot_goal = best;
};

// The best weapon for a fight at this distance.
float(float dist) Bot_Weapon =
{
	local float it;

	it = self.items;
	if (dist > 180 && self.ammo_rockets >= 1 && (it & IT_ROCKET_LAUNCHER))
		return IT_ROCKET_LAUNCHER;
	if (self.waterlevel < 1 && self.ammo_cells >= 1 && (it & IT_LIGHTNING) && dist < 600)
		return IT_LIGHTNING;
	if (self.ammo_nails >= 2 && (it & IT_SUPER_NAILGUN))
		return IT_SUPER_NAILGUN;
	if (self.ammo_shells >= 2 && (it & IT_SUPER_SHOTGUN) && dist < 500)
		return IT_SUPER_SHOTGUN;
	if (dist > 220 && self.ammo_rockets >= 1 && (it & IT_GRENADE_LAUNCHER))
		return IT_GRENADE_LAUNCHER;
	if (self.ammo_nails >= 1 && (it & IT_NAILGUN))
		return IT_NAILGUN;
	if (self.ammo_shells >= 1 && (it & IT_SHOTGUN))
		return IT_SHOTGUN;
	return IT_AXE;
};

// How far it can walk along a yaw before a wall, a drop or slag (0 to 1 of 64).
float(float yaw) Bot_Clear =
{
	local vector dir, from, to;

	dir = [cos (yaw * M_PI / 180), sin (yaw * M_PI / 180), 0];
	from = self.origin;
	to = from + dir * 64;
	tracebox (from, self.mins + '0 0 18', self.maxs, to, FALSE, self);		// step height clears
	if (trace_fraction < 1)
		return trace_fraction * 0.5;
	// Ground under the next step, and nothing hot there.
	traceline (to, to - '0 0 160', TRUE, self);
	if (trace_fraction == 1)
		return 0.1;
	if (pointcontents (trace_endpos + '0 0 4') == CONTENT_LAVA || pointcontents (trace_endpos + '0 0 4') == CONTENT_SLIME)
		return 0;
	return 1;
};

void() Bot_Move =
{
	local vector to, dir;
	local float want, best, best_yaw, i, y, c, dist;

	// Where it wants to go.
	if (self.bot_goal)
		to = self.bot_goal.origin;
	else if (time < self.bot_last_seen_time + 5)
		to = self.bot_last_seen;
	else
	{
		if (time > self.bot_unstick && random () < 0.02)
			self.bot_yaw = anglemod (self.bot_yaw + (random () * 2 - 1) * 90);
		to = self.origin + [cos (self.bot_yaw * M_PI / 180), sin (self.bot_yaw * M_PI / 180), 0] * 200;
	}
	dir = to - self.origin;
	dir_z = 0;
	dist = vlen (dir);
	want = vectoyaw (dir);
	if (time < self.bot_unstick)
		want = self.bot_yaw;

	// The clearest way near the one it wants.
	best = -1;
	best_yaw = want;
	for (i = 0; i < 7; i++)
	{
		y = want + (i == 0 ? 0 : ((i & 1) ? 1 : -1) * floor ((i + 1) / 2) * 35);
		c = Bot_Clear (y) - i * 0.02;
		if (c > best)
		{
			best = c;
			best_yaw = y;
		}
		if (c >= 0.99)
			break;
	}
	if (best < 0.2)
	{
		best_yaw = want + 180;
		self.bot_yaw = best_yaw;
		self.bot_unstick = time + 0.6;
	}
	else if (time >= self.bot_unstick)
		self.bot_yaw = best_yaw;

	// Stuck: it's trying and not getting anywhere.
	if (time > self.bot_check_time)
	{
		if (vlen (self.origin - self.bot_check_pos) < 24 && dist > 48)
		{
			self.bot_yaw = anglemod (best_yaw + 90 + random () * 180);
			self.bot_unstick = time + 0.8;
			if (time > self.bot_jump_next)
			{
				self.button2 = TRUE;
				self.bot_jump_next = time + 1;
			}
		}
		self.bot_check_pos = self.origin;
		self.bot_check_time = time + 0.7;
	}

	// Jump a low thing in the way.
	if (best < 0.99 && (self.flags & FL_ONGROUND) && time > self.bot_jump_next)
	{
		dir = [cos (best_yaw * M_PI / 180), sin (best_yaw * M_PI / 180), 0];
		tracebox (self.origin + '0 0 40', self.mins, self.maxs, self.origin + '0 0 40' + dir * 48, FALSE, self);
		if (trace_fraction == 1)
		{
			self.button2 = TRUE;
			self.bot_jump_next = time + 0.8;
		}
	}

	// Walk the chosen way, whichever way it's looking.
	y = (self.bot_yaw - self.v_angle_y) * M_PI / 180;
	self.movement = [cos (y), sin (y), 0] * 320;

	// In a fight, sidestep, and keep a distance that suits the weapon.
	if (self.enemy)
	{
		if (time > self.bot_strafe_next)
		{
			self.bot_strafe = random () < 0.5 ? -1 : 1;
			self.bot_strafe_next = time + 0.5 + random () * 1.2;
		}
		self.movement_y = self.movement_y + self.bot_strafe * 280;
		if (dist < 140 && self.weapon != IT_AXE)
			self.movement_x = -200;
	}
};

void() Bot_Aim =
{
	local vector to, ang;
	local float sk, turn, dy, dp, err;

	sk = Bot_Skill ();
	if (!self.enemy)
	{
		// Look where it walks.
		dy = anglemod (self.bot_yaw - self.v_angle_y + 180) - 180;
		self.v_angle_y = anglemod (self.v_angle_y + dy * 0.2);
		self.v_angle_x = self.v_angle_x * 0.8;
		return;
	}
	if (time > self.bot_aim_next)
	{
		err = 7 - sk * 1.8;
		self.bot_aim_err = [(random () * 2 - 1) * err, (random () * 2 - 1) * err * 1.4, 0];
		self.bot_aim_next = time + 0.4 + random () * 0.5;
	}
	to = self.enemy.origin + self.enemy.view_ofs * 0.6;
	if (self.weapon == IT_ROCKET_LAUNCHER || self.weapon == IT_GRENADE_LAUNCHER)
		to = self.enemy.origin + self.enemy.velocity * (vlen (to - self.origin) / 1000) * (0.3 + sk * 0.2) - '0 0 12';
	ang = vectoangles (to - (self.origin + self.view_ofs));
	ang_x = 0 - ang_x;
	ang = ang + self.bot_aim_err;
	turn = 0.18 + sk * 0.1;				// of the way there each frame
	dy = anglemod (ang_y - self.v_angle_y + 180) - 180;
	dp = ang_x - self.v_angle_x;
	self.v_angle_y = anglemod (self.v_angle_y + dy * turn);
	self.v_angle_x = self.v_angle_x + dp * turn;

	// Fire once it has reacted and is near enough on target.
	if (time > self.bot_saw_since + 0.65 - sk * 0.15 && fabs (dy) < 12 && fabs (dp) < 14 && Bot_CanSee (self.enemy))
		self.button0 = TRUE;
};

// Called from PlayerPreThink for every bot, before the player code runs.
void() Bot_Think =
{
	local float w;

	self.button0 = self.button2 = FALSE;
	self.movement = '0 0 0';

	if (self.deadflag)
	{
		// Press fire now and then to come back.
		if (random () < 0.1)
			self.button0 = TRUE;
		return;
	}

	if (time > self.bot_next_goal || (self.bot_goal && (self.bot_goal.health <= 0 && self.bot_goal.classname == "player"))
		|| (self.bot_goal && self.bot_goal.model == string_null))
		Bot_PickGoal ();

	if (self.enemy)
	{
		w = Bot_Weapon (vlen (self.enemy.origin - self.origin));
		if (w != self.weapon)
		{
			self.weapon = w;
			W_SetCurrentAmmo ();
		}
	}
	Bot_Aim ();
	Bot_Move ();
};

// Called from StartFrame: keep the bots cvar's count in a Pit fight, none elsewhere.
void() Bots_Update =
{
	local entity e, oself;
	local float want, have, i, used;

	if (time < 1)
		return;
	// Not until someone is in the level: a name sent to a client still
	// joining is more than its scoreboard can take.
	e = find (world, classname, "player");
	while (e && Bot_IsBot (e))
		e = find (e, classname, "player");
	if (!e)
		return;
	want = (deathmatch && !coop) ? cvar ("bots") : 0;

	// Bots carried over from the last map come back into this one.
	have = 0;
	used = 0;
	e = world;
	for (i = 0; i < 32; i++)
	{
		e = nextent (e);
		if (!e)
			break;
		if (Bot_IsBot (e))
		{
			have = have + 1;
			used = used | Bot_Bit (e.bot_name_index);
			if (e.classname != "player")
			{
				oself = self;
				self = e;
				ClientConnect ();
				PutClientInServer ();
				self = oself;
			}
		}
	}

	if (have > want)
	{
		e = world;
		for (i = 0; i < 32; i++)
		{
			e = nextent (e);
			if (!e)
				break;
			if (Bot_IsBot (e))
			{
				dropclient (e);
				return;
			}
		}
	}
	else if (have < want)
	{
		e = spawnclient ();
		if (!e)
			return;
		for (i = 0; i < 8 && (used & Bot_Bit (i)); i++)
			;
		e.bot_name_index = i;
		clientcommand (e, strcat ("name \"", Bot_Name (i), "\"\n"));
		clientcommand (e, strcat ("color ", ftos (i + 2), " ", ftos (i + 2), "\n"));
		oself = self;
		self = e;
		ClientConnect ();
		PutClientInServer ();
		self.bot_yaw = self.angles_y;
		self = oself;
	}
};
