# StarTools: MMDC

### Minecraft Modding Duplicate Checker
StarTools: MMDC is a powerful standalone utility designed for modders, modpack creators, resource pack authors, and especially contributors to the Rename Compat Project.



Minecraft is full of mods that unknowingly add items with the same display name, like:



- Pear



- Copper Nugget



- Limestone



- Orange Jelly



Across large modpacks, this becomes a real problem for:



- balancing



- debugging



- making compat datapacks



- UX consistency



- resource pack override correctness



StarTools: MMDC solves that problem by scanning:



\- Vanilla items

\- Modded items

\- Modded lang files

\- Resource pack overrides

\- Registry dump data



…to find true cross-mod duplicate names.



🔨 What This Tool Can Be Used For

### ✔ Modpack Curation



Find items sharing the exact same display name across mods so you can:



rename them with a resource pack



tweak recipes



identify conflicts



improve player clarity



### ✔ Mod Development



Check if your mod unintentionally reuses display names from other mods.



### ✔ Resource Pack Development



StarTools: MMDC supports RP overrides, so you can see:



which names the RP changes



which duplicates still remain



before/after comparisons



per-mod breakdowns



### ✔ Rename Compat Project (RCP) Contributors



Fully compatible with RCP workflows.

Recommended project:

Rename Compat Project on CurseForge:

https://www.curseforge.com/minecraft/texture-packs/the-rcp



You can scan a modpack, see all duplicates, then update the RP accordingly.

---

✅ Requirements



This tool depends on one critical piece:



✅ You MUST generate a registry dump.



The tool requires actual mod registry data to work.

We strongly recommend using:



✅ Registry Dump (Modrinth)



https://modrinth.com/mod/registry-dump



This tool has been tested exclusively with this mod.

Other dump mods may work, but are not guaranteed.



Registry Dump creates folders like:



dump/items/

dump/blocks/

dump/entities/

dump/worldgen/





StarTools: MMDC reads these.

---

➡ Download \& Run (EXE Version — Recommended)

🔵 1. Download the EXE from Releases



Go to the Releases section of this GitHub repository and download:



StarTools-MMDC.exe



➡ 2. Make sure you have a registry dump



Install the Registry Dump mod in your modpack.

Run the game once so it generates the dump/ folder.

You must do this before scanning.



➡ 3. Open the app



Run the EXE. No installation required.



➡ 4. Select the necessary folders



On first launch, select:



➡ Dump Root (the folder containing items/, blocks/, etc.)



➡ Mods Folder (the folder with .jar mod files)



➡ Resource Pack (optional but recommended for RCP users)



➡ Output Folder (where the reports go)



➡ 5. Save Defaults



Click Save Defaults so you never select these again.



➡ 6. Scan



Pick the dump folder to analyze (like dump/items)

Then click Start Scan.



➡ 7. Read Your Results



The output folder will contain:



BASELINE\_duplicates.txt



AFTER\_RP\_duplicates.txt



RP\_changes\_diff.txt



by\_mod\_AFTER\_RP/ (per-mod breakdown)



➡ 8. Need help?



Check the Help tab inside the app.

It explains:



how scanning works



what each setting does



what the reports mean



how RCP overrides are applied



what the “missing lang key” warnings mean

---

🟠 Running from Source (Python Version)



If you want to run the script directly:



1\. Install dependencies

pip install -r requirements.txt 




2\. Run

mmdc.py



3\. Build the EXE yourself

pyinstaller StarTools-MMDC.spec





Output:



dist/StarTools-MMDC.exe

---

🔧 Features



\- Full GUI using ttkbootstrap (dark/light mode)

\- Select folders once → saved automatically

\- RP override support

\- Per-mod duplicate grouping

\- Before/after RP name comparison

\- Missing-lang-key detection

\- Exclude specific mods

\- Smart prettifier for IDs

\- Simple log output inside the UI

\- Compatible with ALL modloaders



🔗 Links

Rename Compat Project



https://www.curseforge.com/minecraft/texture-packs/the-rcp



Registry Dump (Required, if not using another registry mod)



https://modrinth.com/mod/registry-dump


