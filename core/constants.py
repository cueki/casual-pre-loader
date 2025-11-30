from enum import IntEnum, StrEnum
from typing import Dict


class PCFVersion(StrEnum):
    # PCF version strings
    DMX_BINARY2_DMX1 = "<!-- dmx encoding binary 2 format dmx 1 -->"
    DMX_BINARY2_PCF1 = "<!-- dmx encoding binary 2 format pcf 1 -->"
    DMX_BINARY3_PCF1 = "<!-- dmx encoding binary 3 format pcf 1 -->"


class AttributeType(IntEnum):
    ELEMENT = 0x01
    INTEGER = 0x02
    FLOAT = 0x03
    BOOLEAN = 0x04
    STRING = 0x05
    BINARY = 0x06
    TIME = 0x07
    COLOR = 0x08
    VECTOR2 = 0x09
    VECTOR3 = 0x0A
    VECTOR4 = 0x0B
    QANGLE = 0x0C
    QUATERNION = 0x0D
    MATRIX = 0x0E
    ELEMENT_ARRAY = 0x0F
    INTEGER_ARRAY = 0x10
    FLOAT_ARRAY = 0x11
    BOOLEAN_ARRAY = 0x12
    STRING_ARRAY = 0x13
    BINARY_ARRAY = 0x14
    TIME_ARRAY = 0x15
    COLOR_ARRAY = 0x16
    VECTOR2_ARRAY = 0x17
    VECTOR3_ARRAY = 0x18
    VECTOR4_ARRAY = 0x19
    QANGLE_ARRAY = 0x1A
    QUATERNION_ARRAY = 0x1B
    MATRIX_ARRAY = 0x1C


ATTRIBUTE_VALUES: Dict[AttributeType, str] = {
    AttributeType.ELEMENT: '<I',
    AttributeType.INTEGER: '<i',
    AttributeType.FLOAT: '<f',
    AttributeType.BOOLEAN: 'B',
    AttributeType.STRING: '<H',
    AttributeType.BINARY: '<I',
    AttributeType.COLOR: '<4B',
    AttributeType.VECTOR2: '<2f',
    AttributeType.VECTOR3: '<3f',
    AttributeType.VECTOR4: '<4f',
    AttributeType.MATRIX: '<4f',
    AttributeType.ELEMENT_ARRAY: '<I',
}


ELEMENT_DEFAULTS = [
    ("max_particles", 1000),
    ("initial_particles", 0),
    ("material", b"vgui/white"),
    ("bounding_box_min", (-10.0, -10.0, -10.0)),
    ("bounding_box_max", (10.0, 10.0, 10.0)),
    ("cull_radius", 0.0),
    ("cull_cost", 1.0),
    ("cull_control_point", 0),
    ("cull_replacement_definition", b""),
    ("radius", 5.0),
    ("color", (255, 255, 255, 255)),
    ("rotation", 0.0),
    ("rotation_speed", 0.0),
    ("sequence_number", 0),
    ("sequence_number1", 0),
    ("group id", 0),
    ("maximum time step", 0.1),
    ("maximum sim tick rate", 0.0),
    ("minimum sim tick rate", 0.0),
    ("minimum rendered frames", 0),
    ("control point to disable rendering if it is the camera", -1),
    ("maximum draw distance", 100000.0),
    ("time to sleep when not drawn", 8.0),
    ("Sort particles", True),
    ("batch particle systems", False),
    ("view model effect", False)
]


ATTRIBUTE_DEFAULTS = [
    ("operator start fadein", 0.0),
    ("operator end fadein", 0.0),
    ("operator start fadeout", 0.0),
    ("operator end fadeout", 0.0),
    ("operator fade oscillate", 0.0),
    ("Visibility Proxy Input Control Point Number", -1),
    ("Visibility Proxy Radius", 1.0),
    ("Visibility input minimum", 0.0),
    ("Visibility input maximum", 1.0),
    ("Visibility Alpha Scale minimum", 0.0),
    ("Visibility Alpha Scale maximum", 1.0),
    ("Visibility Radius Scale minimum", 1.0),
    ("Visibility Radius Scale maximum", 1.0),
    ("Visibility Camera Depth Bias", 0.0)
]


