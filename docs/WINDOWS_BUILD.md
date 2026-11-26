# Building Cromite for Windows x64

This branch targets Chromium `159.0.8154.34` on Windows x64. All 301 Windows-relevant patches have been checked and applied in order against the pinned sources. Compiling and launching the Windows executable still require a native test.

## Install the toolchain

Use a 64-bit Windows 10 or 11 machine and an NTFS SSD with at least 100 GB free. Chromium recommends more than 16 GB of RAM. Install Git for Windows and **Visual Studio 2026 (18.0 or later) or its standalone Build Tools**. Select the MSVC x64/x86 tools, ATL and MFC. For the Build Tools bootstrapper, use:

```bat
vs_BuildTools.exe --wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.VC.ATL --add Microsoft.VisualStudio.Component.VC.ATLMFC
```

Chromium uses **Windows 11 SDK 10.0.28000.2270** and **Debugging Tools for Windows 10.0.26100.3323 or newer**. A standalone SDK installation can supply both. Check the SDK's **Debugging Tools for Windows** component. Chromium downloads clang-cl and its build tools during source setup.

[Chromium Windows build instructions for this exact tag](https://github.com/chromium/chromium/blob/159.0.8154.34/docs/windows_build_instructions.md)

## Fetch the pinned sources

Run the following in **cmd.exe**. The example uses `C:\src` for a short checkout path. The Git settings below apply to this shell and its child processes.

```bat
mkdir C:\src
cd /d C:\src
set "GIT_CONFIG_COUNT=2"
set "GIT_CONFIG_KEY_0=core.autocrlf"
set "GIT_CONFIG_VALUE_0=false"
set "GIT_CONFIG_KEY_1=core.longpaths"
set "GIT_CONFIG_VALUE_1=true"
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
git clone --single-branch --branch windows-159.0.8154.34 https://github.com/iGom/cromite.git
set "PATH=C:\src\depot_tools;%PATH%"
set "DEPOT_TOOLS_WIN_TOOLCHAIN=0"
call gclient

mkdir C:\src\chromium
cd /d C:\src\chromium
call gclient config --name=src --custom-var=checkout_pgo_profiles=True https://chromium.googlesource.com/chromium/src.git
call gclient sync --no-history --revision src@4deb883708d3d25100c5aac2148aafc95dae95ac
```

The revision is the commit for the Chromium tag. The PGO setting fetches the profiles selected by its DEPS hooks, including the Win64 profile needed by the Cromite GN settings.

## Check and apply the series

```bat
cd /d C:\src\chromium\src
call python3 C:\src\cromite\tools\apply-windows-patches.py check .
```

The native check and apply commands use the same Windows file selection. They retain shared build files, resources and Cromite flags, and skip Android and iOS implementation files. The check replays every applicable patch on temporary copies, including affected files in V8, Skia, DevTools and BoringSSL. An error names the patch to port. You can update the Cromite branch and repeat the check on the same Chromium checkout.

## Compile after the check passes

Use the same command prompt. The first command repeats the check before applying the series to your working tree. Run the subsequent commands only after it succeeds.

```bat
call python3 C:\src\cromite\tools\apply-windows-patches.py apply .
```

```bat
if not exist out\Cromite mkdir out\Cromite
(echo target_os = "win"& echo target_cpu = "x64"& type C:\src\cromite\build\cromite.gn_args)> out\Cromite\args.gn
call gn gen out\Cromite && call autoninja -C out\Cromite chrome
```

A successful build produces `out\Cromite\chrome.exe` with its DLLs, resources and locales alongside it. To read the executable's version in PowerShell, run `(Get-Item .\out\Cromite\chrome.exe).VersionInfo.ProductVersion`.
