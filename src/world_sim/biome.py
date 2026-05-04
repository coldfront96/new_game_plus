"""LW-002 · LW-003 · LW-013 · LW-015 — Biome enum, species biome bindings, and spawn gate."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.population import PopulationLedger, WorldChunk


class Biome(enum.Enum):
    # Temperature × terrain matrix
    Cold_Forest        = "cold_forest"
    Cold_Hill          = "cold_hill"
    Cold_Plain         = "cold_plain"
    Cold_Desert        = "cold_desert"
    Cold_Aquatic       = "cold_aquatic"
    Cold_Swamp         = "cold_swamp"
    Cold_Mountain      = "cold_mountain"
    Temperate_Forest   = "temperate_forest"
    Temperate_Hill     = "temperate_hill"
    Temperate_Plain    = "temperate_plain"
    Temperate_Desert   = "temperate_desert"
    Temperate_Aquatic  = "temperate_aquatic"
    Temperate_Swamp    = "temperate_swamp"
    Temperate_Mountain = "temperate_mountain"
    Warm_Forest        = "warm_forest"
    Warm_Hill          = "warm_hill"
    Warm_Plain         = "warm_plain"
    Warm_Desert        = "warm_desert"
    Warm_Aquatic       = "warm_aquatic"
    Warm_Swamp         = "warm_swamp"
    Warm_Mountain      = "warm_mountain"
    # Special terrain
    Underground        = "underground"
    Underdark          = "underdark"
    Arctic             = "arctic"
    Any_Urban          = "any_urban"
    Any_Ruin           = "any_ruin"
    Aquatic            = "aquatic"
    # Planar
    Astral             = "astral"
    Ethereal           = "ethereal"
    Positive_Energy    = "positive_energy"
    Negative_Energy    = "negative_energy"
    Elemental_Air      = "elemental_air"
    Elemental_Earth    = "elemental_earth"
    Elemental_Fire     = "elemental_fire"
    Elemental_Water    = "elemental_water"
    Outer_Plane        = "outer_plane"
    # Sentinel — non-biome-restricted
    Any                = "any"
    # Starting area — exists between worlds
    Ashen_Crossroads   = "ashen_crossroads"


@dataclass(slots=True)
class BiomeTemplate:
    """Configuration template for a named biome, including feature spawn rules.

    Attributes:
        biome:                The :class:`Biome` this template describes.
        display_name:         Human-readable name shown in UI and lore.
        description:          Flavour text injected into room descriptions.
        feature_spawn_rates:  Mapping of feature tag → spawn probability [0.0–1.0].
        ambient_mood:         Short string hint for AI lore generators.
        is_starting_biome:    ``True`` for the player's initial spawn area.
        feature_descriptions: Mapping of feature tag → detailed examine text shown
                              when the player types ``examine <feature>``.
    """
    biome: "Biome"
    display_name: str
    description: str
    feature_spawn_rates: dict[str, float]
    ambient_mood: str
    is_starting_biome: bool = False
    feature_descriptions: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Starting Biome — "Ashen Crossroads"
# Vibe: atmospheric, dark, mysterious. Ancient Ruins feature guaranteed.
# ---------------------------------------------------------------------------

ASHEN_CROSSROADS: "BiomeTemplate" = BiomeTemplate(
    biome=Biome.Ashen_Crossroads,
    display_name="Ashen Crossroads",
    description=(
        "A liminal space suspended between life and death. Blackened stone columns "
        "rise from ash-dusted earth beneath a starless, moonless void. The air "
        "carries the taste of iron and forgotten oaths. Sound arrives muffled, as "
        "if the world itself is holding its breath."
    ),
    feature_spawn_rates={
        "ancient_ruins":   1.00,  # guaranteed — iron vault aesthetic
        "collapsed_wall":  0.70,
        "iron_vault":      0.50,
        "crumbling_altar": 0.40,
        "bone_scatter":    0.30,
        "ashen_pillar":    0.60,
        "sealed_door":     0.45,
    },
    ambient_mood="dark, atmospheric, mysterious",
    is_starting_biome=True,
    feature_descriptions={
        "ancient_ruins": (
            "Fractured stonework juts from the ash at wrong angles, as if the ground "
            "itself rejected what stood here. The architecture does not match any "
            "civilisation you have read of — the proportions are subtly wrong, built "
            "for occupants whose geometry did not share yours. Faded carvings spiral "
            "inward along every visible surface, terminating in a glyph you cannot "
            "hold in your mind once your eyes move on."
        ),
        "collapsed_wall": (
            "A section of the chamber wall has caved inward, spilling dressed stone "
            "blocks across the floor in a frozen cascade. The break is old — the "
            "fractured edges are worn smooth by ages of drifting ash. Beyond the gap "
            "is only deeper dark; the air that seeps through is colder still, carrying "
            "a faint mineral smell, like the breath of something very far underground."
        ),
        "iron_vault": (
            "The vault door stands floor-to-ceiling, forged from metal that has never "
            "rusted despite the damp. Its surface is covered in interlocking runes that "
            "shift position the moment your gaze slides away — you cannot catch them "
            "moving, yet they are never where you last saw them. There is no visible "
            "handle, keyhole, or hinge. Whatever is on the other side has not been "
            "disturbed in a very long time, and seems content to remain so."
        ),
        "crumbling_altar": (
            "A low stone table, barely knee-height, occupies a slight recess in the "
            "floor. The depression around it was clearly designed — offerings were meant "
            "to accumulate here. The surface of the altar is stained in concentric rings "
            "of dark residue, oldest at the centre, none of it recent. A shallow bowl "
            "is carved into the stone; it holds nothing but a fine layer of ash, "
            "perfectly undisturbed. You do not know what was worshipped here, but the "
            "altar still feels expectant."
        ),
        "bone_scatter": (
            "A loose arrangement of bones lies against the far wall, half-buried under "
            "decades of ash fall. They are adult-sized and largely intact — whatever "
            "claimed the original occupant did not consume them. The bones are bleached "
            "far beyond normal decay, almost translucent at the thinner points. Among "
            "them, nearly invisible in the grey dust, is a small object you cannot quite "
            "make out without disturbing the scatter. You leave it for now."
        ),
        "ashen_pillar": (
            "One of the chamber's support columns is coated in a thick crust of "
            "compacted ash, built up over what must have been centuries of slow "
            "accumulation. The ash has hardened to something almost like stone, "
            "preserving the outline of carvings beneath in ghostly negative relief. "
            "If you press your palm flat against it, the surface is faintly warm — "
            "warmer than the surrounding air has any right to be. The pillar shows "
            "no sign of cracking despite the weight above it."
        ),
        "sealed_door": (
            "A door-shaped outline is visible in the stone wall, its seams packed with "
            "the same compressed ash that coats everything else. It was sealed "
            "deliberately — you can see the marks where mortar or resin was applied "
            "from this side, meaning whoever closed it was still in the room afterward. "
            "No mechanism is visible. The stone around the frame is slightly discoloured, "
            "as if something seeped through it long ago and was absorbed."
        ),
    },
)


@dataclass(slots=True)
class SpeciesBiomeBinding:
    """LW-003 — Ties a species to its required, tolerated, and forbidden biomes.

    population_base is the world-generation starting count.
    0 = unique singleton; populations are never auto-spawned above this ceiling.
    """
    species_id: str
    primary_biomes: tuple[Biome, ...]
    tolerated_biomes: tuple[Biome, ...]
    forbidden_biomes: tuple[Biome, ...]
    population_base: int = 100


# ---------------------------------------------------------------------------
# LW-013 · Biome Strictness Check
# ---------------------------------------------------------------------------

def apply_biome_strictness(
    binding: SpeciesBiomeBinding,
    world_biomes: set[Biome],
) -> bool:
    """Return True if the world contains at least one of the species' primary biomes.

    Any in primary_biomes acts as a universal pass.
    A False result triggers a population zero-out in the calling initializer.
    """
    if Biome.Any in binding.primary_biomes:
        return True
    return bool(set(binding.primary_biomes) & world_biomes)


# ---------------------------------------------------------------------------
# LW-015 · Spawn Director Biome Gate
# ---------------------------------------------------------------------------

def can_spawn_in_chunk(
    species_id: str,
    chunk: "WorldChunk",
    ledger: "PopulationLedger",
    bindings: dict[str, SpeciesBiomeBinding],
) -> bool:
    """Single authoritative entry point for all spawn decisions.

    Returns False if:
    - Species is extinct or unknown.
    - Chunk biome is in forbidden_biomes.
    - Chunk biome is not in primary + tolerated (unless Any is present).
    - Local population already meets carrying capacity.
    No other code may bypass this gate for non-anomaly spawns.
    """
    record = ledger.get(species_id)
    if record is None or record.is_extinct:
        return False

    binding = bindings.get(species_id)
    if binding is None:
        return False

    if chunk.biome in binding.forbidden_biomes:
        return False

    allowed = set(binding.primary_biomes) | set(binding.tolerated_biomes)
    if Biome.Any not in allowed and chunk.biome not in allowed:
        return False

    cap = chunk.carrying_capacity.get(species_id)
    if cap is not None:
        if chunk.local_populations.get(species_id, 0) >= cap:
            return False

    return True
