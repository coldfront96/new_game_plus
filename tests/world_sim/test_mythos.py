"""tests/world_sim/test_mythos.py
---------------------------------
Regression suite for src.rules_engine.mythos_forge.

Scenarios
~~~~~~~~~
1. Price calculation — weapon, armour, and wondrous items match DMG formulae.
2. Lore persistence  — LLM-generated name/history survive a JSON round-trip
                       and reload correctly in a fresh generator instance.
3. Generator flow    — async generate_artifact_async correctly calls the LLM,
                       stores the result, and returns a well-formed artifact.
4. Fallback lore     — generator produces deterministic fallback when the LLM
                       returns an empty string.
5. Tier validation   — invalid tier raises ValueError.
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.rules_engine.item_specials import ArtifactType
from src.rules_engine.mythos_forge import (
    ArtifactProperties,
    GeneratedArtifact,
    ProceduralArtifactGenerator,
    _artifact_to_dict,
    _dict_to_artifact,
    calculate_artifact_price,
)


# ===========================================================================
# 1. Price calculation
# ===========================================================================

class TestPriceCalculation:
    """DMG 3.5e pricing rules are implemented correctly."""

    def test_weapon_enhancement_only(self):
        # +3 longsword: 15 + 3² × 2000 = 15 + 18_000 = 18_015 gp
        price = calculate_artifact_price(
            item_type="weapon",
            base_item_cost_gp=15,
            enhancement_bonus=3,
            special_abilities=[],
            stat_boosts={},
            spell_effects=[],
        )
        assert price == 15 + (3 ** 2) * 2_000

    def test_weapon_with_flaming(self):
        # +3 flaming longsword: 15 + 3²×2000 + 1²×2000 = 20_015 gp
        price = calculate_artifact_price(
            item_type="weapon",
            base_item_cost_gp=15,
            enhancement_bonus=3,
            special_abilities=["Flaming"],
            stat_boosts={},
            spell_effects=[],
        )
        assert price == 15 + (3 ** 2) * 2_000 + (1 ** 2) * 2_000

    def test_weapon_with_holy_and_keen(self):
        # +2 holy keen longsword: 15 + 2²×2000 + 2²×2000 + 1²×2000 = 15 + 8000+8000+2000 = 18_015 gp
        price = calculate_artifact_price(
            item_type="weapon",
            base_item_cost_gp=15,
            enhancement_bonus=2,
            special_abilities=["Holy", "Keen"],
            stat_boosts={},
            spell_effects=[],
        )
        assert price == 15 + (2 ** 2) * 2_000 + (2 ** 2) * 2_000 + (1 ** 2) * 2_000

    def test_armor_enhancement_only(self):
        # +2 chain mail: 150 + 2² × 1000 = 4_150 gp
        price = calculate_artifact_price(
            item_type="armor",
            base_item_cost_gp=150,
            enhancement_bonus=2,
            special_abilities=[],
            stat_boosts={},
            spell_effects=[],
        )
        assert price == 150 + (2 ** 2) * 1_000

    def test_armor_with_shadow(self):
        # +1 shadow breastplate: 200 + 1²×1000 + 1²×1000 = 2_200 gp
        price = calculate_artifact_price(
            item_type="armor",
            base_item_cost_gp=200,
            enhancement_bonus=1,
            special_abilities=["Shadow"],
            stat_boosts={},
            spell_effects=[],
        )
        assert price == 200 + (1 ** 2) * 1_000 + (1 ** 2) * 1_000

    def test_armor_high_enhancement(self):
        # +5 full plate: 1500 + 5² × 1000 = 26_500 gp
        price = calculate_artifact_price(
            item_type="armor",
            base_item_cost_gp=1_500,
            enhancement_bonus=5,
            special_abilities=[],
            stat_boosts={},
            spell_effects=[],
        )
        assert price == 1_500 + (5 ** 2) * 1_000

    def test_wondrous_stat_boost_plus2(self):
        # Headband of Wis +2: 4_000 gp
        price = calculate_artifact_price(
            item_type="wondrous",
            base_item_cost_gp=0,
            enhancement_bonus=0,
            special_abilities=[],
            stat_boosts={"wisdom": 2},
            spell_effects=[],
        )
        assert price == 4_000

    def test_wondrous_stat_boost_plus4(self):
        # Belt of Str +4: 16_000 gp
        price = calculate_artifact_price(
            item_type="wondrous",
            base_item_cost_gp=0,
            enhancement_bonus=0,
            special_abilities=[],
            stat_boosts={"strength": 4},
            spell_effects=[],
        )
        assert price == 16_000

    def test_wondrous_stat_boost_plus6(self):
        # Gloves of Dex +6: 36_000 gp
        price = calculate_artifact_price(
            item_type="wondrous",
            base_item_cost_gp=0,
            enhancement_bonus=0,
            special_abilities=[],
            stat_boosts={"dexterity": 6},
            spell_effects=[],
        )
        assert price == 36_000

    def test_wondrous_spell_effect_command_word(self):
        # Command-word fly (spell_level=3, caster_level=5): 3 × 5 × 1800 = 27_000 gp
        price = calculate_artifact_price(
            item_type="wondrous",
            base_item_cost_gp=0,
            enhancement_bonus=0,
            special_abilities=[],
            stat_boosts={},
            spell_effects=[{"spell": "fly", "caster_level": 5, "spell_level": 3}],
        )
        assert price == 3 * 5 * 1_800

    def test_wondrous_combined(self):
        # Str +4 (16_000) + command-word haste CL7 (3×7×1800 = 37_800) = 53_800 gp
        price = calculate_artifact_price(
            item_type="wondrous",
            base_item_cost_gp=0,
            enhancement_bonus=0,
            special_abilities=[],
            stat_boosts={"strength": 4},
            spell_effects=[{"spell": "haste", "caster_level": 7, "spell_level": 3}],
        )
        assert price == 16_000 + 3 * 7 * 1_800

    def test_zero_enhancement_weapon(self):
        # A masterwork sword with no enhancement (enhancement=0) → price == base_cost
        price = calculate_artifact_price(
            item_type="weapon",
            base_item_cost_gp=315,
            enhancement_bonus=0,
            special_abilities=[],
            stat_boosts={},
            spell_effects=[],
        )
        assert price == 315


# ===========================================================================
# 2. Lore persistence — JSON round-trip
# ===========================================================================

class TestLorePersistence:
    """LLM-generated lore must survive JSON serialisation and reload."""

    def _make_props(self, item_type: str = "weapon") -> ArtifactProperties:
        art_id = str(uuid.uuid4())
        return ArtifactProperties(
            artifact_id=art_id,
            item_type=item_type,
            enhancement_bonus=5,
            special_abilities=["Vorpal"] if item_type == "weapon" else [],
            stat_boosts={} if item_type == "weapon" else {"strength": 6},
            spell_effects=[],
            calculated_price_gp=200_015 if item_type == "weapon" else 36_000,
            base_item="longsword" if item_type == "weapon" else "wondrous item",
            base_item_cost_gp=15 if item_type == "weapon" else 0,
        )

    def test_weapon_round_trip(self):
        props = self._make_props("weapon")
        original = GeneratedArtifact(
            artifact_id  = props.artifact_id,
            lore_name    = "Blade of the Undying Tyrant",
            lore_history = "Forged in the fires of Mount Dorgath by the lich Malachar, "
                           "this blade has claimed a thousand souls.",
            properties   = props,
            artifact_type = ArtifactType.MAJOR,
        )
        restored = _dict_to_artifact(_artifact_to_dict(original))

        assert restored.lore_name    == original.lore_name
        assert restored.lore_history == original.lore_history
        assert restored.artifact_id  == original.artifact_id
        assert restored.artifact_type == ArtifactType.MAJOR
        assert restored.properties.enhancement_bonus   == 5
        assert restored.properties.calculated_price_gp == 200_015
        assert "Vorpal" in restored.properties.special_abilities

    def test_wondrous_round_trip(self):
        props = self._make_props("wondrous")
        original = GeneratedArtifact(
            artifact_id  = props.artifact_id,
            lore_name    = "Gauntlets of the Storm King",
            lore_history = "Worn by the storm giant Thorrax during the Age of Thunder.",
            properties   = props,
            artifact_type = ArtifactType.MINOR,
        )
        restored = _dict_to_artifact(_artifact_to_dict(original))

        assert restored.lore_name    == original.lore_name
        assert restored.artifact_type == ArtifactType.MINOR
        assert restored.properties.stat_boosts == {"strength": 6}

    def test_all_fields_preserved(self):
        props = self._make_props("armor")
        props2 = ArtifactProperties(
            artifact_id=props.artifact_id,
            item_type="armor",
            enhancement_bonus=3,
            special_abilities=["Shadow", "Silent Moves"],
            stat_boosts={},
            spell_effects=[],
            calculated_price_gp=11_150,
            base_item="chain mail",
            base_item_cost_gp=150,
        )
        original = GeneratedArtifact(
            artifact_id  = props2.artifact_id,
            lore_name    = "Shroud of the Unseen",
            lore_history = "A cloak worn by the legendary assassin Sindrel.",
            properties   = props2,
            artifact_type = ArtifactType.MINOR,
        )
        restored = _dict_to_artifact(_artifact_to_dict(original))
        assert restored.properties.special_abilities == ["Shadow", "Silent Moves"]
        assert restored.properties.base_item == "chain mail"


# ===========================================================================
# 3. Generator flow — async generate_artifact_async with mocked LLM
# ===========================================================================

class TestGeneratorFlow:
    """ProceduralArtifactGenerator correctly integrates with LLMBridge."""

    def _make_generator(self, store: Path, llm_response: str) -> ProceduralArtifactGenerator:
        mock_llm = MagicMock()
        mock_llm.query_model = AsyncMock(return_value=llm_response)
        import random
        return ProceduralArtifactGenerator(
            store_path=store,
            llm_client=mock_llm,
            rng=random.Random(42),
        )

    def test_lore_persists_across_sessions(self, tmp_path):
        store = tmp_path / "artifacts.json"
        gen = self._make_generator(
            store,
            '{"name": "Shadowbane", "history": "A blade forged in shadow."}',
        )
        artifact = asyncio.run(gen.generate_artifact_async(tier="major"))

        assert artifact.lore_name    == "Shadowbane"
        assert artifact.lore_history == "A blade forged in shadow."
        assert store.exists()
        assert artifact.properties.calculated_price_gp > 0

        # Fresh generator loading the same store file
        gen2 = self._make_generator(store, "")
        reloaded = gen2.load_artifact(artifact.artifact_id)

        assert reloaded is not None
        assert reloaded.lore_name    == "Shadowbane"
        assert reloaded.lore_history == "A blade forged in shadow."
        assert reloaded.properties.calculated_price_gp == artifact.properties.calculated_price_gp

    def test_artifact_has_correct_type_for_tier(self, tmp_path):
        store = tmp_path / "artifacts.json"
        gen   = self._make_generator(
            store,
            '{"name": "Minor Relic", "history": "Small but potent."}',
        )
        minor = asyncio.run(gen.generate_artifact_async(tier="minor"))
        assert minor.artifact_type == ArtifactType.MINOR

        gen2  = self._make_generator(tmp_path / "artifacts2.json", '{"name": "Major Relic", "history": "Ancient."}')
        major = asyncio.run(gen2.generate_artifact_async(tier="major"))
        assert major.artifact_type == ArtifactType.MAJOR

    def test_all_artifacts_returns_persisted_entries(self, tmp_path):
        store = tmp_path / "artifacts.json"
        gen   = self._make_generator(
            store,
            '{"name": "Relic A", "history": "Old."}',
        )
        a1 = asyncio.run(gen.generate_artifact_async(tier="minor"))
        a2 = asyncio.run(gen.generate_artifact_async(tier="minor"))

        all_arts = gen.all_artifacts()
        ids = {a.artifact_id for a in all_arts}
        assert a1.artifact_id in ids
        assert a2.artifact_id in ids

    def test_store_contains_valid_json(self, tmp_path):
        store = tmp_path / "artifacts.json"
        gen   = self._make_generator(
            store,
            '{"name": "JSON Test", "history": "Valid."}',
        )
        asyncio.run(gen.generate_artifact_async(tier="minor"))
        raw = store.read_text(encoding="utf-8")
        data = __import__("json").loads(raw)
        assert isinstance(data, dict)
        assert len(data) == 1


# ===========================================================================
# 4. Fallback lore — deterministic placeholder when LLM returns empty string
# ===========================================================================

class TestFallbackLore:
    """When the LLM is unreachable the generator uses deterministic fallback lore."""

    def test_fallback_generates_non_empty_name(self, tmp_path):
        store = tmp_path / "artifacts.json"
        mock_llm = MagicMock()
        mock_llm.query_model = AsyncMock(return_value="")
        import random
        gen = ProceduralArtifactGenerator(
            store_path=store,
            llm_client=mock_llm,
            rng=random.Random(7),
        )
        artifact = asyncio.run(gen.generate_artifact_async(tier="minor"))
        assert artifact.lore_name
        assert artifact.lore_history
        assert artifact.lore_name != ""

    def test_fallback_lore_is_stable_for_same_id(self):
        from src.rules_engine.mythos_forge import _fallback_lore
        props = ArtifactProperties(
            artifact_id="fixed-id-for-test",
            item_type="weapon",
            enhancement_bonus=3,
            special_abilities=[],
            stat_boosts={},
            spell_effects=[],
            calculated_price_gp=18_015,
            base_item="longsword",
            base_item_cost_gp=15,
        )
        name1, hist1 = _fallback_lore(props)
        name2, hist2 = _fallback_lore(props)
        assert name1 == name2
        assert hist1 == hist2


# ===========================================================================
# 5. Tier validation
# ===========================================================================

class TestTierValidation:
    def test_invalid_tier_raises(self, tmp_path):
        mock_llm = MagicMock()
        mock_llm.query_model = AsyncMock(return_value="")
        gen = ProceduralArtifactGenerator(
            store_path=tmp_path / "a.json",
            llm_client=mock_llm,
        )
        with pytest.raises(ValueError, match="tier"):
            asyncio.run(gen.generate_artifact_async(tier="legendary"))
