/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

// THIS IS CORRECT for Odoo 17 (your path is in account)
import { SectionAndNoteText } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";

patch(SectionAndNoteText.prototype, {
    setup() {
        super.setup?.();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
    },

    async onAddProductClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const line = this.props.record;
        if (line.data.display_type !== "line_section") return;

        const orderId = line.model.root.resId;   // sale.order id
        const sectionLineId = line.resId;        // sale.order.line id (section)

        this.dialog.add(SelectCreateDialog, {
            resModel: "product.product",
            title: "Select a Product",
            domain: [["sale_ok", "=", true]],
            context: { search_default_sale_ok: 1 },
            noCreate: false,
            multiSelect: false,

            onSelected: async (ids) => {
                if (!ids?.length) return;

                await this.orm.call(
                    "sale.order",
                    "action_add_product_after_section",
                    [orderId, sectionLineId, ids[0]]
                );

                // refresh lines
                await line.model.root.load();
            },
        });
    },
});
