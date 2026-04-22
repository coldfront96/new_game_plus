"""
tests/rules_engine/test_deities.py
------------------------------------
Unit tests for src.rules_engine.deities (Deity, Domain, DeityRegistry, DomainRegistry).
"""

import pytest

from src.rules_engine.deities import (
    Deity,
    DeityRegistry,
    Domain,
    DomainRegistry,
)


# ---------------------------------------------------------------------------
# Domain dataclass tests
# ---------------------------------------------------------------------------

class TestDomain:
    """Tests for Domain dataclass structure."""

    def test_slots_enabled(self):
        assert hasattr(Domain, "__slots__")

    def test_domain_has_required_fields(self):
        domain = DomainRegistry.get("Healing")
        assert domain.name == "Healing"
        assert isinstance(domain.domain_spells, dict)
        assert isinstance(domain.granted_power, str)

    def test_domain_spells_cover_levels_1_through_9(self):
        domain = DomainRegistry.get("Healing")
        for level in range(1, 10):
            assert level in domain.domain_spells, f"Missing level {level}"

    def test_domain_spell_at_level_1(self):
        domain = DomainRegistry.get("Healing")
        assert domain.domain_spells[1] == "Cure Light Wounds"

    def test_domain_granted_power_text(self):
        domain = DomainRegistry.get("Healing")
        assert "healing" in domain.granted_power.lower()
        assert "+1" in domain.granted_power


# ---------------------------------------------------------------------------
# DomainRegistry tests
# ---------------------------------------------------------------------------

class TestDomainRegistry:
    """Tests for DomainRegistry class."""

    def test_get_healing_domain(self):
        domain = DomainRegistry.get("Healing")
        assert isinstance(domain, Domain)
        assert domain.name == "Healing"

    def test_get_protection_domain(self):
        domain = DomainRegistry.get("Protection")
        assert isinstance(domain, Domain)
        assert domain.name == "Protection"

    def test_get_strength_domain(self):
        domain = DomainRegistry.get("Strength")
        assert isinstance(domain, Domain)
        assert "Enlarge Person" in domain.domain_spells.values()

    def test_get_war_domain(self):
        domain = DomainRegistry.get("War")
        assert "Magic Weapon" in domain.domain_spells.values()

    def test_get_destruction_domain(self):
        domain = DomainRegistry.get("Destruction")
        assert domain.domain_spells[1] == "Inflict Light Wounds"

    def test_get_death_domain(self):
        domain = DomainRegistry.get("Death")
        assert domain.domain_spells[1] == "Cause Fear"

    def test_get_luck_domain(self):
        domain = DomainRegistry.get("Luck")
        assert "reroll" in domain.granted_power.lower() or "Reroll" in domain.granted_power

    def test_get_trickery_domain(self):
        domain = DomainRegistry.get("Trickery")
        assert domain.domain_spells[1] == "Disguise Self"

    def test_get_knowledge_domain(self):
        domain = DomainRegistry.get("Knowledge")
        assert domain.domain_spells[1] == "Detect Secret Doors"

    def test_get_travel_domain(self):
        domain = DomainRegistry.get("Travel")
        assert domain.domain_spells[1] == "Longstrider"

    def test_unknown_domain_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown domain"):
            DomainRegistry.get("FakeDomain")

    def test_all_names_returns_sorted_list(self):
        names = DomainRegistry.all_names()
        assert isinstance(names, list)
        assert names == sorted(names)
        assert "Healing" in names
        assert "Protection" in names
        assert "War" in names

    def test_all_returns_all_domains(self):
        domains = DomainRegistry.all()
        assert all(isinstance(d, Domain) for d in domains)
        assert len(domains) >= 10

    def test_healing_domain_power_callback(self):
        domain = DomainRegistry.get("Healing")
        assert callable(domain.power_callback)
        result = domain.power_callback(None, 5)
        assert result["caster_level_bonus"] == 1
        assert "healing" in result["applies_to"]

    def test_destruction_domain_power_callback(self):
        domain = DomainRegistry.get("Destruction")
        assert callable(domain.power_callback)
        result = domain.power_callback(None, 7)
        assert result["smite_bonus_damage"] == 7
        assert result["uses_per_day"] == 1

    def test_strength_domain_power_callback(self):
        domain = DomainRegistry.get("Strength")
        result = domain.power_callback(None, 10)
        assert result["str_bonus"] == 10
        assert result["duration_rounds"] == 1

    def test_death_domain_power_callback(self):
        domain = DomainRegistry.get("Death")
        result = domain.power_callback(None, 5)
        assert result["death_touch"] is True

    def test_luck_domain_power_callback(self):
        domain = DomainRegistry.get("Luck")
        result = domain.power_callback(None, 3)
        assert result["reroll"] is True

    def test_trickery_domain_power_callback(self):
        domain = DomainRegistry.get("Trickery")
        result = domain.power_callback(None, 4)
        assert "Bluff" in result["bonus_class_skills"]
        assert "Hide" in result["bonus_class_skills"]


