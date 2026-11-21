/*  
	Copyright (C) 1996-1997  Id Software, Inc.
	Copyright (C) 2023 ZungryWare <zungrysoftentertainment@gmail.com>
	Copyright (C) 2024 Ivy Bowling <motolegacy@proton.me>

	This program is free software; you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation; either version 2 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program; if not, write to the Free Software
	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

	See file, 'COPYING', for details.
*/

//
// localized_text.qc -- Centralized location for text that can be printed out
// during gameplay. Formerly localization.qc
//

/*==============================================================================

			SHAFT EPILOGUE STRINGS

		These strings in-engine have a 40 character limit before
		truncation.

==============================================================================*/

#define LOC_EPILOGUE_0		"\nAs the ethereal essence of your very\nbeing drifts through time and space,\nyou experience relentless calm and\nserene determination. You embrace the\nliminal, formless nature of your\nexistence within the amorphous expanse\nbetween realities.\n\nSuspended between the veils of life\nand death, among the realm of celestial\ndissolution, you wait to be called upon\nagain. To regain your corporeal form\nand step into the crucible of fate.\nTo finish your task and keep at bay the\nonslaught of cosmic horrors.\n"
#define LOC_EPILOGUE_1		"The Foundry is quiet. Its Seal is\nyours: carry it up to the Pithead\nand set it on the shelf."
#define LOC_EPILOGUE_1_FREEWARE	LOC_EPILOGUE_1
#define LOC_EPILOGUE_2		"The Cisterns run cold again. Their\nSeal is yours: carry it up to the\nPithead and set it on the shelf."
#define LOC_EPILOGUE_3		"The kilns are out. The Ossuary's\nSeal is yours: carry it up to the\nPithead and set it on the shelf."
#define LOC_EPILOGUE_4		"The Founder is broken. The\nUndervein's Seal is yours: carry it\nup to the Pithead."
#define LOC_EPILOGUE_END	"The bell came down into the Throat\nand stopped it like a cork. The fire\nunder Cinderkirk is banked for good.\n\nUp in the Pithead the night shift\nends. Out in the kirkyard the ash\nlies still, and stays down."
#define LOC_EPILOGUE_RUNES	"Four Seals on the shelf. Down in the\nPithead the grate over the Throat\ngroans and lifts."
#define LOC_EPILOGUE_FINALE	"The pit is shut. The bells of\nCinderkirk ring out over the town,\nand nobody is listening for anything\nelse. Well stoked."

/*==============================================================================

			CLIENT & SERVER STATE STRINGS

==============================================================================*/

#define LOC_CLIENT_JOIN				" joined the server"
#define LOC_CLIENT_EXIT_LEVEL		" exited the level"
#define LOC_CLIENT_DISCON_A			" left the server the game with "
#define LOC_CLIENT_DISCON_B			" frags"

/*==============================================================================

			CLIENT WEAPON STATUS STRINGS

==============================================================================*/

#define LOC_WEAPON_INVALID				"Invalid weapon"
#define LOC_WEAPON_NOAMMO				"Out of ammo"

/*==============================================================================

			CLIENT ITEM COLLECTION STRINGS

==============================================================================*/

#define LOC_ITEM_PICKUP_NORMAL			"You got "
#define LOC_ITEM_PICKUP_HEALTH			"You get "
#define LOC_ITEM_PICKUP_ADD_HEALTH  	" additional health"

#define LOC_ITEM_FROM_BACKPACK			" from a backpack"  // Unused..

#define LOC_ITEM_TYPE_HEALTH			" health"
#define LOC_ITEM_TYPE_ARMOR				" armor"

#define LOC_ITEM_NAME_QUADDMG			"the Forge Heart"
#define LOC_ITEM_NAME_OCTDMG			"the Furnace Heart"
#define LOC_ITEM_NAME_PENTPROT			"the Founder's Mantle"
#define LOC_ITEM_NAME_SHADRING			"the Soot Veil"
#define LOC_ITEM_NAME_BIOSUIT			"the Quench Suit"
#define LOC_ITEM_NAME_BACKPACK			"Backpack"

