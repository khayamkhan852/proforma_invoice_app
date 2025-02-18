app_name = "proforma_invoice_app"
app_title = "Proforma Invoice App"
app_publisher = "Khayam Khan"
app_description = "Custom Frappe ERPNext application for For Creating Proforma Invoice"
app_email = "khayamkhan852@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "proforma_invoice_app",
# 		"logo": "/assets/proforma_invoice_app/logo.png",
# 		"title": "Proforma Invoice App",
# 		"route": "/proforma_invoice_app",
# 		"has_permission": "proforma_invoice_app.api.permission.has_app_permission"
# 	}
# ]

fixtures = [
    {
        "dt": "Custom Field", "filters": [
            [
                "name", "in", [
                    "Sales Invoice Item-custom_proforma",
                    "Sales Invoice Item-custom_proforma_item",
                    "Work Order-custom_proforma",
                    "Work Order-custom_proforma_item",
                    "Material Request Item-custom_proforma",
                    "Material Request Item-custom_proforma_item",
                    "Purchase Order Item-custom_proforma",
                    "Purchase Order Item-custom_proforma_item"
                ]
            ]
        ]
    },
]


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/proforma_invoice_app/css/proforma_invoice_app.css"
# app_include_js = "/assets/proforma_invoice_app/js/proforma_invoice_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/proforma_invoice_app/css/proforma_invoice_app.css"
# web_include_js = "/assets/proforma_invoice_app/js/proforma_invoice_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "proforma_invoice_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "proforma_invoice_app/public/icons.svg"

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
# 	"methods": "proforma_invoice_app.utils.jinja_methods",
# 	"filters": "proforma_invoice_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "proforma_invoice_app.install.before_install"
# after_install = "proforma_invoice_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "proforma_invoice_app.uninstall.before_uninstall"
# after_uninstall = "proforma_invoice_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "proforma_invoice_app.utils.before_app_install"
# after_app_install = "proforma_invoice_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "proforma_invoice_app.utils.before_app_uninstall"
# after_app_uninstall = "proforma_invoice_app.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "proforma_invoice_app.notifications.get_notification_config"

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

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

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
# 		"proforma_invoice_app.tasks.all"
# 	],
# 	"daily": [
# 		"proforma_invoice_app.tasks.daily"
# 	],
# 	"hourly": [
# 		"proforma_invoice_app.tasks.hourly"
# 	],
# 	"weekly": [
# 		"proforma_invoice_app.tasks.weekly"
# 	],
# 	"monthly": [
# 		"proforma_invoice_app.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "proforma_invoice_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "proforma_invoice_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "proforma_invoice_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["proforma_invoice_app.utils.before_request"]
# after_request = ["proforma_invoice_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["proforma_invoice_app.utils.before_job"]
# after_job = ["proforma_invoice_app.utils.after_job"]

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
# 	"proforma_invoice_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

