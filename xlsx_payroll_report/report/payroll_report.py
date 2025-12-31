from odoo import models
import string


class PayrollReport(models.AbstractModel):
    _name = 'report.xlsx_payroll_report.xlsx_payroll_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):

        # ======================
        # Formats (PDF-like)
        # ======================
        blue_title = workbook.add_format({
            'bold': True, 'font_size': 14,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        blue_subtitle = workbook.add_format({
            'bold': True, 'font_size': 12,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        header_blue = workbook.add_format({
            'bold': True, 'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        cell_txt = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1
        })
        cell_money = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })
        cell_money_alt = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F3F6FA',
            'num_format': '#,##0.00'
        })
        cell_txt_alt = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F3F6FA'
        })
        total_blue_txt = workbook.add_format({
            'bold': True, 'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        total_blue_money = workbook.add_format({
            'bold': True, 'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1,
            'num_format': '#,##0.00'
        })

        # ======================
        # Helper for Excel column letters
        # ======================
        def xl_col_to_name(idx0):
            """0-based -> Excel letters"""
            name = ""
            n = idx0 + 1
            while n:
                n, rem = divmod(n - 1, 26)
                name = chr(65 + rem) + name
            return name

        # ======================
        # Fetch used structures
        # ======================
        used_structures = []
        seen_ids = set()
        for sal_structure in lines.slip_ids.struct_id:
            if sal_structure.id not in seen_ids:
                used_structures.append([sal_structure.id, sal_structure.name])
                seen_ids.add(sal_structure.id)

        struct_count = 1
        for used_struct in used_structures:
            sheet = workbook.add_worksheet(str(struct_count) + ' - ' + str(used_struct[1]))

            # Freeze panes below header row (title rows + header row)
            sheet.freeze_panes(6, 2)  # row 6, col 2 (adjusted after styling)

            cols = list(string.ascii_uppercase) + [
                'AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK', 'AL',
                'AM', 'AN', 'AO', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY', 'AZ'
            ]

            rules = []
            col_no = 3  # SHIFTED by +1 because we will add Emp ID, Name, Dept in cols 0..2

            # Salary rules (KEEP your logic)
            salary_rule_ids = lines.slip_ids.line_ids.mapped("salary_rule_id")
            order = ['Basic Salary',
                     'Food',
                     'Accommodation',
                     'Transportation',
                     'Other Payments',
                     'Other Allowances',
                     'Car Allowances',
                     'Fixed Overtime',
                     'Overtime',
                     'Gross',
                     'Late In',
                     'Early Checkout',
                     'Annual Time Off',
                     'Absence',
                     'HRA',
                     'Advance Allowances',
                     'GOSI',
                     # 'Annual Time Off',
                     'Sick Time Off',
                     'Unpaid Leave',
                     'Annual Time Off DED',
                     'Sick Time Off DED',
                     'Net Salary']

            salary_rule_ids = salary_rule_ids.filtered(lambda s: s.name in order)

            order_map = {name: index for index, name in enumerate(order)}
            sorted_rules = sorted(salary_rule_ids, key=lambda x: order_map.get(x.name, 9999))

            for rule in sorted_rules:
                row = [None, None, None, None, None]
                row[0] = col_no
                row[1] = rule.code
                row[2] = rule.name
                col_title = str(cols[col_no]) + ':' + str(cols[col_no])
                row[3] = col_title
                row[4] = 12 if len(rule.name) < 8 else (len(rule.name) + 2)
                rules.append(row)
                col_no += 1

            # Report details (KEEP your logic)
            batch_period = ""
            company_name = ""
            for item in lines.slip_ids:
                if item.struct_id.id == used_struct[0]:
                    batch_period = f"{item.date_from.strftime('%d %B %Y')}  To  {item.date_to.strftime('%d %B %Y')}"
                    company_name = item.company_id.name or ""
                    break

            last_col = col_no - 1

            # ======================
            # Title bars (PDF-like)
            # ======================
            sheet.set_row(0, 22)
            sheet.merge_range(0, 0, 0, last_col, company_name, blue_title)

            sheet.set_row(1, 20)
            sheet.merge_range(1, 0, 1, last_col, f"Payroll Month {item.date_to.strftime('%B %Y')}", blue_subtitle)

            sheet.set_row(2, 20)
            sheet.merge_range(2, 0, 2, last_col, f"For the Period {batch_period}", blue_subtitle)

            # Optional small info row (kept but styled lightly)
            sheet.set_row(3, 16)
            sheet.write(3, 0, "Payslip Structure:", cell_txt)
            sheet.merge_range(3, 1, 3, 2, used_struct[1], cell_txt)

            # ======================
            # Table header row
            # ======================
            header_row = 5
            sheet.set_row(header_row, 18)

            sheet.write(header_row, 0, 'Employee ID', header_blue)
            sheet.write(header_row, 1, 'Employee Name', header_blue)
            sheet.write(header_row, 2, 'Department', header_blue)
            for rule in rules:
                sheet.write(header_row, rule[0], rule[2], header_blue)

            # Column widths
            sheet.set_column('A:A', 12)
            sheet.set_column('B:B', 28)
            sheet.set_column('C:C', 18)
            for rule in rules:
                sheet.set_column(rule[3], rule[4])

            # ======================
            # Data rows (same logic, just styled)
            # ======================
            row = header_row + 1
            first_data_row = row  # for totals formula
            has_payslips = False

            for slip in lines.slip_ids:
                if slip.struct_id.id != used_struct[0]:
                    continue

                has_payslips = True
                is_alt = ((row - first_data_row) % 2 == 1)

                txt_fmt = cell_txt_alt if is_alt else cell_txt
                money_pos_fmt = cell_money_alt if is_alt else cell_money
                money_neg_fmt = cell_money_alt if is_alt else cell_money  # keep same format; Excel shows minus

                sheet.write(row, 0, slip.employee_id.code or '', txt_fmt)
                sheet.write(row, 1, slip.employee_id.name or '', txt_fmt)
                sheet.write(row, 2, slip.employee_id.department_id.name or '', txt_fmt)

                # Fill all rule columns (by code)
                # (Small perf improvement: build dict {code: amount} once per slip)
                slip_amount_by_code = {l.code: l.amount for l in slip.line_ids}

                for rule in rules:
                    val = slip_amount_by_code.get(rule[1], 0.0)
                    fmt = money_pos_fmt if val >= 0 else money_neg_fmt
                    sheet.write(row, rule[0], val, fmt)

                row += 1

            # ======================
            # Total row (blue bar like PDF)
            # ======================
            if has_payslips:
                total_row = row
                sheet.write(total_row, 0, 'Total', total_blue_txt)
                sheet.write(total_row, 1, '', total_blue_txt)
                sheet.write(total_row, 2, '', total_blue_txt)

                # sum each numeric column from col 3..last_col
                for c in range(3, last_col + 1):
                    col_letter = xl_col_to_name(c)
                    # Excel rows are 1-based:
                    start = first_data_row + 1
                    end = total_row
                    sheet.write_formula(
                        total_row, c,
                        f"=SUM({col_letter}{start}:{col_letter}{end})",
                        total_blue_money
                    )

            struct_count += 1