#define LOC_ITEM_FADE_QUADDMG			"The Forge Heart is cooling"
#define LOC_ITEM_FADE_OCTDMG			"The Furnace Heart is cooling"
#define LOC_ITEM_FADE_PENTPROT			"The Founder's Mantle is wearing thin"
#define LOC_ITEM_FADE_SHADRING			"The Soot Veil is lifting"
#define LOC_ITEM_FADE_BIOSUIT			"The Quench Suit's air is running out"

#define LOC_BONUS_POWERS				" is coming for you all!!!"

#define LOC_ITEM_LOST_A					" lost "
#define LOC_ITEM_LOST_B					" with "
#define LOC_ITEM_LOST_C					" seconds left"

/*==============================================================================

			WEAPON AND AMMO STRINGS

==============================================================================*/

#define LOC_WEAPON_NAME_AXE				"Pick"		// Unused..
#define LOC_WEAPON_NAME_SHOTGUN			"Scattergun"   // Unused..
#define LOC_WEAPON_NAME_SUPER_SHOTGUN   "Steam Cannon"
#define LOC_WEAPON_NAME_NAILGUN			"Spitter"
#define LOC_WEAPON_NAME_SUPER_NAILGUN   "Bolt Caster"
#define LOC_WEAPON_NAME_GRENADE_LAUNCH  "Crucible"
#define LOC_WEAPON_NAME_ROCKET_LAUNCH   "Shot Mortar"
#define LOC_WEAPON_NAME_THUNDERBOLT		"Tolling Iron"

#define LOC_WEAPON_AMMO_SHELLS			"shells"
#define LOC_WEAPON_AMMO_NAILS			"slag"
#define LOC_WEAPON_AMMO_ROCKETS			"mortar shells"
#define LOC_WEAPON_AMMO_CELLS			"clappers"

/*==============================================================================

			KEY STRINGS

==============================================================================*/

#define LOC_KEY_NAME_SILVER				"Silver Key"
#define LOC_KEY_NAME_SILVER_RUNE		"Silver Key"
#define LOC_KEY_NAME_SILVER_CARD		"Silver Keycard"
#define LOC_KEY_NAME_GOLD				"Gold Key"
#define LOC_KEY_NAME_GOLD_RUNE			"Gold Key"
#define LOC_KEY_NAME_GOLD_CARD			"Gold Keycard"
#define LOC_KEY_NEED					"You need "

/*==============================================================================

			MISC STRINGS

==============================================================================*/

#define LOC_COUNTER_COUNT_1A			"Only "
#define LOC_COUNTER_COUNT_1B			" more to go..."
#define LOC_COUNTER_COUNT_2				"There are more to go..."
#define LOC_COUNTER_COMPLETE			"Sequence completed!"

#define LOC_SECRET						"You found a secret!"

/*==============================================================================

			SEAL STRINGS

==============================================================================*/

#define LOC_RUNE_GET					"You have the Seal"

#define LOC_RUNE_LQ_YOU					"You"
#define LOC_RUNE_LQ_BLOOD				" took the Foundry Seal"
#define LOC_RUNE_LQ_BONE				" took the Cistern Seal"
#define LOC_RUNE_LQ_MIND				" took the Kiln Seal"
#define LOC_RUNE_LQ_SOUL				" took the Vein Seal"

/*==============================================================================

			CLIENT DEATH TO MONSTER STRINGS

==============================================================================*/

#define LOC_DEATH_ARMY 					" was shot by a Chosen"
#define LOC_DEATH_ENFORCER 				" was mowed down by a Cyberhunter"
#define LOC_DEATH_DOG 					" was gored by a Gore Hound"
#define LOC_DEATH_OGRE 					" was demolished by a Barrel Fang"
#define LOC_DEATH_DEMON1 				" was disemboweled by a Moon Rat"
#define LOC_DEATH_WIZARD 				" was shot by a Messenger"
#define LOC_DEATH_ZOMBIE				" was pelted by a Deathless Cultist"
#define LOC_DEATH_KNIGHT 				" was stabbed by a Carcosan Knight"
#define LOC_DEATH_HELL_KNIGHT 			" was gutted by a Biohell Warrior"
#define LOC_DEATH_FISH 					" was nibbled by a Spine Eel"
#define LOC_DEATH_SHAMBLER 				" was shredded by a Hollow"
#define LOC_DEATH_SHALRATH 				" was blasted by a Servant"
#define LOC_DEATH_TARBABY 				" was swarmed by a Bog Face"
#define LOC_DEATH_BOSS 					" was swallowed by the pit"
#define LOC_DEATH_OLDONE 				" became part of the pit"

