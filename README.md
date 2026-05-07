# Panda Express Map

An **Europa Universalis V** mod that splits the map into a multiplayer-friendly version.

- **Version:** 0.1
- **Game version:** 1.2.0
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
EU5_MOD_PATH=C:\Users\<you>\Documents\Paradox Interactive\Europa Universalis V\mod\Panda Express Map
```

### Applying changes

Run the orchestrator to apply all mod changes in order:

```bash
python scripts/apply_all.py
```

Individual steps can also be run standalone:

```bash
python scripts/apply_resources.py
```

### Debug mode

Add `-debug_mode` to EU5's Steam launch options to see country and location tag overlays in-game — useful for verifying mod changes.
