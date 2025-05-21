{ pkgs ? import <nixpkgs> {} }:

{
  __functor = self: pkgs:
    let
      # Helper to reduce repetition
      callPackage = pkgs.callPackage;
    in
    {
      # The `lib`, `modules`, and `overlays` names are special
      lib = import ./lib { inherit pkgs; }; # functions
      modules = import ./modules;           # NixOS modules
      overlays = import ./overlays;         # nixpkgs overlays

      chatterino = callPackage ./pkgs/chat/chatterino {};
    };
}

