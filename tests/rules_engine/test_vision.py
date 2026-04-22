"""
tests/rules_engine/test_vision.py
----------------------------------
Unit tests for the Environmental Lighting Engine and Voxel Vision System.

Covers:
- LightLevel enum membership.
- LightSystem light-level queries (sunlight, point lights, combinations).
- Low-Light Vision doubling effect.
- Vision component slots and attributes.
- VisionSystem.check_visibility() for Normal vs. Darkvision in Darkness.
- AttackResolver miss-chance integration:
  * Orc (Darkvision) vs. target in Darkness → no miss-chance penalty.
  * Human vs. target in Darkness → 50 % miss chance.
  * Any attacker vs. target in Dim Light → 20 % miss chance.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.ai_sim.components import Position, Vision, VisionType
from src.ai_sim.entity import Entity
from src.ai_sim.systems import VisionSystem
from src.rules_engine.character_35e import Character35e
from src.rules_engine.combat import AttackResolver, CombatResult
from src.terrain.lighting import (
    LightLevel,
    LightState,
    LightSystem,
    PointLight,
    Sunlight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    name: str,
    x: float = 0.0,
    y: float = 64.0,
    z: float = 0.0,
    vision_type: VisionType = VisionType.NORMAL,
    range_ft: float = 60.0,
) -> Entity:
    e = Entity(name=name)
    e.add_component(Position(x=x, y=y, z=z))
    e.add_component(Vision(vision_type=vision_type, range_ft=range_ft))
    return e


def _make_char(name: str, race: str = "Human") -> Character35e:
    return Character35e(
        name=name,
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=12,
        constitution=14,
        race=race,
    )


# ---------------------------------------------------------------------------
# LightLevel enum
# ---------------------------------------------------------------------------

class TestLightLevelEnum:
    def test_members_exist(self):
        assert LightLevel.BRIGHT
        assert LightLevel.DIM
        assert LightLevel.DARKNESS

    def test_ordering(self):
        # BRIGHT < DIM < DARKNESS by .value (auto() assigns 1, 2, 3)
        assert LightLevel.BRIGHT.value < LightLevel.DIM.value
        assert LightLevel.DIM.value < LightLevel.DARKNESS.value


# ---------------------------------------------------------------------------
# LightState dataclass
# ---------------------------------------------------------------------------

class TestLightState:
    def test_slots_enabled(self):
        assert hasattr(LightState, "__slots__")

    def test_fields(self):
        ls = LightState(level=LightLevel.BRIGHT, contributing_source="sunlight")
        assert ls.level == LightLevel.BRIGHT
        assert ls.contributing_source == "sunlight"


# ---------------------------------------------------------------------------
# PointLight / Sunlight dataclasses
# ---------------------------------------------------------------------------

class TestPointLight:
    def test_slots_enabled(self):
        assert hasattr(PointLight, "__slots__")

    def test_defaults(self):
        pl = PointLight(x=0.0, y=64.0, z=0.0)
        assert pl.bright_radius == 4.0
        assert pl.radius == 8.0


class TestSunlight:
    def test_slots_enabled(self):
        assert hasattr(Sunlight, "__slots__")

    def test_defaults(self):
        sun = Sunlight()
        assert sun.surface_y == 64.0
        assert sun.radius == -1.0


# ---------------------------------------------------------------------------
# LightSystem — sunlight
# ---------------------------------------------------------------------------

class TestLightSystemSunlight:
    def test_surface_voxel_is_bright_with_unlimited_sunlight(self):
        system = LightSystem(sunlight=Sunlight(surface_y=64.0))
        assert system.get_light_level(0, 64, 0) == LightLevel.BRIGHT

    def test_below_surface_is_darkness(self):
        system = LightSystem(sunlight=Sunlight(surface_y=64.0))
        assert system.get_light_level(0, 63, 0) == LightLevel.DARKNESS

    def test_no_sunlight_is_darkness(self):
        system = LightSystem(sunlight=None)
        assert system.get_light_level(0, 64, 0) == LightLevel.DARKNESS

    def test_bounded_sunlight_within_bright_radius(self):
        sun = Sunlight(surface_y=64.0, radius=20.0, bright_radius=10.0,
                       origin_x=0.0, origin_z=0.0)
        system = LightSystem(sunlight=sun)
        # At origin → BRIGHT
        assert system.get_light_level(0, 64, 0) == LightLevel.BRIGHT

    def test_bounded_sunlight_between_bright_and_dim_radius(self):
        sun = Sunlight(surface_y=64.0, radius=20.0, bright_radius=10.0,
                       origin_x=0.0, origin_z=0.0)
        system = LightSystem(sunlight=sun)
        # 15 units away → DIM
        assert system.get_light_level(15, 64, 0) == LightLevel.DIM

    def test_bounded_sunlight_beyond_radius_is_darkness(self):
        sun = Sunlight(surface_y=64.0, radius=20.0, bright_radius=10.0,
                       origin_x=0.0, origin_z=0.0)
        system = LightSystem(sunlight=sun)
        assert system.get_light_level(25, 64, 0) == LightLevel.DARKNESS

    def test_set_sunlight_none_removes_light(self):
        system = LightSystem(sunlight=Sunlight(surface_y=64.0))
        assert system.get_light_level(0, 64, 0) == LightLevel.BRIGHT
        system.set_sunlight(None)
        assert system.get_light_level(0, 64, 0) == LightLevel.DARKNESS


# ---------------------------------------------------------------------------
# LightSystem — point lights
# ---------------------------------------------------------------------------

class TestLightSystemPointLight:
    def test_at_source_is_bright(self):
        system = LightSystem()
        system.add_point_light(PointLight(x=10, y=64, z=10))
        assert system.get_light_level(10, 64, 10) == LightLevel.BRIGHT

    def test_within_bright_radius_is_bright(self):
        system = LightSystem()
        system.add_point_light(PointLight(x=0, y=64, z=0, bright_radius=4.0, radius=8.0))
        assert system.get_light_level(3, 64, 0) == LightLevel.BRIGHT

    def test_beyond_bright_within_dim_radius(self):
        system = LightSystem()
        system.add_point_light(PointLight(x=0, y=64, z=0, bright_radius=4.0, radius=8.0))
        assert system.get_light_level(6, 64, 0) == LightLevel.DIM

    def test_beyond_radius_is_darkness(self):
        system = LightSystem()
        system.add_point_light(PointLight(x=0, y=64, z=0, bright_radius=4.0, radius=8.0))
        assert system.get_light_level(20, 64, 0) == LightLevel.DARKNESS

    def test_remove_point_light(self):
        system = LightSystem()
        pl = PointLight(x=0, y=64, z=0, bright_radius=4.0, radius=8.0)
        system.add_point_light(pl)
        system.remove_point_light(pl)
        assert system.get_light_level(0, 64, 0) == LightLevel.DARKNESS

    def test_multiple_lights_best_wins(self):
        system = LightSystem()
        # One dim-only light
        system.add_point_light(PointLight(x=0, y=64, z=0, bright_radius=2.0, radius=10.0))
        # One bright light further away that still reaches
        system.add_point_light(PointLight(x=5, y=64, z=0, bright_radius=10.0, radius=20.0))
        # Position at 7 voxels from first (dim), 2 from second (bright)
        assert system.get_light_level(7, 64, 0) == LightLevel.BRIGHT


# ---------------------------------------------------------------------------
# LightSystem — Low-Light Vision
# ---------------------------------------------------------------------------

class TestLowLightVision:
    def test_low_light_doubles_bright_radius(self):
        sun = Sunlight(surface_y=64.0, radius=20.0, bright_radius=10.0)
        system = LightSystem(sunlight=sun)
        # At 15 voxels: normally DIM; with Low-Light it's within 20 → BRIGHT
        normal = system.get_light_level_for_vision(15, 64, 0, "Normal")
        low_light = system.get_light_level_for_vision(15, 64, 0, "Low-Light Vision")
        assert normal == LightLevel.DIM
        assert low_light == LightLevel.BRIGHT

    def test_low_light_extends_point_light_radius(self):
        system = LightSystem()
        system.add_point_light(PointLight(x=0, y=64, z=0, bright_radius=4.0, radius=8.0))
        # At 6 voxels: DIM for normal; with Low-Light bright_radius doubles to 8 → BRIGHT
        normal = system.get_light_level_for_vision(6, 64, 0, "Normal")
        low_light = system.get_light_level_for_vision(6, 64, 0, "Low-Light Vision")
        assert normal == LightLevel.DIM
        assert low_light == LightLevel.BRIGHT


# ---------------------------------------------------------------------------
# Vision component
# ---------------------------------------------------------------------------

class TestVisionComponent:
    def test_slots_enabled(self):
        assert hasattr(Vision, "__slots__")

    def test_defaults(self):
        v = Vision()
        assert v.vision_type == VisionType.NORMAL
        assert v.range_ft == 60.0

    def test_has_darkvision_property(self):
        v = Vision(vision_type=VisionType.DARKVISION)
        assert v.has_darkvision is True
        assert v.has_low_light_vision is False

    def test_has_low_light_vision_property(self):
        v = Vision(vision_type=VisionType.LOW_LIGHT_VISION)
        assert v.has_low_light_vision is True
        assert v.has_darkvision is False

    def test_normal_neither_flag(self):
        v = Vision(vision_type=VisionType.NORMAL)
        assert v.has_darkvision is False
        assert v.has_low_light_vision is False


# ---------------------------------------------------------------------------
# VisionSystem
# ---------------------------------------------------------------------------

class TestVisionSystem:
    def _make_dark_system(self) -> LightSystem:
        """Return a LightSystem with no light sources → total darkness."""
        return LightSystem(sunlight=None)

    def _make_bright_system(self) -> LightSystem:
        return LightSystem(sunlight=Sunlight(surface_y=64.0))

    def test_normal_vision_in_bright_light_visible(self):
        ls = self._make_bright_system()
        vs = VisionSystem(ls)
        obs = _make_entity("obs", y=64)
        tgt = _make_entity("tgt", x=5, y=64)
        result = vs.check_visibility(obs, tgt)
        assert result.visible is True
        assert result.concealment == 0
        assert result.light_level == LightLevel.BRIGHT

    def test_normal_vision_in_darkness_cannot_see(self):
        ls = self._make_dark_system()
        vs = VisionSystem(ls)
        obs = _make_entity("obs")
        tgt = _make_entity("tgt", x=5)
        result = vs.check_visibility(obs, tgt)
        # Visible is False only if we define total-dark + no darkvision = not truly visible
        # concealment 50 % but still "visible" flag True (can attempt attack) — per SRD
        # concealment != invisible; we check concealment value
        assert result.concealment == 50
        assert result.light_level == LightLevel.DARKNESS

    def test_darkvision_in_darkness_within_range_bright(self):
        ls = self._make_dark_system()
        vs = VisionSystem(ls)
        obs = _make_entity("orc_obs", vision_type=VisionType.DARKVISION, range_ft=60.0)
        tgt = _make_entity("tgt", x=5)  # 5 voxels * 5 ft = 25 ft
        result = vs.check_visibility(obs, tgt)
        assert result.light_level == LightLevel.BRIGHT
        assert result.concealment == 0
        assert result.visible is True

    def test_darkvision_beyond_range_still_dark(self):
        ls = self._make_dark_system()
        vs = VisionSystem(ls)
        obs = _make_entity("orc_obs", vision_type=VisionType.DARKVISION, range_ft=60.0)
        # 20 voxels * 5 ft = 100 ft > 60 ft darkvision range
        tgt = _make_entity("tgt", x=20)
        result = vs.check_visibility(obs, tgt)
        assert result.light_level == LightLevel.DARKNESS
        assert result.concealment == 50

    def test_missing_components_returns_not_visible(self):
        ls = self._make_dark_system()
        vs = VisionSystem(ls)
        obs = Entity(name="no_pos")  # no Position component
        tgt = _make_entity("tgt")
        result = vs.check_visibility(obs, tgt)
        assert result.visible is False

    def test_vision_system_update_is_noop(self):
        vs = VisionSystem(LightSystem())
        vs.update()  # should not raise


# ---------------------------------------------------------------------------
# AttackResolver — miss-chance integration
# ---------------------------------------------------------------------------

class TestAttackResolverMissChance:
    """Verify the 3.5e concealment miss-chance rules in combat."""

    def _always_hit_resolver(self, attacker, defender, **kwargs):
        """Patch dice so the attack always hits AC, then apply lighting."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            from src.rules_engine.dice import RollResult
            mock_d20.return_value = RollResult(raw=20, modifier=0, total=20)
            mock_dmg.return_value = RollResult(raw=5, modifier=3, total=8)
            return AttackResolver.resolve_attack(attacker, defender, **kwargs)

    # --- Bright Light (no penalty) -----------------------------------------

    def test_no_miss_chance_in_bright_light(self):
        attacker = _make_char("Human Fighter")
        defender = _make_char("Goblin")
        result = self._always_hit_resolver(
            attacker, defender,
            defender_light_level=LightLevel.BRIGHT,
        )
        assert result.miss_chance_threshold == 0
        assert result.miss_chance_roll is None
        assert result.miss_chance_triggered is False

    # --- Dim Light (20 % miss chance) --------------------------------------

    def test_dim_light_miss_chance_set_to_20(self):
        attacker = _make_char("Human Fighter")
        defender = _make_char("Goblin")
        # Force the d% roll to be 1 (triggers miss)
        with patch("src.rules_engine.combat.random.randint", return_value=1):
            result = self._always_hit_resolver(
                attacker, defender,
                defender_light_level=LightLevel.DIM,
            )
        assert result.miss_chance_threshold == 20
        assert result.miss_chance_roll == 1
        assert result.miss_chance_triggered is True
        assert result.hit is False

    def test_dim_light_miss_chance_not_triggered_above_threshold(self):
        attacker = _make_char("Human Fighter")
        defender = _make_char("Goblin")
        # Roll 21 → above 20 → no miss
        with patch("src.rules_engine.combat.random.randint", return_value=21):
            result = self._always_hit_resolver(
                attacker, defender,
                defender_light_level=LightLevel.DIM,
            )
        assert result.miss_chance_threshold == 20
        assert result.miss_chance_triggered is False
        assert result.hit is True

    # --- Darkness + Human (50 % miss chance) --------------------------------

    def test_darkness_human_attacker_50_percent_miss_chance(self):
        attacker = _make_char("Human Fighter", race="Human")
        defender = _make_char("Goblin")
        # Force miss
        with patch("src.rules_engine.combat.random.randint", return_value=50):
            result = self._always_hit_resolver(
                attacker, defender,
                defender_light_level=LightLevel.DARKNESS,
                attacker_has_darkvision=False,
            )
        assert result.miss_chance_threshold == 50
        assert result.miss_chance_roll == 50
        assert result.miss_chance_triggered is True
        assert result.hit is False

    def test_darkness_human_attacker_hits_above_50(self):
        attacker = _make_char("Human Fighter")
        defender = _make_char("Goblin")
        with patch("src.rules_engine.combat.random.randint", return_value=51):
            result = self._always_hit_resolver(
                attacker, defender,
                defender_light_level=LightLevel.DARKNESS,
                attacker_has_darkvision=False,
            )
        assert result.miss_chance_threshold == 50
        assert result.miss_chance_triggered is False
        assert result.hit is True

    # --- Darkness + Orc/Darkvision (no miss chance) -------------------------

    def test_darkness_orc_darkvision_no_miss_chance(self):
        """Orc (Darkvision) vs. target in pitch blackness: no miss penalty."""
        orc = _make_char("Orc Fighter", race="Orc")
        target = _make_char("Human Villager")
        result = self._always_hit_resolver(
            orc, target,
            defender_light_level=LightLevel.DARKNESS,
            attacker_has_darkvision=True,
        )
        assert result.miss_chance_threshold == 0
        assert result.miss_chance_roll is None
        assert result.miss_chance_triggered is False
        assert result.hit is True

    # --- No lighting provided (backward compatibility) ----------------------

    def test_no_light_level_provided_no_miss_chance(self):
        """If defender_light_level is None, no miss chance is applied."""
        attacker = _make_char("Fighter")
        defender = _make_char("Goblin")
        result = self._always_hit_resolver(attacker, defender)
        assert result.miss_chance_threshold == 0
        assert result.miss_chance_roll is None


