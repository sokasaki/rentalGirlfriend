/**
 * Shared utility for toggling favorite status of a companion.
 * Used across index, listing, and profile pages.
 */
async function toggleFavorite(btn) {
  const companionId = btn.dataset.companionId;
  const isFavorited = btn.dataset.favorited === "true";

  // Disable button during request
  btn.disabled = true;

  try {
    const resp = await fetch(`/toggle-favorite/${companionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const data = await resp.json();

    // Handle unauthorized or other errors
    if (resp.status === 401 || resp.status === 403) {
      Swal.fire({
        icon: "info",
        title: "Membership Required",
        text: data.message || "Please log in to save favorites.",
        showCancelButton: true,
        confirmButtonText: "Login",
        confirmButtonColor: "#ff6b9d",
      }).then((result) => {
        if (result.isConfirmed) {
          window.location.href = "/login";
        }
      });
      return;
    }

    if (data.success) {
      const icon = btn.querySelector("i");
      if (data.is_favorited) {
        // UI: Mark as favorited
        icon.className =
          "fas fa-heart" + (icon.classList.contains("fa-lg") ? " fa-lg" : "");
        icon.style.color = "#e91e8c";
        btn.dataset.favorited = "true";
        if (btn.hasAttribute("title")) btn.title = "Remove from favorites";

        Swal.fire({
          toast: true,
          position: "top-end",
          icon: "success",
          title: "Added to favorites!",
          showConfirmButton: false,
          timer: 2500,
          timerProgressBar: true,
        });
      } else {
        // UI: Mark as untoggled
        icon.className =
          "far fa-heart" + (icon.classList.contains("fa-lg") ? " fa-lg" : "");
        icon.style.color = "";
        btn.dataset.favorited = "false";
        if (btn.hasAttribute("title")) btn.title = "Add to favorites";

        Swal.fire({
          toast: true,
          position: "top-end",
          icon: "info",
          title: "Removed from favorites",
          showConfirmButton: false,
          timer: 2500,
          timerProgressBar: true,
        });
      }

      // Dispatch a custom event in case other components need to know
      window.dispatchEvent(
        new CustomEvent("favoriteToggled", {
          detail: { companionId, isFavorited: data.is_favorited },
        }),
      );
    }
  } catch (err) {
    console.error("Favorite toggle error:", err);
    Swal.fire({
      icon: "error",
      title: "Connection Error",
      text: "Could not update favorite. Please check your connection and try again.",
    });
  } finally {
    btn.disabled = false;
  }
}
