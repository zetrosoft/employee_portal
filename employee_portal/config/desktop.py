from frappe import _


def get_data():
    return [
        {
            # Definisikan Modul Baru Anda
            "module_name": "Employee Portal",
            "color": "#1abc9c", # Pilih warna yang Anda suka
            "icon": "octicon octicon-person",
            "type": "module",
            "label": _("Portal Karyawan"),
            "links": [
                {
                    "label": _("Pengajuan Cuti"),
                    "type": "doctype",
                    "name": "Leave Application", # DocType ERPNext yang sudah ada
                    "onboard": 1,
                },
                {
                    "label": _("Klaim Biaya"),
                    "type": "doctype",
                    "name": "Expense Claim", # DocType ERPNext yang sudah ada
                    "onboard": 1,
                },
                # Anda dapat menambahkan tautan lain di sini
            ]
        }
    ]
