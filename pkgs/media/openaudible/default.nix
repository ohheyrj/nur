{
  lib,
  stdenvNoCC,
  undmg,
  versionCheckHook,
  xcbuild,
  writeShellScript,
  _7zz,
  config,
  generated
}:

stdenvNoCC.mkDerivation (finalAttrs:{
  inherit (generated) pname version src;

  dontUnpack = true;

  buildInputs = [ _7zz ];

  sourceRoot = ".";

  installPhase = ''
    runHook preInstall
    7zz x $src 'OpenAudible/OpenAudible.app' -o$TMPDIR

    mkdir -p $out/Applications
    mv $TMPDIR/OpenAudible/OpenAudible.app $out/Applications
  '';

  nativeInstallCheckInputs = [ versionCheckHook ];
  versionCheckProgram = writeShellScript "version-check" ''
    ${xcbuild}/bin/PlistBuddy -c "Print :CFBundleShortVersionString" "$1"
  '';
  versionCheckProgramArg = [
    "${placeholder "out"}/Applications/OpenAudible.app/Contents/Info.plist"
  ];
  doInstallCheck = true;

  meta = {
    homepage = "https://openaudible.org/";
    changelog = "https://openaudible.org/versions";
    description = "OpenAudible is a cross-platform desktop app that lets Audible users download, convert, and manage their audiobooks in MP3 or M4B formats for offline listening.";
    license = lib.licenses.asl20;
    platforms = lib.platforms.darwin;
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
    broken = !(config.allowUnfree or false);
  };
}
)
