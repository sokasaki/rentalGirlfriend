// RentACompanion - Main JavaScript File

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", function () {
  // loadNekosAPIImages(); // Disabled - using local images instead
  animateActiveUsers();
  initializeFavorites();
  initializeFilters();
  initializeBookingForm();
  initializeCalendar();
  initializeTimeSlots();
  initializeToasts();
  initializeListingFilters();
});

// ===== ACTIVE USERS ANIMATION =====
function animateActiveUsers() {
  const activeUsersElement = document.getElementById("activeUsers");
  if (!activeUsersElement) return;

  const targetNumber = 2458;
  const duration = 2000; // 2 seconds
  const startTime = Date.now();

  function updateNumber() {
    const currentTime = Date.now();
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // Easing function for smooth animation
    const easeOutQuad = progress * (2 - progress);
    const currentNumber = Math.floor(easeOutQuad * targetNumber);

    activeUsersElement.textContent = currentNumber.toLocaleString();

    if (progress < 1) {
      requestAnimationFrame(updateNumber);
    } else {
      // Add slight random variation every few seconds
      setInterval(() => {
        const variation = Math.floor(Math.random() * 10) - 5;
        const newNumber = targetNumber + variation;
        activeUsersElement.textContent = newNumber.toLocaleString();
      }, 5000);
    }
  }

  updateNumber();
}

// ===== NEKOS API IMAGE LOADING =====
async function loadNekosAPIImages() {
  try {
    // Get all images that need to be loaded from NekosAPI
    const heroImage = document.querySelector(
      '.hero-section-modern img[alt="Happy Companion"]',
    );
    const avatarImages = document.querySelectorAll(".avatar-group img");
    const companionCards = document.querySelectorAll(
      ".companion-card img.card-img-top",
    );
    const safetyImage = document.querySelector(".safety-image-wrapper img");
    const testimonialAvatars = document.querySelectorAll(
      ".card-body img.rounded-circle",
    );

    // Fetch random anime images from NekosAPI
    console.log("🔄 Fetching images from NekosAPI...");
    const response = await fetch(
      "https://api.nekosapi.com/v4/images/random?rating=safe&limit=20",
    );

    console.log("📡 API Response Status:", response.status);
    const data = await response.json();
    console.log("📦 API Data:", data);

    if (data && Array.isArray(data) && data.length > 0) {
      let imageIndex = 0;
      console.log(`🖼️ Found ${data.length} images from API`);

      // Update hero image
      if (heroImage && data[imageIndex]) {
        heroImage.src = data[imageIndex].url;
        heroImage.style.objectFit = "cover";
        console.log(`✅ Hero image loaded: ${data[imageIndex].url}`);
        imageIndex++;
      }

      // Update avatar images
      avatarImages.forEach((img) => {
        if (data[imageIndex]) {
          img.src = data[imageIndex].url;
          img.style.objectFit = "cover";
          console.log(`✅ Avatar ${imageIndex} loaded`);
          imageIndex++;
        }
      });

      // Update companion cards
      companionCards.forEach((img) => {
        if (data[imageIndex]) {
          img.src = data[imageIndex].url;
          img.style.objectFit = "cover";
          console.log(`✅ Companion card ${imageIndex} loaded`);
          imageIndex++;
        }
      });

      // Update safety section image
      if (safetyImage && data[imageIndex]) {
        safetyImage.src = data[imageIndex].url;
        safetyImage.style.objectFit = "cover";
        console.log(`✅ Safety image loaded`);
        imageIndex++;
      }

      // Update testimonial avatars
      testimonialAvatars.forEach((img) => {
        if (data[imageIndex]) {
          img.src = data[imageIndex].url;
          img.style.objectFit = "cover";
          console.log(`✅ Testimonial avatar ${imageIndex} loaded`);
          imageIndex++;
        }
      });

      console.log(`✅ Successfully loaded ${imageIndex} images from NekosAPI`);
    } else {
      console.warn("⚠️ No images found in API response");
    }
  } catch (error) {
    console.error("❌ Error loading images from NekosAPI:", error);
    // Images will fall back to the static URLs in HTML
  }
}

