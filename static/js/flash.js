document.addEventListener("click", (event) => {
    const dismissButton = event.target.closest("[data-flash-dismiss]");
    if (!dismissButton) return;

    const message = dismissButton.closest(".flash-message");
    if (message) message.remove();
});
