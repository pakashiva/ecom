document.addEventListener("click", (event) => {
    const dismissButton = event.target.closest("[data-flash-dismiss]");
    if (!dismissButton) return;

    const message = dismissButton.closest(".flash-message");
    if (message) message.remove();
});

window.showFlashMessage = (messageText, category = "info") => {
    const allowedCategories = new Set(["success", "error", "warning", "info"]);
    const safeCategory = allowedCategories.has(category) ? category : "info";
    let stack = document.querySelector(".flash-stack");

    if (!stack) {
        stack = document.createElement("div");
        stack.className = "flash-stack";
        stack.setAttribute("role", "region");
        stack.setAttribute("aria-label", "Notifications");
        document.body.append(stack);
    }

    const notification = document.createElement("div");
    notification.className = `flash-message flash-${safeCategory}`;
    notification.setAttribute("role", safeCategory === "error" ? "alert" : "status");

    const text = document.createElement("span");
    text.className = "flash-message-text";
    text.textContent = messageText;

    const dismissButton = document.createElement("button");
    dismissButton.className = "flash-dismiss";
    dismissButton.type = "button";
    dismissButton.setAttribute("aria-label", "Dismiss notification");
    dismissButton.dataset.flashDismiss = "";
    dismissButton.textContent = "×";

    notification.append(text, dismissButton);
    stack.append(notification);
};
