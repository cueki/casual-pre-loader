# How does this work?
Here you can find an in-depth explanation to how this preloader works in a step by step process. The project is also open source, so if you wish to dig in the files yourself, feel free! If you wanna contact cueki, or anyone else who has worked on anything with this preloader for more details about it, join the **[discord](https://discord.gg/64sNFhqUaB)** and shoot us a message!

## Explanation:

There are **two exploits** in use, one that many are familiar with, being the `game_info` change *(nothing really noteworthy here, since it has been known widely since at least 2020)*, and the second being that **the game doesn't actually check the md5 hashes outlined in the directory vpk**. I combine both of these in order to "*replace*" the particles already present in the game with modded ones, which then point to the custom directory for their material files.

When first approaching this, I had no idea about the md5 hash being unchecked, I stumbled across that fact by accident some time in August 2023. *(Surely this has no correlation to any events whatsoever.)*

While the game may not enforce the hashes, it *does enforce* the file sizes, therefore, in order to replace any of the files in the game, I need to ensure that the replacement is the same size or less than whats already there, if it's smaller, I can simply pad it out with whitespace bytes to keep the dir vpk happy. This ultimately means that, in order to get custom particles working, I had to learn how particle files were structured, and then use that knowledge to remove any redundant data so that I could use that extra space for modded data.
    
### So fundamentally, the process works as follows:

1. **Figure out what mods the user is actually adding**
    - Mod makers will sometimes cluster their particle effects into one giant file for simplicity's sake, and to force the load order of the game. This works, and is actually pretty clever, but unfortunately goes directly against what I am trying to accomplish because it assumes that whatever particle effects are not being modified are contained within the games files, and I am replacing those directly. Therefore, I must look at the files being presented to the application and use a reverse lookup to figure out what particles are actually being referenced, the mapping is found inside of `particle_system_map.json`
>This process can be found in: `operations/advanced_particle_merger.py`.
 2. **Rebuild the particle files**
    - Now that we know what particle elements are actually being modified, we now need to make sure that the particle files we put in the game are not missing anything. If, for example, you just want to replace the short circuits blinding awful no good very bad flashbang by modifying just the `dxhr_lightningball`, you could patch that back into the game no issue, but then the machina would no longer have any tracers and the widowmaker would lose its shell ejections, because they are all part of the same particle file. So we use the same mapping of `particle_system_map.json` to get the rest of the particle elements from the games base files, and combine them all into one `dxhr_fx.pcf` then patch that back into the game. This is worse than it looks because the tree structure of the particle files is annoying to traverse. Sometimes the names in the string dictionary are different, sometimes Valve has duplicate elements in different files by mistake. All part of the process.
>This process can be found in: `operations/pcf_rebuild.py`.
3. **Compress the particle files**
    - Once the files have been rebuilt there is a new problem, they are too big to fit within the vpks. As mentioned above, my solution to this problem was to find any redundant data within the particle files that I could remove. Turns out, the particle files are about 3.5x larger than they need to be. You can look at the code to see exactly what I'm doing, mostly just removing duplicate data, updating references, and making the internal structure more efficient. This ratio is not linear, the larger the file the better the compression, while smaller files have much less to work with.
>This process can be found in: `operations/pcf_compress.py`.
4. **Patch the files back into the vpk**
    - Once we have the compressed particle files, we then need to patch them back into the game's multi-file misc vpks. Most vpk tools do not allow for direct modification of vpks without unpacking and repacking, so I wrote my own parser and handler.
>This process can be found in: `core/handlers/file_handler.py`.
5. **Move files into the game**
    - Then we need to get the specified effect materials into the games custom dir, as well as whatever else is needed. I get only the files needed from looking inside the pcf at the materials attribute path. Then, I pack them back into a vpk just for better load times. I also add a config file that loads the itemtest map on startup, so that all the custom stuff gets loaded.
>This process can be found in a bunch of various scripts.

There are many details of the problem-solving process that I may elaborate on in the future.

Therefore, skipping over the details of me slowly figuring this all out, the most difficult problem I wanted to solve was providing a solution that actually worked for the average TF2 player, and that's how we got here.

-cueki :)
