import frappe

from frapkeys.presets.registry import PRESETS, get_preset_names, restore_active_preset


@frappe.whitelist()
def get_presets():
	frappe.only_for("System Manager")
	return [
		{
			"name": name,
			"description": PRESETS.get(name, {}).get(
				"description", "Disable code-backed preset shortcuts."
			),
			"shortcut_count": len(PRESETS.get(name, {}).get("shortcuts", [])),
		}
		for name in get_preset_names()
	]


@frappe.whitelist(methods=["POST"])
def restore_preset():
	frappe.only_for("System Manager")
	return restore_active_preset()