/*==============================================================================

			CLIENT DEATH TO ENVIRONMENT STRINGS

==============================================================================*/

#define LOC_DEATH_EXPLO_BOX				" was sent sky high"
#define LOC_DEATH_SQUISH 				" was crushed"
#define LOC_DEATH_SQUISH2 				" was crushed by "
#define LOC_DEATH_TRAP_SPIKE			" was perforated"
#define LOC_DEATH_TRAP_LASER			" was lasered"
#define LOC_DEATH_FIREBALL				" was hit by a gob of slag"
#define LOC_DEATH_LEAVE					" tried to escape"
#define LOC_DEATH_DROWN1				" forgot how to swim"
#define LOC_DEATH_DROWN2				" ran out of air"
#define LOC_DEATH_SLIME1				" dissolved in the lime"
#define LOC_DEATH_SLIME2				" was eaten by the lime"
#define LOC_DEATH_LAVA1					" fell into the slag"
#define LOC_DEATH_LAVA2					" went up like a candle"
#define LOC_DEATH_LAVA3					" dove into the slag"
#define LOC_DEATH_FALL1					" fell down the pit"
#define LOC_DEATH_FALL2					" missed the cage"
#define LOC_DEATH_SPACE1				" fell into space"
#define LOC_DEATH_SPACE2				"'s screams went unheard"
#define LOC_DEATH_VOID1					" fell into the void"
#define LOC_DEATH_VOID2					" fell out of existence"
#define LOC_DEATH_DISCHARGE_WATER		" rang the Tolling Iron under water"
#define LOC_DEATH_DISCHARGE_SLIME		" rang the Tolling Iron in the lime"
#define LOC_DEATH_DISCHARGE_LAVA		" rang the Tolling Iron in the slag"
#define LOC_DEATH_DISCHARGE_SELF		"'s Tolling Iron rang back"
#define LOC_DEATH_SELF_GRENADE			" stood too near their own Crucible"
#define LOC_DEATH_SELF_ROCKET			" was caught in their own Shot Mortar"
#define LOC_DEATH_SELF_OTHER			" burst their own boiler"
#define LOC_DEATH_SUICIDE				" went into the furnace"
#define LOC_DEATH_OTHER					" died"

/*==============================================================================

			CLIENT DEATH TO CLIENT STRINGS

==============================================================================*/

// Deathstring 1 is the standard one
// Deathstring 2 has a 1/100 chance to be used instead
// Deathstring G is used for when the victim was gibbed (Grenade Launcher and Rocket Launcher only)
// Deathstring Q is used if the attacker had a Quad Damage
// Deathstring D1 is used if the attack was a discharge (Lightning Gun only)
// Deathstring D2 has a 1/100 chance to be used instead (Lightning Gun only)
// The format for printing is: victim name, deathstring A, attacker name, deathstring B

#define LOC_DEATH_AXE_1A				" was picked apart by "
#define LOC_DEATH_AXE_1B				""
#define LOC_DEATH_AXE_2A				" was broken up by "
#define LOC_DEATH_AXE_2B				""
#define LOC_DEATH_AXE_QA				" was split like coke by "
#define LOC_DEATH_AXE_QB				""

#define LOC_DEATH_SHOTGUN_1A			" was peppered by "
#define LOC_DEATH_SHOTGUN_1B			"'s Scattergun"
#define LOC_DEATH_SHOTGUN_2A			" caught "
#define LOC_DEATH_SHOTGUN_2B			"'s scatter"
#define LOC_DEATH_SHOTGUN_QA			" was scattered by "
#define LOC_DEATH_SHOTGUN_QB			""

#define LOC_DEATH_SUPER_SHOTGUN_1A		" was scalded by "
#define LOC_DEATH_SUPER_SHOTGUN_1B		"'s Steam Cannon"
#define LOC_DEATH_SUPER_SHOTGUN_2A		" was boiled by "
#define LOC_DEATH_SUPER_SHOTGUN_2B		""
#define LOC_DEATH_SUPER_SHOTGUN_QA		" was blown off their feet by "
#define LOC_DEATH_SUPER_SHOTGUN_QB		""

