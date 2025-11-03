frappe.listview_settings['Sales Order'] = {
    formatters: {
        workflow_state: function(value) {
            let color = {
                "Draft": "darkgrey",
                "Pending Approval (Sales Manager)": "orange",
                "Pending Approval (Finance Manager)": "orange",
                "Pending Approval (Director)": "orange",
                "Approved": "green",
                "Rejected": "red"
            }[value] || "darkgrey";
            return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        }
    }
};