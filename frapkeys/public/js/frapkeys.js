frappe.provide("frapkeys");

(() => {
	const BUTTON_ID = "frapkeys-navbar-button";

	const escape_html = (value) => frappe.utils.escape_html(value == null ? "" : String(value));

	const shortcut_rows = (shortcuts) => {
		if (!shortcuts.length) {
			return `
				<div class="frapkeys-empty-state text-muted">
					${__("No shortcuts have been configured yet.")}
				</div>
			`;
		}

		return shortcuts
			.map(
				(shortcut) => `
					<div class="frapkeys-shortcut-row">
						<div class="frapkeys-shortcut-copy">
							<strong>${escape_html(__(shortcut.shortcut_name))}</strong>
							<div class="text-muted small">${escape_html(__(shortcut.description))}</div>
						</div>
						<kbd>${escape_html(shortcut.key_combination)}</kbd>
					</div>
				`
			)
			.join("");
	};

	frapkeys.show_shortcut_dialog = () => {
		const dialog = new frappe.ui.Dialog({
			title: __("Keyboard Shortcuts"),
			fields: [
				{
					fieldname: "shortcut_list",
					fieldtype: "HTML",
				},
			],
			primary_action_label: __("Close"),
			primary_action: () => dialog.hide(),
		});

		dialog.fields_dict.shortcut_list.$wrapper.html(
			`<div class="frapkeys-loading text-muted">${__("Loading shortcuts…")}</div>`
		);
		dialog.show();

		frappe.call("frapkeys.api.get_shortcuts").then(({ message }) => {
			if (!message || !message.enabled) {
				dialog.fields_dict.shortcut_list.$wrapper.html(
					`<div class="frapkeys-empty-state text-muted">${__("Frapkeys is disabled.")}</div>`
				);
				return;
			}

			dialog.fields_dict.shortcut_list.$wrapper.html(
				`<div class="frapkeys-shortcut-list">${shortcut_rows(message.shortcuts || [])}</div>`
			);
		});
	};

	const mount_navbar_button = () => {
		if (document.getElementById(BUTTON_ID)) return;

		const search_bar = document.querySelector("header .navbar .search-bar");
		if (!search_bar) return;

		const button = document.createElement("button");
		button.id = BUTTON_ID;
		button.type = "button";
		button.className = "btn-reset nav-link frapkeys-navbar-button";
		button.setAttribute("aria-label", __("Keyboard Shortcuts"));
		button.setAttribute("title", __("Keyboard Shortcuts"));
		button.innerHTML = frappe.utils.icon("keyboard", "sm");
		button.addEventListener("click", frapkeys.show_shortcut_dialog);

		search_bar.before(button);
	};

	frappe.ready(() => {
		mount_navbar_button();
		frappe.router.on("change", mount_navbar_button);

		const navbar = document.querySelector("header .navbar");
		if (navbar) {
			new MutationObserver(mount_navbar_button).observe(navbar, {
				childList: true,
				subtree: true,
			});
		}
	});
})();
