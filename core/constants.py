from enum import IntEnum, StrEnum
from typing import Dict, Tuple


class PCFVersion(StrEnum):
    # PCF version strings
    DMX_BINARY2_DMX1 = "<!-- dmx encoding binary 2 format dmx 1 -->"
    DMX_BINARY2_PCF1 = "<!-- dmx encoding binary 2 format pcf 1 -->"
    DMX_BINARY3_PCF1 = "<!-- dmx encoding binary 3 format pcf 1 -->"
    DMX_BINARY3_PCF2 = "<!-- dmx encoding binary 3 format pcf 2 -->"
    DMX_BINARY4_PCF2 = "<!-- dmx encoding binary 4 format pcf 2 -->"
    DMX_BINARY5_PCF2 = "<!-- dmx encoding binary 5 format pcf 2 -->"


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


# PCF_OFFSETS: Dict[str, Tuple[int, int]] = {
#     # PCF_FILE: (OFFSET, SIZE)
#     "bigboom.pcf": (7645741, 93747), # "bigboom.pcf": (7661562, 93747),
#     "blood_impact.pcf": (7206409, 93642),
#     "blood_trail.pcf": (7300993, 5706),
#     # "blood_trail_dx80.pcf": (7300993, 5706),
#     "bl_killtaunt.pcf": (11435825, 104075),
#     # "bl_killtaunt_dx80.pcf": (11435825, 103778),
#     "bombinomicon.pcf": (10308505, 7143),
#     "buildingdamage.pcf": (7871850, 52069),
#     "bullet_tracers.pcf": (7969784, 62761),
#     "burningplayer.pcf": (7056758, 148827),
#     # "burningplayer_dx80.pcf": (98925283, 138721),
#     "cig_smoke.pcf": (7473855, 8447),
#     # "cig_smoke_dx80.pcf": (7473855, 8447),
#     "cinefx.pcf": (9023063, 81997),
#     "class_fx.pcf": (9198369, 236392),
#     "coin_spin.pcf": (9785031, 5606),
#     "conc_stars.pcf": (9180603, 17459),
#     "crit.pcf": (7482458, 24175),
#     "dirty_explode.pcf": (9435374, 57251),
#     "disguise.pcf": (8044047, 21199),
#     "doomsday_fx.pcf": (10858205, 27228),
#     "drg_bison.pcf": (9996007, 60413),
#     "drg_cowmangler.pcf": (9837786, 157797),
#     # "drg_cowmangler_dx80.pcf": (9837786, 157797),
#     "drg_engineer.pcf": (10343831, 56203),
#     "drg_pyro.pcf": (10400034, 125151),
#     "dxhr_fx.pcf": (10056420, 123290),
#     "explosion.pcf": (6516928, 132368),
#     "eyeboss.pcf": (10179980, 128394),
#     "flag_particles.pcf": (8113165, 26396),
#     "flamethrower.pcf": (6708720, 310292),
#     "flamethrower_mvm.pcf": (7021295, 35463),
#     "halloween.pcf": (10885528, 492066),
#     "harbor_fx.pcf": (10315648, 28042),
#     "impact_fx.pcf": (9105621, 74982),
#     "items_demo.pcf": (11377744, 42654),
#     "items_engineer.pcf": (11420398, 15427),
#     "item_fx.pcf": (8170897, 845558),
#     "level_fx.pcf": (9605509, 143898),
#     "medicgun_attrib.pcf": (8145548, 25349),
#     "medicgun_beam.pcf": (7507719, 135045),
#     "muzzle_flash.pcf": (7306699, 83923),
#     "mvm.pcf": (10578245, 278605),
#     "nailtrails.pcf": (7923919, 9242),
#     "nemesis.pcf": (8032682, 10861),
#     "npc_fx.pcf": (9823592, 13847),
#     "player_recent_teleport.pcf": (6649990, 25217),
#     # "player_recent_teleport_dx80.pcf": (99072451, 18719),
#     "rain_custom.pcf": (9795597, 27995),
#     "rocketbackblast.pcf": (6702798, 5922),
#     "rocketjumptrail.pcf": (6675544, 27075),
#     "rockettrail.pcf": (6245745, 118126),
#     "scary_ghost.pcf": (9497497, 70763),
#     "shellejection.pcf": (8140261, 5106),
#     # "shellejection_dx80.pcf": (8140261, 5106),
#     "shellejection_high.pcf": (8140261, 5106),
#     "smoke_blackbillow.pcf": (6364723, 62587),
#     "smoke_blackbillow_hoodoo.pcf": (9492625, 4872), #TEST THIS ONE LATER FOR BUG PATCH
#     "soldierbuff.pcf": (9568260, 37065),
#     # "soldierbuff_dx80.pcf": (9568260, 37065),
#     "sparks.pcf": (8065389, 47776),
#     "speechbubbles.pcf": (7933161, 35872),
#     "stamp_spin.pcf": (9790637, 4960),
#     "stickybomb.pcf": (7827932, 43918),
#     # "stickybomb_dx80.pcf": (7827932, 43701),
#     "stormfront.pcf": (9778246, 6785),
#     "teleported_fx.pcf": (7391073, 80869),
#     "teleport_status.pcf": (6427310, 88929),
#     "training.pcf": (9749407, 28839),
#     "water.pcf": (7741026, 86046),
#     # "water_dx80.pcf": (99091170, 81788),
#     "xms.pcf": (10525798, 52280),
# }