// ===== FAVORITE BUTTON FUNCTIONALITY =====
// Favorite logic is now handled inline by toggleFavorite() on each page.
function initializeFavorites() {
  // No-op: each page manages its own favorite button via toggleFavorite()
}

// ===== FILTER FUNCTIONALITY =====
function initializeFilters() {
  const filterChips = document.querySelectorAll(".filter-chip");

  filterChips.forEach((chip) => {
    chip.addEventListener("click", function () {
      this.classList.toggle("active");
      filterCompanions();
    });
  });

  // Price range filter
  const priceRange = document.getElementById("priceRange");
  const priceDisplay = document.getElementById("priceValue");

  if (priceRange && priceDisplay) {
    priceRange.addEventListener("input", function () {
      priceDisplay.textContent = `$${this.value}`;
      filterCompanions();
    });
  }

  // Search functionality
  const searchInput = document.getElementById("searchCompanions");
  if (searchInput) {
    searchInput.addEventListener("input", debounce(filterCompanions, 300));
  }
}

function filterCompanions() {
  const searchInput = document.getElementById("searchCompanions");
  const priceRange = document.getElementById("priceRange");
  const filterChips = document.querySelectorAll(".filter-chip");
  const ageSelect = document.querySelector(".filter-section select");
  const availableToday = document.getElementById("availableToday");
  const companionCards = document.querySelectorAll(".companion-card");
  const resultsCount = document.querySelector(".results-count strong");

  const searchTerm = searchInput?.value.toLowerCase() || "";
  const maxPrice = parseInt(priceRange?.value || 200);
  const activePersonalities = Array.from(
    document.querySelectorAll(".filter-chip.active"),
  ).map((chip) => chip.dataset.filter);

  let visibleCount = 0;

  companionCards.forEach((card) => {
    const cardParent = card.closest(".col-6");
    const name =
      card.querySelector(".companion-name")?.textContent.toLowerCase() || "";
    const priceText = card.querySelector(".price-tag")?.textContent || "";
    const price = parseInt(priceText.replace(/[^0-9]/g, "")) || 0;
    const personalities = Array.from(
      card.querySelectorAll(".personality-tag"),
    ).map((tag) => tag.textContent.toLowerCase());
    const hasAvailableBadge = card.querySelector(".status-badge");

    let shouldShow = true;

    // Search filter
    if (searchTerm && !name.includes(searchTerm)) {
      shouldShow = false;
    }

    // Price filter
    if (price > maxPrice) {
      shouldShow = false;
    }

    // Personality filter
    if (activePersonalities.length > 0) {
      const hasMatchingPersonality = activePersonalities.some((p) =>
        personalities.some((cardP) => cardP.includes(p)),
      );
      if (!hasMatchingPersonality) {
        shouldShow = false;
      }
    }

    // Availability filter
    if (availableToday?.checked && !hasAvailableBadge) {
      shouldShow = false;
    }

    // Show/hide card
    if (cardParent) {
      cardParent.style.display = shouldShow ? "" : "none";
      if (shouldShow) visibleCount++;
    }
  });

  // Update results count
  if (resultsCount) {
    resultsCount.textContent = visibleCount;
  }
}

// ===== BOOKING FORM VALIDATION =====
function initializeBookingForm() {
  const bookingForm = document.getElementById("bookingForm");

  if (bookingForm) {
    // Set minimum date to today
    const bookingDate = document.getElementById("bookingDate");
    if (bookingDate) {
      const today = new Date().toISOString().split("T")[0];
      bookingDate.setAttribute("min", today);
    }

    bookingForm.addEventListener("submit", function (e) {
      e.preventDefault();

      if (validateBookingForm(this)) {
        showBookingConfirmation();
      }
    });
  }
}

