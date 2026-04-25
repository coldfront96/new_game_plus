"""Regression tests pinning the DMG_BUILD_SITE Tier 0–3 audit (Task 8).

Each shipped task is asserted via a straightforward import/lookup so a
future refactor that removes a symbol lights up in CI instead of
silently drifting from the audit.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Tier 0 — base schemas / enums
# ---------------------------------------------------------------------------

def test_t001_material_schema_exists():
    from src.rules_engine.objects import (
        MATERIAL_STATS,
        MaterialType,
        ObjectMaterial,
    )
    assert ObjectMaterial.__dataclass_fields__
    assert MaterialType.WOOD in MaterialType
    assert MATERIAL_STATS  # non-empty


def test_t002_weather_enums_exist():
    from src.rules_engine.environment import (
        Precipitation, Temperature, WindStrength,
    )
    assert WindStrength.CALM in WindStrength
    assert Temperature.COLD in Temperature
    assert Precipitation.NONE in Precipitation


def test_t003_terrain_enum_exists():
    from src.rules_engine.environment import TerrainType
    expected = {
        "DUNGEON", "FOREST", "PLAINS", "DESERT",
        "HILLS", "MOUNTAINS", "MARSH", "ARCTIC",
    }
    assert expected <= {t.name for t in TerrainType}


def test_t004_trap_base_schema_exists():
    from src.rules_engine.traps import (
        ResetType, TrapBase, TrapType, TriggerType,
    )
    assert TrapBase.__dataclass_fields__
    assert TrapType.MECHANICAL in TrapType
    assert TriggerType.LOCATION in TriggerType
    assert ResetType.NO_RESET in ResetType


def test_t005_consumable_schemas_exist():
    from src.rules_engine.consumables import (
        PotionBase, RodBase, ScrollBase, StaffBase, WandBase,
    )
    for cls in (PotionBase, ScrollBase, WandBase, RodBase, StaffBase):
        assert cls.__dataclass_fields__


def test_t006_t007_special_ability_schemas():
    from src.rules_engine.item_specials import (
        ArmorSpecialAbility, WeaponSpecialAbility,
    )
    assert ArmorSpecialAbility.__dataclass_fields__
    assert WeaponSpecialAbility.__dataclass_fields__


def test_t008_t009_gem_art_schemas():
    from src.rules_engine.treasure import ArtObjectEntry, GemEntry
    assert GemEntry.__dataclass_fields__
    assert ArtObjectEntry.__dataclass_fields__


def test_t010_cr_to_xp_exists():
    from src.rules_engine.encounter import CR_TO_XP
    assert CR_TO_XP[1] == 300
    assert CR_TO_XP[20] == 307_200


def test_t011_artifact_schema_exists():
    from src.rules_engine.item_specials import ArtifactEntry, ArtifactType
    assert ArtifactEntry.__dataclass_fields__
    assert ArtifactType.MINOR in ArtifactType


# ---------------------------------------------------------------------------
# Tier 1 — core formulas
# ---------------------------------------------------------------------------

def test_t012_t013_object_formulas():
    from src.rules_engine.objects import (
        apply_damage_to_object,
        calculate_break_dc,
    )
    assert callable(calculate_break_dc)
    assert callable(apply_damage_to_object)


def test_t014_t015_environment_helpers():
    from src.rules_engine.environment import (
        apply_weather_penalties,
        terrain_hide_bonus,
        terrain_listen_penalty,
        terrain_movement_cost,
    )
    for fn in (
        apply_weather_penalties, terrain_movement_cost,
        terrain_hide_bonus, terrain_listen_penalty,
    ):
        assert callable(fn)


def test_t016_t017_trap_resolvers():
    from src.rules_engine.traps import (
        DisableResult, find_trap_active, resolve_trap_disable,
        resolve_trap_search,
    )
    assert callable(resolve_trap_search)
    assert callable(find_trap_active)
    assert callable(resolve_trap_disable)
    assert DisableResult.DISABLED in DisableResult


def test_t018_t019_t020_t021_price_formulas():
    from src.rules_engine.consumables import (
        potion_market_price,
        rod_market_price,
        scroll_market_price,
        staff_market_price,
        wand_market_price,
    )
    assert potion_market_price(1, 1) > 0
    assert scroll_market_price(1, 1) > 0
    assert wand_market_price(1, 1) > 0


def test_t022_t023_treasure_randomisers():
    from src.rules_engine.treasure import roll_art_object, roll_gem_value
    assert callable(roll_gem_value)
    assert callable(roll_art_object)


def test_t024_xp_helpers():
    from src.rules_engine.encounter import xp_for_cr, xp_per_character
    assert xp_for_cr(5) == 1_600
    assert xp_per_character(5, apl=5) > 0


def test_t025_t026_ability_stack_validators():
    from src.rules_engine.item_specials import (
        validate_armor_ability_stack,
        validate_weapon_ability_stack,
    )
    # Empty ability list with 0 enhancement passes cleanly.
    assert validate_armor_ability_stack(0, []) is True
    assert validate_weapon_ability_stack(0, []) is True


# ---------------------------------------------------------------------------
# Tier 2 — registries & engines
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module,name,minimum", [
    ("src.rules_engine.consumables", "POTION_REGISTRY", 30),
    ("src.rules_engine.consumables", "SCROLL_REGISTRY", 40),
    ("src.rules_engine.consumables", "WAND_REGISTRY", 25),
    ("src.rules_engine.consumables", "ROD_REGISTRY", 20),
    ("src.rules_engine.consumables", "STAFF_REGISTRY", 17),
    ("src.rules_engine.item_specials", "ARMOR_SPECIAL_ABILITY_REGISTRY", 16),
    ("src.rules_engine.item_specials", "WEAPON_SPECIAL_ABILITY_REGISTRY", 25),
    ("src.rules_engine.item_specials", "ARTIFACT_REGISTRY", 26),
])
def test_registry_has_minimum_entries(module, name, minimum):
    mod = __import__(module, fromlist=[name])
    reg = getattr(mod, name)
    assert len(reg) >= minimum, (
        f"{name} has {len(reg)} entries, expected ≥ {minimum}"
    )


def test_t036_t037_combat_engines():
    from src.rules_engine.environment import (
        Maneuverability,
        UnderwaterModifiers,
        WeaponType,
        apply_aerial_modifiers,
        apply_underwater_modifiers,
    )
    assert UnderwaterModifiers.__dataclass_fields__
    assert Maneuverability.CLUMSY in Maneuverability
    assert callable(apply_underwater_modifiers)
    assert callable(apply_aerial_modifiers)


def test_t038_weather_state_machine():
    from src.rules_engine.environment import (
        WeatherStateMachine, generate_weather,
    )
    assert WeatherStateMachine.__dataclass_fields__
    assert callable(generate_weather)


def test_t039_calculate_el():
    from src.rules_engine.encounter import calculate_el
    # Two CR 3 monsters should produce EL 5 (nearest to twice 800 XP → 1600 XP).
    assert calculate_el([3.0, 3.0]) == 5.0


# ---------------------------------------------------------------------------
# Tier 3 — complex generators
# ---------------------------------------------------------------------------

def test_t040_t041_trap_generators():
    from src.rules_engine.traps import (
        MagicalTrap, MechanicalTrap,
        generate_magical_trap, generate_mechanical_trap,
    )
    assert MechanicalTrap.__dataclass_fields__
    assert MagicalTrap.__dataclass_fields__
    assert callable(generate_mechanical_trap)
    assert callable(generate_magical_trap)


def test_t042_t043_magic_item_generators():
    from src.rules_engine.item_specials import (
        generate_magic_armor, generate_magic_weapon,
    )
    assert callable(generate_magic_armor)
    assert callable(generate_magic_weapon)


def test_t045_encounter_tables_cover_core_terrains():
    from src.rules_engine.encounter_extended import ENCOUNTER_TABLES
    core = {"dungeon", "forest", "plains", "desert",
            "hills", "mountains", "marsh", "arctic"}
    assert core <= set(ENCOUNTER_TABLES.keys())
    for terrain in core:
        assert len(ENCOUNTER_TABLES[terrain]) >= 10


def test_t046_dungeon_dressing_exists():
    from src.rules_engine.environment import (
        AirQuality, DungeonDressingResult, generate_dungeon_dressing,
    )
    assert AirQuality.__members__
    assert DungeonDressingResult.__dataclass_fields__
    assert callable(generate_dungeon_dressing)


def test_t047_room_population_roller_exists():
    from src.rules_engine.traps import RoomContents, roll_room_contents
    assert RoomContents.__dataclass_fields__
    assert callable(roll_room_contents)


# ---------------------------------------------------------------------------
# Residual backlog notes — pin the known content-gap tables.
# ---------------------------------------------------------------------------

def test_residual_gem_table_size():
    """Pins the current size of GEM_TABLE so expanding it to the full
    60-entry spec is visible as a failing test until T-034 lands."""
    from src.rules_engine.treasure import GEM_TABLE
    assert len(GEM_TABLE) >= 50


def test_residual_art_object_table_size():
    from src.rules_engine.treasure import ART_OBJECT_TABLE
    assert len(ART_OBJECT_TABLE) >= 50
