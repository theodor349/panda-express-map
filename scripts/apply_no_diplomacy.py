import os

MOD_ROOT = r"c:\Users\theod\Documents\Paradox Interactive\Europa Universalis V\mod\Panda Express Map"
DIPLOMACY_PATH = os.path.join(MOD_ROOT, "main_menu", "setup", "start", "12_diplomacy.txt")

content = "diplomacy_manager = {\n\n}\n"

os.makedirs(os.path.dirname(DIPLOMACY_PATH), exist_ok=True)
with open(DIPLOMACY_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written: {DIPLOMACY_PATH}")
