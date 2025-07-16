# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import xlsxwriter
import json
import datetime
import io
from datetime import date
from odoo.modules.module import get_module_resource
from PIL import Image


class KsDynamicFinancialXlsxTB(models.Model):
    _inherit = 'ks.dynamic.financial.base'

    def ks_get_xlsx_trial_balance(self, ks_df_informations):

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        row_pos = 0
        row_pos_2 = 0
        lang = self.env.user.lang
        lang_id = self.env['res.lang'].search([('code', '=', lang)])['date_format'].replace('/', '-')

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

        move_lines, retained, subtotal = self.ks_process_trial_balance(ks_df_informations)
        ks_company_id = self.env['res.company'].sudo().browse(ks_df_informations.get('company_id'))
        sheet = workbook.add_worksheet('Trial Balance')
        sheet.insert_image('A1', header_image_path, {
            'x_offset': 8,
            'y_offset': y_offset,
            'x_scale': 0.8,
            'y_scale': y_scale,
        })


        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 15)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 15)
        sheet.set_column(5, 5, 15)
        sheet.set_column(6, 6, 15)
        sheet.set_column(7, 7, 15)
        sheet.set_column(8, 8, 15)
        sheet.set_column(9, 9, 15)

        format_title = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 12,
            'font': 'Arial',
        })
        format_header_old = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'align': 'center',
            # 'border': True,
        })
        format_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'font': 'Arial',
            'align': 'center',
            # 'border': True,
             'bg_color': '#09abdf',  # Light gray or any hex color
            'pattern': 1,
        })
        format_merged_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'right': True,
            'left': True,
            'font': 'Arial',
        })
        format_merged_header_without_border = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
        })
        content_header = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
        })
        line_header = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
        })
        line_header_total = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'top': True,
            'bottom': True,
            'bg_color': '#09abdf',  # Light gray or any hex color
            'pattern': 1,
        })
        line_header_total.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)
        line_header_left = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
        })
        line_header_left_total = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
            'top': True,
            'bottom': True,
            'bg_color': '#09abdf',  # Light gray or any hex color
            'pattern': 1,
        })
        line_header_light = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'bg_color': '#09abdf',  # Light gray or any hex color
            'pattern': 1,
        })
        line_header_light.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)
        line_header_light_total = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
            'top': True,
            'bottom': True,
            'bg_color': '#09abdf',  # Light gray or any hex color
            'pattern': 1,
        })
        line_header_light_total.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)
        line_header_light_left = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'left',
            'font': 'Arial',
        })
        line_header_highlight = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'right',
            'font': 'Arial',
        })
        line_header_highlight.set_num_format(
            '#,##0.' + '0' * ks_company_id.currency_id.decimal_places or 2)
        line_header_light_date = workbook.add_format({
            'bold': False,
            'font_size': 10,
            'align': 'center',
            'font': 'Arial',
        })
        row_pos_2 += 0

        ks_new_start_date = (datetime.datetime.strptime(
            ks_df_informations['date'].get('ks_start_date'), '%Y-%m-%d').date()).strftime(lang_id)
        for_new_end_date = ks_df_informations['date'].get('ks_end_date') if ks_df_informations['date'].get('ks_end_date') else date.today()
        ks_new_end_date = (datetime.datetime.strptime(
            str(for_new_end_date), '%Y-%m-%d').date()).strftime(lang_id)

        if ks_df_informations:
            # Date from
            if ks_df_informations['date']['ks_process'] == 'range':
                sheet.write_string(row_pos_2, 0, _('Date From'), format_header_old)
                sheet.write_string(row_pos_2 + 1, row_pos_2, ks_new_start_date,
                                   format_merged_header_without_border)

                sheet.write_string(row_pos_2, row_pos_2 + 1, _('Date To'), format_header_old)
                sheet.write_string(row_pos_2 + 1, row_pos_2 + 1, ks_new_end_date,
                                   format_merged_header_without_border)
            else:
                sheet.write_string(row_pos_2, 0, _('As of Date'), format_header_old)
                sheet.write_string(row_pos_2 + 1, row_pos_2, ks_new_end_date,
                                   format_merged_header_without_border)

            # Journals
            row_pos_2 += 0
            sheet.write_string(row_pos_2, 3, _('Journals'), format_header_old)
            j_list = ', '.join(
                journal.get('name') or '' for journal in ks_df_informations['journals'] if journal.get('selected'))
            sheet.write_string(row_pos_2 + 1, 3, j_list,
                               content_header)

            # Account
            row_pos_2 += 0
            sheet.write_string(row_pos_2, 4, _('Account'), format_header_old)
            j_list = ', '.join(
                journal.get('name') or '' for journal in ks_df_informations['account'] if journal.get('selected'))
            sheet.write_string(row_pos_2 + 1, 4, j_list,
                               content_header)
            #
            # # Accounts
            row_pos_2 += 0
            if ks_df_informations.get('analytic_accounts'):
                sheet.write_string(row_pos_2, 5, _('Analytic Accounts'), format_header_old)
                a_list = ', '.join(lt or '' for lt in ks_df_informations['selected_analytic_account_names'])
                sheet.write_string(row_pos_2 + 1, 5, a_list, content_header)

            row_pos_2 += 0
            if ks_df_informations.get('analytic_tags'):
                sheet.write_string(row_pos_2, 6, _('Tags'), format_header_old)
                a_list = ', '.join(lt or '' for lt in ks_df_informations['selected_analytic_tag_names'])
                sheet.write_string(row_pos_2 + 1, 6, a_list, content_header)
        row_pos += 5

        sheet.merge_range(row_pos, 1, row_pos, 3, 'Initial Balance', format_merged_header)

        sheet.write_string(row_pos, 4, ks_new_start_date,
                           format_merged_header_without_border)
        sheet.write_string(row_pos, 5, _(' To '),
                           format_merged_header_without_border)

        sheet.write_string(row_pos, 6, ks_new_end_date,
                           format_merged_header_without_border)
        sheet.merge_range(row_pos, 7, row_pos, 9, 'Ending Balance', format_merged_header)
        row_pos += 1
        sheet.write_string(row_pos, 0, _('Account'),
                           format_header)
        sheet.write_string(row_pos, 1, _('Debit'),
                           format_header)
        sheet.write_string(
            row_pos, 2, _('Credit'),
            format_header)
        sheet.write_string(row_pos, 3, _('Balance'),
                           format_header)
        sheet.write_string(row_pos, 4, _('Debit'),
                           format_header)
        sheet.write_string(row_pos, 5, _('Credit'),
                           format_header)
        sheet.write_string(row_pos, 6, _('Balance'),
                           format_header)
        sheet.write_string(row_pos, 7, _('Debit'),
                           format_header)
        sheet.write_string(row_pos, 8, _('Credit'),
                           format_header)
        sheet.write_string(row_pos, 9, _('Balance'),
                           format_header)

        for line in move_lines.values():  # Normal lines
            row_pos += 1
            blank_space = '   ' * len(line)
            # if line.get('dummy'):
            #     sheet.write_string(row_pos, 0, blank_space + line.get('code'),
            #                             line_header_light_left)
            # else:
            sheet.write_string(row_pos, 0, line.get('code') + ' ' + line.get('name'),
                               line_header_light_left)
            sheet.write_number(row_pos, 1, float(line.get('initial_debit')), line_header_light)
            sheet.write_number(row_pos, 2, float(line.get('initial_credit')), line_header_light)
            sheet.write_number(row_pos, 3, float(line.get('initial_balance')), line_header_highlight)
            sheet.write_number(row_pos, 4, float(line.get('debit')), line_header_light)
            sheet.write_number(row_pos, 5, float(line.get('credit')), line_header_light)
            sheet.write_number(row_pos, 6, float(line.get('balance')), line_header_highlight)
            sheet.write_number(row_pos, 7, float(line.get('ending_debit')), line_header_light)
            sheet.write_number(row_pos, 8, float(line.get('ending_credit')), line_header_light)
            sheet.write_number(row_pos, 9, float(line.get('ending_balance')), line_header_highlight)
        row_pos += 2
        sheet.write_string(row_pos, 0,
                           subtotal['SUBTOTAL'].get('code') + ' ' + subtotal['SUBTOTAL'].get('name'),
                           line_header_left_total)
        sheet.write_number(row_pos, 1, float(subtotal['SUBTOTAL'].get('initial_debit')),
                           line_header_light_total)
        sheet.write_number(row_pos, 2, float(subtotal['SUBTOTAL'].get('initial_credit')),
                           line_header_light_total)
        sheet.write_number(row_pos, 3, float(subtotal['SUBTOTAL'].get('initial_balance')),
                           line_header_total)
        sheet.write_number(row_pos, 4, float(subtotal['SUBTOTAL'].get('debit')), line_header_light_total)
        sheet.write_number(row_pos, 5, float(subtotal['SUBTOTAL'].get('credit')),
                           line_header_light_total)
        sheet.write_number(row_pos, 6, float(subtotal['SUBTOTAL'].get('balance')), line_header_total)
        sheet.write_number(row_pos, 7, float(subtotal['SUBTOTAL'].get('ending_debit')),
                           line_header_light_total)
        sheet.write_number(row_pos, 8, float(subtotal['SUBTOTAL'].get('ending_credit')),
                           line_header_light_total)
        sheet.write_number(row_pos, 9, float(subtotal['SUBTOTAL'].get('ending_balance')),
                           line_header_total)

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
            'x_offset': 8,
            'y_offset': y_offset,
            'x_scale': 0.8,
            'y_scale': y_scale,
        })
        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file
