# Panda Express Map

An **Europa Universalis V** mod that splits the map into a multiplayer-friendly version.

- **Version:** 0.6
- **Game version:** 1.4.6 (1337 start date only)
- **Scope:** Map changes only (English)

## Features

- Reorganizes the map into balanced, multiplayer-ready territories
- Custom country definitions with location assignments
- No gameplay or balance changes — map only

## Installation

1. Download or clone this repository into your EU5 mods folder:
   ```
   Documents\Paradox Interactive\Europa Universalis V\mod\Panda Express Map\
   ```
2. Launch EU5 and enable **Panda Express Map** in the mod manager.

## Development

### Prerequisites

- Python 3.10+
- `python-dotenv` (`pip install python-dotenv`)

### Setup

Create a `.env.local` file in the mod root to override default paths:

```env
EU5_GAME_PATH=E:\SteamLibrary\steamapps\common\Europa Universalis V\game
```

### Applying changes

Delete `10_countries.txt`, `12_diplomacy.txt`, `country_names_l_english.yml` and `location_templates.txt` so the build starts from fresh base files, then run the orchestrator to apply all mod changes in order:

```bash
python scripts/apply_all.py
```

Individual steps can also be run standalone:

```bash
python scripts/apply_resources.py
```

### Debug mode

Add `-debug_mode` to EU5's Steam launch options to see country and location tag overlays in-game — useful for verifying mod changes.
