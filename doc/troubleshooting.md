# Troubleshooting
Here you can find common troubleshooting problems and potential fixes/solutions. If none of these work, or your problem isn't listed here, please join the **[discord]({{ discord_url }})** and open a support ticket.

**If you encounter any error, please try upgrading to the [latest version]({{ config.repo_url }}/releases) first.**

## For users installing mods:

1. **If there was a TF2 update, run the preloader again.**
2. **All of your mods should be in the preloader, not custom.**
    - The only thing you should keep in custom (if you want to) is your hud.
3. **Check your load order.**
    - The preloader will tell you if any files are conflicting with one another and use that to decide what should take priority. **Animations should be installed last in the load order if you have custom weapon models.**
4. **Make sure you have all of your desired mods have their boxes checked before installing.**
5. **Make sure you're launching with `+exec w/config.cfg`**.
6. **Make sure the mod has correct file pathing.**
    - While the preloader can handle most mods, even non-'*casual compatible*' ones, they will need to reflect the file structure of TF2. You can either contact the mod author to fix it, or follow the instructions in the [*'For users creating mods'*](#for-developers-creating-mods) section to fix it yourself.
7. **If you change huds after installing your mods, make sure to run the preloader again.**

!!! note
    There are a select few mods that **WON'T** work when put in the preloader, they are as follows:

    - Bsp packed content (think modern community maps).
    - Blacklisted sounds (for now).
    - Decals (for now).
    - Configs (these can stay in custom).
    - No hats bgum ([this version](https://gamebanana.com/tools/20969) works with the preloader).
    - Custom named materials and models (ONLY works with casual compatible file paths).

## For developers creating mods:
While this tool doesn't need a mod to be '*casual compatible*' for it to work, there's still some issues that will need to be addressed. <br>

1. **When making mods, please make sure to include *at least* the VTF and the base TF2 model itself. If the model is a custom model, please add in a VMT as well.**
2. **Make sure that your paths reflect the structure of tf2!**
    - For example, if you're making a pyro cosmetic, the file path **SHOULD** look like this: `models/workshop/player/items/pyro/dec17_cats_pajamas/dec17_cats_pajamas.mdl`
    - **NOT** like this: `models/alaxe/tf2/cosmetics/pyro_female/charred_chainmail.mdl`
3. **If you're using '*casual compatible*' paths, custom names are valid for materials ONLY.**
4. **Double check your VMT's are calling the correct paths.**
5. **Make sure your textures (VTF'S) have `no mipmap` and `no level of detail` checkmarked so textures don't break.**

The preloader also includes an easy sorting system with the use of `mod.json`, which can help end users sort their mods in the preloader easier. To use it, put your mod in the prelaoder, select it, then navigate to the bottom of the 'details' area. Then, click 'edit mod.json', and fill in all the information. Once you're finished, click save, then navigate back to the bottom of the 'details' area, and click 'export as vpk'. This is the file you will upload to Gamebanana.

## I got a VAC error! I don't wanna get banned!
The "`Disconnected: An issue with your computer is blocking the VAC system. You cannot play on secure servers.`" error has nothing to do with the preloader, and is a pretty common Steam bug. **To fix it, simply restart Steam.** If that doesn't work, restart your computer. This error usually will resolve itself in a few minutes with no user input.

## Common issues/bugs
This section contains known bugs/issues with the preloader, and fixes for them in case you happen to encounter any.

!!! note
    If your game is crashing out of the blue, it is most likely an issue with the mods you have installed, and not the preloader. Please troubleshoot your mods FIRST before seeking further assistance in the discord.

### Linux
1. I have personally encountered a bug with quickprecache, where with some mods, not all, TF2 will crash *every other launch*. If this is happening to you, please **contact me** in the [discord]({{ discord_url }}).
2. Black weapons/models. Just reboot.

### Windows
1. Auto updater not working. This could be for a plethora of reasons, but the easiest fix is to just install the [new version]({{ config.repo_url }}/releases) of the preloader manually.
