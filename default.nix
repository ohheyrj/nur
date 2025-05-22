
{ pkgs ? import <nixpkgs> {} }:

let
  inherit (pkgs) lib stdenv;

  sharedOverrides = {
    versionCheckHook = pkgs.versionCheckHook;
    _7zz = pkgs._7zz or pkgs.sevenZip;
    writeShellScript = pkgs.writeShellScriptBin or pkgs.writeShellScript;
    xcbuild = pkgs.xcbuild;
  };

  maybeEnable = drv:
    if lib.elem stdenv.hostPlatform.system (drv.meta.platforms or []) then drv else null;

  openaudible = maybeEnable (pkgs.callPackage ./pkgs/media/openaudible sharedOverrides);
  chatterino  = maybeEnable (pkgs.callPackage ./pkgs/chat/chatterino {});
  kobo-desktop = maybeEnable (pkgs.callPackage ./pkgs/media/kobo-desktop sharedOverrides);

in {
  lib = import ./lib { inherit pkgs; };
  modules = import ./modules;
  overlays = import ./overlays;
} // lib.filterAttrs (_: v: v != null) {
  inherit openaudible chatterino kobo-desktop;
}

