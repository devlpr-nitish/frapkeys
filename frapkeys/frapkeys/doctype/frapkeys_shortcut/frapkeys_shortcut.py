import re

import frappe
from frappe import _
from frappe.model.document import Document


MODIFIER_ORDER = ("ctrl", "alt", "shift")
KEY_ALIASES = {
	"control": "ctrl",
	"command": "ctrl",
	"cmd": "ctrl",
	"meta": "ctrl",
	"option": "alt",
	"escape": "esc",
	"return": "enter",
}
VALID_NAMED_KEYS = {
	"backspace",
	"delete",
	"down",
	"end",
	"enter",
	"esc",
	"home",
	"left",
	"pagedown",
	"pageup",
	"right",
	"space",
	"tab",
	"up",
}


class FrapkeysShortcut(Document):
	def validate(self):
		self.key_combination = normalize_key_combination(self.key_combination)
		self.validate_action_target()

	def validate_action_target(self):
		if self.action_type in {"Open DocType List", "Create Document"} and not self.target_doctype:
			frappe.throw(_("Target DocType is required for {0}.").format(self.action_type))

		if self.action_type == "Open Internal Route" and not self.target_route:
			frappe.throw(_("Target Route is required for Open Internal Route."))

		if self.action_type == "Open Report" and not self.target_report:
			frappe.throw(_("Target Report is required for Open Report."))

		if self.action_type == "Run Document Action" and not self.document_action:
			frappe.throw(_("Document Action is required for Run Document Action."))

		if self.scope in {"Form", "List", "Report"} and not self.scope_doctype:
			frappe.throw(_("Scope DocType is required for {0} scope.").format(self.scope))


def normalize_key_combination(value):
	parts = [part.strip().lower() for part in (value or "").split("+") if part.strip()]
	parts = [KEY_ALIASES.get(part, part) for part in parts]
	modifiers = {part for part in parts if part in MODIFIER_ORDER}
	keys = [part for part in parts if part not in MODIFIER_ORDER]

	if len(keys) != 1 or len(parts) != len(modifiers) + 1:
		frappe.throw(_("Enter one key with optional Ctrl, Alt, and Shift modifiers."))

	key = keys[0]
	valid_key = (
		bool(re.fullmatch(r"[a-z0-9]", key))
		or bool(re.fullmatch(r"f([1-9]|1[0-2])", key))
		or key in VALID_NAMED_KEYS
		or key in {"/", ".", ",", ";", "'", "[", "]", "-", "="}
	)
	if not valid_key:
		frappe.throw(_("Unsupported shortcut key: {0}").format(key))

	return "+".join([modifier for modifier in MODIFIER_ORDER if modifier in modifiers] + [key])
