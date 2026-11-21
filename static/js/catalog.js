(() => {
    const PAGE_SIZE = 12;
    const API_URL = "/api/products";
    const body = document.body;
    const productGrid = document.getElementById("product-grid");
    const productCount = document.getElementById("product-count");
    const catalogDescription = document.getElementById("catalog-description");
    const catalogState = document.getElementById("catalog-state");
    const retryButton = document.getElementById("catalog-retry");
    const emptyState = document.getElementById("empty-state");
    const previousButton = document.getElementById("previous-page");
    const nextButton = document.getElementById("next-page");
    const currentPageLabel = document.getElementById("current-page");
    const pageCountLabel = document.getElementById("page-count");
    const selectedCartSummary = document.getElementById("selected-cart-summary");
    const addToCartButton = document.getElementById("add-selected-to-cart");

    let selectedCategory = "All";
    let currentPage = 1;
    let totalPages = 1;
    let isLoading = false;
    let isAddingToCart = false;
    let activeController = null;
    let requestSequence = 0;
    const selectedQuantities = new Map();

    function syncControls() {
        document.querySelectorAll("[data-category]").forEach((button) => {
            const isSelected = button.dataset.category === selectedCategory;
            button.classList.toggle("is-active", isSelected);
            button.setAttribute("aria-pressed", String(isSelected));
        });

        currentPageLabel.textContent = String(currentPage);
        pageCountLabel.textContent = String(totalPages);

        previousButton.disabled = isLoading || currentPage <= 1;
        nextButton.disabled = isLoading || currentPage >= totalPages;
        previousButton.classList.toggle("is-disabled", previousButton.disabled);
        nextButton.classList.toggle("is-disabled", nextButton.disabled);
        addToCartButton.disabled = isAddingToCart || selectedQuantities.size === 0;

        const selectedLineCount = selectedQuantities.size;
        const selectedUnitCount = Array.from(selectedQuantities.values())
            .reduce((total, quantity) => total + quantity, 0);
        selectedCartSummary.textContent = selectedLineCount === 0
            ? "No products selected"
            : `${selectedLineCount} product${selectedLineCount === 1 ? "" : "s"} · ${selectedUnitCount} item${selectedUnitCount === 1 ? "" : "s"}`;
    }

    function createProductCard(product, index) {
        const productId = String(product.product_id);
        const productName = String(product.product_name ?? "");
        const stockQuantity = Math.max(0, Number(product.stock_quantity) || 0);
        const selectedQuantity = Math.min(selectedQuantities.get(productId) || 0, stockQuantity);
        if (selectedQuantity > 0) selectedQuantities.set(productId, selectedQuantity);
        else selectedQuantities.delete(productId);

        const card = document.createElement("article");
        card.className = "product-card";
        card.dataset.productId = productId;
        card.dataset.stockQuantity = String(stockQuantity);

        const imageWrap = document.createElement("div");
        imageWrap.className = "product-image-wrap";

        const image = document.createElement("img");
        image.className = "product-image";
        image.src = body.dataset.productImage;
        image.alt = productName;
        image.loading = "lazy";

        const imageIndex = document.createElement("span");
        imageIndex.className = "image-index";
        imageIndex.textContent = String(index + 1).padStart(2, "0");

        imageWrap.append(image, imageIndex);

        const meta = document.createElement("div");
        meta.className = "product-meta";

        const category = document.createElement("span");
        category.className = "product-category";
        category.textContent = String(product.category ?? "");
        meta.append(category);

        const stockNote = document.createElement("span");
        stockNote.className = stockQuantity === 0 ? "stock-note out-of-stock" : "stock-note";
        stockNote.textContent = `${stockQuantity} in stock`;
        meta.append(stockNote);

        const info = document.createElement("div");
        info.className = "product-info";

        const heading = document.createElement("h3");
        heading.textContent = productName;

        const price = document.createElement("p");
        price.className = "product-price";
        const numericPrice = Number(product.price);
        price.textContent = Number.isFinite(numericPrice)
            ? `₹${numericPrice.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : "Price unavailable";

        info.append(heading, price);

        const quantityControl = document.createElement("div");
        quantityControl.className = "quantity-control";
        quantityControl.setAttribute("aria-label", `Quantity for ${productName}`);

        const decreaseButton = document.createElement("button");
        decreaseButton.className = "quantity-step";
        decreaseButton.type = "button";
        decreaseButton.dataset.quantityStep = "-1";
        decreaseButton.setAttribute("aria-label", `Remove one ${productName}`);
        decreaseButton.textContent = "−";
        decreaseButton.disabled = selectedQuantity === 0;

        const quantityValue = document.createElement("output");
        quantityValue.className = "quantity-value";
        quantityValue.dataset.quantityValue = "";
        quantityValue.textContent = String(selectedQuantity);
        quantityValue.setAttribute("aria-live", "polite");

        const increaseButton = document.createElement("button");
        increaseButton.className = "quantity-step";
        increaseButton.type = "button";
        increaseButton.dataset.quantityStep = "1";
        increaseButton.setAttribute("aria-label", `Add one ${productName}`);
        increaseButton.textContent = "+";
        increaseButton.disabled = stockQuantity === 0 || selectedQuantity >= stockQuantity;

        quantityControl.append(decreaseButton, quantityValue, increaseButton);
        card.append(imageWrap, meta, info, quantityControl);
        return card;
    }

    async function loadProducts() {
        if (activeController) activeController.abort();
        activeController = new AbortController();
        const controller = activeController;
        const sequence = ++requestSequence;
        isLoading = true;
        syncControls();

        catalogState.hidden = false;
        catalogState.textContent = "Loading the collection…";
        retryButton.hidden = true;
        emptyState.hidden = true;
        productGrid.hidden = true;
        productGrid.setAttribute("aria-busy", "true");

        const url = new URL(API_URL, window.location.origin);
        url.searchParams.set("category", selectedCategory);
        url.searchParams.set("page", String(currentPage));
        url.searchParams.set("page_size", String(PAGE_SIZE));

        try {
            const response = await fetch(url, {
                headers: { Accept: "application/json" },
                signal: controller.signal,
            });

            if (!response.ok) {
                throw new Error(`Products request failed with status ${response.status}`);
            }

            const data = await response.json();
            if (!Array.isArray(data.items)) {
                throw new Error("Products response must include an items array");
            }
            if (sequence !== requestSequence) return;

            data.items.forEach((product) => {
                const id = String(product.product_id);
                const stock = Math.max(0, Number(product.stock_quantity) || 0);
                const selected = Math.min(selectedQuantities.get(id) || 0, stock);
                if (selected > 0) selectedQuantities.set(id, selected);
                else selectedQuantities.delete(id);
            });

            currentPage = Math.max(1, Number(data.page) || currentPage);
            const totalItems = Math.max(0, Number(data.total_items) || 0);
            totalPages = Math.max(
                1,
                Number(data.total_pages) || Math.ceil(totalItems / PAGE_SIZE),
            );
            currentPage = Math.min(currentPage, totalPages);
            productCount.textContent = `${totalItems} ${totalItems === 1 ? "piece" : "pieces"}`;
            catalogDescription.textContent = selectedCategory === "All"
                ? "A considered edit of everyday essentials"
                : selectedCategory;

            productGrid.replaceChildren(...data.items.map(createProductCard));
            catalogState.hidden = true;
            retryButton.hidden = true;
            productGrid.hidden = data.items.length === 0;
            emptyState.hidden = data.items.length !== 0;
        } catch (error) {
            if (error.name === "AbortError" || sequence !== requestSequence) return;
            console.error("Unable to load products:", error);
            productGrid.replaceChildren();
            productGrid.hidden = true;
            emptyState.hidden = true;
            productCount.textContent = "Products unavailable";
            catalogState.hidden = false;
            catalogState.textContent = "We couldn't load the collection. Please try again.";
            retryButton.hidden = false;
        } finally {
            if (sequence === requestSequence) {
                isLoading = false;
                productGrid.setAttribute("aria-busy", "false");
                syncControls();
            }
        }
    }

    async function addSelectedToCart() {
        const items = Array.from(selectedQuantities, ([product_id, quantity]) => ({
            product_id,
            quantity,
        }));
        if (items.length === 0 || isAddingToCart) return;

        isAddingToCart = true;
        addToCartButton.textContent = "Adding…";
        syncControls();

        try {
            const response = await fetch("/api/cart/items", {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({ items }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || data.message || data.msg || "Could not add these products to your cart.");
            }

            window.location.assign("/orders");
        } catch (error) {
            if (typeof window.showFlashMessage === "function") {
                window.showFlashMessage(error.message, "error");
            }
        } finally {
            isAddingToCart = false;
            addToCartButton.innerHTML = 'Add selected to cart <span aria-hidden="true">→</span>';
            syncControls();
        }
    }

    document.addEventListener("click", (event) => {
        const quantityButton = event.target.closest("[data-quantity-step]");
        if (quantityButton) {
            const card = quantityButton.closest(".product-card");
            const productId = card.dataset.productId;
            const stockQuantity = Number(card.dataset.stockQuantity);
            const currentQuantity = selectedQuantities.get(productId) || 0;
            const step = Number(quantityButton.dataset.quantityStep);
            const nextQuantity = Math.min(stockQuantity, Math.max(0, currentQuantity + step));

            if (nextQuantity === 0) selectedQuantities.delete(productId);
            else selectedQuantities.set(productId, nextQuantity);

            card.querySelector("[data-quantity-value]").textContent = String(nextQuantity);
            card.querySelector('[data-quantity-step="-1"]').disabled = nextQuantity === 0;
            card.querySelector('[data-quantity-step="1"]').disabled = nextQuantity >= stockQuantity;
            syncControls();
            return;
        }

        if (event.target.closest("#add-selected-to-cart")) {
            addSelectedToCart();
            return;
        }

        const categoryButton = event.target.closest("[data-category]");
        if (categoryButton) {
            selectedCategory = categoryButton.dataset.category;
            currentPage = 1;
            loadProducts();
            return;
        }

        if (event.target.closest("#previous-page") && currentPage > 1) {
            currentPage -= 1;
            loadProducts();
        } else if (event.target.closest("#next-page") && currentPage < totalPages) {
            currentPage += 1;
            loadProducts();
        } else if (event.target.closest("#catalog-retry")) {
            loadProducts();
        }
    });

    syncControls();
    loadProducts();
})();
