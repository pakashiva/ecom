(() => {
    const API_URL = "/api/admin/products";
    const PAGE_SIZE = 24;
    const grid = document.getElementById("inventory-grid");
    const state = document.getElementById("inventory-state");
    const count = document.getElementById("inventory-count");
    const pagination = document.getElementById("inventory-pagination");
    const previousButton = document.getElementById("inventory-previous");
    const nextButton = document.getElementById("inventory-next");
    const pageStatus = document.getElementById("inventory-page-status");

    let selectedCategory = "All";
    let currentPage = 1;
    let totalPages = 1;
    let isLoading = false;

    function showMessage(message, category = "error") {
        if (typeof window.showFlashMessage === "function") {
            window.showFlashMessage(message, category);
        }
    }

    async function requestJson(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                Accept: "application/json",
                ...(options.body ? { "Content-Type": "application/json" } : {}),
                ...options.headers,
            },
            credentials: "same-origin",
            cache: "no-store",
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || data.message || data.msg || `Request failed (${response.status})`);
        }
        return data;
    }

    function makeProductCard(product) {
        const card = document.createElement("article");
        card.className = "inventory-card";
        card.dataset.productId = String(product.product_id);

        const imageWrap = document.createElement("div");
        imageWrap.className = "inventory-image-wrap";
        const image = document.createElement("img");
        image.className = "inventory-image";
        image.src = document.body.dataset.productImage || "/static/images/product-default.svg";
        image.alt = "";
        image.loading = "lazy";
        imageWrap.append(image);

        const details = document.createElement("div");
        details.className = "inventory-product-details";
        const category = document.createElement("p");
        category.className = "inventory-category";
        category.textContent = String(product.category ?? "");
        const name = document.createElement("h2");
        name.className = "inventory-product-name";
        name.textContent = String(product.product_name ?? `Product ${product.product_id}`);
        const id = document.createElement("span");
        id.className = "inventory-product-id";
        id.textContent = `Product #${product.product_id}`;
        details.append(category, name, id);

        const fields = document.createElement("div");
        fields.className = "inventory-fields";

        const priceLabel = document.createElement("label");
        priceLabel.className = "inventory-field";
        const priceCaption = document.createElement("span");
        priceCaption.textContent = "Price · ₹";
        const priceInput = document.createElement("input");
        priceInput.type = "number";
        priceInput.name = "price";
        priceInput.dataset.inventoryField = "price";
        priceInput.min = "0";
        priceInput.step = "0.01";
        priceInput.required = true;
        priceInput.inputMode = "decimal";
        priceInput.value = String(product.price);
        priceInput.setAttribute("aria-label", `Price for ${name.textContent}`);
        priceLabel.append(priceCaption, priceInput);

        const quantityLabel = document.createElement("label");
        quantityLabel.className = "inventory-field";
        const quantityCaption = document.createElement("span");
        quantityCaption.textContent = "Available quantity";
        const quantityInput = document.createElement("input");
        quantityInput.type = "number";
        quantityInput.name = "stock_quantity";
        quantityInput.dataset.inventoryField = "stock_quantity";
        quantityInput.min = "0";
        quantityInput.step = "1";
        quantityInput.required = true;
        quantityInput.inputMode = "numeric";
        quantityInput.value = String(product.stock_quantity);
        quantityInput.setAttribute("aria-label", `Available quantity for ${name.textContent}`);
        quantityLabel.append(quantityCaption, quantityInput);
        fields.append(priceLabel, quantityLabel);

        const footer = document.createElement("div");
        footer.className = "inventory-card-footer";
        const saveButton = document.createElement("button");
        saveButton.className = "button button-dark inventory-save";
        saveButton.type = "button";
        saveButton.dataset.saveInventory = "";
        saveButton.textContent = "Save changes";
        footer.append(saveButton);

        card.append(imageWrap, details, fields, footer);
        return card;
    }

    async function loadInventory(page = currentPage) {
        if (isLoading) return;
        isLoading = true;
        state.hidden = false;
        state.textContent = "Loading inventory…";
        grid.setAttribute("aria-busy", "true");
        pagination.hidden = true;
        document.querySelectorAll("[data-inventory-category]").forEach((button) => {
            button.disabled = true;
        });

        const url = new URL(API_URL, window.location.origin);
        url.searchParams.set("category", selectedCategory);
        url.searchParams.set("page", String(page));
        url.searchParams.set("page_size", String(PAGE_SIZE));

        try {
            const data = await requestJson(url);
            if (!Array.isArray(data.items)) {
                throw new Error("Inventory API response must include an items array");
            }
            currentPage = Math.max(1, Number(data.page) || page);
            totalPages = Math.max(1, Number(data.total_pages) || 1);
            const totalItems = Math.max(0, Number(data.total_items) || 0);
            grid.replaceChildren(...data.items.map(makeProductCard));
            count.textContent = `${totalItems} product${totalItems === 1 ? "" : "s"}`;
            state.hidden = data.items.length > 0;
            state.textContent = data.items.length > 0 ? "" : "No products found.";
            pageStatus.textContent = `Page ${currentPage} of ${totalPages}`;
            previousButton.disabled = currentPage <= 1;
            nextButton.disabled = currentPage >= totalPages;
            previousButton.classList.toggle("is-disabled", previousButton.disabled);
            nextButton.classList.toggle("is-disabled", nextButton.disabled);
            pagination.hidden = totalPages <= 1;
        } catch (error) {
            grid.replaceChildren();
            count.textContent = "";
            state.hidden = false;
            state.textContent = "Inventory could not be loaded.";
            showMessage(error.message);
        } finally {
            isLoading = false;
            grid.setAttribute("aria-busy", "false");
            document.querySelectorAll("[data-inventory-category]").forEach((button) => {
                button.disabled = false;
            });
        }
    }

    async function saveProduct(card) {
        const productId = card.dataset.productId;
        const priceInput = card.querySelector('[data-inventory-field="price"]');
        const quantityInput = card.querySelector('[data-inventory-field="stock_quantity"]');
        const saveButton = card.querySelector("[data-save-inventory]");

        if (!priceInput.reportValidity() || !quantityInput.reportValidity()) return;

        saveButton.disabled = true;
        saveButton.textContent = "Saving…";
        try {
            const result = await requestJson(`${API_URL}/${encodeURIComponent(productId)}`, {
                method: "PATCH",
                body: JSON.stringify({
                    price: priceInput.value,
                    stock_quantity: Number(quantityInput.value),
                }),
            });
            const savedProduct = result.product || {};
            priceInput.value = String(savedProduct.price ?? priceInput.value);
            quantityInput.value = String(savedProduct.stock_quantity ?? quantityInput.value);
            showMessage(result.message || `Product #${productId} updated`, "success");
        } catch (error) {
            showMessage(error.message);
        } finally {
            saveButton.disabled = false;
            saveButton.textContent = "Save changes";
        }
    }

    grid.addEventListener("click", (event) => {
        const button = event.target.closest("[data-save-inventory]");
        if (!button) return;
        saveProduct(button.closest(".inventory-card"));
    });

    document.querySelectorAll("[data-inventory-category]").forEach((button) => {
        button.addEventListener("click", () => {
            selectedCategory = button.dataset.inventoryCategory;
            document.querySelectorAll("[data-inventory-category]").forEach((categoryButton) => {
                const selected = categoryButton.dataset.inventoryCategory === selectedCategory;
                categoryButton.classList.toggle("is-active", selected);
                categoryButton.setAttribute("aria-pressed", String(selected));
            });
            loadInventory(1);
        });
    });

    previousButton.addEventListener("click", () => {
        if (!isLoading && currentPage > 1) loadInventory(currentPage - 1);
    });
    nextButton.addEventListener("click", () => {
        if (!isLoading && currentPage < totalPages) loadInventory(currentPage + 1);
    });

    loadInventory(1);
})();
