import { createApp } from "vue";
import FrapkeysWidget from "./frapkeys/FrapkeysWidget.vue";
import ShortcutRecorder from "./frapkeys/ShortcutRecorder.vue";

if (window.frappe?.ui?.form?.on) {
	window.frappe.ui.form.on("Frapkeys Settings", {
		active_preset(frm) {
			const preset = frm.__frapkeysPresets?.find((item) => item.name === frm.doc.active_preset);
			if (!preset) return;
			frm.set_df_property(
				"active_preset",
				"description",
				`${preset.description} ${preset.shortcut_count} code-backed shortcuts. Save to apply.`
			);
		},
		refresh(frm) {
			window.frappe.call({
				method: "frapkeys.api.presets.get_presets",
				callback(response) {
					frm.__frapkeysPresets = response.message || [];
					const options = frm.__frapkeysPresets.map((preset) => preset.name);
					if (options.length) frm.set_df_property("active_preset", "options", options.join("\n"));
					frm.trigger("active_preset");
				},
			});

			if (frm.doc.active_preset && frm.doc.active_preset !== "None") {
				frm.add_custom_button(
					"Restore Active Preset",
					() => {
						window.frappe.call({
							method: "frapkeys.api.presets.restore_preset",
							type: "POST",
							freeze: true,
							freeze_message: "Restoring shortcut preset…",
							callback(response) {
								const result = response.message || {};
								window.dispatchEvent(new CustomEvent("frapkeys:refresh"));
								window.frappe.show_alert({
									message: `${result.preset || "Preset"}: ${result.active || 0} shortcuts restored`,
									indicator: "green",
								});
								frm.reload_doc();
							},
						});
					},
					"Presets"
				);
			}
		},
		after_save() {
			window.dispatchEvent(new CustomEvent("frapkeys:refresh"));
		},
	});

	window.frappe.ui.form.on("Frapkeys Shortcut", {
		refresh(frm) {
			const wrapper = frm.fields_dict.key_recorder?.$wrapper?.get(0);
			if (!wrapper || wrapper.__frapkeysRecorderApp) return;

			const recorderApp = createApp(ShortcutRecorder, {
				initialValue: frm.doc.key_combination || "",
				onRecorded: (value) => frm.set_value("key_combination", value),
			});
			recorderApp.mount(wrapper);
			wrapper.__frapkeysRecorderApp = recorderApp;
		},
		after_save() {
			window.dispatchEvent(new CustomEvent("frapkeys:refresh"));
		},
	});
}

