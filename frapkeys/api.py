import frappe
from frappe import _
from frappe.utils import cint


@frappe.whitelist()
def get_shortcuts():
	"""Return the enabled shortcut definitions visible to the current Desk user."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to view shortcuts."), frappe.PermissionError)

	enabled = frappe.db.get_single_value("Frapkeys Settings", "enabled")
	show_navbar_icon = frappe.db.get_single_value("Frapkeys Settings", "show_navbar_icon")

	# A newly installed Single has no values until it is saved for the first time.
	if enabled is not None and not cint(enabled):
		return {"enabled": False, "show_navbar_icon": cint(show_navbar_icon), "shortcuts": []}

	shortcuts = frappe.get_all(
		"Frapkeys Shortcut",
		filters={"enabled": 1},
		fields=[
			"name",
			"shortcut_name",
			"key_combination",
			"description",
			"action_type",
			"scope",
			"scope_doctype",
			"priority",
		],
		order_by="priority desc, shortcut_name asc",
	)

	if not shortcuts:
		return {
			"enabled": True,
			"show_navbar_icon": True if show_navbar_icon is None else bool(cint(show_navbar_icon)),
			"shortcuts": [],
		}

	shortcut_names = [shortcut.name for shortcut in shortcuts]
	role_rows = frappe.get_all(
		"Frapkeys Shortcut Role",
		filters={"parent": ["in", shortcut_names], "parenttype": "Frapkeys Shortcut"},
		fields=["parent", "role"],
	)
	roles_by_shortcut = {}
	for row in role_rows:
		roles_by_shortcut.setdefault(row.parent, set()).add(row.role)

	user_roles = set(frappe.get_roles())
	visible_shortcuts = [
		shortcut
		for shortcut in shortcuts
		if not roles_by_shortcut.get(shortcut.name)
		or roles_by_shortcut[shortcut.name].intersection(user_roles)
	]

	return {
		"enabled": True,
		"show_navbar_icon": True if show_navbar_icon is None else bool(cint(show_navbar_icon)),
		"shortcuts": visible_shortcuts,
	}
