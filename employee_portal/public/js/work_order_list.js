frappe.listview_settings['Work Order'] = {
    formatters: {
        workflow_state: function(value) {
            let color = {
                "Draft": "darkgrey",
                "Pending Approval (Manager)": "orange",
                "Approved": "green",
                "Rejected": "red"
            }[value] || "darkgrey";
            return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        }
    }
};