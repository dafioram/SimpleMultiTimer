// Shared helpers for index.html and history.html.
// Loaded as a classic script, so everything here is a global.

const STORAGE_KEYS = ["timers", "history"];

// True inside the Android app (Capacitor), false in a browser or the PWA.
const isNativeApp = !!window.Capacitor?.isNativePlatform?.();

// Calls a Capacitor plugin method. The native bridge is injected into every
// page of the app, so no bundler or plugin JS is needed.
function callNative(plugin, method, options = {}) {
    return window.Capacitor.nativePromise(plugin, method, options);
}

// --- Storage -------------------------------------------------------------
// Browser/PWA: localStorage, read and written directly.
// Android app: the app's own private storage (Capacitor Preferences), which
// Chrome can't clear. It's read once into memory by initStorage(), so the
// rest of the code can stay synchronous; writes update memory immediately
// and are saved in the background, in order.
const nativeCache = new Map();
let nativeWrites = Promise.resolve();

async function initStorage() {
    if (!isNativeApp) return;
    for (const key of STORAGE_KEYS) {
        const { value } = await callNative("Preferences", "get", { key });
        if (value != null) nativeCache.set(key, value);
    }
}

function queueNativeWrite(method, options) {
    nativeWrites = nativeWrites
        .then(() => callNative("Preferences", method, options))
        .catch(err => {
            console.error(err);
            showToast("❌ Couldn't save your data.", true);
        });
}

function readItem(key) {
    return isNativeApp ? (nativeCache.get(key) ?? null) : localStorage.getItem(key);
}

function writeItem(key, value) {
    if (!isNativeApp) return localStorage.setItem(key, value);
    nativeCache.set(key, value);
    queueNativeWrite("set", { key, value });
}

function removeItem(key) {
    if (!isNativeApp) return localStorage.removeItem(key);
    nativeCache.delete(key);
    queueNativeWrite("remove", { key });
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// Formats milliseconds as HH:MM:SS, keeping the sign for negative values.
function formatTime(ms = 0) {
    ms = Number(ms) || 0;
    const sign = ms < 0 ? "-" : "";
    const total = Math.floor(Math.abs(ms) / 1000);
    const h = String(Math.floor(total / 3600)).padStart(2, "0");
    const m = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
    const s = String(total % 60).padStart(2, "0");
    return `${sign}${h}:${m}:${s}`;
}

function showToast(message, isError = false) {
    const toast = document.createElement("div");
    toast.className = `toast${isError ? " error" : ""}`;
    toast.setAttribute("role", "status");
    toast.textContent = message;

    document.body.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add("show");
    });

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

function loadState(key) {
    const raw = readItem(key);
    if (!raw) return [];
    try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) throw new Error("Expected an array");
        return parsed;
    } catch (err) {
        console.error(`Corrupted "${key}" data:`, err);
        // Preserve the bad data instead of silently discarding it
        writeItem(`${key}_corrupted_${Date.now()}`, raw);
        removeItem(key);
        showToast(`Your saved ${key} was corrupted and has been reset. A backup was kept.`, true);
        return [];
    }
}

async function ensurePersistentStorage() {
    // The Android app's storage is already permanent.
    if (isNativeApp) return;
    if (navigator.storage?.persist) {
        const already = await navigator.storage.persisted();
        if (!already) await navigator.storage.persist();
    }
}

// Calls `callback` when another tab changes timers or history.
// (The storage event never fires in the tab that made the change.)
function onStoredDataChange(callback) {
    window.addEventListener("storage", event => {
        // event.key is null when another tab calls localStorage.clear()
        if (event.key === null || STORAGE_KEYS.includes(event.key)) callback();
    });
}

// Keeps the screen on while `wanted` is true. In the browser the wake lock is
// dropped whenever the page is hidden, so it's re-requested on return.
let keepAwakeWanted = false;
let wakeLock = null;
let wakeLockPending = false;

function setKeepAwake(wanted) {
    if (isNativeApp) {
        if (wanted === keepAwakeWanted) return;
        keepAwakeWanted = wanted;
        callNative("KeepAwake", wanted ? "keepAwake" : "allowSleep").catch(console.warn);
        return;
    }
    keepAwakeWanted = wanted;
    syncWakeLock();
}

async function syncWakeLock() {
    if (!("wakeLock" in navigator) || wakeLockPending) return;
    const wanted = () => keepAwakeWanted && document.visibilityState === "visible";

    if (wanted() && !wakeLock) {
        wakeLockPending = true;
        try {
            const lock = await navigator.wakeLock.request("screen");
            lock.addEventListener("release", () => { if (wakeLock === lock) wakeLock = null; });
            wakeLock = lock;
        } catch (err) {
            // e.g. battery saver is on; the timers still work without it
            console.warn("Wake lock unavailable:", err);
        } finally {
            wakeLockPending = false;
        }
        // Timers may have stopped while we were waiting
        if (!wanted()) syncWakeLock();
    } else if (!wanted() && wakeLock) {
        const lock = wakeLock;
        wakeLock = null;
        lock.release();
    }
}

if (!isNativeApp) document.addEventListener("visibilitychange", syncWakeLock);

// Saves `text` as a file the user keeps: a download in the browser, the
// share sheet (Files, Drive, email...) in the Android app. Resolves to
// false if the user closed the share sheet without saving.
async function saveTextFile(filename, text) {
    if (isNativeApp) {
        const { uri } = await callNative("Filesystem", "writeFile", {
            path: filename,
            data: text,
            directory: "CACHE",
            encoding: "utf8"
        });
        try {
            await callNative("Share", "share", { title: filename, files: [uri] });
        } catch (err) {
            // Closing the share sheet without picking anything isn't an error
            if (/cancel/i.test(err?.message)) return false;
            throw err;
        }
        return true;
    }

    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return true;
}

// Registers the offline service worker (browser/PWA only; the Android app
// ships its files inside the app).
function registerServiceWorker() {
    if (isNativeApp || !("serviceWorker" in navigator)) return;
    // Strip trailing slashes or /page.html to get the clean base directory
    const basePath = window.location.pathname.replace(/\/[^/]*\.html$/, '').replace(/\/$/, '');
    navigator.serviceWorker.register(`${basePath}/sw.js`, {
        scope: `${basePath}/`
    }).catch(console.error);
}
