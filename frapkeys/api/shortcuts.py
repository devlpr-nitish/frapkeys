import frappe
from frappe import _
from frappe.utils import cint


@frappe.whitelist()
def get_shortcuts():
	"""Return enabled shortcut definitions visible to the current Desk user."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to view shortcuts."), frappe.PermissionError)

	settings = frappe.get_single("Frapkeys Settings")
	enabled = bool(cint(settings.enabled))
	show_navbar_icon = bool(cint(settings.show_navbar_icon))
	response = {
		"enabled": enabled,
		"show_navbar_icon": show_navbar_icon,
		"can_manage": frappe.has_permission("Frapkeys Shortcut", "write"),
		"shortcuts": [],
	}
	if not enabled:
		return response

	shortcuts = frappe.get_all(
		"Frapkeys Shortcut",
		filters={"enabled": 1},
		fields=[
			"name",
			"shortcut_name",
			"key_combination",
			"description",
			"action_type",
			"target_doctype",
			"target_route",
			"target_report",
			"document_action",
			"scope",
			"scope_doctype",
			"ignore_when_typing",
			"priority",
		],
		order_by="priority desc, shortcut_name asc",
	)
	if not shortcuts:
		return response

	role_rows = frappe.get_all(
		"Frapkeys Shortcut Role",
		filters={
			"parent": ["in", [shortcut.name for shortcut in shortcuts]],
			"parenttype": "Frapkeys Shortcut",
		},
		fields=["parent", "role"],
	)
	roles_by_shortcut = {}
	for row in role_rows:
		roles_by_shortcut.setdefault(row.parent, set()).add(row.role)

	user_roles = set(frappe.get_roles())
	response["shortcuts"] = [
		shortcut
		for shortcut in shortcuts
		if not roles_by_shortcut.get(shortcut.name)
		or roles_by_shortcut[shortcut.name].intersection(user_roles)
	]
	return response
