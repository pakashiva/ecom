(() => {
    const ordersState = document.getElementById("orders-state");
    const orderContent = document.getElementById("order-content");
    const orderItems = document.getElementById("order-items");
    const orderLineCount = document.getElementById("order-line-count");
    const orderSubtotal = document.getElementById("order-subtotal");
    const orderTotal = document.getElementById("order-total");
    const walletBalance = document.getElementById("order-wallet-balance");
    const balanceWarning = document.getElementById("balance-warning");
    const checkoutButton = document.getElementById("checkout-button");
    const emptyState = document.getElementById("orders-empty");
    const confirmation = document.getElementById("order-confirmation");
    const confirmationDetail = document.getElementById("confirmation-detail");

    let cart = null;
    let isMutating = false;

    function showMessage(message, category = "error") {
        if (typeof window.showFlashMessage === "function") {
            window.showFlashMessage(message, category);
        }
    }

    function formatMoney(value) {
        const amount = Number(value);
        if (!Number.isFinite(amount)) throw new Error("The cart API returned an invalid amount");
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(amount);
    }

    async function sendRequest(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                Accept: "application/json",
                ...(options.body ? { "Content-Type": "application/json" } : {}),
                ...options.headers,
            },
            credentials: "same-origin",
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || data.message || data.msg || "The order request could not be completed.");
        }
        return data;
    }

    function createOrderItem(item) {
        const productId = String(item.product_id);
        const quantity = Number(item.quantity);
        const row = document.createElement("article");
        row.className = "order-item";
        row.dataset.productId = productId;
        row.dataset.quantity = String(quantity);

        const image = document.createElement("img");
        image.className = "order-item-image";
        image.src = document.body.dataset.productImage || "/static/images/product-default.svg";
        image.alt = "";
        image.loading = "lazy";

        const details = document.createElement("div");
        details.className = "order-item-details";

        const category = document.createElement("p");
        category.className = "order-item-category";
        category.textContent = String(item.category ?? "");

        const name = document.createElement("h3");
        name.className = "order-item-name";
        name.textContent = String(item.product_name ?? "");

        const controls = document.createElement("div");
        controls.className = "order-item-controls";

        const decrease = document.createElement("button");
        decrease.className = "quantity-step";
        decrease.type = "button";
        decrease.dataset.cartStep = "-1";
        decrease.setAttribute("aria-label", `Remove one ${item.product_name}`);
        decrease.textContent = "−";

        const value = document.createElement("output");
        value.className = "quantity-value";
        value.textContent = String(quantity);
        value.setAttribute("aria-live", "polite");

        const increase = document.createElement("button");
        increase.className = "quantity-step";
        increase.type = "button";
        increase.dataset.cartStep = "1";
        increase.setAttribute("aria-label", `Add one ${item.product_name}`);
        increase.textContent = "+";

        controls.append(decrease, value, increase);
        details.append(category, name, controls);

        const linePrice = document.createElement("div");
        linePrice.className = "order-item-price";
        const total = document.createElement("strong");
        total.textContent = formatMoney(Number(item.unit_price) * quantity);
        const unit = document.createElement("span");
        unit.textContent = `${formatMoney(item.unit_price)} each`;
        linePrice.append(total, unit);

        row.append(image, details, linePrice);
        return row;
    }

    function renderCart(data) {
        cart = data;
        const items = Array.isArray(data.items) ? data.items : [];
        if (items.length === 0) {
            ordersState.hidden = true;
            orderContent.hidden = true;
            emptyState.hidden = false;
            return;
        }

        orderItems.replaceChildren(...items.map(createOrderItem));
        const unitCount = items.reduce((total, item) => total + Number(item.quantity), 0);
        orderLineCount.textContent = String(unitCount);
        orderSubtotal.textContent = formatMoney(data.total_amount);
        orderTotal.textContent = formatMoney(data.total_amount);
        walletBalance.textContent = formatMoney(data.balance);
        ordersState.hidden = true;
        emptyState.hidden = true;
        orderContent.hidden = false;
        syncCheckout();
    }

    function syncCheckout() {
        if (!cart) return;
        const itemCount = Array.isArray(cart.items) ? cart.items.length : 0;
        const total = Number(cart.total_amount);
        const balance = Number(cart.balance);
        const sufficientBalance = Number.isFinite(total) && Number.isFinite(balance) && balance >= total;

        balanceWarning.hidden = sufficientBalance;
        balanceWarning.textContent = sufficientBalance
            ? ""
            : "Your practice balance is too low. Add funds to continue.";
        checkoutButton.disabled = isMutating || itemCount === 0 || !sufficientBalance;
        checkoutButton.textContent = `Pay ${formatMoney(cart.total_amount)} from wallet`;
        orderItems.querySelectorAll(".order-item").forEach((row) => {
            const quantity = Number(row.dataset.quantity);
            const decrease = row.querySelector('[data-cart-step="-1"]');
            const increase = row.querySelector('[data-cart-step="1"]');
            decrease.disabled = isMutating || quantity < 1;
            increase.disabled = isMutating;
        });
    }

    async function loadCart(showLoading = true) {
        if (showLoading) {
            ordersState.hidden = false;
            ordersState.textContent = "Loading your order…";
            orderContent.hidden = true;
            emptyState.hidden = true;
        }

        try {
            const data = await sendRequest("/api/cart");
            if (!Array.isArray(data.items)) throw new Error("Cart API response must include an items array");
            renderCart(data);
        } catch (error) {
            if (showLoading) {
                ordersState.hidden = false;
                ordersState.textContent = "We couldn't load your order.";
                orderContent.hidden = true;
                emptyState.hidden = true;
            }
            showMessage(error.message);
        }
    }

    async function changeQuantity(productId, nextQuantity) {
        if (isMutating) return;
        isMutating = true;
        syncCheckout();

        try {
            if (nextQuantity === 0) {
                await sendRequest(`/api/cart/items/${encodeURIComponent(productId)}`, { method: "DELETE" });
            } else {
                await sendRequest(`/api/cart/items/${encodeURIComponent(productId)}`, {
                    method: "PATCH",
                    body: JSON.stringify({ quantity: nextQuantity }),
                });
            }
            await loadCart(false);
        } catch (error) {
            showMessage(error.message);
            await loadCart(false);
        } finally {
            isMutating = false;
            syncCheckout();
        }
    }

    async function checkout() {
        if (isMutating || checkoutButton.disabled) return;
        isMutating = true;
        syncCheckout();
        checkoutButton.textContent = "Processing practice order…";

        try {
            const result = await sendRequest("/api/orders/checkout", { method: "POST" });
            orderContent.hidden = true;
            emptyState.hidden = true;
            ordersState.hidden = true;
            confirmation.hidden = false;
            const orderNumber = result.order_id ? ` #${result.order_id}` : "";
            confirmationDetail.textContent = `Practice order${orderNumber} is complete. No real payment was made.`;
        } catch (error) {
            showMessage(error.message);
            await loadCart(false);
        } finally {
            isMutating = false;
            if (cart) syncCheckout();
        }
    }

    orderItems.addEventListener("click", (event) => {
        const button = event.target.closest("[data-cart-step]");
        if (!button || isMutating) return;

        const row = button.closest(".order-item");
        const currentQuantity = Number(row.dataset.quantity);
        const step = Number(button.dataset.cartStep);
        const nextQuantity = Math.max(0, currentQuantity + step);
        if (nextQuantity !== currentQuantity) {
            changeQuantity(row.dataset.productId, nextQuantity);
        }
    });

    checkoutButton.addEventListener("click", checkout);
    loadCart();
})();
