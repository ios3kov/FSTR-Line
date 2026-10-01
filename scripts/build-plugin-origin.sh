#!/bin/zsh
set -euo pipefail
: "${FSTR_AE_SDK_ROOT:?Set FSTR_AE_SDK_ROOT to the extracted AE 25.6 SDK}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
test -z "$(git -C "$ROOT" status --porcelain)" || { echo "Dirty source: build refused" >&2; exit 2; }
COMMIT="$(git -C "$ROOT" rev-parse HEAD)"
BUILD_ID="fstr-plugin-origin-${COMMIT[1,12]}-$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$ROOT/.artifacts/plugin-origin/$BUILD_ID"
mkdir -p "$OUT/sdk-workspace/AEGP"
for directory in Headers Util Resources; do
  cp -R "$FSTR_AE_SDK_ROOT/Examples/$directory" "$OUT/sdk-workspace/$directory"
done
cp -R "$FSTR_AE_SDK_ROOT/Examples/AEGP/Commando" "$OUT/sdk-workspace/AEGP/Commando"
PROBE="$OUT/sdk-workspace/AEGP/Commando"
/usr/libexec/PlistBuddy -c 'Set :CFBundleExecutable FSTRPluginOrigin' "$PROBE/Mac/Commando.plugin-Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleName FSTR Plugin Origin Probe' "$PROBE/Mac/Commando.plugin-Info.plist"
/usr/libexec/PlistBuddy -c 'Delete :NSHumanReadableCopyright' "$PROBE/Mac/Commando.plugin-Info.plist" 2>/dev/null || true
cp "$ROOT/native/plugin-origin/PluginOrigin.cpp" "$PROBE/Commando.cpp"
cp "$ROOT/native/plugin-origin/PluginOrigin.h" "$PROBE/PluginOrigin.h"
cp "$ROOT/native/plugin-origin/PluginOrigin_PiPL.r" "$PROBE/Commando_PiPL.r"
print "#define FSTR_PLUGIN_ORIGIN_BUILD_ID \"$BUILD_ID\"" > "$PROBE/PluginOriginBuild.h"
git -C "$ROOT" rev-parse HEAD > "$OUT/source-commit.txt"
shasum -a 256 "$ROOT"/native/plugin-origin/* "$0" > "$OUT/source-sha256.txt"
xcodebuild -version > "$OUT/toolchain.txt"
xcodebuild -project "$PROBE/Mac/Commando.xcodeproj" -configuration Debug -target Commando \
  SYMROOT="$OUT/build" OBJROOT="$OUT/obj" build CODE_SIGNING_ALLOWED=NO \
  PRODUCT_BUNDLE_IDENTIFIER=com.ios3kov.fstrline.pluginorigin PRODUCT_NAME=FSTRPluginOrigin \
  ARCHS=arm64 ONLY_ACTIVE_ARCH=YES MACOSX_DEPLOYMENT_TARGET=12.0 CLANG_CXX_LANGUAGE_STANDARD=c++17 \
  > "$OUT/xcodebuild.log" 2>&1 || { cat "$OUT/xcodebuild.log"; exit 1; }
PLUGIN="$OUT/build/Debug/FSTRPluginOrigin.plugin"
mkdir -p "$PLUGIN/Contents/Resources"
cat > "$PLUGIN/Contents/Resources/FSTRPluginOriginBuild.json" <<JSON
{"buildId":"$BUILD_ID","sourceCommit":"$COMMIT","targetAE":"25.6.0.101","diagnosticOnly":true}
JSON
codesign --force --sign - "$PLUGIN"
codesign --verify --strict "$PLUGIN"
nm -gU "$PLUGIN/Contents/MacOS/FSTRPluginOrigin" | grep ' _EntryPointFunc$'
file "$PLUGIN/Contents/MacOS/FSTRPluginOrigin"
ditto -c -k --keepParent "$PLUGIN" "$OUT/FSTRPluginOrigin.zip"
shasum -a 256 "$OUT/FSTRPluginOrigin.zip" > "$OUT/SHA256.txt"
print "Build ID: $BUILD_ID"
print "Artifact: $PLUGIN"
