frappe.ready(function() {
    console.log("Employee Login Script: Ready state triggered.");

    // Only run this script on the login page
    if (window.location.pathname !== '/login') {
        console.log("Employee Login Script: Not on login page. Exiting.");
        return;
    }
    console.log("Employee Login Script: On login page. Proceeding.");

    frappe.call({
        method: 'employee_portal.api.get_login_settings',
        callback: function(r) {
            console.log("Employee Login Script: Settings received.", r);
            if (r.message && r.message.allow_login_using_mobile_number) {
                console.log("Employee Login Script: Login with mobile is allowed. Setting up...");
                setup_employee_login();
            } else {
                console.log("Employee Login Script: Login with mobile is NOT allowed.");
            }
        }
    });

    function setup_employee_login() {
        console.log("Employee Login Script: setup_employee_login() called.");
        // Change placeholders to be more informative
        const $login_email = $('#login_email');
        const $login_password = $('#login_password');

        $login_email.attr('placeholder', 'Email atau No. Telepon');
        $login_password.attr('placeholder', 'Password atau Tgl Lahir (ddmmyyyy)');
        console.log("Employee Login Script: Placeholders updated.");

        // Override the login button click event
        const $login_btn = $('.btn-login');
        if ($login_btn.length === 0) {
            console.error("Employee Login Script: Login button '.btn-login' not found!");
            return;
        }
        console.log("Employee Login Script: Login button found. Overriding click event.");

        $login_btn.off('click').on('click', function(e) {
            console.log("Employee Login Script: Login button clicked.");
            e.preventDefault();

            const username = $login_email.val();
            const password = $login_password.val();
            console.log("Employee Login Script: Username entered:", username);
            console.log("Employee Login Script: Is username numeric?", $.isNumeric(username));

            // Simple check to see if it's a phone number (numeric)
            if ($.isNumeric(username)) {
                console.log("Employee Login Script: Detected phone number. Calling custom employee_login API.");
                frappe.call({
                    method: 'employee_portal.api.employee_login',
                    args: {
                        phone_number: username,
                        dob: password
                    },
                    callback: function(r) {
                        console.log("Employee Login Script: Custom API callback received.", r);
                        if (!r.exc) {
                            // Success
                            window.location.href = '/app';
                        } else {
                            // Handled error from backend
                            frappe.msgprint(r.exc_message || 'Login Gagal');
                        }
                    },
                    error: function(r) {
                        console.error("Employee Login Script: Custom API call failed.", r);
                        frappe.msgprint('Terjadi kesalahan server saat mencoba login karyawan.');
                    }
                });
            } else {
                // Fallback to standard login
                console.log("Employee Login Script: Detected email. Falling back to standard login.");
                frappe.login.login();
            }
        });
    }
});