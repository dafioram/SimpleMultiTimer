# Simple Multi Timer

Track time across several activities. One set of files runs two ways:

| | Where | Data stored in |
|---|---|---|
| **PWA** (desktop, any browser) | GitHub Pages serves the repo root | Browser storage (`localStorage`) |
| **Android app** | APK built by GitHub Actions with [Capacitor](https://capacitorjs.com) | The app's private storage ([Preferences](https://capacitorjs.com/docs/apis/preferences)); only removed by uninstalling or "Clear storage" |

The app code is the same in both. `common.js` checks whether it's running
inside the Android app and picks the storage, keep-screen-on and export
method to match.

## PWA

Nothing to build: GitHub Pages publishes `index.html`, `history.html`,
`common.js`, `sw.js`, `manifest.json` and `icons/` as they are.

## Android app

Every push to `static-app` (and every pull request) runs the
**Android app** workflow. Download the APK from the run's *Artifacts*
section and open it on your phone (allow installs from that source once).

### One-time: signing key

Android only installs an update if it's signed with the same key as the
installed app. Uninstalling to get around a key mismatch deletes the app's
data, so set up one key and keep it:

```sh
keytool -genkeypair -v -keystore my-timer.jks -alias my-timer \
  -keyalg RSA -keysize 2048 -validity 10000
base64 -w0 my-timer.jks   # macOS: base64 -i my-timer.jks
```

Then in the repo's **Settings → Secrets and variables → Actions** add:

- `ANDROID_KEYSTORE_BASE64`: the base64 output
- `ANDROID_KEYSTORE_PASSWORD`: the keystore password
- `ANDROID_KEY_ALIAS`: `my-timer`
- `ANDROID_KEY_PASSWORD`: the key password (often the same)

Back up `my-timer.jks` and its password somewhere safe. Without the
secrets the workflow still builds, but with a throwaway debug key that
changes every run.

### Building locally

Needs Node 22, JDK 21 and the Android SDK (e.g. via Android Studio):

```sh
npm ci
npm run android:add      # generates android/ (git-ignored)
cd android && ./gradlew assembleDebug
```

After changing the web files, `npm run android:sync` copies them into the
Android project.

### Moving data from the PWA to the app

The app and the PWA keep separate data. In the PWA use **Export**, then
**Import** that file in the app.
