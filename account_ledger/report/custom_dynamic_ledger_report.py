from odoo import models
import io
import base64
import xlsxwriter
from odoo import models
from datetime import datetime
from PIL import Image


class CustomDynamicLedgerReport(models.AbstractModel):
    _name = 'report.account_ledger.custom_dynamic_ledger_report'
    _inherit = 'report.report_xlsx.abstract'

    # def generate_xlsx_report(self, workbook, data, wizard_id):
    #     report_data = wizard_id.generate_balance_report()
    #     sheet = workbook.add_worksheet(wizard_id.main_head)
    #
    #     # Insert larger company logo (around 150x110)
    #     # if wizard_id.company_id.logo:
    #     #     image_data = base64.b64decode(wizard_id.company_id.logo)
    #     #     image_stream = io.BytesIO(image_data)
    #     #     image = Image.open(image_stream)
    #     #     image.thumbnail((150, 110), Image.ANTIALIAS)  # larger size
    #     #     output_stream = io.BytesIO()
    #     #     image.save(output_stream, format='PNG')
    #     #     output_stream.seek(0)
    #     #     sheet.insert_image('H1', 'logo.png', {'image_data': output_stream})
    #
    #     # Header info - bigger font and bold
    #     header_info_format = workbook.add_format({
    #         'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'
    #     })
    #
    #     sheet.merge_range('A1:H1', f"Company: {wizard_id.company_id.name}", header_info_format)
    #     sheet.merge_range('A2:H2', f"Period: {wizard_id.date_start} to {wizard_id.date_end}", header_info_format)
    #
    #     department_name = wizard_id.department_id.name if wizard_id.department_id else ""
    #     section_name = wizard_id.section_id.name if wizard_id.section_id else ""
    #     project_name = wizard_id.project_id.name if wizard_id.project_id else ""
    #
    #     sub_header_info_format = workbook.add_format({
    #         'bold': True, 'font_size': 12, 'align': 'center', 'valign': 'vcenter'
    #     })
    #
    #     if department_name:
    #         sheet.merge_range('A3:H3', f"Department: {department_name}", sub_header_info_format)
    #     if section_name:
    #         sheet.merge_range('A4:H4', f"Section: {section_name}", sub_header_info_format)
    #     if project_name:
    #         sheet.merge_range('A5:H5', f"Project: {project_name}", sub_header_info_format)
    #
    #     # Define formats
    #     header_main_format = workbook.add_format({
    #         'bold': True, 'bg_color': '#DDEBF7', 'border': 1, 'align': 'center', 'valign': 'vcenter'
    #     })
    #     header_sub_format = workbook.add_format({
    #         'bold': True, 'bg_color': '#DDEBF7', 'border': 1, 'align': 'center', 'valign': 'vcenter'
    #     })
    #     negative_format = workbook.add_format({
    #         'font_color': 'red', 'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter', 'bottom': 1
    #     })
    #     level_formats = {
    #         0: workbook.add_format(
    #             {'bold': True, 'font_size': 12, 'bg_color': '#BDD7EE', 'align': 'center', 'valign': 'vcenter',
    #              'bottom': 1}),
    #         1: workbook.add_format(
    #             {'bold': True, 'font_size': 11, 'bg_color': '#D9E1F2', 'align': 'center', 'valign': 'vcenter',
    #              'bottom': 1}),
    #         2: workbook.add_format(
    #             {'bold': True, 'font_size': 10, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter',
    #              'bottom': 1}),
    #         3: workbook.add_format(
    #             {'font_size': 9, 'bg_color': '#F9F9F9', 'align': 'center', 'valign': 'vcenter', 'bottom': 1}),
    #     }
    #
    #     # Adjust column widths
    #     sheet.set_column('A:A', 15)  # Account code
    #     sheet.set_column('B:B', 30)  # Account name
    #     sheet.set_column('C:H', 15)  # Balance columns
    #
    #     start_row = 7
    #
    #     # Merge Account header across two columns: A and B
    #     sheet.merge_range(start_row, 0, start_row, 1, 'Account', header_main_format)
    #     sheet.merge_range(start_row, 2, start_row, 3, 'Initial Balance', header_main_format)
    #     sheet.merge_range(start_row, 4, start_row, 5, 'Period Balance', header_main_format)
    #     sheet.merge_range(start_row, 6, start_row, 7, 'Ending Balance', header_main_format)
    #
    #     # Sub headers row: split Account into "Code" and "Name"
    #     sheet.write(start_row + 1, 0, 'Code', header_sub_format)
    #     sheet.write(start_row + 1, 1, 'Name', header_sub_format)
    #     sheet.write(start_row + 1, 2, 'Debit', header_sub_format)
    #     sheet.write(start_row + 1, 3, 'Credit', header_sub_format)
    #     sheet.write(start_row + 1, 4, 'Debit', header_sub_format)
    #     sheet.write(start_row + 1, 5, 'Credit', header_sub_format)
    #     sheet.write(start_row + 1, 6, 'Debit', header_sub_format)
    #     sheet.write(start_row + 1, 7, 'Credit', header_sub_format)
    #
    #     # Write data rows starting row + 2
    #     for row_idx, row in enumerate(report_data, start=start_row + 2):
    #         indent_spaces = len(row['level']) - len(row['level'].lstrip())
    #         level = indent_spaces // 4
    #         fmt = level_formats.get(level, level_formats[3])
    #         sheet.set_row(row_idx, 25)
    #
    #         account_text = row['level'].strip()
    #         account_info = account_text.split(' - ', 1)
    #         account_code = account_info[0].strip()
    #         account_name = account_info[1].strip() if len(account_info) > 1 else ''
    #
    #         if level == 0 or level == 1 or level == 2:
    #             # Merge columns A and B for header rows (categories and subcategories)
    #             sheet.merge_range(row_idx, 0, row_idx, 1, account_text, fmt)
    #         else:
    #             # Regular data rows: write code and name separately
    #             sheet.write(row_idx, 0, account_code, fmt)
    #             sheet.write(row_idx, 1, account_name, fmt)
    #
    #         def write_number(col, value):
    #             fmt_to_use = fmt if value >= 0 else negative_format
    #             sheet.write_number(row_idx, col, value, fmt_to_use)
    #
    #         write_number(2, row['initial_debit'])
    #         write_number(3, row['initial_credit'])
    #         write_number(4, row['period_debit'])
    #         write_number(5, row['period_credit'])
    #         write_number(6, row['ending_debit'])
    #         write_number(7, row['ending_credit'])

    def generate_xlsx_report(self, workbook, data, wizard_id):
        report_data = wizard_id.generate_balance_report()
        sheet = workbook.add_worksheet(wizard_id.main_head)

        # Header info - big, bold
        header_info_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'
        })

        sheet.merge_range('A1:E1', f"Company: {wizard_id.company_id.name}", header_info_format)
        sheet.merge_range('A2:E2', f"Period: {wizard_id.date_start} to {wizard_id.date_end}", header_info_format)

        department_name = wizard_id.department_id.name if wizard_id.department_id else ""
        section_name = wizard_id.section_id.name if wizard_id.section_id else ""
        project_name = wizard_id.project_id.name if wizard_id.project_id else ""

        sub_header_info_format = workbook.add_format({
            'bold': True, 'font_size': 12, 'align': 'center', 'valign': 'vcenter'
        })

        row_offset = 2
        if department_name:
            sheet.merge_range(f"A{row_offset + 2}:E{row_offset + 2}", f"Department: {department_name}",
                              sub_header_info_format)
            row_offset += 1
        if section_name:
            sheet.merge_range(f"A{row_offset + 2}:E{row_offset + 2}", f"Section: {section_name}",
                              sub_header_info_format)
            row_offset += 1
        if project_name:
            sheet.merge_range(f"A{row_offset + 2}:E{row_offset + 2}", f"Project: {project_name}",
                              sub_header_info_format)
            row_offset += 1

        # Use SAR currency format
        currency_format_string = '#,##0.00 [$SAR]'

        def make_format(base_format, bg_color):
            return workbook.add_format({
                'font_size': base_format.get('font_size', 10),
                'bold': base_format.get('bold', False),
                'align': 'center',
                'valign': 'vcenter',
                'bottom': 1,
                'bg_color': bg_color,
                'num_format': currency_format_string
            })

        def make_negative_format(base_format, bg_color):
            return workbook.add_format({
                'font_size': base_format.get('font_size', 10),
                'bold': base_format.get('bold', False),
                'align': 'center',
                'valign': 'vcenter',
                'bottom': 1,
                'bg_color': bg_color,
                'font_color': 'red',
                'num_format': currency_format_string
            })

        # Style definitions for each level
        base_levels = {
            0: {'bold': True, 'font_size': 12},
            1: {'bold': True, 'font_size': 11},
            2: {'bold': True, 'font_size': 10},
            3: {'font_size': 9},
        }
        bg_colors = {
            0: '#BDD7EE',
            1: '#D9E1F2',
            2: '#F2F2F2',
            3: '#F9F9F9',
        }

        # Create all styles (text, positive, negative) per level
        number_formats = {}
        for lvl in range(4):
            number_formats[lvl] = {
                'pos': make_format(base_levels[lvl], bg_colors[lvl]),
                'neg': make_negative_format(base_levels[lvl], bg_colors[lvl]),
                'text': workbook.add_format(
                    {**base_levels[lvl], 'bg_color': bg_colors[lvl], 'align': 'center', 'valign': 'vcenter',
                     'bottom': 1}),
            }

        # Column widths
        sheet.set_column('A:A', 15)  # Code
        sheet.set_column('B:B', 30)  # Name
        sheet.set_column('C:E', 20)  # Balances

        start_row = row_offset + 5

        # Header
        sheet.merge_range(start_row, 0, start_row, 1, 'Account', number_formats[0]['text'])
        # sheet.merge_range(start_row, 2, start_row, 3, 'Opening Balance', number_formats[0]['text'])
        # sheet.merge_range(start_row, 4, start_row, 5, 'Period Balance', number_formats[0]['text'])
        sheet.merge_range(start_row, 2, start_row, 3, 'Closing Balance', number_formats[0]['text'])

        # Sub-headers
        sheet.write(start_row + 1, 0, 'Code', number_formats[0]['text'])
        sheet.write(start_row + 1, 1, 'Name', number_formats[0]['text'])
        # sheet.write(start_row + 1, 2, 'Balance', number_formats[0]['text'])
        # sheet.write(start_row + 1, 3, 'Type', number_formats[0]['text'])
        # sheet.write(start_row + 1, 4, 'Balance', number_formats[0]['text'])
        # sheet.write(start_row + 1, 5, 'Type', number_formats[0]['text'])
        sheet.write(start_row + 1, 2, 'Balance', number_formats[0]['text'])
        sheet.write(start_row + 1, 3, 'Type', number_formats[0]['text'])

        # Write data
        for row_idx, row in enumerate(report_data, start=start_row + 2):
            indent_spaces = len(row['level']) - len(row['level'].lstrip())
            level = indent_spaces // 4
            level_data = number_formats.get(level, number_formats[3])
            fmt_text = level_data['text']

            sheet.set_row(row_idx, 25)

            account_text = row['level'].strip()
            account_info = account_text.split(' - ', 1)
            account_code = account_info[0].strip()
            account_name = account_info[1].strip() if len(account_info) > 1 else ''

            if level in (0, 1, 2):
                sheet.merge_range(row_idx, 0, row_idx, 1, account_text, fmt_text)
            else:
                sheet.write(row_idx, 0, account_code, fmt_text)
                sheet.write(row_idx, 1, account_name, fmt_text)

            # def write_number(col, value):
            #     fmt_to_use = level_data['pos'] if value >= 0 else level_data['neg']
            #     sheet.write_number(row_idx, col, value, fmt_to_use)

            def write_number(col, value):
                if isinstance(value, (int, float)):
                    fmt_to_use = level_data['pos'] if value >= 0 else level_data['neg']
                    sheet.write_number(row_idx, col, value, fmt_to_use)
                else:
                    sheet.write(row_idx, col, str(value), fmt_text)

            # Balances
            # initial_balance = row['initial_debit'] - row['initial_credit']
            # period_balance = row['period_debit'] - row['period_credit']
            # ending_balance = row['ending_debit'] - row['ending_credit']
            #
            # write_number(2, initial_balance)
            # write_number(3, period_balance)
            # write_number(4, ending_balance)

            # Initial Balance Data
            if row['initial_debit'] > row['initial_credit']:
                initial_balance = row['initial_debit'] - row['initial_credit']
                initial_balance_type = "Debit"
            elif row['initial_credit'] > row['initial_debit']:
                initial_balance = row['initial_credit'] - row['initial_debit']
                initial_balance_type = "Credit"
            elif row['initial_debit'] == row['initial_credit']:
                initial_balance = row['initial_debit'] - row['initial_credit'] or 0.0
                initial_balance_type = " - "

            # Period Balance Data
            if row['period_debit'] > row['period_credit']:
                period_balance = row['period_debit'] - row['period_credit']
                period_balance_type = "Debit"
            elif row['period_credit'] > row['period_debit']:
                period_balance = row['period_credit'] - row['period_debit']
                period_balance_type = "Credit"
            elif row['period_debit'] == row['period_credit']:
                period_balance = row['period_debit'] - row['period_credit'] or 0.0
                period_balance_type = " - "

            # Ending Balance Data
            if row['ending_debit'] > row['ending_credit']:
                ending_balance = row['ending_debit'] - row['ending_credit']
                ending_balance_type = "Debit"
            elif row['ending_credit'] > row['ending_debit']:
                ending_balance = row['ending_credit'] - row['ending_debit']
                ending_balance_type = "Credit"
            elif row['ending_debit'] == row['ending_credit']:
                ending_balance = row['ending_debit'] - row['ending_credit'] or 0.0
                ending_balance_type = " - "

            # write_number(2, initial_balance)
            # write_number(3, initial_balance_type)
            # write_number(4, period_balance)
            # write_number(5, period_balance_type)
            write_number(2, ending_balance)
            write_number(3, ending_balance_type)


class CustomDynamicLedgerPdfReport(models.AbstractModel):
    _name = 'report.account_ledger.custom_dynamic_ledger_rep'

    def _get_report_values(self, docids, data=None):
        wizard = self.env['custom.dynamic.ledger.report.wizard'].browse(docids)
        wizard.ensure_one()

        report_rows = wizard.generate_balance_report()
        today = datetime.today()

        return {
            'doc_ids': wizard.ids,
            'doc_model': wizard._name,
            'docs': report_rows,
            'company_name': wizard.company_id.name,
            'date_start': wizard.date_start,
            'date_end': wizard.date_end,
            'main_head': wizard.main_head,
            'department_name': wizard.department_id.name if wizard.department_id else "",
            'section_name': wizard.section_id.name if wizard.section_id else "",
            'project_name': wizard.project_id.name if wizard.project_id else "",
            'report_date': today.strftime("%b-%d-%Y"),
        }
