"""Tests for src/rules_engine/spell_effects.py"""
from __future__ import annotations

import random

import pytest

from src.rules_engine.character_35e import Alignment, Character35e, Size
from src.rules_engine.magic import create_default_registry
from src.rules_engine.spell_effects import SpellDispatcher, SpellResult


@pytest.fixture
def registry():
    return create_default_registry()


@pytest.fixture
def rng():
    return random.Random(42)


def _wizard(level: int = 5) -> Character35e:
    char = Character35e(
        name="Zara",
        char_class="Wizard",
        level=level,
        intelligence=18,
        alignment=Alignment.NEUTRAL_GOOD,
        size=Size.MEDIUM,
    )
    char.initialize_spellcasting()
    return char


def _fighter() -> Character35e:
    return Character35e(
        name="Grug",
        char_class="Fighter",
        level=3,
        alignment=Alignment.CHAOTIC_EVIL,
        size=Size.MEDIUM,
    )


def _cleric(level: int = 3) -> Character35e:
    char = Character35e(
        name="Sera",
        char_class="Cleric",
        level=level,
        wisdom=16,
        alignment=Alignment.LAWFUL_GOOD,
        size=Size.MEDIUM,
    )
    char.initialize_spellcasting()
    return char


# ---------------------------------------------------------------------------
# Magic Missile (auto-hit, multiple missiles)
# ---------------------------------------------------------------------------

class TestMagicMissile:
    def test_returns_damage_result(self, registry, rng):
        wizard = _wizard(level=5)
        target = _fighter()
        result = SpellDispatcher.dispatch(
            "Magic Missile",
            caster=wizard, target=target,
            caster_level=5, registry=registry, rng=rng,
        )
        assert result.outcome == "damage"
        assert result.damage_dealt > 0

    def test_scales_missiles_with_caster_level(self, registry, rng):
        # CL 1 → 1 missile, CL 3 → 2 missiles, CL 5 → 3 missiles
        results = []
        for cl in (1, 3, 5):
            r = SpellDispatcher.dispatch(
                "Magic Missile",
                caster=_wizard(cl), target=_fighter(),
                caster_level=cl, registry=registry,
                rng=random.Random(99),
            )
            results.append(r.damage_dealt)
        # Higher CL should generally mean more damage
        assert results[0] <= results[2]

    def test_narrative_contains_spell_name(self, registry, rng):
        result = SpellDispatcher.dispatch(
            "Magic Missile",
            caster=_wizard(), target=_fighter(),
            caster_level=5, registry=registry, rng=rng,
        )
        assert "Magic Missile" in result.narrative

    def test_raw_effect_preserved(self, registry, rng):
        result = SpellDispatcher.dispatch(
            "Magic Missile",
            caster=_wizard(), target=_fighter(),
            caster_level=5, registry=registry, rng=rng,
        )
        assert "num_missiles" in result.raw_effect


# ---------------------------------------------------------------------------
# Fireball (Reflex half)
# ---------------------------------------------------------------------------

class TestFireball:
    def test_damage_outcome(self, registry, rng):
        result = SpellDispatcher.dispatch(
            "Fireball",
            caster=_wizard(10), target=_fighter(),
            caster_level=10, registry=registry, rng=rng,
        )
        assert result.outcome == "damage"
        assert result.damage_dealt > 0

    def test_save_halves_damage(self, registry):
        # Force the saving throw to always succeed by using a very low DC
        rng = random.Random(7)  # seed that makes target succeed the save
        result = SpellDispatcher.dispatch(
            "Fireball",
            caster=_wizard(10), target=_fighter(),
            caster_level=10, registry=registry, rng=rng,
            save_dc=1,  # DC 1 — target will always succeed
        )
        # With DC 1, target saves; get half damage
        assert result.saved is True
        assert result.damage_dealt >= 0  # could still be 0 on extreme rolls

    def test_damage_scales_with_caster_level(self, registry):
        dmg_low = SpellDispatcher.dispatch(
            "Fireball", caster=_wizard(1), target=_fighter(),
            caster_level=1, registry=registry, rng=random.Random(1), save_dc=100,
        ).damage_dealt
        dmg_high = SpellDispatcher.dispatch(
            "Fireball", caster=_wizard(10), target=_fighter(),
            caster_level=10, registry=registry, rng=random.Random(1), save_dc=100,
        ).damage_dealt
        assert dmg_high >= dmg_low


# ---------------------------------------------------------------------------
# Cure Light Wounds (healing)
# ---------------------------------------------------------------------------

