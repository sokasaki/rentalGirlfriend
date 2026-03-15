// Handle hash navigation for tabs
document.addEventListener('DOMContentLoaded', function () {
    const hash = window.location.hash;
    if (hash) {
        const tabTrigger = document.querySelector(`button[data-bs-target="${hash}"]`);
        if (tabTrigger) {
            const tab = new bootstrap.Tab(tabTrigger);
            tab.show();
        }
    }
});

// Handle View Booking Details
document.querySelectorAll('.view-booking-btn').forEach(button => {
    button.addEventListener('click', async function () {
        const bookingId = this.getAttribute('data-booking-id');
        const modalElement = document.getElementById('bookingDetailModal');
        const modal = new bootstrap.Modal(modalElement);
        const content = document.getElementById('bookingDetailContent');

        modal.show();
        content.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"></div></div>';

        try {
            const response = await fetch(`/get_booking_details/${bookingId}`);
            const data = await response.json();

            if (data.success) {
                const b = data.booking;
                const c = data.customer;
                const p = data.payment;

                let statusBadge = '';
                if (b.status === 'COMPLETED') statusBadge = '<span class="badge bg-success">Completed</span>';
                else if (b.status === 'APPROVED' || b.status === 'PAID') statusBadge = '<span class="badge bg-primary">Confirmed</span>';
                else if (b.status === 'PENDING') statusBadge = '<span class="badge bg-warning text-dark">Pending</span>';
                else if (b.status === 'REJECTED') statusBadge = '<span class="badge bg-danger">Rejected</span>';
                else statusBadge = `<span class="badge bg-secondary">${b.status}</span>`;

                content.innerHTML = `
                            <div class="d-flex align-items-center mb-4 pb-3 border-bottom">
                                <img src="${c.photo}" class="rounded-circle me-3" style="width: 64px; height: 64px; object-fit: cover; border: 3px solid #f8f9fa;">
                                <div>
                                    <h5 class="fw-bold mb-1">${c.name}</h5>
                                    <div class="text-muted small"><i class="fas fa-map-marker-alt me-1"></i>${c.location || 'No location set'}</div>
                                </div>
                                <div class="ms-auto">
                                    ${statusBadge}
                                </div>
                            </div>
                            
                            <div class="row g-3 mb-4">
                                <div class="col-6">
                                    <div class="p-3 bg-light rounded-3 h-100">
                                        <small class="text-muted d-block text-uppercase fw-bold mb-1" style="font-size: 0.65rem;">Schedule</small>
                                        <div class="fw-semibold small">${b.start_time}</div>
                                        <div class="text-primary small">${b.duration} session</div>
                                    </div>
                                </div>
                                <div class="col-6">
                                    <div class="p-3 bg-light rounded-3 h-100">
                                        <small class="text-muted d-block text-uppercase fw-bold mb-1" style="font-size: 0.65rem;">Financials</small>
                                        <div class="fw-bold text-success">$${b.total_price.toFixed(2)}</div>
                                        <div class="text-muted small">Status: <strong>${p.status}</strong></div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mb-4">
                                <h6 class="fw-bold mb-2 small text-uppercase text-secondary">Meeting Location</h6>
                                <div class="p-3 bg-white border border-light-subtle rounded-3 shadow-sm small">
                                    <i class="fas fa-map-marked-alt text-primary me-2"></i> ${b.location || 'Not specified'}
                                </div>
                            </div>
                            
                            <div class="mb-0">
                                <h6 class="fw-bold mb-2 small text-uppercase text-secondary">Customer Bio</h6>
                                <div class="p-3 bg-light rounded-3 small text-muted italic">${c.bio}</div>
                            </div>
                            
                            ${b.rejection_reason ? `
                            <div class="mt-4 pt-3 border-top">
                                <h6 class="fw-bold mb-2 small text-uppercase text-danger">Rejection Reason</h6>
                                <div class="alert alert-danger mb-0 small">${b.rejection_reason}</div>
                            </div>` : ''}
                        `;

                // Update Modal Footer for PENDING bookings
                const footer = document.getElementById('bookingModalFooter');
                if (b.status === 'PENDING') {
                    footer.innerHTML = `
                                <button type="button" class="btn btn-outline-danger rounded-pill px-4 me-auto modal-reject-btn" data-booking-id="${b.id}">Decline</button>
                                <button type="button" class="btn btn-light rounded-pill px-4" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="btn btn-primary rounded-pill px-4 modal-approve-btn" data-booking-id="${b.id}">Accept Booking</button>
                            `;

                    // Add Event Listeners for new buttons
                    footer.querySelector('.modal-approve-btn').addEventListener('click', () => {
                        // Close modal first if you like, or just trigger the button
                        const originalBtn = document.querySelector(`.approve-booking-btn[data-booking-id="${b.id}"]`);
                        if (originalBtn) {
                            modal.hide();
                            originalBtn.click();
                        }
                    });

                    footer.querySelector('.modal-reject-btn').addEventListener('click', () => {
                        const originalBtn = document.querySelector(`.reject-booking-btn[data-booking-id="${b.id}"]`);
                        if (originalBtn) {
                            modal.hide();
                            originalBtn.click();
                        }
                    });
                } else {
                    // Reset to default close button
                    footer.innerHTML = '<button type="button" class="btn btn-light rounded-pill px-4" data-bs-dismiss="modal">Close</button>';
                }
            } else {
                content.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
            }
        } catch (error) {
            console.error('Error:', error);
            content.innerHTML = `<div class="alert alert-danger">Error loading details. Please try again.</div>`;
        }
    });
});