function validateBookingForm(form) {
  const date = form.querySelector('input[type="date"]')?.value;
  const time = form.querySelector('input[type="time"]')?.value;
  const duration = form.querySelector('select[name="duration"]')?.value;
  const location = form.querySelector('input[name="location"]')?.value;
  const termsCheck = form.querySelector("#termsCheck")?.checked;

  if (!date) {
    showToast("Please select a date", "error");
    return false;
  }

  if (!time) {
    showToast("Please select a time", "error");
    return false;
  }

  if (!duration) {
    showToast("Please select duration", "error");
    return false;
  }

  if (!location || location.trim() === "") {
    showToast("Please enter a location", "error");
    return false;
  }

  if (!termsCheck) {
    showToast("Please agree to the Terms of Service", "error");
    return false;
  }

  const selectedDate = new Date(date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (selectedDate < today) {
    showToast("Please select a future date", "error");
    return false;
  }

  return true;
}

function showBookingConfirmation() {
  const form = document.getElementById("bookingForm");
  const modal = new bootstrap.Modal(document.getElementById("bookingModal"));

  // Get booking details
  const date = form.querySelector('input[type="date"]')?.value;
  const time = form.querySelector('input[type="time"]')?.value;
  const duration = form.querySelector('select[name="duration"]')?.value;
  const location = form.querySelector('input[name="location"]')?.value;

  // Format the date nicely
  const dateObj = new Date(date);
  const formattedDate = dateObj.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  // Update modal content with booking details
  const modalBody = document.querySelector("#bookingModal .modal-body");
  if (modalBody) {
    modalBody.innerHTML = `
      <div class="text-center p-4">
        <div class="success-icon mb-4">
          <i class="fas fa-check-circle text-success" style="font-size: 5rem;"></i>
        </div>
        <h3 class="fw-bold mb-3">Booking Request Sent!</h3>
        <p class="text-muted mb-4">Your booking request has been sent to Sarah. You will receive a confirmation once she accepts.</p>
        <div class="bg-light p-3 rounded mb-4 text-start">
          <h6 class="fw-bold mb-3">Booking Details:</h6>
          <p class="mb-2"><i class="fas fa-calendar me-2 text-primary"></i><strong>Date:</strong> ${formattedDate}</p>
          <p class="mb-2"><i class="fas fa-clock me-2 text-primary"></i><strong>Time:</strong> ${time}</p>
          <p class="mb-2"><i class="fas fa-hourglass-half me-2 text-primary"></i><strong>Duration:</strong> ${duration} hours</p>
          <p class="mb-0"><i class="fas fa-map-marker-alt me-2 text-primary"></i><strong>Location:</strong> ${location}</p>
        </div>
        <button class="btn btn-primary rounded-pill px-5" data-bs-dismiss="modal">OK</button>
      </div>
    `;
  }

  modal.show();

  // Reset form after showing modal
  form.reset();
  const priceDisplay = document.getElementById("totalPrice");
  if (priceDisplay) {
    priceDisplay.value = "Select duration";
    priceDisplay.classList.remove("text-success");
  }

  // Show success toast
  setTimeout(() => {
    showToast("Booking request submitted successfully!", "success");
  }, 500);
}

// ===== CALENDAR FUNCTIONALITY =====
function initializeCalendar() {
  const daySlots = document.querySelectorAll(".day-slot");

  daySlots.forEach((slot) => {
    if (!slot.classList.contains("unavailable")) {
      slot.addEventListener("click", function () {
        // Remove selected from all
        daySlots.forEach((s) => s.classList.remove("selected"));
        // Add selected to clicked
        this.classList.add("selected");

        // Update hidden input if exists
        const dateInput = document.getElementById("selectedDate");
        if (dateInput) {
          dateInput.value = this.dataset.date;
        }
      });
    }
  });
}

// ===== TIME SLOTS FUNCTIONALITY =====
function initializeTimeSlots() {
  const timeSlots = document.querySelectorAll(".time-slot");

  timeSlots.forEach((slot) => {
    if (!slot.classList.contains("unavailable")) {
      slot.addEventListener("click", function () {
        // Remove selected from all
        timeSlots.forEach((s) => s.classList.remove("selected"));
        // Add selected to clicked
        this.classList.add("selected");

        // Update hidden input if exists
        const timeInput = document.getElementById("selectedTime");
        if (timeInput) {
          timeInput.value = this.dataset.time;
        }
      });
    }
  });
}

// ===== TOAST NOTIFICATIONS =====
function initializeToasts() {
  // Auto-hide toasts after 3 seconds
  const toastElements = document.querySelectorAll(".toast");
  toastElements.forEach((toastEl) => {
    const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 3000 });
  });
}

