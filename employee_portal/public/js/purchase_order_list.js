frappe.listview_settings['Purchase Order'] = {
    formatters: {
        workflow_state: function(value) {
            let color = {
                "Draft": "darkgrey",
                "Pending Approval (Manager)": "orange",
                "Pending Approval (Director)": "orange",
                "Approved": "green",
                "Rejected": "red"
            }[value] || "darkgrey";
            return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        }
    }
};