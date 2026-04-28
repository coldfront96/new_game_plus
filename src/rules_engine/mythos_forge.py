"""LW-MMF-001 — Procedural Artifact Generator with LLM lore integration.

Assembles high-tier mechanical properties for weapons, armour, and wondrous
items following strict 3.5e DMG pricing rules, then queries the local LLM
via LLMBridge to generate a unique name and historical backstory.

Artifacts persist to ``data/generated_artifacts.json`` so each world keeps
its own set of unique, named relics across sessions.

Pricing formulae (DMG Chapter 7)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Weapon       : base_cost + enhancement² × 2,000 + Σ ability_equiv² × 2,000
Armour       : base_cost + enhancement² × 1,000 + Σ ability_equiv² × 1,000
Wondrous stat: +2 → 4,000 gp | +4 → 16,000 gp | +6 → 36,000 gp  (per score)
Wondrous spell: spell_level × caster_level × 1,800 gp  (command-word, 1/day)

Usage::

    from src.rules_engine.mythos_forge import ProceduralArtifactGenerator

    gen  = ProceduralArtifactGenerator()
    art  = gen.generate_artifact(tier="major")
    print(art.lore_name, art.properties.calculated_price_gp)

    # Reload from disk in a later session
    gen2    = ProceduralArtifactGenerator()
    reloaded = gen2.load_artifact(art.artifact_id)
    assert reloaded.lore_name == art.lore_name
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ai_sim.llm_bridge import LLMClient, CognitiveState
from src.rules_engine.item_specials import (
    ARMOR_SPECIAL_ABILITY_REGISTRY,
    WEAPON_SPECIAL_ABILITY_REGISTRY,
    ArtifactType,
    validate_armor_ability_stack,
    validate_weapon_ability_stack,
)

# ---------------------------------------------------------------------------
# Persistence path — data/ at project root
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parents[2]
_DEFAULT_STORE: Path = _PROJECT_ROOT / "data" / "generated_artifacts.json"

# ---------------------------------------------------------------------------
# DMG pricing constants
# ---------------------------------------------------------------------------

_WEAPON_GP_PER_PLUS_SQ: int = 2_000   # enhancement² × 2000 gp
_ARMOR_GP_PER_PLUS_SQ:  int = 1_000   # enhancement² × 1000 gp

_STAT_BOOST_COSTS: dict[int, int] = {
    2: 4_000,
    4: 16_000,
    6: 36_000,
}

_COMMAND_WORD_GP: int = 1_800   # spell_level × caster_level × 1800 gp (1/day)

_SPELL_LEVELS: dict[str, int] = {
    "fly": 3, "haste": 3, "invisibility": 2,
    "fireball": 3, "lightning bolt": 3, "greater teleport": 7,
    "dimension door": 4, "stoneskin": 4, "displacement": 3,
}

_WEAPON_BASE_COSTS: dict[str, int] = {
    "longsword": 15, "greataxe": 20, "shortbow": 30,
    "rapier": 20, "greatsword": 50, "dagger": 2,
}
_ARMOR_BASE_COSTS: dict[str, int] = {
    "chain mail": 150, "full plate": 1_500,
    "mithral shirt": 1_100, "breastplate": 200,
}


# ---------------------------------------------------------------------------
# Data schemas
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ArtifactProperties:
    """Mechanical properties assembled by the generator."""
    artifact_id: str
    item_type: str                  # "weapon" | "armor" | "wondrous"
    enhancement_bonus: int          # 0 for wondrous
    special_abilities: list[str]    # names from WEAPON/ARMOR_SPECIAL_ABILITY_REGISTRY
    stat_boosts: dict[str, int]     # e.g. {"strength": 4}
    spell_effects: list[dict]       # {"spell", "caster_level", "charges", "spell_level"}
    calculated_price_gp: int
    base_item: str
    base_item_cost_gp: int


@dataclass(slots=True)
class GeneratedArtifact:
    """A procedural artifact with LLM-sourced lore attached."""
    artifact_id: str
    lore_name: str
    lore_history: str
    properties: ArtifactProperties
    artifact_type: ArtifactType


# ---------------------------------------------------------------------------
# Standalone price calculator (also used by tests)
# ---------------------------------------------------------------------------

def calculate_artifact_price(
    item_type: str,
    base_item_cost_gp: int,
    enhancement_bonus: int,
    special_abilities: list[str],
    stat_boosts: dict[str, int],
    spell_effects: list[dict],
) -> int:
    """Return the market price in gp per DMG 3.5e pricing rules.

    Args:
        item_type:        ``"weapon"``, ``"armor"``, or ``"wondrous"``.
        base_item_cost_gp: Cost of the mundane base item.
        enhancement_bonus: +1…+10 enhancement (0 for wondrous items).
        special_abilities: List of ability names from the relevant registry.
        stat_boosts:       Dict mapping ability name → bonus amount (+2/+4/+6).
        spell_effects:     List of dicts with keys ``spell_level`` and
                           ``caster_level`` for each spell effect.
    """
    if item_type == "weapon":
        ability_gp = sum(
            (WEAPON_SPECIAL_ABILITY_REGISTRY[n].bonus_equivalent ** 2) * _WEAPON_GP_PER_PLUS_SQ
            for n in special_abilities
            if n in WEAPON_SPECIAL_ABILITY_REGISTRY
        )
        return base_item_cost_gp + (enhancement_bonus ** 2) * _WEAPON_GP_PER_PLUS_SQ + ability_gp

    if item_type == "armor":
        ability_gp = sum(
            (ARMOR_SPECIAL_ABILITY_REGISTRY[n].bonus_equivalent ** 2) * _ARMOR_GP_PER_PLUS_SQ
            for n in special_abilities
            if n in ARMOR_SPECIAL_ABILITY_REGISTRY
        )
        return base_item_cost_gp + (enhancement_bonus ** 2) * _ARMOR_GP_PER_PLUS_SQ + ability_gp

    # Wondrous item
    stat_gp = sum(_STAT_BOOST_COSTS.get(v, 4_000) for v in stat_boosts.values())
    spell_gp = sum(
        se.get("spell_level", 0) * se.get("caster_level", 1) * _COMMAND_WORD_GP
        for se in spell_effects
    )
    return base_item_cost_gp + stat_gp + spell_gp


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------

def _artifact_to_dict(artifact: GeneratedArtifact) -> dict[str, Any]:
    p = artifact.properties
    return {
        "artifact_id":   artifact.artifact_id,
        "lore_name":     artifact.lore_name,
        "lore_history":  artifact.lore_history,
        "artifact_type": artifact.artifact_type.value,
        "properties": {
            "artifact_id":          p.artifact_id,
            "item_type":            p.item_type,
            "enhancement_bonus":    p.enhancement_bonus,
            "special_abilities":    p.special_abilities,
            "stat_boosts":          p.stat_boosts,
            "spell_effects":        p.spell_effects,
            "calculated_price_gp":  p.calculated_price_gp,
            "base_item":            p.base_item,
            "base_item_cost_gp":    p.base_item_cost_gp,
        },
    }


def _dict_to_artifact(data: dict[str, Any]) -> GeneratedArtifact:
    p = data["properties"]
    props = ArtifactProperties(
        artifact_id         = p["artifact_id"],
        item_type           = p["item_type"],
        enhancement_bonus   = p["enhancement_bonus"],
        special_abilities   = p["special_abilities"],
        stat_boosts         = p["stat_boosts"],
        spell_effects       = p["spell_effects"],
        calculated_price_gp = p["calculated_price_gp"],
        base_item           = p["base_item"],
        base_item_cost_gp   = p["base_item_cost_gp"],
    )
    return GeneratedArtifact(
        artifact_id  = data["artifact_id"],
        lore_name    = data["lore_name"],
        lore_history = data["lore_history"],
        properties   = props,
        artifact_type = ArtifactType(data["artifact_type"]),
    )


# ---------------------------------------------------------------------------
# LLM helper — minimal cognitive state for the artifact oracle prompt
# ---------------------------------------------------------------------------

def _forge_state() -> CognitiveState:
    """Placeholder CognitiveState fed to LLMClient for artifact lore queries."""
    return CognitiveState(
        character_name  = "Artifact Oracle",
        char_class      = "Artificer",
        level           = 20,
        current_hp      = 100,
        max_hp          = 100,
        conditions      = [],
        known_spells    = [],
        action_tracker  = {"standard_used": False, "move_used": False, "swift_used": False},
        visible_entities = [],
        memory_log      = [],
    )


def _fallback_lore(props: ArtifactProperties) -> tuple[str, str]:
    """Generate deterministic placeholder lore when the LLM is unavailable."""
    adjectives = ["Ancient", "Forgotten", "Infernal", "Celestial", "Accursed", "Radiant"]
    nouns = {
        "weapon":  ["Blade", "Edge", "Fang", "Cleaver"],
        "armor":   ["Shield", "Ward", "Aegis", "Mantle"],
        "wondrous": ["Relic", "Shard", "Orb", "Talisman"],
    }
    rng = random.Random(hash(props.artifact_id))
    adj  = rng.choice(adjectives)
    noun = rng.choice(nouns.get(props.item_type, ["Relic"]))
    name = f"The {adj} {noun}"
    history = (
        f"Recovered from the ruins of a long-dead empire, {name} bears "
        f"the mark of its forgotten maker.  Its power is undiminished by time."
    )
    return name, history


# ---------------------------------------------------------------------------
# ProceduralArtifactGenerator
# ---------------------------------------------------------------------------

class ProceduralArtifactGenerator:
    """Generates unique artifacts with DMG-accurate pricing and LLM lore.

    Args:
        store_path:  Path to the JSON registry file on disk.
        llm_client:  Optional pre-configured :class:`~src.ai_sim.llm_bridge.LLMClient`.
                     Defaults to a new client pointed at ``localhost:11434``.
        rng:         Optional :class:`random.Random` instance for reproducible generation.
    """

    def __init__(
        self,
        store_path: Path = _DEFAULT_STORE,
        llm_client: LLMClient | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._store  = store_path
        self._llm    = llm_client or LLMClient()
        self._rng    = rng or random.Random()
        self._cache: dict[str, dict[str, Any]] = self._load_registry()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_registry(self) -> dict[str, dict[str, Any]]:
        if self._store.exists():
            try:
                return json.loads(self._store.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_registry(self) -> None:
        self._store.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_text(
            json.dumps(self._cache, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Mechanical property assembly
    # ------------------------------------------------------------------

    def _assemble_properties(self, tier: str) -> ArtifactProperties:
        artifact_id = str(uuid.uuid4())
        max_abilities = 2 if tier == "minor" else 4
        enh_range     = (1, 5) if tier == "minor" else (5, 10)

        item_type = self._rng.choice(["weapon", "armor", "wondrous"])

        if item_type == "weapon":
            base_item = self._rng.choice(list(_WEAPON_BASE_COSTS))
            base_cost = _WEAPON_BASE_COSTS[base_item]
            enhancement = self._rng.randint(*enh_range)
            abilities = self._pick_abilities(
                WEAPON_SPECIAL_ABILITY_REGISTRY, enhancement, max_abilities
            )
            try:
                validate_weapon_ability_stack(
                    enhancement,
                    [WEAPON_SPECIAL_ABILITY_REGISTRY[n] for n in abilities],
                )
            except Exception:
                abilities = []
            price = calculate_artifact_price(
                "weapon", base_cost, enhancement, abilities, {}, []
            )
            return ArtifactProperties(
                artifact_id=artifact_id, item_type="weapon",
                enhancement_bonus=enhancement, special_abilities=abilities,
                stat_boosts={}, spell_effects=[],
                calculated_price_gp=price,
                base_item=base_item, base_item_cost_gp=base_cost,
            )

        if item_type == "armor":
            base_item = self._rng.choice(list(_ARMOR_BASE_COSTS))
            base_cost = _ARMOR_BASE_COSTS[base_item]
            enhancement = self._rng.randint(*enh_range)
            abilities = self._pick_abilities(
                ARMOR_SPECIAL_ABILITY_REGISTRY, enhancement, max_abilities
            )
            try:
                validate_armor_ability_stack(
                    enhancement,
                    [ARMOR_SPECIAL_ABILITY_REGISTRY[n] for n in abilities],
                )
            except Exception:
                abilities = []
            price = calculate_artifact_price(
                "armor", base_cost, enhancement, abilities, {}, []
            )
            return ArtifactProperties(
                artifact_id=artifact_id, item_type="armor",
                enhancement_bonus=enhancement, special_abilities=abilities,
                stat_boosts={}, spell_effects=[],
                calculated_price_gp=price,
                base_item=base_item, base_item_cost_gp=base_cost,
            )

        # Wondrous item
        ability_names = ["strength", "dexterity", "constitution",
                         "intelligence", "wisdom", "charisma"]
        chosen_stats = self._rng.sample(ability_names, k=self._rng.randint(1, 3))
        boost_val = self._rng.choice([2, 4, 6])
        stat_boosts = {stat: boost_val for stat in chosen_stats}

        spell_pool = list(_SPELL_LEVELS)
        chosen_spells = self._rng.sample(spell_pool, k=self._rng.randint(1, 3))
        spell_effects = [
            {
                "spell":        sp,
                "caster_level": self._rng.randint(5, 15),
                "charges":      self._rng.randint(1, 3),
                "spell_level":  _SPELL_LEVELS[sp],
            }
            for sp in chosen_spells
        ]
        price = calculate_artifact_price("wondrous", 0, 0, [], stat_boosts, spell_effects)
        return ArtifactProperties(
            artifact_id=artifact_id, item_type="wondrous",
            enhancement_bonus=0, special_abilities=[],
            stat_boosts=stat_boosts, spell_effects=spell_effects,
            calculated_price_gp=price,
            base_item="wondrous item", base_item_cost_gp=0,
        )

    def _pick_abilities(
        self,
        registry: dict,
        base_enhancement: int,
        max_count: int,
    ) -> list[str]:
        """Pick special abilities that keep total effective bonus ≤ +10."""
        available = list(registry.values())
        self._rng.shuffle(available)
        chosen: list[str] = []
        total = base_enhancement
        for ab in available:
            if len(chosen) >= max_count:
                break
            if total + ab.bonus_equivalent <= 10:
                chosen.append(ab.name)
                total += ab.bonus_equivalent
        return chosen

    # ------------------------------------------------------------------
    # LLM lore
    # ------------------------------------------------------------------

    async def _fetch_lore(self, props: ArtifactProperties) -> tuple[str, str]:
        """Query LLMBridge for a unique name and backstory.  Falls back to
        deterministic placeholder lore if the LLM server is unreachable."""
        parts: list[str] = [f"Item type: {props.item_type}"]
        if props.enhancement_bonus:
            parts.append(f"Enhancement: +{props.enhancement_bonus}")
        if props.special_abilities:
            parts.append(f"Special abilities: {', '.join(props.special_abilities)}")
        if props.stat_boosts:
            parts.append(f"Stat boosts: {props.stat_boosts}")
        if props.spell_effects:
            parts.append(f"Spell effects: {[s['spell'] for s in props.spell_effects]}")
        parts.append(f"Value: {props.calculated_price_gp:,} gp")

        system_prompt = (
            "You are a master chronicler of magical artifacts in a D&D 3.5e world. "
            "Given the mechanical properties of an artifact, invent a short evocative "
            "proper name and a 2–3 sentence historical backstory. "
            'Reply ONLY with valid JSON: {"name": "...", "history": "..."}'
        )
        raw = await self._llm.query_model(
            system_prompt=system_prompt,
            cognitive_state=_forge_state(),
            user_prompt="\n".join(parts),
        )

        if raw:
            json_match = re.search(r'\{[^{}]*"name"[^{}]*"history"[^{}]*\}', raw, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    name    = data.get("name", "").strip()
                    history = data.get("history", "").strip()
                    if name and history:
                        return name, history
                except (json.JSONDecodeError, KeyError):
                    pass

        return _fallback_lore(props)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_artifact_async(self, tier: str = "minor") -> GeneratedArtifact:
        """Assemble properties, fetch lore, persist to JSON, and return artifact.

        Args:
            tier: ``"minor"`` (enhancement +1…+5) or ``"major"`` (+5…+10).
        """
        if tier not in ("minor", "major"):
            raise ValueError(f"tier must be 'minor' or 'major', got {tier!r}")

        props         = self._assemble_properties(tier)
        name, history = await self._fetch_lore(props)
        artifact_type = ArtifactType.MINOR if tier == "minor" else ArtifactType.MAJOR

        artifact = GeneratedArtifact(
            artifact_id  = props.artifact_id,
            lore_name    = name,
            lore_history = history,
            properties   = props,
            artifact_type = artifact_type,
        )
        self._cache[props.artifact_id] = _artifact_to_dict(artifact)
        self._save_registry()
        return artifact

    def generate_artifact(self, tier: str = "minor") -> GeneratedArtifact:
        """Synchronous wrapper around :meth:`generate_artifact_async`."""
        return asyncio.run(self.generate_artifact_async(tier))

    def load_artifact(self, artifact_id: str) -> GeneratedArtifact | None:
        """Return a previously generated artifact by ID, or ``None`` if unknown."""
        data = self._cache.get(artifact_id)
        return _dict_to_artifact(data) if data is not None else None

    def all_artifacts(self) -> list[GeneratedArtifact]:
        """Return all artifacts currently in the world registry."""
        return [_dict_to_artifact(d) for d in self._cache.values()]