# ---------------------------------------------------------------------------
# Deity dataclass tests
# ---------------------------------------------------------------------------

class TestDeity:
    """Tests for Deity dataclass structure."""

    def test_slots_enabled(self):
        assert hasattr(Deity, "__slots__")

    def test_deity_has_required_fields(self):
        deity = DeityRegistry.get("Pelor")
        assert deity.name == "Pelor"
        assert isinstance(deity.alignment, str)
        assert isinstance(deity.portfolio, list)
        assert isinstance(deity.domains, list)
        assert isinstance(deity.favored_weapon, str)

    def test_pelor_alignment(self):
        deity = DeityRegistry.get("Pelor")
        assert deity.alignment == "NG"

    def test_pelor_favored_weapon(self):
        deity = DeityRegistry.get("Pelor")
        assert deity.favored_weapon == "Heavy Mace"

    def test_pelor_domains_include_healing(self):
        deity = DeityRegistry.get("Pelor")
        assert "Healing" in deity.domains


# ---------------------------------------------------------------------------
# DeityRegistry tests
# ---------------------------------------------------------------------------

class TestDeityRegistry:
    """Tests for DeityRegistry class."""

    def test_get_pelor(self):
        deity = DeityRegistry.get("Pelor")
        assert isinstance(deity, Deity)
        assert deity.name == "Pelor"

    def test_get_heironeous(self):
        deity = DeityRegistry.get("Heironeous")
        assert deity.alignment == "LG"
        assert deity.favored_weapon == "Longsword"

    def test_get_moradin(self):
        deity = DeityRegistry.get("Moradin")
        assert deity.alignment == "LG"
        assert deity.favored_weapon == "Warhammer"

    def test_get_corellon_larethian(self):
        deity = DeityRegistry.get("Corellon Larethian")
        assert deity.alignment == "CG"

    def test_get_hextor(self):
        deity = DeityRegistry.get("Hextor")
        assert deity.alignment == "LE"
        assert deity.favored_weapon == "Heavy Flail"

    def test_get_nerull(self):
        deity = DeityRegistry.get("Nerull")
        assert deity.alignment == "NE"
        assert deity.favored_weapon == "Scythe"

    def test_get_boccob(self):
        deity = DeityRegistry.get("Boccob")
        assert deity.alignment == "N"

    def test_get_erythnul(self):
        deity = DeityRegistry.get("Erythnul")
        assert deity.alignment == "CE"

    def test_unknown_deity_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown deity"):
            DeityRegistry.get("FakeDeity")

    def test_all_names_returns_sorted_list(self):
        names = DeityRegistry.all_names()
        assert isinstance(names, list)
        assert names == sorted(names)
        assert "Pelor" in names
        assert "Hextor" in names

    def test_all_returns_all_deities(self):
        deities = DeityRegistry.all()
        assert all(isinstance(d, Deity) for d in deities)
        assert len(deities) >= 8

    def test_all_deities_have_valid_alignment_codes(self):
        valid_codes = {"LG", "NG", "CG", "LN", "N", "CN", "LE", "NE", "CE"}
        for deity in DeityRegistry.all():
            assert deity.alignment in valid_codes, (
                f"{deity.name} has invalid alignment: {deity.alignment}"
            )

    def test_all_deities_have_non_empty_domains(self):
        for deity in DeityRegistry.all():
            assert len(deity.domains) > 0, f"{deity.name} has no domains"

    def test_portfolio_is_non_empty_list(self):
        for deity in DeityRegistry.all():
            assert isinstance(deity.portfolio, list)
            assert len(deity.portfolio) > 0, f"{deity.name} has empty portfolio"
