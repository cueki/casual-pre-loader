# Troubleshooting
Here you can find common troublshooting problems and potential fixes/solutions. If none of these work, or your problem isn't listed here, please join the **[discord](https://discord.gg/64sNFhqUaB)** and open a support ticket.

**If you encounter any error, please try upgrading to the [latest version](https://github.com/cueki/casual-pre-loader/releases) first.**

## This mod doesn't work!/My mod doesn't work!

### For users installing mods:
1. **All of your mods should be in the preloader, not custom.**
    - The only thing you should keep in custom (if you want to) is your hud.
2. **Check your load order.**
    - The preloader will tell you if any files are conflicting with one another and use that to decide what should take priority. **Animations should be installed last in the load order if you have custom weapon models.**
3. **Make sure you have all of your desired mods checked off before installing.**
4. **Make sure you're launching with `+exec w/config.cfg`**.
5. **Make sure the mod has correct file pathing.**
    - While the preloader can handle most mods, even non-'*casual compatible*' ones, they will need to reflect the file structure of TF2. You can either contact the mod author to fix it, or follow the instructions in the [*'For users creating mods:'*](#for-users-creating-mods) section to fix it yourself.
6. **If you change huds after installing your mods, make sure to run the preloader again.**
7. **If there was a TF2 update, run the preloader again.**
> NOTE: There are a select few mods that **WON'T** work when put in the preloader, they are as follows:
> 
> - Bsp packed content (think modern community maps).
> 
> - Blacklisted sounds (for now).
> 
> - Decals (for now).
> 
> - Configs (these can stay in custom).
> 
> - No hats mod (this should also stay in custom).
> 
> - Custom named materials and models (ONLY works with casual compatible file paths).
<!-- i know it looks strange, but this is how it needs to be formatted for the list to be nested within the blockquote. im sorry -->

### For users creating mods:
While this tool doesn't need a mod to be '*casual compatible*' for it to work, there's still some issues that will need to be addressed. <br>

1. **When making mods, please make sure to include *at least* the VTF and the base TF2 model itself. If the model is a custom model, please add in a VMT as well.**
2. **Make sure that your paths reflect the structure of tf2!**
    - For example, if you're making a pyro cosmetic, the file path **SHOULD** look like this: `models/workshop/player/items/pyro/dec17_cats_pajamas/dec17_cats_pajamas.mdl`
    - **NOT** like this: `models/alaxe/tf2/cosmetics/pyro_female/charred_chainmail.mdl`
3. **If you're using '*casual compatible*' paths, custom names are valid for materials ONLY.**
4. **Double check your VMT's are calling the correct paths.**
5. **Make sure your textures (VTF'S) have `no mipmap` and `no level of detail` checkmarked so textures don't break.**

The preloader also includes an easy sorting system with the use of `mod.json`, which can help end users sort their mods in the preloader easier. To use it, create a json file called mod.json, and paste this example inside: <br>
```
{
  "addon_name": "your mod name here",
  "type": "use one of these categories: Experimental, HUD, Misc, Texture, Animation, Sound, Skin, or Model",
  "description": "a brief desctription of what your mod is and what it does",
  "gamebanana_link": "the link to your mods gamebanana page",
}
```

## I got a VAC error! I dont wanna get banned!
The "`Disconnected: An issue with your computer is blocking the VAC system. You cannot play on secure servers.`" error has nothing to do with the preloader, and is a pretty common Steam bug. **To fix it, simply restart steam.** If that doesnt work, try verifying the integrity of your game files, and running the preloader again.

## Common issues/bugs
This section contains known bugs/issues with the preloader, and fixes for them in case you happen to encounter any.
>NOTE:
If your game is crashing out of the blue, it is most likely an issue with the mods you have installed, and not the preloader. Please troubleshoot your mods FIRST before seeking further assistance in the discord.

### Linux
1. Sometimes a bug with quickprecache can crash your TF2 instance on launch. Just launch again to fix it.
2. Black weapons/models. Just reboot.

### Windows
1. Auto updater not working. This could be for a plethora of reasons, but the easiest fix is to just install the [new version](https://github.com/cueki/casual-pre-loader/releases) of the preloader manually.
