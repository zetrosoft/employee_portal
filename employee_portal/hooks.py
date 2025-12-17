app_name = "employee_portal"
app_title = "Employee Portal"
app_publisher = "Bijak Technology"
app_description = "Portal untuk semua Employee mengatur Leave dan Expenses"
app_email = "support@bijaktechnology.com"
app_license = "mit"

fixtures = [
	"Custom Field",
	"Workflow State",
	{"doctype": "Workflow", "filters": {"name": "Material Request Approval"}},
	{"doctype": "Workflow", "filters": {"name": "Purchase Order Approval"}},
	{"doctype": "Workflow", "filters": {"name": "Payment Approval"}},
	{"doctype": "Workflow", "filters": {"name": "Purchase Invoice Approval"}},
	{"doctype": "Workflow", "filters": {"name": "Sales Order Approval"}},
	{"doctype": "Workflow", "filters": {"name": "Sales Invoice Approval"}},
	{"doctype": "Workflow", "filters": {"name": "Work Order Approval"}},
	{"doctype": "Workflow", "filters": {"name": "Quality Inspection Approval"}},
	"Property Setter",
	{"doctype": "Workspace", "filters": {"name": "Leave"}},
	{"doctype": "Workspace", "filters": {"name": "Expenses Claim"}},
	{"doctype": "Role", "filters": {"name": "Employee User"}},
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "employee_portal",
# 		"logo": "/assets/employee_portal/logo.png",
# 		"title": "Employee Portal",
# 		"route": "/employee_portal",
# 		"has_permission": "employee_portal.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/employee_portal/css/custom_notification.css"
# app_include_js = "/assets/employee_portal/js/employee_portal.js"

# include js, css files in header of web template
# web_include_css = "/assets/employee_portal/css/employee_portal.css"
# web_include_js = "/assets/employee_portal/js/employee_portal.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "employee_portal/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_list_js = {
	"Sales Order": "public/js/sales_order_list.js",
	"Work Order": "public/js/work_order_list.js",
	"Quality Inspection": "public/js/quality_inspection_list.js",
	"Material Request": "public/js/material_request_list.js",
	"Purchase Order": "public/js/purchase_order_list.js",
	"Purchase Invoice": "public/js/purchase_invoice_list.js",
	"Payment Entry": "public/js/payment_entry_list.js",
	"Delivery Note": "public/js/delivery_note_list.js",
	"Stock Entry": "public/js/stock_entry_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "employee_portal/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "employee_portal.utils.jinja_methods",
# 	"filters": "employee_portal.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "employee_portal.install.before_install"
# after_install = "employee_portal.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "employee_portal.uninstall.before_uninstall"
# after_uninstall = "employee_portal.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "employee_portal.utils.before_app_install"
# after_app_install = "employee_portal.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "employee_portal.utils.before_app_uninstall"
# after_app_uninstall = "employee_portal.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "employee_portal.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
 	"Leave Application": "employee_portal.overrides.leave_application.LeaveApplicationCustom",
    "Expense Claim": "employee_portal.overrides.expense_claim.ExpenseClaimCustom"
}
#"Payment Entry": "employee_portal.overrides.payment_entry.PaymentEntryCustom" -- di hide dulu
# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Work Order": {"on_update": "employee_portal.doc_events.wo_push_notification.execute"},
	"Material Request": {
		"on_update": "employee_portal.doc_events.mr_push_notification.execute",
		"on_submit": "employee_portal.doc_events.mr_push_notification.execute",
	},
	"Purchase Order": {"on_update": "employee_portal.doc_events.po_push_notification.execute"},
	"Purchase Receipt": {
		"on_update": "employee_portal.doc_events.pr_qc_validation.execute_validation",
		"before_submit": "employee_portal.doc_events.pr_qc_validation.execute_validation",
	},
	"Purchase Invoice": {"on_update": "employee_portal.doc_events.pi_push_notification.execute"},
	"Payment Entry": {"on_update": "employee_portal.doc_events.pe_push_notification.execute"},
	"Quality Inspection": {
		"on_update": "employee_portal.doc_events.qc_push_notification.execute",
		"on_submit": [
			"employee_portal.doc_events.qi_submit_notification.send_notification_on_submit",
			"employee_portal.doc_events.dn_qc_validation.update_delivery_note_on_qi_submit",
			"employee_portal.doc_events.se_qc_validation.update_stock_entry_on_qi_submit",
		],
	},
	"Sales Order": {"on_update": "employee_portal.doc_events.so_push_notification.execute"},
	"Sales Invoice": {"on_update": "employee_portal.doc_events.si_push_notification.execute"},
	"Stock Entry": {
		"before_submit": "employee_portal.doc_events.se_qc_validation.execute_validation",
		"on_update": "employee_portal.doc_events.se_push_notification.execute",
	},
	"Delivery Note": {
		"before_submit": "employee_portal.doc_events.dn_qc_validation.execute_validation",
		"on_update": "employee_portal.doc_events.dn_push_notification.execute",
	},
	"Expense Claim": {
		"on_update": "employee_portal.doc_events.expense_claim_notification.send_notification_on_state_change"
	},
	"Leave Application": {
		"on_update": "employee_portal.doc_events.leave_application_notification.send_notification_on_state_change"
	},
	"Leave Policy": {
		"on_submit": "employee_portal.utils.mass_leave_allocation.create_mass_leave_allocation",
		"on_update": "employee_portal.utils.mass_leave_allocation.create_mass_leave_allocation",
	},
}

# update di quality inspection
# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"employee_portal.tasks.all"
# 	],
# 	"daily": [
# 		"employee_portal.tasks.daily"
# 	],
# 	"hourly": [
# 		"employee_portal.tasks.hourly"
# 	],
# 	"weekly": [
# 		"employee_portal.tasks.weekly"
# 	],
# 	"monthly": [
# 		"employee_portal.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "employee_portal.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "employee_portal.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "employee_portal.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["employee_portal.utils.before_request"]
# after_request = ["employee_portal.utils.after_request"]

# Job Events
# ----------
# before_job = ["employee_portal.utils.before_job"]
# after_job = ["employee_portal.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"employee_portal.custom_auth.custom_employee_login"
# ]

# Commands
# --------

commands = [
    "employee_portal.commands.check_payroll",  # <-- TAMBAHKAN INI
]

override_whitelisted_methods = {
    "frappe.auth.login": "employee_portal.custom_auth.custom_employee_login",
    "hrms.hr.doctype.expense_claim.expense_claim.make_bank_entry": "employee_portal.overrides.expense_claim_payments.make_bank_entry"
}


doctype_js = {
	"Purchase Order": "public/js/purchase_order_status.js",
	"Purchase Invoice": "public/js/purchase_invoice_status.js",
	"Payment Entry": "public/js/payment_entry_status.js",
	"Material Request": "public/js/material_request_status.js",
	"Sales Order": "public/js/sales_order_status.js",
	"Work Order": "public/js/work_order_status.js",
	"Quality Inspection": "public/js/quality_inspection_status.js",
	"Delivery Note": "public/js/delivery_note_status.js",
	"Stock Entry": "public/js/stock_entry_status.js",
}

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
# File: my_custom_app/hooks.py

# File: hooks.py (Bagian workflow_methods)

# workflow_methods = {
#     "Material Request": {
#         "submit": "employee_portal.templates.mr_notification.handle_submit_transition",
#         "approve": "employee_portal.templates.mr_notification.handle_approval_transition",
#         "reject": "employee_portal.templates.mr_notification.handle_rejection_transition",
#     }
# }
