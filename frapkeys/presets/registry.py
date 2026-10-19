import frappe
from frappe import _
from frappe.utils.data import escape_html

from frapkeys.frapkeys.doctype.frapkeys_shortcut.frapkeys_shortcut import (
	key_combinations_overlap,
	normalize_key_combination,
)

NO_PRESET = "None"
PRESET_ALIASES = {"Frappe Defaults": "Default", "Tally Inspired": "Tally"}

PRESETS = {
	"Default": {
		"description": "Useful Frappe Desk navigation shortcuts.",
		"shortcuts": [
			{
				"preset_key": "default.focus_search",
				"shortcut_name": "Focus Global Search",
				"key_combination": "ctrl+shift+space",
				"description": "Focus the Desk global search box.",
				"action_type": "Focus Global Search",
				"priority": 90,
			},
			{
				"preset_key": "default.go_home",
				"shortcut_name": "Go to Desk Home",
				"key_combination": "alt+shift+h",
				"description": "Open the Desk home page.",
				"action_type": "Go Home",
				"priority": 80,
			},
			{
				"preset_key": "default.sales_invoice_list",
				"shortcut_name": "Open Sales Invoice List (Default)",
				"key_combination": "ctrl+shift+1",
				"description": "Open the Sales Invoice list.",
				"action_type": "Open DocType List",
				"target_doctype": "Sales Invoice",
				"priority": 70,
			},
			{
				"preset_key": "default.sales_order_list",
				"shortcut_name": "Open Sales Order List (Default)",
				"key_combination": "ctrl+shift+2",
				"description": "Open the Sales Order list.",
				"action_type": "Open DocType List",
				"target_doctype": "Sales Order",
				"priority": 60,
			},
		],
	},
	"Tally": {
		"description": "Tally-inspired ERPNext accounting shortcuts.",
		"shortcuts": [
			{
				"preset_key": "tally.journal_list",
				"shortcut_name": "Tally F4 - Journal Entries",
				"key_combination": "f4",
				"description": "Open the Journal Entry list.",
				"action_type": "Open DocType List",
				"target_doctype": "Journal Entry",
				"priority": 90,
			},
			{
				"preset_key": "tally.new_payment",
				"shortcut_name": "Tally F5 - New Payment Entry",
				"key_combination": "f5",
				"description": "Create a Payment Entry.",
				"action_type": "Create Document",
				"target_doctype": "Payment Entry",
				"priority": 80,
			},
			{
				"preset_key": "tally.payment_list",
				"shortcut_name": "Tally F6 - Payment Entries",
				"key_combination": "f6",
				"description": "Open the Payment Entry list.",
				"action_type": "Open DocType List",
				"target_doctype": "Payment Entry",
				"priority": 70,
			},
			{
				"preset_key": "tally.new_journal",
				"shortcut_name": "Tally F7 - New Journal Entry",
				"key_combination": "f7",
				"description": "Create a Journal Entry.",
				"action_type": "Create Document",
				"target_doctype": "Journal Entry",
				"priority": 60,
			},
			{
				"preset_key": "tally.new_sales_invoice",
				"shortcut_name": "Tally F8 - New Sales Invoice",
				"key_combination": "f8",
				"description": "Create a Sales Invoice.",
				"action_type": "Create Document",
				"target_doctype": "Sales Invoice",
				"priority": 50,
			},
			{
				"preset_key": "tally.new_purchase_invoice",
				"shortcut_name": "Tally F9 - New Purchase Invoice",
				"key_combination": "f9",
				"description": "Create a Purchase Invoice.",
				"action_type": "Create Document",
				"target_doctype": "Purchase Invoice",
				"priority": 40,
			},
		],
	},
}


def get_preset_names():
	return [NO_PRESET, *PRESETS]


def get_preset(name):
	name = PRESET_ALIASES.get(name, name)
	if name == NO_PRESET:
		return {"description": "Disable code-backed preset shortcuts.", "shortcuts": []}
	if name not in PRESETS:
		frappe.throw(_("Unknown Frapkeys preset: {0}").format(name))
	return PRESETS[name]


def get_available_shortcuts(name):
	name = PRESET_ALIASES.get(name, name)
	shortcuts = []
	for shortcut in get_preset(name)["shortcuts"]:
		target_doctype = shortcut.get("target_doctype")
		if target_doctype and not frappe.db.exists("DocType", target_doctype):
			continue
		shortcuts.append(
			{
				**shortcut,
				"key_combination": normalize_key_combination(shortcut["key_combination"]),
			}
		)
	return shortcuts


def validate_preset_activation(name):
	name = PRESET_ALIASES.get(name, name)
	definitions = get_available_shortcuts(name)
	for index, definition in enumerate(definitions):
		for other in definitions[index + 1 :]:
			if key_combinations_overlap(definition["key_combination"], other["key_combination"]):
				frappe.throw(
					_("Preset {0} contains overlapping shortcuts {1} and {2}.").format(
						name, definition["shortcut_name"], other["shortcut_name"]
					)
				)

	custom_shortcuts = frappe.get_all(
		"Frapkeys Shortcut",
		filters={"enabled": 1, "is_standard_preset": 0},
		fields=["shortcut_name", "key_combination"],
	)
	conflicts = []
	for definition in definitions:
		for custom in custom_shortcuts:
			if key_combinations_overlap(definition["key_combination"], custom.key_combination):
				conflicts.append(
					f"{definition['shortcut_name']} ({definition['key_combination']}) ↔ "
					f"{custom.shortcut_name} ({custom.key_combination})"
				)
	if conflicts:
		frappe.throw(
			_("Preset cannot be activated because these enabled shortcuts overlap:<br>{0}").format(
				"<br>".join(escape_html(conflict) for conflict in conflicts)
			)
		)
	return definitions


def synchronize_preset(preset_name):
	preset_name = PRESET_ALIASES.get(preset_name, preset_name)
	definitions = validate_preset_activation(preset_name)
	desired_keys = {definition["preset_key"] for definition in definitions}

	for row in frappe.get_all(
		"Frapkeys Shortcut",
		filters={"is_standard_preset": 1},
		fields=["name", "preset_key", "enabled"],
	):
		if row.preset_key not in desired_keys and row.enabled:
			frappe.db.set_value("Frapkeys Shortcut", row.name, "enabled", 0)

	created = 0
	updated = 0
	for definition in definitions:
		document_name = frappe.db.get_value(
			"Frapkeys Shortcut", {"preset_key": definition["preset_key"]}, "name"
		)
		if not document_name:
			name_collision = frappe.db.get_value(
				"Frapkeys Shortcut", {"shortcut_name": definition["shortcut_name"]}, "name"
			)
			if name_collision:
				frappe.throw(
					_("Cannot restore preset shortcut {0} because that title is already in use.").format(
						frappe.bold(definition["shortcut_name"])
					)
				)
		doc = (
			frappe.get_doc("Frapkeys Shortcut", document_name)
			if document_name
			else frappe.new_doc("Frapkeys Shortcut")
		)
		for fieldname, value in definition.items():
			doc.set(fieldname, value)
		doc.enabled = 1
		doc.scope = "Global"
		doc.is_standard_preset = 1
		doc.save(ignore_permissions=True)
		if document_name:
			updated += 1
		else:
			created += 1

	return {
		"preset": preset_name,
		"created": created,
		"updated": updated,
		"active": len(definitions),
	}


def restore_active_preset():
	settings = frappe.get_single("Frapkeys Settings")
	return synchronize_preset(settings.active_preset or NO_PRESET)
