#!/bin/zsh
set -euo pipefail
: "${FSTR_AE_SDK_ROOT:?Set FSTR_AE_SDK_ROOT to the extracted AE 25.6 SDK}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(git -C "$ROOT" rev-parse --short HEAD)-$$"
OUT="$ROOT/.artifacts/command-probe/$BUILD_ID"
mkdir -p "$OUT/sdk-workspace/AEGP"
for directory in Headers Util Resources; do
  cp -R "$FSTR_AE_SDK_ROOT/Examples/$directory" "$OUT/sdk-workspace/$directory"
done
cp -R "$FSTR_AE_SDK_ROOT/Examples/AEGP/Commando" "$OUT/sdk-workspace/AEGP/Commando"
PROBE="$OUT/sdk-workspace/AEGP/Commando"
/usr/libexec/PlistBuddy -c 'Set :CFBundleExecutable FSTRCommandProbe' "$PROBE/Mac/Commando.plugin-Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleName FSTR Command Probe' "$PROBE/Mac/Commando.plugin-Info.plist"
/usr/libexec/PlistBuddy -c 'Delete :NSHumanReadableCopyright' "$PROBE/Mac/Commando.plugin-Info.plist"
cp "$ROOT/native/command-probe/CommandProbe.cpp" "$PROBE/Commando.cpp"
cp "$ROOT/native/command-probe/CommandProbe.h" "$PROBE/CommandProbe.h"
cp "$ROOT/native/command-probe/CommandProbe_PiPL.r" "$PROBE/Commando_PiPL.r"
print "#define FSTR_PROBE_BUILD_ID \"$BUILD_ID\"" > "$PROBE/ProbeBuild.h"
git -C "$ROOT" rev-parse HEAD > "$OUT/source-commit.txt"
git -C "$ROOT" status --short > "$OUT/source-state.txt"
shasum -a 256 "$ROOT"/native/command-probe/* "$0" > "$OUT/source-sha256.txt"
xcodebuild -version > "$OUT/toolchain.txt"
xcodebuild -project "$PROBE/Mac/Commando.xcodeproj" -configuration Debug -target Commando \
  SYMROOT="$OUT/build" OBJROOT="$OUT/obj" build CODE_SIGNING_ALLOWED=NO \
  PRODUCT_BUNDLE_IDENTIFIER=com.ios3kov.fstrline.commandprobe PRODUCT_NAME=FSTRCommandProbe \
  ARCHS=arm64 ONLY_ACTIVE_ARCH=YES MACOSX_DEPLOYMENT_TARGET=12.0 CLANG_CXX_LANGUAGE_STANDARD=c++17 \
  > "$OUT/xcodebuild.log" 2>&1 || { cat "$OUT/xcodebuild.log"; exit 1; }
PLUGIN="$OUT/build/Debug/FSTRCommandProbe.plugin"
codesign --force --sign - "$PLUGIN"
codesign --verify --strict "$PLUGIN"
nm -gU "$PLUGIN/Contents/MacOS/FSTRCommandProbe" | grep ' _EntryPointFunc$'
file "$PLUGIN/Contents/MacOS/FSTRCommandProbe"
ditto -c -k --keepParent "$PLUGIN" "$OUT/FSTRCommandProbe.zip"
shasum -a 256 "$OUT/FSTRCommandProbe.zip" > "$OUT/SHA256.txt"
print "Build ID: $BUILD_ID"
print "Artifact: $PLUGIN"
