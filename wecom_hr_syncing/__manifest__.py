# -*- coding: utf-8 -*-
{
    "name": "WeCom Hr Syncing",
    "author": "RStudio",
    "website": "https://gitee.com/rainbowstudio/wxwork",
    "sequence": 608,
    "installable": True,
    "application": True,
    "auto_install": False,
    "category": "WeCom/WeCom",
    "version": "14.0.0.1",
    "summary": """
        WeCom users are synchronized to Odoo Hr and Users
        """,
    "description": """


        """,
    "depends": [
        "base",
        "mail",
        "wecom_api",
        "wecom_hr",
    ],
    "external_dependencies": {
        "python": [],
    },
    # "external_dependencies": {"python": ["numpy", "opencv-python",],},
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "data/auth_oauth_data.xml",
        "views/ir_cron_views.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "views/hr_employee_view.xml",
        "views/res_users_views.xml",
        "wizard/wizard_wecom_contacts_sync.xml",
        "wizard/wizard_wecom_sync_user.xml",
        "wizard/wizard_wecom_sync_tag.xml",
        "views/assets_templates.xml",
        "views/menu_views.xml",
    ],
    "qweb": [
        "static/src/xml/*.xml",
    ],
}