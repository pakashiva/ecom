(() => {
    const body = document.body;
    if (body.dataset.demoMode !== "true") return;

    const cards = Array.from(document.querySelectorAll(".product-card"));
    const pageSize = 8;
    const params = new URLSearchParams(window.location.search);
    const selectedCategory = params.get("category") || "All";
    const filtered = cards.filter((card) =>
        selectedCategory === "All" || card.dataset.category === selectedCategory
    );
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    const requestedPage = Number.parseInt(params.get("page") || "1", 10);
    const currentPage = Math.min(Math.max(requestedPage || 1, 1), totalPages);

    cards.forEach((card) => { card.hidden = true; });
    filtered
        .slice((currentPage - 1) * pageSize, currentPage * pageSize)
        .forEach((card) => { card.hidden = false; });

    document.getElementById("current-page").textContent = currentPage;
    document.getElementById("page-count").textContent = totalPages;
    document.getElementById("product-count").textContent = `${filtered.length} pieces`;

    const makePageUrl = (page) => {
        const next = new URL(window.location.href);
        next.searchParams.set("category", selectedCategory);
        next.searchParams.set("page", page);
        return next.toString();
    };

    const previous = document.getElementById("previous-page");
    const next = document.getElementById("next-page");
    previous.href = makePageUrl(Math.max(1, currentPage - 1));
    next.href = makePageUrl(Math.min(totalPages, currentPage + 1));

    [[previous, currentPage <= 1], [next, currentPage >= totalPages]].forEach(([link, disabled]) => {
        link.classList.toggle("is-disabled", disabled);
        if (disabled) link.setAttribute("aria-disabled", "true");
        else link.removeAttribute("aria-disabled");
    });
})();
