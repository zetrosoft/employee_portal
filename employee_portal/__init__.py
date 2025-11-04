# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# This code will run when the app is loaded.
# It monkey-patches the standard login function with our custom router.

import frappe

# Use a try-except block to prevent crashes if the modules are not available
try:
    from .api import custom_login
    import frappe.www.login as login_module

    # The actual monkey-patch: replace the function in the loaded module
    login_module.login = custom_login
    frappe.flags.employee_login_patched = True

except (ImportError, AttributeError) as e:
    # Log an error if patching fails for some reason
    # This helps in debugging if the app fails to load
    frappe.log_error(f"Failed to patch employee login: {e}", "Employee Portal Patch")