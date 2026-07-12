---
description: Create a new country in an EU5 mod. Covers all required files and optional advanced sections. Use when the user wants to add a new country to the mod.
---

# Create a New Country

The mod directory is `c:\Users\theod\Documents\Paradox Interactive\Europa Universalis V\mod\Panda Express Map`.
The base game directory is `e:\SteamLibrary\steamapps\common\Europa Universalis V\game`.

## Before starting

1. **Resolve province names to locations.** If the user gives province names (e.g. `murcia_province`), look them up in `e:\SteamLibrary\steamapps\common\Europa Universalis V\game\in_game\map_data\definitions.txt` to get the individual location names inside each province.

2. **Choose a tag** that is not already in use. Grep the base game `in_game/setup/countries/` and the mod's `in_game/setup/countries/panda_express_map.txt` for the tag to confirm it is free.

3. **Choose a name and adjective** for the country. Check the localization file `main_menu/localization/english/country_names_l_english.yml` to confirm the name is not already taken.

---

## Creating the country — use the script

Run `scripts/create_country.py` from the mod root. It handles `10_countries.txt`, `in_game/setup/countries/panda_express_map.txt`, and the localization file in one step:

```
python scripts/create_country.py \
    --tag TAG \
    --name "Country Name" \
    --adj "Country Adjective" \
    --region iberian|french \
    --locations loc1 loc2 loc3 \
    [--color R G B] \
    [--culture castilian] \
    [--religion catholic] \
    [--rank rank_duchy] \
    [--includes template1 template2 ...]
```

**`--region` is required.** Choose based on the country's geographic region:

| Region | Culture default | Includes default |
|--------|----------------|-----------------|
| `iberian` | `castilian` | `expl_mediterranean expl_silk_road_west iberian_monarchy` |
| `french` | `french` | `expl_western_europe catholic_monarchy_no_coast` |

Religion defaults to `catholic` for both regions. `--culture` and `--includes` override region defaults.

The script will error if the tag or name already exists.

---

## After running the script

### Coat of arms — `main_menu/common/coat_of_arms/coat_of_arms/panda_express_map.txt`

The script does **not** handle the CoA — add it manually:

```
TAG = { # Country Name
    pattern = "pattern_solid.dds"
    color1 = "red"
    color2 = "yellow"
    color3 = "white"

    colored_emblem = {
        texture = "ce_castle_short.dds"
        color1 = color2
        color2 = color2
        color3 = color3
    }
}
```

Available patterns: `main_menu/gfx/coat_of_arms/patterns/`
Available emblems: `main_menu/gfx/coat_of_arms/colored_emblems/`

---

## Optional steps

### International organizations — `main_menu/setup/start/15_international_organizations.txt`

Required if the country should be a member of the HRE or another organization at game start:
```
holy_roman_empire = {
    members = {
        ... TAG ...
    }
}
```

### Advanced government setup

Edit the country block in `10_countries.txt` directly after the script runs. Inside `government = { }` you can add:
- `reforms = { reform_name ... }` — government reforms
- `laws = { law_key = law_value ... }` — specific law overrides
- Societal value sliders, e.g. `centralization_vs_decentralization = 15`
- `tolerated_cultures = { culture1 culture2 }` — accepted minority cultures
- `ruler = character_tag` + `ruler_term = { ... }` — historical rulers

---

## Verification checklist

- [ ] Tag does not conflict with any existing country in the base game or mod
- [ ] Script ran without errors
- [ ] CoA entry added to `panda_express_map.txt`
- [ ] Reload the mod fully in the launcher before testing — clicking "New Game" alone is not enough
