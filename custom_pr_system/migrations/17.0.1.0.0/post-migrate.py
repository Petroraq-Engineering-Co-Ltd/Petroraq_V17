from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """Drop old selection column and let Odoo recreate Many2one field"""
    cr.execute("""
        DO $$
        BEGIN
            -- check if column 'unit' exists and drop it
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='custom_pr_line'
                  AND column_name='unit'
            ) THEN
                ALTER TABLE custom_pr_line DROP COLUMN unit CASCADE;
            END IF;
        END$$;
    """)
