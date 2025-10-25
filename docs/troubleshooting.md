# Troubleshooting
Here you can find common troublshooting problems and potential fixes/solutions. If none of these work, or your problem isnt listed here, please join the **[discord](https://discord.gg/64sNFhqUaB)** and open a support ticket. 

**If you encounter any error, please try upgrading to the [latest version](https://github.com/cueki/casual-pre-loader/releases) first.**

## This mod doesn't work!/My mod doesn't work!

### For users installing mods:
1. **All of your mods should be in the preloader, not custom.**
    - The only thing you should keep in custom (if you want to) is your hud.
2. **Check your load order.** 
    - The preloader will tell you if any files are conflicting with one another and use that to decide what should take priority. **Animations should be installed last in the load order if you have custom weapon models.**
3. **Make sure you have all of your desired mods checked off before installing.**
4. **Make sure youre launching with `+exec w/config.cfg`**.
5. **Make sure the mod has correct file pathing.**
    - While the preloader can handle most mods, even non casual compatible ones, they will need to reflect the file structure of TF2. You can either contact the mod author to fix it, or follow the instructions in the [*"For users creating mods:"*](#for-users-creating-mods) section to fix it yourself.
6. **If you change huds after installing your mods, make sure to run the preloader again.**
7. **If there was a TF2 update, run the preloader again.**
    

### For users creating mods:
While this tool doesn't need a mod to be "*casual compatible*" for it to work, there's still some issues that will need to be addressed. <br>

1. **When making mods, please make sure to include *at least* the VTF and the base TF2 model itself. If the model is a custom model, please add in a VMT as well.**
2. **Make sure that your paths reflect the structure of tf2!**
    - For example, if you're making a pyro cosmetic, the file path **SHOULD** look like this: `models/workshop/player/items/pyro/dec17_cats_pajamas/dec17_cats_pajamas.mdl` .
    - **NOT** like this: `models/alaxe/tf2/cosmetics/pyro_female/charred_chainmail.mdl`.
3. **If youre using "*casual compatible*" paths, custom names are valid for materials ONLY.**
4. **Double check your VMT's are calling the correct paths.**

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
The "`Disconnected: An issue with your computer is blocking the VAC system. You cannot play on secure servers.`" error has nothing to do with the preloader, and is a pretty common steam bug. **To fix it, simply restart steam.** If that doesnt work, try verifying the integrity of your game files, and running the preloader again.