function showToast(message, type = "info") {
  // Create toast container if it doesn't exist
  let toastContainer = document.querySelector(".toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.className = "toast-container position-fixed top-0 end-0 p-3";
    toastContainer.style.zIndex = "9999";
    document.body.appendChild(toastContainer);
  }

  // Create toast element
  const toastEl = document.createElement("div");
  toastEl.className = `toast align-items-center text-white border-0 ${
    type === "success"
      ? "bg-success"
      : type === "error"
        ? "bg-danger"
        : "bg-primary"
  }`;
  toastEl.setAttribute("role", "alert");
  toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

  toastContainer.appendChild(toastEl);

  const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 3000 });
  toast.show();

  // Remove toast element after it's hidden
  toastEl.addEventListener("hidden.bs.toast", () => {
    toastEl.remove();
  });
}

// ===== UTILITY FUNCTIONS =====
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// ===== LOGIN FORM =====
function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById("loginEmail")?.value;
  const password = document.getElementById("loginPassword")?.value;

  if (!email || !password) {
    showToast("Please fill in all fields", "error");
    return;
  }

  if (!isValidEmail(email)) {
    showToast("Please enter a valid email address", "error");
    return;
  }

  // Simulate login
  showToast("Login successful!", "success");
  setTimeout(() => {
    window.location.href = "dashboard-customer.html";
  }, 1500);
}

// ===== REGISTER FORM =====
function handleRegister(event) {
  event.preventDefault();

  const name = document.getElementById("registerName")?.value;
  const email = document.getElementById("registerEmail")?.value;
  const password = document.getElementById("registerPassword")?.value;
  const confirmPassword = document.getElementById("confirmPassword")?.value;

  if (!name || !email || !password || !confirmPassword) {
    showToast("Please fill in all fields", "error");
    return;
  }

  if (!isValidEmail(email)) {
    showToast("Please enter a valid email address", "error");
    return;
  }

  if (password.length < 6) {
    showToast("Password must be at least 6 characters", "error");
    return;
  }

  if (password !== confirmPassword) {
    showToast("Passwords do not match", "error");
    return;
  }

  // Simulate registration
  showToast("Registration successful!", "success");
  setTimeout(() => {
    window.location.href = "login.html";
  }, 1500);
}

// ===== EMAIL VALIDATION =====
function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

// ===== PRICE CALCULATION =====
function calculatePrice(hourlyRate, duration) {
  const hours = parseInt(duration);
  return hourlyRate * hours;
}

function updatePriceDisplay() {
  const hourlyRate = parseInt(
    document.getElementById("hourlyRate")?.dataset.rate || 50,
  );
  const durationSelect = document.querySelector('select[name="duration"]');
  const priceDisplay = document.getElementById("totalPrice");

  if (durationSelect && priceDisplay) {
    const duration = parseInt(durationSelect.value || 0);
    if (duration > 0) {
      const total = calculatePrice(hourlyRate, duration);
      priceDisplay.value = `$${total}`;
      priceDisplay.classList.add("text-success");
    } else {
      priceDisplay.value = "Select duration";
      priceDisplay.classList.remove("text-success");
    }
  }
}

// ===== BOOKING ACTIONS =====
function acceptBooking(bookingId) {
  showToast("Booking accepted successfully!", "success");
  const button = event.target;
  button.textContent = "Accepted";
  button.classList.remove("btn-success");
  button.classList.add("btn-secondary");
  button.disabled = true;
}

function rejectBooking(bookingId) {
  if (confirm("Are you sure you want to reject this booking?")) {
    showToast("Booking rejected", "info");
    const row = event.target.closest("tr");
    row.style.opacity = "0.5";
  }
}