DX8_LIST = [
    "burningplayer",
    "cig_smoke",
    "bigboom",
    "player_recent_teleport",
    "water",
    "bl_killtaunt",
    "blood_trail",
    "class_fx",
    "drg_cowmangler",
    "drg_pyro",
    "explosion",
    "eyeboss",
    "firstperson_weapon_fx",
    "flamethrower",
    "harbor_fx",
    "medicgun_beam",
    "muzzle_flash",
    "rockettrail",
    "shellejection",
    "smoke_blackbillow",
    "soldierbuff",
    "stickybomb"
]


CUSTOM_VPK_NAME = "_casual_preloader.vpk"
CUSTOM_VPK_SPLIT_PATTERN = "_casual_preloader_"
LEGACY_VPK_NAMES = [
    "_wermware_2025.vpk",
    "_fragaholic_config.vpk",
    "_cuekicuttersolution.vpk",
    "_meow_meow_meow_sad_song_1_hour_compilation.vpk",
    "_pls_answer_my_email_eric.vpk",
    "_SUBJECT_LINE_VERY_POTENTIAL_LIKELY_BAD_THING_TF2.vpk",
    "_go_spin_the_badge.vpk",
    "_4_year_ban_for_this_btw.vpk",
    "_rgl_anti_anticheat.vpk"
]
CUSTOM_VPK_NAMES = [CUSTOM_VPK_NAME] + LEGACY_VPK_NAMES
BACKUP_MAINMENU_FOLDER = "zz_run_preloader_again_if_you_add_a_custom_hud_or_else_i_will_kill_you_rahhhh_anyways_just_run_the_install_again_please"


QUICKPRECACHE_FILE_SUFFIXES = [
    ".dx80.vtx",
    ".dx90.vtx",
    ".mdl",
    ".phy",
    ".sw.vtx",
    ".vvd"
]


QUICKPRECACHE_MODEL_LIST = [
    "prop",
    "flag",
    "bots",
    "ammo_box",
    "ammopack",
    "medkit",
    "currencypack"
]


DECAL_MAPPING = {
    # this is just the blood decal mapping, would need to add bullet holes and such if we want those
    "decal/flesh/blood1": {"position": (384, 64), "size": (64, 64)},
    "decal/flesh/blood2": {"position": (448, 0), "size": (64, 64)},
    "decal/flesh/blood3": {"position": (448, 64), "size": (64, 64)},
    "decal/flesh/blood4": {"position": (512, 0), "size": (64, 64)},
    "decal/flesh/blood5": {"position": (512, 64), "size": (64, 64)},
    "decal/blood1": {"position": (384, 128), "size": (128, 128)},
    "decal/blood2": {"position": (512, 128), "size": (128, 128)},
    "decal/blood3": {"position": (640, 128), "size": (128, 128)},
    "decal/blood4": {"position": (768, 128), "size": (128, 128)},
    "decal/blood5": {"position": (256, 256), "size": (128, 128)},
    "decal/blood6": {"position": (384, 256), "size": (128, 128)},
}


