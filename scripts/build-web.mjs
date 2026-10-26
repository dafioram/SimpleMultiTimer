// Copies the web app into www/, the folder Capacitor bundles into the
// Android app. GitHub Pages keeps serving the same files from the repo root.
import { cpSync, rmSync } from "node:fs";

const FILES = ["index.html", "history.html", "common.js", "manifest.json", "icons"];

rmSync("www", { recursive: true, force: true });
for (const file of FILES) {
    cpSync(file, `www/${file}`, { recursive: true });
}
console.log(`Copied ${FILES.join(", ")} to www/`);
