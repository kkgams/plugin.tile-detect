{
  description = "GAMS standalone component build toolchain";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/d233902339c02a9c334e7e593de68855ad26c4cb";
    odin-src = {
      url = "github:odin-lang/Odin/db0cd79633fe05069dc4f9248d2796eb8ec3b858";
      flake = false;
    };
    wasm-tools-src = {
      url = "github:bytecodealliance/wasm-tools/v1.248.0";
      flake = false;
    };
    wit-bindgen-src = {
      url = "github:bytecodealliance/wit-bindgen/v0.57.1";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, odin-src, wasm-tools-src, wit-bindgen-src }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          odin = pkgs.odin.overrideAttrs (old: {
            version = "dev-2026-08-db0cd7963";
            src = odin-src;
            # Keep the Nix/Darwin linker purity patch. The unrelated raylib
            # patch from nixpkgs targets an older Odin tree and no longer applies.
            patches = [ (builtins.elemAt old.patches 0) ];
            postPatch = ''
              substituteInPlace src/build_settings.cpp \
                --replace-fail "arm64-apple-macosx" "arm64-apple-darwin"
              substituteInPlace build_odin.sh \
                --replace-fail 'GIT_DATE=$(date +"%Y-%m")' 'GIT_DATE="2026-08"; CPPFLAGS="$CPPFLAGS -DGIT_SHA=\"db0cd7963\""'
              patchShebangs --build build_odin.sh
            '';
            installPhase = ''
              runHook preInstall
              mkdir -p "$out/bin" "$out/share"
              cp odin "$out/bin/odin"
              cp -R base core vendor shared "$out/share/"
              wrapProgram "$out/bin/odin" \
                --prefix PATH : "${pkgs.lib.makeBinPath (with pkgs.llvmPackages; [ bintools llvm clang lld ])}" \
                --set-default ODIN_ROOT "$out/share"
              runHook postInstall
            '';
          });
          toolArtifacts = {
            aarch64-darwin = {
              platform = "aarch64-macos";
              wasm-tools = "sha256-TgPp40IXapxS4MJblwfH+Ana6w9JhnQiWMaXSWge/nk=";
              wit-bindgen = "sha256-QYU9Jbu86oSuLn83T45pHUIlx8qLDbe46U2VzjJZF04=";
            };
            x86_64-darwin = {
              platform = "x86_64-macos";
              wasm-tools = "sha256-GIVowpkLtMCaCTbYS/tiVRmfl+SETNRfQYtZw9Yjh4g=";
              wit-bindgen = "sha256-ElIqY9rxBn1IHEG9fkyWTnmdtP8XsmTu1mPk5EO5K5g=";
            };
            aarch64-linux = {
              platform = "aarch64-linux";
              wasm-tools = "sha256-y3o656ea6z282x0G7t6nu0Xm1ceiHpYOFORdWCsrn5c=";
              wit-bindgen = "sha256-gypI+MF4JsdZd5Y3MuZpWePNov/+WdA8MtepQ/G2lP8=";
            };
            x86_64-linux = {
              platform = "x86_64-linux";
              wasm-tools = "sha256-3NfVh7D0ZEqryFzURxy3ld6E82po7gEgHVJh+HwNY0k=";
              wit-bindgen = "sha256-/5Wy2vQP5Og/MOvH4S6RnJqWRA8yu4fUkV6K5emK8vM=";
            };
          };
          toolArtifact = toolArtifacts.${system};
          linuxPatching = {
            nativeBuildInputs = pkgs.lib.optionals pkgs.stdenv.isLinux [ pkgs.autoPatchelfHook ];
            # SDK 33 bundles libedit.so, which needs libtinfo.so.6 on Linux.
            # Keep autoPatchelf strict: supply the library rather than ignoring it.
            buildInputs = pkgs.lib.optionals pkgs.stdenv.isLinux [ pkgs.stdenv.cc.cc.lib pkgs.ncurses.out ];
          };
          mkReleaseTool = { pname, version, hash }:
            pkgs.stdenvNoCC.mkDerivation (linuxPatching // {
              inherit pname version;
              src = pkgs.fetchurl {
                url = "https://github.com/bytecodealliance/${pname}/releases/download/v${version}/${pname}-${version}-${toolArtifact.platform}.tar.gz";
                inherit hash;
              };
              sourceRoot = ".";
              installPhase = ''
                tool_dir=$(find . -mindepth 1 -maxdepth 1 -type d -name '${pname}-*' -print -quit)
                test -n "$tool_dir"
                mkdir -p "$out/bin"
                install -m755 "$tool_dir/${pname}" "$out/bin/${pname}"
              '';
            });
          wasm-tools = mkReleaseTool {
            pname = "wasm-tools";
            version = "1.248.0";
            hash = toolArtifact.wasm-tools;
          };
          wit-bindgen = mkReleaseTool {
            pname = "wit-bindgen";
            version = "0.57.1";
            hash = toolArtifact.wit-bindgen;
          };
          wasiArtifacts = {
            aarch64-darwin = {
              platform = "arm64-macos";
              hash = "sha256-hcmXomZerZFnO1u4i30N8/yJAN87+iRPcg1HgYe73Hg=";
            };
            x86_64-darwin = {
              platform = "x86_64-macos";
              hash = "sha256-GPPyAbqXNOakRVsLZBBpA5WlXp/6n29QZvZgg6lLk7M=";
            };
            aarch64-linux = {
              platform = "arm64-linux";
              hash = "sha256-T5juc4x6u0XIGpTRRh/FPMVp0c0BSYlRyBhNhBoCeEQ=";
            };
            x86_64-linux = {
              platform = "x86_64-linux";
              hash = "sha256-C6i1v66yrfPym6tYQdds9TGKuOFkLqGV+IuroavUe84=";
            };
          };
          wasiArtifact = wasiArtifacts.${system};
          wasi-sdk = pkgs.stdenvNoCC.mkDerivation (linuxPatching // {
            pname = "wasi-sdk";
            version = "33.0";
            src = pkgs.fetchurl {
              url = "https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-33/wasi-sdk-33.0-${wasiArtifact.platform}.tar.gz";
              hash = wasiArtifact.hash;
            };
            sourceRoot = ".";
            installPhase = ''
              runHook preInstall
              sdk_dir=$(find . -mindepth 1 -maxdepth 1 -type d -name 'wasi-sdk-*' -print -quit)
              test -n "$sdk_dir"
              mkdir -p "$out"
              cp -R "$sdk_dir"/. "$out"/
              runHook postInstall
            '';
          });
        in {
          default = pkgs.mkShell {
            packages = [ odin wasm-tools wit-bindgen wasi-sdk pkgs.go_1_25 pkgs.tinygo pkgs.nodejs_24 pkgs.gnumake pkgs.coreutils pkgs.python3 pkgs.bash ];
            shellHook = ''
              export WASI_SDK_PATH="${wasi-sdk}"
              export WASI_SYSROOT="$WASI_SDK_PATH/share/wasi-sysroot"
              export PATH="$PATH:$WASI_SDK_PATH/bin"
            '';
          };
        });
    };
}
