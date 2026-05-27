(() => {
  const root = document.documentElement;
  const toggle = document.getElementById("themeToggle");
  const storageKey = "finance-llm-theme";

  const applyTheme = (theme) => {
    root.setAttribute("data-bs-theme", theme);
    localStorage.setItem(storageKey, theme);
  };

  const savedTheme = localStorage.getItem(storageKey);
  if (savedTheme) {
    applyTheme(savedTheme);
  }

  if (toggle) {
    toggle.addEventListener("click", () => {
      const nextTheme = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      fetch("/theme", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ theme: nextTheme }),
      }).catch(() => {});
    });
  }

  document.querySelectorAll(".js-propagate-upi").forEach((button) => {
    button.addEventListener("click", () => {
      const targetFormId = button.dataset.targetForm;
      const upiId = button.dataset.upiId;
      const form = document.getElementById(targetFormId);
      if (!form) {
        return;
      }

      const applyToSame = window.confirm(`Apply this category to all transactions with the same UPI ID (${upiId})?`);
      if (!applyToSame) {
        return;
      }

      let hidden = form.querySelector('input[name="apply_same_upi"]');
      if (!hidden) {
        hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = "apply_same_upi";
        form.appendChild(hidden);
      }
      hidden.value = "true";
      form.submit();
    });
  });
})();
