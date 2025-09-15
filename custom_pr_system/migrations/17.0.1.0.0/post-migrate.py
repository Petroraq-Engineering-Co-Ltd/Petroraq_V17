# from odoo import api, SUPERUSER_ID

# def migrate(cr, version):
#     """Drop old selection column and let Odoo recreate Many2one field"""
#     cr.execute("""
#         DO $$
#         BEGIN
#             -- check if column 'unit' exists and drop it
#             IF EXISTS (
#                 SELECT 1
#                 FROM information_schema.columns
#                 WHERE table_name='custom_pr_line'
#                   AND column_name='unit'
#             ) THEN
#                 ALTER TABLE custom_pr_line DROP COLUMN unit CASCADE;
#             END IF;
#         END$$;
#     """)
from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """Remove old selection entries for unit field to avoid errors"""
    cr.execute("""
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE model = 'custom.pr.line' AND name = 'unit'
        );
    """)
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'custom.pr.line' AND name = 'unit';
    """)