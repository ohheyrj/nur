{ pkgs ? import <nixpkgs> {} }:

let
  inherit (pkgs) lib stdenv;

  # Shared overrides to inject into every package
  sharedOverrides = {
    versionCheckHook = pkgs.versionCheckHook;
    writeShellScript = pkgs.writeShellScriptBin or pkgs.writeShellScript;
    xcbuild = pkgs.xcbuild;
  };

  # Function to recursively find all default.nix files in pkgs/
  findPackages = dir:
    let
      contents = builtins.readDir dir;
      
      # Find all subdirectories
      subdirs = lib.filterAttrs (name: type: type == "directory") contents;
      
      # Check if current directory has a default.nix (making it a package)
      hasDefault = contents ? "default.nix";
      
      # Recursively search subdirectories
      subPackages = lib.concatMapAttrs (name: _: 
        lib.mapAttrs' (subName: subPath: 
          lib.nameValuePair "${name}-${subName}" subPath
        ) (findPackages (dir + "/${name}"))
      ) subdirs;
      
    in
      if hasDefault then
        # This directory is a package
        { ${baseNameOf (toString dir)} = dir; } // subPackages
      else
        # This directory is not a package, just return subdirectory results
        subPackages;

  # Discover all packages in pkgs/
  discoveredPackages = findPackages ./pkgs;

  # Function to safely get platforms from a package
  getPlatforms = name: path:
    let
      # Try to import and evaluate the package to get its meta.platforms
      tryEval = builtins.tryEval (
        let
          packageFn = import path;
          # Call with pkgs + overrides to get the derivation
          evalPkg = pkgs.callPackage packageFn sharedOverrides;
        in
          evalPkg.meta.platforms or []
      );
    in
      if tryEval.success then
        tryEval.value
      else
        # Fallback: if we can't evaluate, assume it's Darwin-only based on your current setup
        [ "x86_64-darwin" "aarch64-darwin" ];

  # Filter packages based on current platform
  compatiblePackages = lib.filterAttrs (name: path:
    let platforms = getPlatforms name path;
    in lib.elem stdenv.hostPlatform.system platforms
  ) discoveredPackages;

  # Build the compatible packages using callPackage with shared overrides
  builtPackages = lib.mapAttrs (name: path:
    pkgs.callPackage path sharedOverrides
  ) compatiblePackages;

in {
  lib = import ./lib { inherit pkgs; };
  modules = import ./modules;
  overlays = import ./overlays;
} // builtPackages
