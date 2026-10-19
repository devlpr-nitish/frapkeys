import frappe
from frappe import _
from frappe.model.document import Document

from frapkeys.frapkeys.doctype.frapkeys_shortcut.frapkeys_shortcut import (
	key_combinations_overlap,
	normalize_key_combination,
)
from frapkeys.presets import get_preset_names, synchronize_preset, validate_preset_activation
from frapkeys.presets.registry import PRESET_ALIASES


class FrapkeysSettings(Document):
	def validate(self):
		self.open_shortcut_dialog_key = normalize_key_combination(
			self.open_shortcut_dialog_key or "left_ctrl+left_shift+k"
		)
		self.validate_dialog_shortcut_conflict()
		self.active_preset = PRESET_ALIASES.get(self.active_preset, self.active_preset) or "None"
		if self.active_preset not in get_preset_names():
			frappe.throw(_("Unknown Frapkeys preset: {0}").format(self.active_preset))
		validate_preset_activation(self.active_preset)

	def on_update(self):
		synchronize_preset(self.active_preset)

	def validate_dialog_shortcut_conflict(self):
		for shortcut in frappe.get_all(
			"Frapkeys Shortcut",
			filters={"enabled": 1},
			fields=["shortcut_name", "key_combination"],
		):
			if key_combinations_overlap(
				self.open_shortcut_dialog_key, shortcut.key_combination
			):
				frappe.throw(
					_("Modal shortcut overlaps with enabled shortcut {0} ({1}).").format(
						frappe.bold(shortcut.shortcut_name), shortcut.key_combination
					)
				)
