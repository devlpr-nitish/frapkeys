import re
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document

MODIFIER_ORDER = (
	"ctrl",
	"left_ctrl",
	"right_ctrl",
	"left_cmd",
	"right_cmd",
	"alt",
	"left_alt",
	"right_alt",
	"shift",
	"left_shift",
	"right_shift",
)
KEY_ALIASES = {
	"control": "ctrl",
	"command": "ctrl",
	"cmd": "ctrl",
	"meta": "ctrl",
	"option": "alt",
	"control_left": "left_ctrl",
	"control_right": "right_ctrl",
	"command_left": "left_cmd",
	"command_right": "right_cmd",
	"option_left": "left_alt",
	"option_right": "right_alt",
	"ctrl_left": "left_ctrl",
	"ctrl_right": "right_ctrl",
	"cmd_left": "left_cmd",
	"cmd_right": "right_cmd",
	"alt_left": "left_alt",
	"alt_right": "right_alt",
	"shift_left": "left_shift",
	"shift_right": "right_shift",
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
MODIFIER_FAMILIES = {
	"ctrl": {"ctrl", "left_ctrl", "right_ctrl", "left_cmd", "right_cmd"},
	"alt": {"alt", "left_alt", "right_alt"},
	"shift": {"shift", "left_shift", "right_shift"},
}


class FrapkeysShortcut(Document):
	def validate(self):
		self.key_combination = normalize_key_combination(self.key_combination)
		self.validate_action_target()
		self.validate_key_conflict()

	def validate_action_target(self):
		if self.action_type in {"Open DocType List", "Create Document"} and not self.target_doctype:
			frappe.throw(_("Target DocType is required for {0}.").format(self.action_type))

		if self.action_type == "Open Internal Route" and not self.target_route:
			frappe.throw(_("Target Route is required for Open Internal Route."))

		if self.action_type == "Open External Link":
			self.validate_external_url()

		if self.action_type == "Open Report" and not self.target_report:
			frappe.throw(_("Target Report is required for Open Report."))

		if self.action_type == "Run Document Action" and not self.document_action:
			frappe.throw(_("Document Action is required for Run Document Action."))

		if self.scope in {"Form", "List", "Report"} and not self.scope_doctype:
			frappe.throw(_("Scope DocType is required for {0} scope.").format(self.scope))

	def validate_external_url(self):
		self.external_url = normalize_external_url(self.external_url)

	def validate_key_conflict(self):
		if not self.enabled:
			return

		for shortcut in frappe.get_all(
			"Frapkeys Shortcut",
			filters={"enabled": 1, "name": ["!=", self.name or ""]},
			fields=["name", "shortcut_name", "key_combination"],
		):
			if key_combinations_overlap(self.key_combination, shortcut.key_combination):
				frappe.throw(
					_("Key combination overlaps with enabled shortcut {0} ({1}).").format(
						frappe.bold(shortcut.shortcut_name),
						shortcut.key_combination,
					)
				)


def normalize_key_combination(value):
	parts = [part.strip().lower() for part in (value or "").split("+") if part.strip()]
	parts = [KEY_ALIASES.get(part, part) for part in parts]
	modifiers = {part for part in parts if part in MODIFIER_ORDER}
	keys = [part for part in parts if part not in MODIFIER_ORDER]

	if len(keys) != 1 or len(parts) != len(modifiers) + 1:
		frappe.throw(
			_("Enter one key with optional Ctrl, Command, Alt, and Shift modifiers.")
		)

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


def normalize_external_url(value):
	value = (value or "").strip()
	parsed_url = urlparse(value)
	if parsed_url.scheme.lower() not in {"http", "https"} or not parsed_url.netloc:
		frappe.throw(_("Enter a complete external URL beginning with http:// or https://."))
	return value


def key_combinations_overlap(first, second):
	"""Return whether two combinations can be triggered by the same physical keys."""
	first_parts = set(normalize_key_combination(first).split("+"))
	second_parts = set(normalize_key_combination(second).split("+"))
	first_key = next((part for part in first_parts if part not in MODIFIER_ORDER), None)
	second_key = next((part for part in second_parts if part not in MODIFIER_ORDER), None)
	if not first_key or first_key != second_key:
		return False

	for generic, family in MODIFIER_FAMILIES.items():
		first_required = first_parts.intersection(family)
		second_required = second_parts.intersection(family)
		if not first_required and not second_required:
			continue
		if not first_required or not second_required:
			return False
		if generic in first_required or generic in second_required:
			continue
		if first_required != second_required:
			return False

	return True
