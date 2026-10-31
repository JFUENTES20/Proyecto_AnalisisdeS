(() => {
    "use strict";

    const button = document.querySelector(".menu-toggle");
    const nav = document.getElementById("navegacion-principal");
    if (!button || !nav) return;

    const narrow = window.matchMedia("(max-width: 800px)");
    const header = button.closest("header");
    let expanded = false;

    function render() {
        const open = narrow.matches && expanded;
        nav.hidden = narrow.matches && !open;
        button.setAttribute("aria-expanded", String(open));
        button.setAttribute("aria-label", open ? "Cerrar menú de navegación" : "Abrir menú de navegación");
    }

    function close(restoreFocus = false) {
        if (!expanded) return;
        expanded = false;
        render();
        if (restoreFocus) button.focus();
    }

    button.addEventListener("click", () => {
        expanded = !expanded;
        render();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && expanded) {
            event.preventDefault();
            close(true);
        }
    });

    nav.addEventListener("click", (event) => {
        const link = event.target.closest("a");
        if (!link || !narrow.matches) return;
        close();
        // Un enlace a la misma página debe dejar el foco en su destino, no oculto.
        const destination = new URL(link.href);
        if (destination.pathname === location.pathname && destination.hash) {
            const target = document.getElementById(destination.hash.slice(1));
            if (target) {
                if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
                target.focus({ preventScroll: true });
            }
        }
    });

    document.addEventListener("click", (event) => {
        if (!header.contains(event.target)) close();
    });

    header.addEventListener("focusout", (event) => {
        if (event.relatedTarget && !header.contains(event.relatedTarget)) close();
    });

    narrow.addEventListener("change", () => {
        const focusInNav = nav.contains(document.activeElement);
        const focusOnButton = document.activeElement === button;
        expanded = false;
        render();
        if (narrow.matches && focusInNav) button.focus();
        if (!narrow.matches && focusOnButton) nav.querySelector("a").focus();
    });

    // Sin JavaScript, los enlaces siguen visibles y el botón no se presenta.
    render();
    button.hidden = false;
})();
