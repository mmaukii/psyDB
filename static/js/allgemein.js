// Toast-Funktion global verfügbar machen
function showToast(text = "Gespeichert!", durationMs = 2000) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = text;
    toast.classList.add("show");


    if (durationMs !== null) {
        setTimeout(() => {
            toast.classList.remove("show");
        }, durationMs);
    }
}

const APP_TITLE = "psyDB";

function updateBrowserTabTitle(activeTabText = "") {
    const activeNavLink = document.querySelector(".nav-link.active");
    const navTitle = activeNavLink ? activeNavLink.textContent.trim() : "";
    const tabTitle = activeTabText ? activeTabText.trim() : "";

    let title = APP_TITLE;
    if (navTitle && tabTitle) {
        title = `${navTitle} - ${tabTitle}`;
    } else if (navTitle) {
        title = `${navTitle}`;
    } else if (tabTitle) {
        title = `${tabTitle} `;
    }

    document.title = title;
}

// Tab Umschalten
const tabs = document.querySelectorAll(".tab");
const contents = document.querySelectorAll(".tab-content");

tabs.forEach(tab => {
    tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");

        contents.forEach(c => c.classList.remove("active"));
        const content = document.getElementById(tab.dataset.tab);
        if (content) {
            content.classList.add("active");
        }

        updateBrowserTabTitle(tab.textContent);
    });
});


document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll(".nav-link");
    const currentPath = window.location.pathname;

    links.forEach(link => {
        const href = link.getAttribute("href");
        if (href === "/" && currentPath === "/") {
            link.classList.add("active");
        } else if (href !== "/" && currentPath.startsWith(href)) {
            link.classList.add("active");
        }
    });

    const activeTab = document.querySelector(".tab.active");
    updateBrowserTabTitle(activeTab ? activeTab.textContent : "");
});