PARTICLE_GROUP_MAPPING = {
    "explosions": ["drg_cowmangler.pcf", "stickybomb.pcf", "rocketbackblast.pcf",
                   "explosion.pcf", "rockettrail.pcf", "classic_rocket_trail.pcf"],
    "fire": ["drg_pyro.pcf", "burningplayer.pcf", "flamethrower_mvm.pcf", "flamethrower.pcf"],
    "bullets": ["impact_fx.pcf", "shellejection.pcf", "bullet_tracers.pcf",
                "nailtrails.pcf", "muzzle_flash.pcf"],
    "blood": ["blood_impact.pcf", "blood_trail.pcf"],
    "weapons": ["rocketpack.pcf", "invasion_ray_gun_fx.pcf", "firstperson_weapon_fx.pcf",
                "items_engineer.pcf", "items_demo.pcf", "xms.pcf", "drg_engineer.pcf",
                "dxhr_fx.pcf", "drg_bison.pcf", "soldierbuff.pcf", "medicgun_attrib.pcf", "medicgun_beam.pcf"],
    "maps": ["urban_fx.pcf", "smoke_island_volcano.pcf", "doomsday_fx.pcf", "harbor_fx.pcf",
             "rain_custom.pcf", "stormfront.pcf", "dirty_explode.pcf", "water.pcf",
             "bigboom.pcf", "smoke_blackbillow.pcf"],
    "game_modes": ["powerups.pcf", "passtime_tv_projection.pcf", "passtime_beam.pcf", "passtime.pcf",
                   "halloween.pcf", "mvm.pcf", "eyeboss.pcf", "scary_ghost.pcf", "flag_particles.pcf"],
    "unusuals_hats": ["item_fx_unusuals.pcf", "unusual_burning_flames.pcf", "unusual_darkblaze.pcf",
                      "unusual_demonflame.pcf", "unusual_ghostly_ghosts.pcf", "unusual_purple_energy.pcf",
                      "unusual_scorching_flames.pcf", "unusual_tesla_coil.pcf",
                      "halloween2015_unusuals.pcf", "halloween2016_unusuals.pcf", "halloween2018_unusuals.pcf",
                      "halloween2019_unusuals.pcf", "halloween2020_unusuals.pcf", "halloween2021_unusuals.pcf",
                      "halloween2022_unusuals.pcf", "halloween2023_unusuals.pcf", "halloween2024_unusuals.pcf",
                      "halloween2025_unusuals.pcf", "invasion_unusuals.pcf", "smissmas2019_unusuals.pcf",
                      "smissmas2020_unusuals.pcf", "smissmas2021_unusuals.pcf", "smissmas2022_unusuals.pcf",
                      "smissmas2023_unusuals.pcf", "smissmas2024_unusuals.pcf", "summer2020_unusuals.pcf",
                      "summer2021_unusuals.pcf", "summer2022_unusuals.pcf", "summer2023_unusuals.pcf",
                      "summer2024_unusuals.pcf", "summer2025_unusuals.pcf"],
    "unusual_weapons": ["weapon_unusual_cool.pcf", "weapon_unusual_energyorb.pcf", "weapon_unusual_hot.pcf",
                        "weapon_unusual_isotope.pcf"],
    "player": ["taunt_fx.pcf", "rps.pcf", "killstreak.pcf", "bl_killtaunt.pcf", "class_fx.pcf",
               "conc_stars.pcf", "item_fx_gameplay.pcf", "disguise.pcf", "nemesis.pcf", "speechbubbles.pcf",
               "crit.pcf", "cig_smoke.pcf", "rocketjumptrail.pcf"],
    "buildings": ["teleport_status.pcf", "player_recent_teleport.pcf", "teleported_fx.pcf", "buildingdamage.pcf",
                  "sparks.pcf"],
    "misc": ["bombinomicon.pcf", "training.pcf", "cinefx.pcf", "vgui_menu_particles.pcf", "rankup.pcf",
             "stamp_spin.pcf", "coin_spin.pcf", "npc_fx.pcf"]
}


VALID_MOD_ROOT_FOLDERS = {
    "cfg",
    "classes",
    "expressions",
    "maps",
    "materials",
    "media",
    "models",
    "particles",
    "resource",
    "scenes",
    "scripts",
    "servers",
    "sound"
}


MOD_TYPE_COLORS = {
    "skin": "#4CAF50",         # green
    "model": "#2196F3",        # blue
    "texture": "#9C27B0",      # magenta
    "misc": "#FF9800",         # orange
    "animation": "#392C52",    # purple
    "experimental": "#EED202", # yellow
    "hud": "#00BCD4",          # cyan
    "sound": "#E91E63",        # pink
    "unknown": "#FF0000"       # red
}


# project and remote repository info
PROGRAM_AUTHOR = 'cueki'
PROGRAM_NAME = 'casual-pre-loader'
REMOTE_REPO = f'{PROGRAM_AUTHOR}/{PROGRAM_NAME}'


# directories and files to include in releases
# used by build script and auto-updater to avoid unpacking python binaries on linux
BUILD_DIRS = [
    'core',
    'gui',
    'backup',
    'data',
]

BUILD_FILES = [
    'main.py',
    'LICENSE',
    'README.md',
    'requirements.txt'
]


# particle split configuration
PARTICLE_SPLITS = {
    "item_fx.pcf": {
        "item_fx_unusuals.pcf": lambda name: (
            name.startswith("unusual_") or
            name.startswith("superrare_") or
            name == "superare_balloon"  # typo in original Valve file (lol)
        ),
        "item_fx_gameplay.pcf": "**EVERYTHING_ELSE**"
    }
}