# ---------------------------------------------------------------------------
# End-to-end scenario: Orc vs. Human in darkness
# ---------------------------------------------------------------------------

class TestDarknessScenario:
    """
    End-to-end: Orc (Darkvision) can hit a target in pitch blackness with no
    penalty, while a Human has a 50 % miss chance.
    """

    TRIALS = 1000

    def test_orc_always_applies_no_miss_chance_in_darkness(self):
        """Over many trials, Orc's miss_chance_threshold is always 0."""
        orc = _make_char("Orc", race="Orc")
        target = _make_char("Human")

        for _ in range(self.TRIALS):
            with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
                 patch("src.rules_engine.combat.roll_dice") as mock_dmg:
                from src.rules_engine.dice import RollResult
                mock_d20.return_value = RollResult(raw=20, modifier=0, total=99)
                mock_dmg.return_value = RollResult(raw=5, modifier=3, total=8)
                result = AttackResolver.resolve_attack(
                    orc, target,
                    defender_light_level=LightLevel.DARKNESS,
                    attacker_has_darkvision=True,
                )
            assert result.miss_chance_threshold == 0, (
                "Orc (Darkvision) should never have a miss-chance threshold > 0"
            )

    def test_human_incurs_50_percent_miss_chance_in_darkness(self):
        """Human attacker must always receive miss_chance_threshold=50 in darkness."""
        human = _make_char("Human", race="Human")
        target = _make_char("Orc")

        for _ in range(self.TRIALS):
            with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
                 patch("src.rules_engine.combat.roll_dice") as mock_dmg:
                from src.rules_engine.dice import RollResult
                mock_d20.return_value = RollResult(raw=20, modifier=0, total=99)
                mock_dmg.return_value = RollResult(raw=5, modifier=3, total=8)
                result = AttackResolver.resolve_attack(
                    human, target,
                    defender_light_level=LightLevel.DARKNESS,
                    attacker_has_darkvision=False,
                )
            assert result.miss_chance_threshold == 50, (
                "Human should always face a 50 % miss chance in Darkness"
            )
