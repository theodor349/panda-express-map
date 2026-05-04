# CLAUDE.md

## Project

**Panda Express Map** — EU5 mod (`id: panda-exp-map`, v0.1, game v1.1.0) that splits the map into a multiplayer-friendly version. Scope: English only, map changes only.

## Paths

| Purpose | Path |
|---|---|
| Base game files | `E:\SteamLibrary\steamapps\common\Europa Universalis V\game\` |
| Mod root | `c:\Users\theod\Documents\Paradox Interactive\Europa Universalis V\mod\Panda Express Map\` |

## Mod structure (planned)

```
Panda Express Map/
├── .metadata/metadata.json
├── main_menu/
│   ├── common/coat_of_arms/coat_of_arms/   
│   │   └── panda_express_map.txt           # Mod COA definitions: color, culture, religion
│   ├── localization/english/               # country_names_l_english.yml
│   │   └── country_names_l_english.yml
│   └── setup/start/
│       ├── 10_countries.txt                # Country location assignments
│       └── 12_diplomacy.txt                # Starting diplomacy
├── in_game/setup/countries/
│   └── panda_express_map.txt               # Mod Country definitions: color, culture, religion
└── scripts/                                # Python automation
```

## Key rules

- **English only** — no other localization files.
- **Map changes only** — do not modify gameplay, balance, or non-map systems.
- **Always copy the full base game file** before modifying — the game replaces the entire file, not individual entries.
- **Mirror the base game path** exactly (e.g., `main_menu/setup/start/10_countries.txt`).
- A location may only appear in one country's own_control_core block in `10_countries.txt`.
