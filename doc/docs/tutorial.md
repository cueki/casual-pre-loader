# Tutorial
Here you can find two tutorials, one for [**Windows**](#windows-tutorial), and one for [**Linux**](#linux-tutorial). If you're having trouble with your *already installed* preloader, please refer to the **[troubleshooting doc](troubleshooting.md)**.

**If you encounter any error, please try upgrading to the [latest version]({{ config.repo_url }}/releases) first.**

If you need further assistance installing the preloader, or just want to chat, join the **[discord]({{ discord_url }})**!

If you want a video supplement, please refer to the [**Video Supplement**](#video-supplement) section!

!!! note
    MacOS support for Team Fortress 2 was officially dropped in 2024, and hasn't been properly playable since 2019.
    It is possible to download older depots, or to run the windows build through `wine`/`crossover`, but this requires running an older version of the game and/or prevents users from connecting to VAC-enabled servers (e.g. casual servers).
    As such, the casual-pre-loader does not support MacOS, and support is not planned.

## Windows Tutorial:

### Step 1: Installation

1. **Install the latest version of the preloader from [GitHub]({{ config.repo_url }}/releases) or [Gamebanana]({{ gamebanana_url }}).**
2. **Once you have the zip file, extract it, and put the folder anywhere you like.**

!!! note
    Ensure it is not under a Onedrive shared folder or a folder the user does not have write permissions for (e.g. `C:\program files`).
    Do not put the casual-pre-loader in your game's `custom` folder. It is not a mod, and does not get loaded by the game.

!!! note
    If you're interested in packaging the casual-pre-loader via winget, choco, scoop, or any other windows package manager, please feel free to open a PR!

### Step 2: Adding your mods

1. **Prepare your mods. The preloader can handle all mods, even mods that aren't *'casual compatible',* so don't be afraid to use whatever you'd like! Once you have all the mods you want, set them aside.**
      - While you *can* put your hud in the preloader, it does the exact same thing as putting it in custom, so you don't have to if you don't want to.
      - Certain mods are either broken or outdated. I cannot guarantee that absolutely everything will work.
2. **Open the preloader by running `RUNME.bat`, and follow the first-time set-up instructions that pop up.**
      - The '*import*' tab can be ignored unless you're updating from a super old version of the preloader, or decided not to let the auto-updater update your preloader.
3. **Once the preloader is open, drag and drop your mods anywhere over the window to import them.**

### Step 3: Configuring your mods

1. **The first tab of the preloader is for your particles, on this tab you can mix and match your different particle packs for whatever look you're going for.**
      - If you want even more in-depth customization, instead of the general groups we put the particles into, navigate to the top left of your window, and un-check '*simple particle mode*'.

2. **The second tab of the preloader is everything else, including your models, animations, huds, skins, skyboxes, etc. You first check all the mods you want to use on the left by clicking on the check box next to them, then change the load order on the right by clicking and dragging.**
      - If you have an animation pack, and any model mod, make sure to load your animation pack last!

!!! note
    Some mods you install may contain the same files. When this happens, the preloader displays a caution symbol to warn you about conflicts. To resolve this, place the mod you want to see **HIGHER** in your load order *(bigger number)* so it takes priority. You can hover over the caution symbol to see how many files overlap *(just like Minecraft texture packs!)*.


### Step 4: Installing your mods to TF2

  1. **Don't forget to add `+exec w/config.cfg` to your launch options!**
     - You can do this by going onto the page for your game in Steam. Then, you go to settings, down to properties, then paste the command in your launch options!
  2. **Click install on the bottom right!**

  3. **Launch tf2 and boot up a casual match! You should see all of your mods working.**

## Linux Tutorial:

!!! note
    If you're interested in packaging the casual-pre-loader for your distro, please feel free to open a PR!

### Arch Linux or similar distros
There is an [AUR package](https://aur.archlinux.org/packages/casual-pre-loader-git). After installing, you can run the program with `casual-pre-loader` or through your launcher.  

Settings are stored under `${XDG_CONFIG_HOME}/casual-pre-loader`, defaulting to `~/.config/casual-pre-loader` if `${XDG_CONFIG_HOME}` is unset or empty.

Mod data is stored under `${XDG_DATA_HOME}/casual-pre-loader`, defaulting to `~/.local/share/casual-pre-loader` if `${XDG_DATA_HOME}` is unset or empty.

### Any Linux distro
Ensure that the following dependencies are installed:  
`python3.12+ python-ensurepip python-venv`  
These may be packaged differently depending on the distro.

!!! note
    There is an additional optional dependency on `wine`. If it's installed, it is used to run the windows build of `studiomdl` in order to compile MDL files.  
    (This may be unnecessary in the future if [this PR](https://github.com/craftablescience/sourcepp/pull/85)) gets merged.

You can then download and run the program by cloning the repo:
```sh
git clone --recursive https://github.com/cueki/casual-pre-loader
cd casual-pre-loader
./scripts/run.sh
```
The run script helps set up a virtualenv, if you know what you're doing, you could also just skip the run script and install any required python packages globally.

The program stores settings and mod data under the `userdata/` directory that is created on program launch.  
If you'd rather store user files in the regular per-user locations (like the AUR package does), you can create an empty `.noportable` file in the project's root folder
```sh
touch .noportable
```

!!! warning
    Linux users should use `scripts/run.sh` to launch the application. Do **NOT** run `RUNME.bat` under wine.

### Aditional steps for immutable distros (e.g. SteamOS, Bazzite, etc.)
Since installing packages is quite a hassle on most immutable distros - and usually has some downsides - using something like [`flatpak`](https://flatpak.org/) to install `wine` is recommended.
```sh
flatpak install "$(flatpak remote-ls flathub --app --columns=ref | grep org.winehq.Wine | grep stable | sort -Vr | head -n1)"
```

However, the wine flatpak requires you to invoke it as `flatpak run org.winehq.Wine`, and since the preloader expects a binary named `wine` to be on the `PATH`, we need to put a small script on the `PATH` that just calls the correct invocation.

User scripts that should be on the `PATH` are typically placed in `${XDG_BIN_HOME}`, which should be `~/.local/bin` by default.
To add this directory to the `PATH` if it hasn't already:
```sh
echo 'PATH="${PATH+"${PATH}:"}${XDG_BIN_HOME:="${HOME}/.local/bin"}"' >>~/.bash_profile # or `~/.profile`, or wherever else you set envvars
```

Then we simply create a small wrapper script:
```sh
: "${XDG_BIN_HOME:="${HOME}/.local/bin"}"
mkdir -p "${XDG_BIN_HOME}"
printf '#!/bin/sh\n\nexec flatpak run org.winehq.Wine "${@}"' >"${XDG_BIN_HOME}/wine"
chmod +x "${XDG_BIN_HOME}/wine"
```

!!! note
    Packaging the preloader as a `flatpak` would render all of this unnecessary, [there is already an open issue](https://github.com/cueki/casual-pre-loader/issues/142).


### Additional steps for Ubuntu or derivatives (e.g. Mint, PopOS, etc.)
You may get an error similiar to the following:
```
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
```
Installing `libxcb-cursor-dev` should solve the issue:
```sh
sudo apt-get install -y libxcb-cursor-dev
```

## Video Supplement:
<iframe width="560" height="315" src="https://www.youtube.com/embed/hwQ5XwYG-vE" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