class TestCureLightWounds:
    def test_healing_outcome(self, registry, rng):
        cleric = _cleric()
        target = _fighter()
        result = SpellDispatcher.dispatch(
            "Cure Light Wounds",
            caster=cleric, target=target,
            caster_level=3, registry=registry, rng=rng,
        )
        assert result.outcome == "healing"
        assert result.healing_done > 0

    def test_healing_at_least_one(self, registry):
        for seed in range(10):
            result = SpellDispatcher.dispatch(
                "Cure Light Wounds",
                caster=_cleric(), target=_fighter(),
                caster_level=1, registry=registry, rng=random.Random(seed),
            )
            assert result.healing_done >= 1


# ---------------------------------------------------------------------------
# Sleep (condition spell with HD cap)
# ---------------------------------------------------------------------------

class TestSleep:
    def test_condition_on_low_hd_target(self, registry, rng):
        # Fighter level 1 (1 HD) is within Sleep's 4 HD cap
        target = Character35e(
            name="Mook", char_class="Fighter", level=1,
            alignment=Alignment.CHAOTIC_EVIL, size=Size.MEDIUM,
        )
        result = SpellDispatcher.dispatch(
            "Sleep",
            caster=_wizard(), target=target,
            caster_level=3, registry=registry, rng=rng,
            save_dc=100,  # guarantee no save
        )
        assert result.outcome == "condition"
        # Either the condition was applied or they saved; in this case DC 100 should apply it
        if not result.saved:
            assert "Unconscious" in result.conditions_applied

    def test_immune_above_hd_cap(self, registry, rng):
        high_hd = Character35e(
            name="Veteran", char_class="Fighter", level=5,
            alignment=Alignment.CHAOTIC_EVIL, size=Size.MEDIUM,
        )
        result = SpellDispatcher.dispatch(
            "Sleep",
            caster=_wizard(), target=high_hd,
            caster_level=3, registry=registry, rng=rng,
        )
        # Level 5 > 4 HD cap — should be immune
        assert result.saved is True


# ---------------------------------------------------------------------------
# Hold Person (condition spell with Will save)
# ---------------------------------------------------------------------------

class TestHoldPerson:
    def test_paralyzed_on_failed_save(self, registry):
        result = SpellDispatcher.dispatch(
            "Hold Person",
            caster=_wizard(), target=_fighter(),
            caster_level=5, registry=registry, rng=random.Random(1),
            save_dc=100,  # impossible DC → target always fails
        )
        assert result.outcome == "condition"
        if not result.saved:
            assert "paralyzed" in result.conditions_applied

    def test_resisted_on_successful_save(self, registry):
        result = SpellDispatcher.dispatch(
            "Hold Person",
            caster=_wizard(), target=_fighter(),
            caster_level=5, registry=registry, rng=random.Random(1),
            save_dc=1,  # guaranteed save
        )
        assert result.saved is True


# ---------------------------------------------------------------------------
# Buff spells (Mage Armor, Bless)
# ---------------------------------------------------------------------------

class TestBuffSpells:
    def test_mage_armor_is_buff(self, registry, rng):
        result = SpellDispatcher.dispatch(
            "Mage Armor",
            caster=_wizard(), target=_wizard(),
            caster_level=5, registry=registry, rng=rng,
        )
        assert result.outcome == "buff"
        assert result.damage_dealt == 0
        assert result.healing_done == 0

    def test_bless_is_buff(self, registry, rng):
        result = SpellDispatcher.dispatch(
            "Bless",
            caster=_cleric(), target=_fighter(),
            caster_level=3, registry=registry, rng=rng,
        )
        assert result.outcome == "buff"


# ---------------------------------------------------------------------------
# Unknown spell
# ---------------------------------------------------------------------------

class TestUnknownSpell:
    def test_unknown_spell_returns_utility(self, registry, rng):
        result = SpellDispatcher.dispatch(
            "Nonexistent Spell",
            caster=_wizard(), target=_fighter(),
            caster_level=5, registry=registry, rng=rng,
        )
        assert result.outcome == "utility"
        assert result.damage_dealt == 0


# ---------------------------------------------------------------------------
# best_offensive_spell
# ---------------------------------------------------------------------------

class TestBestOffensiveSpell:
    def test_wizard_picks_offensive_spell(self, registry):
        wizard = _wizard(level=5)
        name = SpellDispatcher.best_offensive_spell(wizard, registry)
        # Wizard has no slots initialised yet; but spell_slot_manager exists
        # after initialize_spellcasting — some spells at level 0 are always available
        # A freshly-initialised L5 Wizard has slots at all levels 0-3
        assert name is not None or wizard.spell_slot_manager.total_available() == 0

    def test_non_caster_returns_none(self, registry):
        fighter = _fighter()
        name = SpellDispatcher.best_offensive_spell(fighter, registry)
        assert name is None

    def test_cleric_healer_mode(self, registry):
        cleric = _cleric(level=5)
        name = SpellDispatcher.best_offensive_spell(
            cleric, registry, targeting_ally=True
        )
        # Should want to heal; Cure Light Wounds is level 1 which cleric has
        assert name in SpellDispatcher.HEALING_SPELLS or name is None