(() => {
	if (window.__frapkeysWidgetBooted || window.__frapkeysWidgetBooting) return;

	const AWESOME_BAR_SELECTOR = ".search-bar > .awesomplete";
	let app = null;
	let host = null;
	let payload = null;
	let observer = null;
	let shortcutsRegistered = false;
	const activeModifierCodes = new Set();
	const modifierTokenByCode = {
		ControlLeft: "left_ctrl",
		ControlRight: "right_ctrl",
		MetaLeft: "left_cmd",
		MetaRight: "right_cmd",
		AltLeft: "left_alt",
		AltRight: "right_alt",
		ShiftLeft: "left_shift",
		ShiftRight: "right_shift",
	};
	const genericModifierByToken = {
		left_ctrl: "ctrl",
		right_ctrl: "ctrl",
		left_cmd: "ctrl",
		right_cmd: "ctrl",
		left_alt: "alt",
		right_alt: "alt",
		left_shift: "shift",
		right_shift: "shift",
	};
	const modifierTokens = new Set([
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
	]);

	function keyFromEvent(event) {
		if (/^Key[A-Z]$/.test(event.code)) return event.code.slice(3).toLowerCase();
		if (/^Digit[0-9]$/.test(event.code)) return event.code.slice(5);
		if (/^F([1-9]|1[0-2])$/.test(event.code)) return event.code.toLowerCase();

		const codeKeys = {
			Slash: "/",
			Period: ".",
			Comma: ",",
			Semicolon: ";",
			Quote: "'",
			BracketLeft: "[",
			BracketRight: "]",
			Minus: "-",
			Equal: "=",
		};
		if (codeKeys[event.code]) return codeKeys[event.code];

		const aliases = {
			" ": "space",
			Escape: "esc",
			ArrowUp: "up",
			ArrowDown: "down",
			ArrowLeft: "left",
			ArrowRight: "right",
			PageUp: "pageup",
			PageDown: "pagedown",
		};
		return aliases[event.key] || String(event.key || "").toLowerCase();
	}

	function activeModifierTokens(event) {
		const tokens = [...activeModifierCodes].map((code) => modifierTokenByCode[code]);
		const genericTokens = new Set(tokens.map((token) => genericModifierByToken[token]));

		// Fall back to generic modifiers if this tab did not receive the modifier keydown.
		if ((event.ctrlKey || event.metaKey) && !genericTokens.has("ctrl")) tokens.push("ctrl");
		if (event.altKey && !genericTokens.has("alt")) tokens.push("alt");
		if (event.shiftKey && !genericTokens.has("shift")) tokens.push("shift");
		return tokens;
	}

	function matchesShortcut(value, key, pressedModifiers) {
		const parts = String(value || "")
			.toLowerCase()
			.split("+")
			.map((part) => part.trim())
			.filter(Boolean);
		const storedKey = parts.find((part) => !modifierTokens.has(part));
		const requiredModifiers = new Set(parts.filter((part) => modifierTokens.has(part)));
		if (!storedKey || storedKey !== key) return false;

		for (const required of requiredModifiers) {
			if (["ctrl", "alt", "shift"].includes(required)) {
				const familyIsPressed = pressedModifiers.some(
					(token) => token === required || genericModifierByToken[token] === required
				);
				if (!familyIsPressed) return false;
			} else if (!pressedModifiers.includes(required)) {
				return false;
			}
		}

		return pressedModifiers.every((token) => {
			const generic = genericModifierByToken[token];
			return requiredModifiers.has(token) || (generic && requiredModifiers.has(generic));
		});
	}

	function isTypingTarget(target) {
		return Boolean(target?.closest?.("input, select, textarea, [contenteditable='true']"));
	}

	function dispatchShortcut(shortcut) {
		switch (shortcut.action_type) {
			case "Open Internal Route": {
				const route = String(shortcut.target_route || "").replace(/^\/app\/?/, "");
				if (route) window.frappe.set_route(route);
				break;
			}
			case "Open External Link": {
				try {
					const url = new URL(shortcut.external_url);
					if (!["http:", "https:"].includes(url.protocol)) return;
					window.open(url.href, "_blank", "noopener,noreferrer");
				} catch (error) {
					console.warn("Frapkeys blocked an invalid external URL.", error);
				}
				break;
			}
			case "Open DocType List":
				if (shortcut.target_doctype) {
					window.frappe.set_route("List", shortcut.target_doctype);
				}
				break;
			case "Create Document":
				if (shortcut.target_doctype) window.frappe.new_doc(shortcut.target_doctype);
				break;
			case "Open Report":
				if (shortcut.target_report) {
					window.frappe.set_route("query-report", shortcut.target_report);
				}
				break;
			case "Focus Global Search":
				document.querySelector("#navbar-search")?.focus();
				break;
			case "Go Home":
				window.frappe.set_route("");
				break;
			case "Open Frapkeys Modal":
				window.dispatchEvent(new CustomEvent("frapkeys:open"));
				break;
		}
	}

	function registerShortcuts() {
		if (shortcutsRegistered) return;

		window.addEventListener(
			"keydown",
			(event) => {
				if (modifierTokenByCode[event.code]) {
					activeModifierCodes.add(event.code);
					return;
				}
				if (document.querySelector(".frapkeys-recorder__value.is-recording")) return;

				const key = keyFromEvent(event);
				if (!key || ["control", "meta", "alt", "shift"].includes(key)) return;
				const pressedModifiers = activeModifierTokens(event);
				const shortcuts = payload?.shortcuts || [];
				const shortcut = shortcuts.find(
					(item) => matchesShortcut(item.key_combination, key, pressedModifiers)
				);
				if (!shortcut) return;
				if (isTypingTarget(event.target) && !Boolean(shortcut.ignore_when_typing)) return;

				event.preventDefault();
				event.stopPropagation();
				event.stopImmediatePropagation();
				console.log("[Frapkeys] Shortcut hit", {
					shortcut: shortcut.key_combination,
					pressed_shortcut: [...pressedModifiers, key].join("+"),
					name: shortcut.shortcut_name,
					action: shortcut.action_type,
					key: event.key,
					code: event.code,
					platform: /Mac|iPhone|iPad|iPod/i.test(
						navigator.userAgentData?.platform || navigator.platform || ""
					)
						? "macOS"
						: "Windows/Linux",
				});
				dispatchShortcut(shortcut);
			},
			true
		);
		window.addEventListener(
			"keyup",
			(event) => {
				if (modifierTokenByCode[event.code]) activeModifierCodes.delete(event.code);
			},
			true
		);
		window.addEventListener("blur", () => activeModifierCodes.clear());
		console.log(
			"[Frapkeys] Shortcuts registered",
			(payload?.shortcuts || []).map((shortcut) => shortcut.key_combination)
		);
		shortcutsRegistered = true;
	}

	async function refreshShortcuts(showConfirmation = false) {
		const response = await fetch("/api/method/frapkeys.api.shortcuts.get_shortcuts", {
			headers: { Accept: "application/json" },
			credentials: "same-origin",
		});
		const result = await response.json();
		if (!response.ok || !result.message) throw new Error("Unable to refresh Frapkeys shortcuts.");

		payload = result.message;
		if (payload.enabled) registerShortcuts();
		window.dispatchEvent(
			new CustomEvent("frapkeys:shortcuts-refreshed", { detail: payload })
		);
		console.log(
			"[Frapkeys] Shortcuts refreshed",
			(payload.shortcuts || []).map((shortcut) => shortcut.key_combination)
		);
		if (showConfirmation) {
			window.frappe?.show_alert?.({ message: "Keyboard shortcuts refreshed", indicator: "green" });
		}
	}

	function mountBesideAwesomeBar() {
		const awesomeBar = document.querySelector(AWESOME_BAR_SELECTOR);
		if (!awesomeBar) return false;
		awesomeBar.parentElement?.classList.add("frapkeys-mounted");

		if (!host) {
			host = document.createElement("div");
			host.id = "frapkeys-widget-host";
		}

		if (host.nextElementSibling !== awesomeBar) {
			awesomeBar.before(host);
		}

		if (!app) {
			app = createApp(FrapkeysWidget, {
				initialShortcuts: payload?.shortcuts || [],
				canManage:
					Boolean(payload?.can_manage) ||
					Boolean(window.frappe?.user_roles?.includes("System Manager")),
			});
			app.mount(host);
			window.__frapkeysWidgetBooted = true;
			console.log("[Frapkeys] Launcher mounted before .awesomplete", host);
		}

		return true;
	}

	function watchNavbar() {
		if (observer) return;
		observer = new MutationObserver(mountBesideAwesomeBar);
		observer.observe(document.body, { childList: true, subtree: true });
	}

	async function bootWidget() {
		if (window.__frapkeysWidgetBooted || window.__frapkeysWidgetBooting) return;
		window.__frapkeysWidgetBooting = true;
		watchNavbar();
		mountBesideAwesomeBar();

		try {
			await refreshShortcuts();
		} catch (error) {
			console.warn("Frapkeys could not load its settings.", error);
		} finally {
			window.__frapkeysWidgetBooting = false;
		}
	}

	window.addEventListener("frapkeys:refresh", () => {
		refreshShortcuts(true).catch((error) => {
			console.warn("Frapkeys could not refresh its shortcuts.", error);
		});
	});

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", bootWidget, { once: true });
	} else {
		bootWidget();
	}
})();
