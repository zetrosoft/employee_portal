frappe.listview_settings['Stock Entry'] = {
    formatters: {
        workflow_state: function(value) {
            if (!value) return;
            let color = {
                "Draft": "darkgrey",
                "Pending PM Approval": "orange",
                "Pending QC Inspection": "#3498DB", // Blue
                "Approved QC": "#1ABC9C", // Turquoise
                "Rejected QC": "#9B59B6", // Purple
                "Submitted": "green",
                "Rejected": "red",
                "Closed": "#2C3E50" // Dark Slate
            }[value] || "darkgrey";
            return `<span style="color: ${color}; font-weight: bold;">${value}</span>`;
        }
    }
};
