# employee_portal/hooks.py

app_name = "employee_portal"
app_title = "Employee Portal"
app_publisher = "Your Company Name"
app_description = "Employee portal for siumang."
app_email = "your-email@example.com"
app_license = "MIT"

doc_events = {
    "Material Request": {
        "on_update": "employee_portal.doc_events.material_request.trigger_notifications"
    }
}