(() => {
    const balanceElement = document.getElementById("wallet-balance");
    const toggleButton = document.getElementById("show-deposit");
    const depositPanel = document.getElementById("deposit-panel");
    const depositForm = document.getElementById("deposit-form");
    const amountInput = document.getElementById("deposit-amount");
    const submitButton = document.getElementById("submit-deposit");
    const cancelButton = document.getElementById("cancel-deposit");

    function showMessage(message, category) {
        if (typeof window.showFlashMessage === "function") {
            window.showFlashMessage(message, category);
        }
    }

    function formatBalance(amount) {
        const value = Number(amount);
        if (!Number.isFinite(value)) throw new Error("Wallet API returned an invalid balance");
        return new Intl.NumberFormat("en-IN", {
            style: "currency",
            currency: "INR",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    }

    async function readJsonResponse(response) {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || data.message || data.msg || "The wallet request could not be completed.");
        }
        return data;
    }

    async function loadBalance() {
        balanceElement.textContent = "Loading…";
        try {
            const response = await fetch("/api/wallet", {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
            });
            const data = await readJsonResponse(response);
            balanceElement.textContent = formatBalance(data.balance);
        } catch (error) {
            balanceElement.textContent = "Unavailable";
            showMessage(error.message, "error");
        }
    }

    toggleButton.addEventListener("click", () => {
        const isOpening = depositPanel.hidden;
        depositPanel.hidden = !isOpening;
        toggleButton.setAttribute("aria-expanded", String(isOpening));
        if (isOpening) amountInput.focus();
    });

    cancelButton.addEventListener("click", () => {
        depositPanel.hidden = true;
        toggleButton.setAttribute("aria-expanded", "false");
        depositForm.reset();
    });

    depositForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const amount = amountInput.value.trim();

        if (!amount || !Number.isFinite(Number(amount)) || Number(amount) <= 0) {
            showMessage("Enter an amount greater than zero.", "error");
            amountInput.focus();
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "Adding…";

        try {
            const response = await fetch("/api/wallet/deposits", {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                credentials: "same-origin",
                body: JSON.stringify({ amount }),
            });
            const data = await readJsonResponse(response);
            balanceElement.textContent = formatBalance(data.balance);
            depositForm.reset();
            depositPanel.hidden = true;
            toggleButton.setAttribute("aria-expanded", "false");
            showMessage(data.message || "Practice funds added successfully.", "success");
        } catch (error) {
            showMessage(error.message, "error");
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Add funds";
        }
    });

    loadBalance();
})();
