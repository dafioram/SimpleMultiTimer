// Shared helpers for index.html and history.html.
// Loaded as a classic script, so everything here is a global.

const STORAGE_KEYS = ["timers", "history"];

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
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) throw new Error("Expected an array");
        return parsed;
    } catch (err) {
        console.error(`Corrupted "${key}" data:`, err);
        // Preserve the bad data instead of silently discarding it
        localStorage.setItem(`${key}_corrupted_${Date.now()}`, raw);
        localStorage.removeItem(key);
        showToast(`Your saved ${key} was corrupted and has been reset. A backup was kept.`, true);
        return [];
    }
}

async function ensurePersistentStorage() {
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
