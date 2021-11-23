# -*- coding: utf-8 -*-

{
    "name": "WeCom Base",
    "author": "RStudio",
    "sequence": 600,
    "installable": True,
    "application": True,
    "auto_install": False,
    "category": "WeCom/WeCom",
    "website": "https://gitee.com/rainbowstudio/wxwork",
    "version": "14.0.0.1",
    "summary": """
        
        """,
    "description": """

        """,
    "depends": ["base_setup", "wecom_l10n", "wecom_widget"],
    "data": [
        "security/wecom_base_security.xml",
        "data/ir_module_category_data.xml",
        "data/res_company_data.xml",
        "views/assets_templates.xml",
        "views/res_config_settings_views.xml",
        "views/res_company_views.xml",
        "views/res_users_views.xml",
        "views/menu.xml",
    ],
    "qweb": [
        "static/src/xml/*.xml",
    ],
    "external_dependencies": {
        "python": [],
    },
    # "post_init_hook": "_open_wecom_settings",
}