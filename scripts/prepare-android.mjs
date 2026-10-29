// Customizes the Android project that `npx cap add android` generates:
// the app icon, a dark launch screen instead of Capacitor's logo, and the
// version number. Run after `cap add android`, before building.
//
//   VERSION_CODE=42 node scripts/prepare-android.mjs
import { copyFileSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";

const res = "android/app/src/main/res";
const BACKGROUND = "#121212";

function edit(file, replacements) {
    let text = readFileSync(file, "utf8");
    for (const [from, to] of replacements) {
        if (!text.includes(from)) throw new Error(`${file}: expected to find ${from}`);
        text = text.replace(from, to);
    }
    writeFileSync(file, text);
}

// Icon: use the PWA icon at every density. Removing the adaptive-icon XML
// makes Android use these PNGs instead of Capacitor's default icon.
rmSync(`${res}/mipmap-anydpi-v26`, { recursive: true, force: true });
for (const dir of readdirSync(res).filter(d => d.startsWith("mipmap-"))) {
    for (const name of ["ic_launcher.png", "ic_launcher_round.png"]) {
        copyFileSync("icons/icon-192.png", `${res}/${dir}/${name}`);
    }
}

// Launch screen: the app's dark background rather than Capacitor's splash image.
edit(`${res}/values/styles.xml`, [[
    `<item name="android:background">@drawable/splash</item>`,
    `<item name="android:background">${BACKGROUND}</item>\n        <item name="windowSplashScreenBackground">${BACKGROUND}</item>`
]]);

// Version: Android only installs an update over the existing app if the
// version code doesn't go down, so CI passes its run number. Release builds
// pass VERSION_NAME (the tag without its "v"); other builds show the
// package.json version plus the build number.
const versionCode = Number(process.env.VERSION_CODE || 1);
const pkg = JSON.parse(readFileSync("package.json", "utf8"));
const versionName = process.env.VERSION_NAME || `${pkg.version}.${versionCode}`;
edit("android/app/build.gradle", [
    ["versionCode 1", `versionCode ${versionCode}`],
    [`versionName "1.0"`, `versionName "${versionName}"`]
]);

console.log(`Android project prepared (version ${versionName}, code ${versionCode})`);
