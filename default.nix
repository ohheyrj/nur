
{ pkgs ? import <nixpkgs> { } }:

let
  inherit (pkgs) lib stdenv;

  # Helper to find all default.nix files in ./pkgs
  discoverPackages = dir:
    lib.pipe (builtins.readDir dir) [
      (lib.filterAttrs (_: type: type == "directory"))
      (lib.mapAttrsToList (name: _: 
        let path = "${dir}/${name}/default.nix";
        in if builtins.pathExists path then { inherit name path; } else null))
      (lib.filter (x: x != null))
    ];

  # Load and optionally skip non-darwin packages
  loadPackages = packages:
    lib.genAttrs (map (x: x.name) packages) (name:
      let drv = pkgs.callPackage (builtins.getAttr name (lib.genAttrs (map (x: x.name) packages) (n: builtins.getAttr n (lib.listToAttrs packages)))) {};
      in if lib.elem stdenv.hostPlatform.system drv.meta.platforms or [ ] then drv else null
    );

  packageDirs = discoverPackages ./pkgs;
  loaded = loadPackages packageDirs;
in
{
  lib = import ./lib { inherit pkgs; };
  modules = import ./modules;
  overlays = import ./overlays;
} // lib.filterAttrs (_: v: v != null) loaded