// Handle approve booking
document.querySelectorAll('.approve-booking-btn').forEach(btn => {
    btn.addEventListener('click', async function () {
        const bookingId = this.getAttribute('data-booking-id');
        const originalHTML = this.innerHTML;

        // Disable button and show loading
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch(`/approve_booking/${bookingId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                // Show success message
                Swal.fire({
                    icon: 'success',
                    title: 'Booking Approved!',
                    text: result.message,
                    confirmButtonColor: '#4CAF50'
                });

                // Remove the card from the grid
                this.closest('.col-md-6').remove();

                // Reload page to update counts
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops!',
                    text: result.message || 'Failed to approve booking',
                    confirmButtonColor: '#f44336'
                });
                this.disabled = false;
                this.innerHTML = originalHTML;
            }
        } catch (error) {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'An error occurred. Please try again.',
                confirmButtonColor: '#f44336'
            });
            this.disabled = false;
            this.innerHTML = originalHTML;
        }
    });
});

// Handle reject booking
document.querySelectorAll('.reject-booking-btn').forEach(btn => {
    btn.addEventListener('click', async function () {
        const bookingId = this.getAttribute('data-booking-id');
        const originalHTML = this.innerHTML;

        // Confirm rejection with reason
        const confirmResult = await Swal.fire({
            icon: 'warning',
            title: 'Decline Booking?',
            text: 'Please provide a reason for declining this request:',
            input: 'textarea',
            inputPlaceholder: 'Type your reason here...',
            inputAttributes: {
                'aria-label': 'Type your reason here'
            },
            showCancelButton: true,
            confirmButtonColor: '#f44336',
            cancelButtonColor: '#9e9e9e',
            confirmButtonText: 'Yes, Decline',
            cancelButtonText: 'Cancel',
            inputValidator: (value) => {
                if (!value) {
                    return 'You need to provide a reason!'
                }
            }
        });

        if (!confirmResult.isConfirmed) {
            return;
        }

        const rejectionReason = confirmResult.value;

        // Disable button and show loading
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch(`/reject_booking/${bookingId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    rejection_reason: rejectionReason
                })
            });

            const result = await response.json();

            if (result.success) {
                // Show success message
                Swal.fire({
                    icon: 'success',
                    title: 'Booking Declined',
                    text: result.message,
                    confirmButtonColor: '#4CAF50'
                });

                // Remove the card from the grid
                this.closest('.col-md-6').remove();

                // Reload page to update counts
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops!',
                    text: result.message || 'Failed to reject booking',
                    confirmButtonColor: '#f44336'
                });
                this.disabled = false;
                this.innerHTML = originalHTML;
            }
        } catch (error) {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'An error occurred. Please try again.',
                confirmButtonColor: '#f44336'
            });
            this.disabled = false;
            this.innerHTML = originalHTML;
        }
    });
});
// Handle Companion Report Modal
const reportBookingModal = document.getElementById('reportBookingModal');
if (reportBookingModal) {
    // Set customer ID on open
    reportBookingModal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        const customerId = button.getAttribute('data-customer-id');
        document.getElementById('companion_report_customer_id').value = customerId;
    });

    // Reset on close
    reportBookingModal.addEventListener('hidden.bs.modal', function () {
        document.querySelectorAll('.companion-reason-card').forEach(c => c.classList.remove('selected'));
        document.getElementById('companion_report_reason').value = '';
        document.getElementById('companionReportDetails').value = '';
        document.getElementById('companionCharCount').textContent = '0';
        document.getElementById('companionReasonError').classList.add('d-none');
    });

    // Card selection
    document.querySelectorAll('.companion-reason-card').forEach(card => {
        card.addEventListener('click', function () {
            document.querySelectorAll('.companion-reason-card').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            document.getElementById('companion_report_reason').value = this.dataset.reason;
            document.getElementById('companionReasonError').classList.add('d-none');
        });
    });

    // Character counter
    document.getElementById('companionReportDetails').addEventListener('input', function () {
        document.getElementById('companionCharCount').textContent = this.value.length;
    });
}

// Handle Companion Report Form Submission (standard POST, same as customer flow)
const companionReportForm = document.getElementById('companionReportForm');
if (companionReportForm) {
    companionReportForm.addEventListener('submit', function (e) {
        const reason = document.getElementById('companion_report_reason').value;
        if (!reason) {
            e.preventDefault();
            document.getElementById('companionReasonError').classList.remove('d-none');
            document.getElementById('companionReasonCards').scrollIntoView({
                behavior: 'smooth'
            });
            return;
        }
        // Show loading state and let form submit normally
        const btn = document.getElementById('companionReportSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
    });
}