#define LOC_DEATH_NAILGUN_1A			" was riveted by "
#define LOC_DEATH_NAILGUN_1B			"'s Spitter"
#define LOC_DEATH_NAILGUN_2A			" was spat full of iron by "
#define LOC_DEATH_NAILGUN_2B			""
#define LOC_DEATH_NAILGUN_QA			" was nailed to the floor by "
#define LOC_DEATH_NAILGUN_QB			""

#define LOC_DEATH_SUPER_NAILGUN_1A		" was bolted by "
#define LOC_DEATH_SUPER_NAILGUN_1B		"'s Bolt Caster"
#define LOC_DEATH_SUPER_NAILGUN_2A		" was pinned up by "
#define LOC_DEATH_SUPER_NAILGUN_2B		""
#define LOC_DEATH_SUPER_NAILGUN_QA		" was hung on the wall by "
#define LOC_DEATH_SUPER_NAILGUN_QB		""

#define LOC_DEATH_GRENADE_LAUNCHER_1A	" stepped in "
#define LOC_DEATH_GRENADE_LAUNCHER_1B	"'s pour"
#define LOC_DEATH_GRENADE_LAUNCHER_2A	" was cast in "
#define LOC_DEATH_GRENADE_LAUNCHER_2B	"'s Crucible"
#define LOC_DEATH_GRENADE_LAUNCHER_GA	" was spattered by "
#define LOC_DEATH_GRENADE_LAUNCHER_GB	"'s Crucible"
#define LOC_DEATH_GRENADE_LAUNCHER_QA	" was poured into a mould by "
#define LOC_DEATH_GRENADE_LAUNCHER_QB	""

#define LOC_DEATH_ROCKET_LAUNCHER_1A	" was shelled by "
#define LOC_DEATH_ROCKET_LAUNCHER_1B	"'s Shot Mortar"
#define LOC_DEATH_ROCKET_LAUNCHER_2A	" caught "
#define LOC_DEATH_ROCKET_LAUNCHER_2B	"'s shot"
#define LOC_DEATH_ROCKET_LAUNCHER_GA	" was blown to cinders by "
#define LOC_DEATH_ROCKET_LAUNCHER_GB	"'s Shot Mortar"
#define LOC_DEATH_ROCKET_LAUNCHER_Q1A	" was flattened by "
#define LOC_DEATH_ROCKET_LAUNCHER_Q1B	"'s Forge Heart"

#define LOC_DEATH_LIGHTNING_1A			" was tolled by "
#define LOC_DEATH_LIGHTNING_1B			"'s Tolling Iron"
#define LOC_DEATH_LIGHTNING_2A			" heard "
#define LOC_DEATH_LIGHTNING_2B			"'s bell for the last time"
#define LOC_DEATH_LIGHTNING_QA			" was rung out by "
#define LOC_DEATH_LIGHTNING_QB			""
#define LOC_DEATH_LIGHTNING_DA			" was rung out in the water by "
#define LOC_DEATH_LIGHTNING_DB			""

#define LOC_DEATH_TELEFRAG				" was stood on by "

#define LOC_DEATH_DEFLECT_A				"The Founder's Mantle turned aside "
#define LOC_DEATH_DEFLECT_B				"'s telefrag on "

#define LOC_TEAMKILL_1					" killed a teammate"
#define LOC_TEAMKILL_2					" friendly-fired"
#define LOC_TEAMKILL_3					" hit the wrong stoker"
#define LOC_TEAMKILL_4					" betrayed their friend"
#define LOC_TEAMKILL_SQUISH				" crushed a teammate"

#define LOC_DEATH_KILL					" killed "

/*==============================================================================

			LIBREQUAKE UTILITY STRINGS

==============================================================================*/

#define LOC_LQ_ISDEVELOPER				"You must be a developer!"

/*==============================================================================

			LIBREQUAKE CAMERA STRINGS

==============================================================================*/

#define LOC_LQ_CAMERAS_MAX				"You have too many cameras!"
#define LOC_LQ_CAMERA_SPAWN_A			"Camera placed successfully, "
#define LOC_LQ_CAMERA_SPAWN_B			" remaining"
#define LOC_LQ_CAMERA_TIME_A			"Time between cameras changed to "
#define LOC_LQ_CAMERA_TIME_B			" seconds"
#define LOC_LQ_CAMERA_NONE				"Oh noes! No camera found! :("