PCF_OFFSETS: Dict[str, Tuple[int, int]] = {
    "water.pcf": (7756847, 86046),
    "level_fx.pcf": (9621330, 143898),
    "flamethrower.pcf": (6724541, 310292),
    "halloween.pcf": (10901349, 492066),
    "teleport_status.pcf": (6443131, 88929),
    "stamp_spin.pcf": (9806458, 4960),
    "burningplayer.pcf": (7072579, 148827),
    "doomsday_fx.pcf": (10874026, 27228),
    "muzzle_flash.pcf": (7322520, 83923),
    "items_engineer.pcf": (11436219, 15427),
    "items_demo.pcf": (11393565, 42654),
    "drg_cowmangler.pcf": (9853607, 157797),
    "conc_stars.pcf": (9196424, 17459),
    "mvm.pcf": (10594066, 278605),
    "soldierbuff.pcf": (9584081, 37065),
    "training.pcf": (9765228, 28839),
    "disguise.pcf": (8059868, 21199),
    "scary_ghost.pcf": (9513318, 70763),
    "bullet_tracers.pcf": (7985605, 62761),
    "blood_trail.pcf": (7316814, 5706),
    "smoke_blackbillow_hoodoo.pcf": (9508446, 4872),
    "npc_fx.pcf": (9839413, 13847),
    "smoke_blackbillow.pcf": (6380544, 62587),
    "cig_smoke.pcf": (7489676, 8447),
    "flamethrower_mvm.pcf": (7037116, 35463),
    "nemesis.pcf": (8048503, 10861),
    "buildingdamage.pcf": (7887671, 52069),
    "flag_particles.pcf": (8128986, 26396),
    "medicgun_attrib.pcf": (8161369, 25349),
    "blood_impact.pcf": (7222230, 93642),
    "rocketjumptrail.pcf": (6691365, 27075),
    "sparks.pcf": (8081210, 47776),
    "bombinomicon.pcf": (10324326, 7143),
    "rockettrail.pcf": (6261566, 118126),
    "coin_spin.pcf": (9800852, 5606),
    "stickybomb.pcf": (7843753, 43918),
    "explosion.pcf": (6532749, 132368),
    "player_recent_teleport.pcf": (6665811, 25217),
    "bigboom.pcf": (7661562, 93747),
    "eyeboss.pcf": (10195801, 128394),
    "speechbubbles.pcf": (7948982, 35872),
    "dirty_explode.pcf": (9451195, 57251),
    "nailtrails.pcf": (7939740, 9242),
    "teleported_fx.pcf": (7406894, 80869),
    "shellejection.pcf": (8156082, 5106),
    "cinefx.pcf": (9038884, 81997),
    "item_fx.pcf": (8186718, 845558),
    "medicgun_beam.pcf": (7523540, 135045),
    "drg_pyro.pcf": (10415855, 125151),
    "xms.pcf": (10541619, 52280),
    "drg_engineer.pcf": (10359652, 56203),
    "dxhr_fx.pcf": (10072241, 123290),
    "class_fx.pcf": (9214190, 236392),
    "shellejection_high.pcf": (8156082, 5106),
    "impact_fx.pcf": (9121442, 74982),
    "drg_bison.pcf": (10011828, 60413),
    "bl_killtaunt.pcf": (11451646, 104075),
    "crit.pcf": (7498279, 24175),
    "stormfront.pcf": (9794067, 6785),
    "rocketbackblast.pcf": (6718619, 5922),
    "harbor_fx.pcf": (10331469, 28042),
    "rain_custom.pcf": (9811418, 27995),
}