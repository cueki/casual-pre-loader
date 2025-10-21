[![Join Our Discord!](https://img.shields.io/badge/Discord-Join%20Us-7289DA.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/2SZbfXzKYQ)

# Download the latest release [Here](https://github.com/cueki/casual-particle-pre-loader/releases/).
# If you want to run with python (Linux):

We need studiomdl.exe from the Windows version of TF2.

First, force the use of proton in game properties, make sure to click "update" after.

![](images/proton.png)

Once updated, navigate to your `Steam/steamapps/common/Team Fortress 2/` and rename bin/ to something other than bin/, for example, bin_/.

![](images/bin.png)

Disable proton in game properties, and update again.

![](images/disable_proton.png)

Back in `Steam/steamapps/common/Team Fortress 2/`, rename bin_/ back to bin/ to merge the directories, or copy its contents into bin/.

![](images/bin_merge.png)

If done right, you should now see `studiomdl.exe` inside the bin/ folder!

![](images/studiomdl.png)

Now you can clone the repo, or install it as an [AUR package](https://aur.archlinux.org/packages/casual-pre-loader-git)!

Using [yay](https://github.com/Jguer/yay):
```sh
yay -S casual-pre-loader-git
casual-pre-loader
```

Using [paru](https://github.com/Morganamilo/paru):
```sg
paru -S casual-pre-loader-git
casual-pre-loader
```

Or with git:
```sh
git clone https://github.com/cueki/casual-pre-loader
cd casual-pre-loader
python -m venv .venv
source .venv/bin/activate # (you will need to activate the venv each time)
pip install -r requirements.txt
python main.py
```

If you're on Ubuntu, or an Ubuntu-based derivative (such as Mint or PopOS), you may get an error similiar to the following:
```
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
```
Installing `libxcb-cursor-dev` should solve the issue:
```sh
sudo apt-get install -y libxcb-cursor-dev
```

# How does this work?

There are two exploits im using, one that many are familiar with, being the game_info change (nothing really noteworthy here, known widely since at least ~~2018-2019~~ **2020!** my bad, incorrectly recalled dates, should have double-checked), and the second being that the game doesn't actually check the md5 hashes outlined in the directory vpk.
I combine both of these in order to "replace" the particles already present in the game with modded ones, which then point to the custom directory for their material files.

When first approaching this, I had no idea about the md5 hash being unchecked, I stumbled across that fact by accident some time in August 2023. Surely this has no correlation to any events whatsoever.

While the game may not enforce the hashes, it does enforce the file sizes, therefore, in order to replace any of the files in the game, I need to ensure that the replacement is the same size or less as what is already there, if it's smaller, I can simply pad it out with whitespace bytes to keep the dir vpk happy.
This means that, in order to get custom particles working, I had to learn how particle files were structured, and then use that knowledge to remove any redundant data so that I could use that extra space for modded data.

So fundamentally, the process works as follows:
- **Step 1:** <ins>Figure out what mods the user is actually adding</ins> (`operations/advanced_particle_merger.py`). Mod makers will sometimes cluster their particle effects into one giant file for simplicity's sake, and to force the load order of the game. This works, and is actually pretty clever, but unfortunately goes directly against what I am trying to accomplish because it assumes that whatever particle effects are not being modified are contained within the games files, and I am replacing those directly. Therefore, I must look at the files being presented to the application and use a reverse lookup to figure out what particles are actually being referenced, the mapping is found inside of `particle_system_map.json`
- **Step 2:** <ins>Rebuild the particle files</ins> (`operations/pcf_rebuild.py`). Now that we know what particle elements are actually being modified, we now need to make sure that the particle files we put in the game are not missing anything. If, for example, you just want to replace the short circuits blinding awful no good very bad flashbang by modifying just the `dxhr_lightningball`, you could patch that back into the game no issue, but then the machina would no longer have any tracers and the widowmaker would lose its shell ejections, because they are all part of the same particle file. So we use the same mapping of `particle_system_map.json` to get the rest of the particle elements from the games base files, and combine them all into one `dxhr_fx.pcf` then patch that back into the game. This is worse than it looks because the tree structure of the particle files is annoying to traverse. Sometimes the names in the string dictionary are different, sometimes Valve has duplicate elements in different files by mistake. All part of the process.
- **Step 3:** <ins>Compress the particle files</ins> (`operations/pcf_compress.py`). Once the files have been rebuilt there is a new problem, they are too big to fit within the vpks. As mentioned above, my solution to this problem was to find any redundant data within the particle files that I could remove. Turns out, the particle files are about 3.5x larger than they need to be. You can look at the code to see exactly what I'm doing, mostly just removing duplicate data, updating references, and making the internal structure more efficient. This ratio is not linear, the larger the file the better the compression, while smaller files have much less to work with.
- **Step 4:** <ins>Patch the files back into the vpk</ins> (`core/handlers/file_handler.py`). Once we have the compressed particle files, we then need to patch them back into the game's multi-file misc vpks. Most vpk tools do not allow for direct modification of vpks without unpacking and repacking, so I wrote my own parser and handler.
- **Step 5:** <ins>Move files into the game</ins> (various scripts). Then we need to get the specified effect materials into the games custom dir, as well as whatever else is needed. I get only the files needed from looking inside the pcf at the materials attribute path. Then, I pack them back into a vpk just for better load times. I also add a config file that loads the itemtest map on startup, so that all the custom stuff gets loaded.

There are many details of the problem-solving process that I may elaborate on in the future.

Therefore, skipping over the details of me slowly figuring this all out, the most difficult problem I wanted to solve was providing a solution that actually worked for the average TF2 player, and that's how we got here.

Is this VAC safe? Yes.

Could Valve patch this out of the game easily? Also yes.

Enjoy it while you can :).

-cukei
# Thank you <3:

[THE GOAT](https://gamebanana.com/members/2133251) This person made the [square_series](https://gamebanana.com/mods/435309) preset.

[Skeleton Hotel](https://gamebanana.com/members/1414545).

[Taxicat](https://gamebanana.com/members/1333549) and [Qorange](https://gamebanana.com/members/2060075) for the [transparent_flamethrower](https://gamebanana.com/mods/348622).

[Ashe_tf](https://gamebanana.com/members/1932153) for fixing the [medicgun_beam](https://gamebanana.com/mods/437447).

[SonOfDiscordiA](https://gamebanana.com/members/2670597) for the [short_circuit](https://gamebanana.com/mods/446897).

[agrastiOs](https://github.com/agrastiOs) for the [UltimateVisualFixPack](https://github.com/agrastiOs/Ultimate-TF2-Visual-Fix-Pack).

## Star History

<a href="https://www.star-history.com/#cueki/casual-pre-loader&Date">
    <picture>
        <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=cueki/casual-pre-loader&type=Date&theme=dark" />
        <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=cueki/casual-pre-loader&type=Date" />
        <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=cueki/casual-pre-loader&type=Date" />
    </picture>
</a>


