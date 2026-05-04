---
description: Create a new country in an EU5 mod. Covers all required files and optional advanced sections. Use when the user wants to add a new country to the mod.
---

# Create a New Country

The mod directory is `<EU5-mods-dir>\<mod-name>` (e.g. `C:\Users\theod\Documents\Paradox Interactive\Europa Universalis V\mod\Fractured Europe`).
The base game directory is `<EU5-game-dir>` (e.g. `e:\SteamLibrary\steamapps\common\Europa Universalis V\game`).

## Before starting

**Choose a 3-letter tag** that is not already in use. Grep the base game for `^\s*TAG\s*=\s*\{` across `in_game/setup/countries/` to confirm it is free.

---

## Required steps

### 1. Assign locations — `main_menu/setup/start/10_countries.txt`

Use the `update-country-locations` skill to:
- Add the new country block with `own_control_core = { <locations> }`
- Remove those locations from any other country that currently owns them

Minimum country block:
```
#<Country Name>
TAG = {
    own_control_core = {
        location1 location2 location3
    }

    starting_technology_level = 3
    include = "expl_mediterranean"  # depends on region — take inspiration from the
    include = "expl_silk_road_west" # countries whose locations were transferred to
    include = "expl_silk_road_center" # this new country
    include = "iberian_monarchy"    # or appropriate regional template

    government = {
        type = monarchy
        heir_selection = cognatic_primogeniture
    }

    country_rank = rank_duchy    # rank_county / rank_duchy / rank_kingdom / rank_empire
    capital = <capital_location>
}
```

### 2. Country name — `main_menu/localization/english/country_names_l_english.yml`

Add two lines near geographically related countries:
```yaml
 TAG: "Country Name"
 TAG_ADJ: "Country Adjective"
```

### 3. Coat of arms — `main_menu/common/coat_of_arms/coat_of_arms/<mod-file>.txt`

Add an entry to the centralised mod coat of arms file. Minimum entry:
```
TAG = { # Country Name
    pattern = "pattern_solid.dds"
    color1 = "blue"
    color2 = "yellow"
    color3 = "white"

    colored_emblem = {
        texture = "ce_border.dds"
        color1 = color2
        color2 = color2
    }
    colored_emblem = {
        texture = "ce_castle_short.dds"
        color1 = color2
        color2 = color1
    }
}
```

Available patterns: `main_menu/gfx/coat_of_arms/patterns/`
Available emblems: `main_menu/gfx/coat_of_arms/colored_emblems/`

### 4. Country definition — `in_game/setup/countries/<mod-file>.txt`

Add an entry to the centralised mod country definitions file:
```
TAG = {
    color = rgb { R G B }

    culture_definition = portuguese    # or appropriate culture
    religion_definition = catholic     # or appropriate religion
}
```

---

## Optional steps

### International organizations — `main_menu/setup/start/15_international_organizations.txt`

Required if the country should be a member of the HRE or another organization at game start. Add the tag inside the relevant organization block, e.g.:
```
holy_roman_empire = {
    members = {
        ... TAG ...
    }
}
```

### Advanced government setup

Inside the `government = { }` block in `10_countries.txt`, you can add:
- `reforms = { reform_name ... }` — government reforms
- `laws = { law_key = law_value ... }` — specific law overrides
- Societal value sliders, e.g. `centralization_vs_decentralization = 15`
- `tolerated_cultures = { culture1 culture2 }` — accepted minority cultures
- `ruler = character_tag` + `ruler_term = { ... }` — historical rulers (requires entries in `05_characters.txt`)
- `ai_advance_preference_tags = { exploration = 5 }` — AI behaviour hints

---

## Verification checklist

- [ ] Tag does not conflict with any existing country in the base game or mod
- [ ] All assigned locations appear in exactly one country's block (use `update-country-locations` skill)
- [ ] Localization key matches the tag exactly (`TAG:` not `tag:`)
- [ ] Reload the mod fully in the launcher before testing — clicking "New Game" alone is not enough