// ===== MODAL FUNCTIONS =====
function showSuccessModal(title, message) {
  const modal = document.getElementById("successModal");
  if (modal) {
    modal.querySelector(".modal-title").textContent = title;
    modal.querySelector(".modal-body").innerHTML = `
            <div class="text-center">
                <div class="success-icon mb-4">
                    <i class="fas fa-check-circle text-success" style="font-size: 5rem;"></i>
                </div>
                <p class="lead">${message}</p>
            </div>
        `;
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
  }
}

// ===== PROFILE IMAGE PREVIEW =====
function previewProfileImage(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      const preview = document.getElementById("profileImagePreview");
      if (preview) {
        preview.src = e.target.result;
      }
    };
    reader.readAsDataURL(input.files[0]);
  }
}

// ===== LISTING PAGE FILTERS =====
function initializeListingFilters() {
  // Toggle filters on mobile/tablet
  const toggleBtn = document.getElementById("toggleFilters");
  const filtersPanel = document.getElementById("filtersPanel");

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      filtersPanel.classList.toggle("d-none");
      const icon = toggleBtn.querySelector("i");
      if (filtersPanel.classList.contains("d-none")) {
        icon.classList.remove("fa-times");
        icon.classList.add("fa-filter");
        toggleBtn.innerHTML = '<i class="fas fa-filter me-2"></i>Filters';
      } else {
        icon.classList.remove("fa-filter");
        icon.classList.add("fa-times");
        toggleBtn.innerHTML = '<i class="fas fa-times me-2"></i>Close';
      }
    });
  }

  // Price range slider
  const priceRange = document.getElementById("priceRange");
  const priceValue = document.getElementById("priceValue");
  if (priceRange) {
    priceRange.addEventListener("input", function () {
      priceValue.textContent = "$" + this.value;
    });
  }

  // Personality filter chips
  const personalityChips = document.querySelectorAll(".filter-chip");
  const personalityInput = document.getElementById("personalityInput");

  personalityChips.forEach((chip) => {
    chip.addEventListener("click", function (e) {
      e.preventDefault();
      this.classList.toggle("active");
      updatePersonalityFilter();
    });
  });

  function updatePersonalityFilter() {
    const selected = Array.from(
      document.querySelectorAll(".filter-chip.active"),
    )
      .map((chip) => chip.getAttribute("data-filter"))
      .join(",");
    if (personalityInput) {
      personalityInput.value = selected;
    }
  }

  // Highlight selected chips on page load
  const selectedPersonalities = personalityInput?.value || "";
  if (selectedPersonalities) {
    selectedPersonalities.split(",").forEach((trait) => {
      const chip = document.querySelector(
        '.filter-chip[data-filter="' + trait.trim() + '"]',
      );
      if (chip) {
        chip.classList.add("active");
      }
    });

    // Keep personality section expanded if filters are active
    const personalityCollapse = document.getElementById("personalityCollapse");
    if (personalityCollapse) {
      personalityCollapse.classList.add("show");
      const chevron = document.getElementById("personalityChevron");
      if (chevron) {
        chevron.style.transform = "rotate(180deg)";
      }
    }
  }
}

// Filter collapse toggle function
function toggleFilterSection(sectionId) {
  const section = document.getElementById(sectionId);
  const chevronId = sectionId.replace("Collapse", "Chevron");
  const chevron = document.getElementById(chevronId);

  if (section && chevron) {
    if (section.classList.contains("show")) {
      section.classList.remove("show");
      chevron.style.transform = "rotate(0deg)";
    } else {
      section.classList.add("show");
      chevron.style.transform = "rotate(180deg)";
    }
  }
}

// Export functions for use in HTML
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.updatePriceDisplay = updatePriceDisplay;
window.acceptBooking = acceptBooking;
window.rejectBooking = rejectBooking;
window.previewProfileImage = previewProfileImage;
window.toggleFilterSection = toggleFilterSection;
window.initializeListingFilters = initializeListingFilters;
