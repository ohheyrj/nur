
{ pkgs ? import <nixpkgs> {} }:

let
  inherit (pkgs) lib stdenv;

  maybeEnable = drv:
    if lib.elem stdenv.hostPlatform.system (drv.meta.platforms or []) then drv else null;

  openaudible = maybeEnable (pkgs.callPackage ./pkgs/media/openaudible {});
  chatterino  = maybeEnable (pkgs.callPackage ./pkgs/chat/chatterino {});
  kobo-desktop = maybeEnable (pkgs.callPackage ./pkgs/media/kobo-desktop {});

in {
  lib = import ./lib { inherit pkgs; };
  modules = import ./modules;
  overlays = import ./overlays;
} // lib.filterAttrs (_: v: v != null) {
  inherit openaudible chatterino kobo-desktop;
}

