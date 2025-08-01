# -*- coding: utf-8 -*-
import io
from odoo import models, api, _, fields
from odoo.tools.misc import xlsxwriter
import datetime
from datetime import date
from odoo.modules.module import get_module_resource
from PIL import Image


class KsDynamicFinancialXlsxPL(models.Model):
    _inherit = 'ks.dynamic.financial.base'

    @api.model
    def ks_get_xlsx_partner_ledger(self, ks_df_informations):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        ctx = self.env.context.copy()
        ctx['OFFSET'] = True
        self.env.context = ctx

        # Header Image
        header_image_path = get_module_resource(
            'ks_dynamic_financial_report', 'static/src/img', 'header_custom.png'
        )
        img = Image.open(header_image_path)
        image_height_px = img.size[1]  # Get height in pixels
        img.close()

        y_scale = 0.5
        y_offset = 5
        # Then calculate how many Excel rows it takes
        image_rows = int((image_height_px * y_scale + y_offset) / 15) + 1

        row_pos = image_rows
        row_pos_2 = image_rows

        move_lines = self.ks_partner_process_data(ks_df_informations)
        ks_company_id = self.env['res.company'].sudo().browse(ks_df_informations.get('company_id'))
        # lang = self.env.user.lang
        # language_id = self.env['res.lang'].search([('code','=',lang)])[0]
        # self._format_float_and_dates(self.env.user.company_id.currency_id,language_id)
        sheet = workbook.add_worksheet('Partner Ledger')
        sheet.insert_image('A1', header_image_path, {
            'x_offset': 7,
            'y_offset': y_offset,
            'x_scale': 0.7,
            'y_scale': y_scale,
        })
        sheet.freeze_panes(5, 2)
        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 12)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 3, 18)
        sheet.set_column(4, 4, 30)
        sheet.set_column(5, 5, 10)
        sheet.set_column(6, 6, 10)
        sheet.set_column(7, 7, 10)

        format_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 12,
            'font': 'Arial',
            'border': False
        })
        format_header_old = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            # 'border': True
        })
        format_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            # 'border': True
            'bg_color': '#09abdf',  # Light gray or any hex color
            'pattern': 1,
        })
        content_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            # 'border': True,
            'font': 'Arial',
        })
        content_header_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            # 'border': True,
            'align': 'center',
            'font': 'Arial',
        })
        line_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'top': True,
            'bottom': True,
            'font': 'Arial',
            'text_wrap': True,
        })
        line_header.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)
        line_header_light = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'text_wrap': True,
            'font': 'Arial',
            'valign': 'top'
        })
        line_header_light.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)
        line_header_light_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
            'num_format': 'mm/dd/yyyy'
        })
        line_header_light_initial = workbook.add_format({
            'italic': True,
            'font_size': 10,
            'align': 'center',
            'bottom': True,
            'font': 'Arial',
            'valign': 'top'
        })
        line_header_light_initial.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)
        line_header_light_ending = workbook.add_format({
            'italic': True,
            'font_size': 10,
            'align': 'center',
            'top': True,
            'font': 'Arial',
            'valign': 'top'
        })
        line_header_light_ending.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)

        row_pos_2 += 0
        lang = self.env.user.lang
        lang_id = self.env['res.lang'].search([('code', '=', lang)])['date_format'].replace('/', '-')
        ks_new_start_date = (datetime.datetime.strptime(
            ks_df_informations['date'].get('ks_start_date'), '%Y-%m-%d').date()).strftime(lang_id)
        for_e_date = ks_df_informations['date'].get('ks_end_date') if ks_df_informations['date'].get(
            'ks_end_date') else date.today()
        ks_new_end_date = (datetime.datetime.strptime(
            str(for_e_date), '%Y-%m-%d').date()).strftime(lang_id)
        if ks_df_informations:
            # Date from
            if ks_df_informations['date']['ks_process'] == 'range':
                sheet.write_string(row_pos_2, 0, _('Date From'),
                                   format_header_old)
                sheet.write_string(row_pos_2 + 1, row_pos_2, ks_new_start_date,
                                   content_header_date)

                sheet.write_string(row_pos_2, row_pos_2 + 1, _('Date To'),
                                   format_header_old)

                sheet.write_string(row_pos_2 + 1, row_pos_2 + 1, ks_new_end_date,
                                   content_header_date)
            else:
                sheet.write_string(row_pos_2, 0, _('As of Date'),
                                   format_header_old)

                sheet.write_string(row_pos_2 + 1, row_pos_2, ks_new_end_date,
                                   content_header_date)

            # row_pos_2 += 0
            # sheet.write_string(row_pos_2, 3, _('Journals'),
            #                    format_header)
            # j_list = ', '.join(
            #     journal.get('code') or '' for journal in ks_df_informations['journals'] if journal.get('selected'))
            # sheet.write_string(row_pos_2 + 1, 3, j_list,
            #                    content_header)

            row_pos_2 += 0

            sheet.write_string(row_pos_2, 3, _('Partners'),
                               format_header_old)
            p_list = ', '.join(lt or '' for lt in ks_df_informations['ks_selected_partner_name'])
            sheet.write_string(row_pos_2 + 1, 3, p_list,
                               content_header)

            row_pos_2 += 3
            sheet.write_string(row_pos_2, 0, _('Reconciled'),
                               format_header_old)
            if ks_df_informations['ks_reconciled']:
                sheet.write_string(row_pos_2 + 1, 0, 'Yes',
                                   content_header)
            else:
                sheet.write_string(row_pos_2 + 1, 0, 'No',
                                   content_header)

            row_pos_2 += 0
            sheet.write_string(row_pos_2, 3, _('Accounts'),
                               format_header_old)
            pt_list = ', '.join(lt.get('name') or '' for lt in ks_df_informations['account_type'] if lt.get('selected'))
            sheet.write_string(row_pos_2 + 1, 3, pt_list,
                               content_header)

        row_pos += 7

        if ks_df_informations.get('ks_report_with_lines', False):
            sheet.write_string(row_pos, 0, _('Date'),
                               format_header)
            sheet.write_string(row_pos, 1, _('JRNL'),
                               format_header)
            sheet.write_string(row_pos, 2, _('Account'),
                               format_header)
            # sheet.write_string(row_pos, 3, _('Ref'),
            #                         format_header)
            sheet.write_string(row_pos, 3, _('Move'),
                               format_header)
            sheet.write_string(row_pos, 4, _('Entry Label'),
                               format_header)
            sheet.write_string(row_pos, 5, _('Debit'),
                               format_header)
            sheet.write_string(row_pos, 6, _('Credit'),
                               format_header)
            sheet.write_string(row_pos, 7, _('Balance'),
                               format_header)
        else:
            sheet.merge_range(row_pos, 0, row_pos, 4, _('Partner'), format_header)
            sheet.write_string(row_pos, 5, _('Debit'),
                               format_header)
            sheet.write_string(row_pos, 6, _('Credit'),
                               format_header)
            sheet.write_string(row_pos, 7, _('Balance'),
                               format_header)
        if move_lines:
            for line in move_lines[0]:
                row_pos += 1
                sheet.merge_range(row_pos, 0, row_pos, 4, move_lines[0][line].get('name'), line_header)
                sheet.write_number(row_pos, 5, float(move_lines[0][line].get('debit')), line_header)
                sheet.write_number(row_pos, 6, float(move_lines[0][line].get('credit')), line_header)
                sheet.write_number(row_pos, 7, float(move_lines[0][line].get('balance')), line_header)

                if ks_df_informations.get('ks_report_with_lines', False):

                    for sub_line in move_lines[0][line]['lines']:
                        if sub_line['initial_bal']:
                            row_pos += 1
                            sheet.write_string(row_pos, 4, sub_line.get('move_name'),
                                               line_header_light_initial)
                            sheet.write_number(row_pos, 5, float(sub_line.get('debit', 0)),
                                               line_header_light_initial)
                            sheet.write_number(row_pos, 6, float(sub_line.get('credit')),
                                               line_header_light_initial)
                            sheet.write_number(row_pos, 7, float(sub_line.get('balance')),
                                               line_header_light_initial)
                        elif not sub_line['initial_bal'] and not sub_line['ending_bal']:
                            row_pos += 1
                            date_3 = sub_line.get('ldate')
                            lang = self.env.user.lang
                            lang_id = self.env['res.lang'].search([('code', '=', lang)])['date_format']
                            new_date = date_3.strftime(lang_id)
                            sheet.write(row_pos, 0, new_date,
                                        line_header_light_date)
                            sheet.write_string(row_pos, 1, sub_line.get('lcode'),
                                               line_header_light)
                            sheet.write_string(row_pos, 2, sub_line.get('account_name')[lang] if lang and isinstance(
                                sub_line.get('account_name'), dict) else sub_line.get('account_name') or '',
                                               line_header_light)
                            # sheet.write_string(row_pos, 3, sub_line.get('lref') or '',
                            #                         line_header_light)
                            sheet.write_string(row_pos, 3, sub_line.get('move_name'),
                                               line_header_light)
                            sheet.write_string(row_pos, 4, sub_line.get('lname') or '',
                                               line_header_light)
                            sheet.write_number(row_pos, 5,
                                               float(sub_line.get('debit')), line_header_light)
                            sheet.write_number(row_pos, 6,
                                               float(sub_line.get('credit')), line_header_light)
                            sheet.write_number(row_pos, 7,
                                               float(sub_line.get('balance')), line_header_light)
                        else:  # Ending Balance
                            row_pos += 1
                            sheet.write(row_pos, 4, sub_line.get('move_name'),
                                        line_header_light_ending)
                            sheet.write_number(row_pos, 5, float(move_lines[0][line].get('debit')),
                                               line_header_light_ending)
                            sheet.write_number(row_pos, 6, float(move_lines[0][line].get('credit')),
                                               line_header_light_ending)
                            sheet.write_number(row_pos, 7, float(move_lines[0][line].get('balance')),
                                               line_header_light_ending)

        ctx = self.env.context.copy()
        ctx['OFFSET'] = False
        self.env.context = ctx

        # Get footer image path
        footer_image_path = get_module_resource(
            'ks_dynamic_financial_report', 'static/src/img', 'footer.png'
        )

        # Open image to get its height
        footer_img = Image.open(footer_image_path)
        footer_image_height_px = footer_img.size[1]
        footer_img.close()

        # Estimate how many rows the image will take
        y_scale = 0.5
        y_offset = 5
        image_rows = int((footer_image_height_px * y_scale + y_offset) / 15) + 1

        # Insert footer image AFTER the last row of data
        footer_start_row = sheet.dim_rowmax + 3
        footer_cell = f'A{footer_start_row + 1}'  # Excel rows start from 1, not 0
        sheet.insert_image(footer_cell, footer_image_path, {
            'x_offset': 7,
            'y_offset': y_offset,
            'x_scale': 0.7,
            'y_scale': y_scale,
        })
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file
