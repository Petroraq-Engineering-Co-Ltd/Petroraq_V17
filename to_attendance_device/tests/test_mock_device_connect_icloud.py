from odoo.tests.common import tagged
from .common import Common


@tagged('post_install', '-at_install')
class TestMockDeviceConnectIcloud(Common):
    def setUp(self):
        super(TestMockDeviceConnectIcloud, self).setUp()
        self.device_icloud = self.env['attendance.device'].create({
            'name': 'test_device_icloud',
            'serialnumber': 'serial_12345678',
            'protocol': 'icloud',
            'location_id': self.attendance_device_location.id,
            'state': 'confirmed'
        })
        # data user info
        self.data_user_info = "USER PIN=1\tName=Nv1\tPri=0\tPasswd=1234\tCard=\tGrp=1\tTZ=0001000100000000\tVerify=-1\tViceCard="
        # data user finger
        self.data_user_finger = "FP PIN=1\tFID=6\tSize=1536\tValid=1\tTMP=TcNTUzIxAAAEgIMECAUHCc7"
        # data user attendance
        self.data_user_attendance = "1\t2023-08-16 10:15:24\t0\t1\t\t0\t0\t\t\n"\
                                    "1\t2023-08-16 10:22:26\t1\t1\t\t0\t0\t\t\n"\
                                    "1\t2023-08-16 10:53:25\t255\t1\t\t0\t0\t\t\n"
        # response command data
        self.data_response = "ID=1&Return=0&CMD=CHECK\n"

    def connection(self, url, method='POST', data_test=None):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url_server = base_url + url
        self.headers = {'Content-Type': 'text/html; charset=utf-8',
                        'Accept': 'text/plain',
                        }
        if method == 'GET':
            response = self.opener.get(url_server, headers=self.headers)
        else:
            response = self.opener.post(url_server, headers=self.headers, data=data_test)
        return response

    def test_process_getrequest_01(self):
        """
            Test case: Device kết nối đến server khi device chưa đăng ký trên server
            Return: - Kết nối thành công
                    - Kết quả trả về là ký tự 'OK'
        """
        serial = '12345678'
        url_server = '/iclock/getrequest?SN={}'.format(serial)
        method = 'GET'
        res = self.connection(url_server, method)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, 'OK')

    def test_process_getrequest_02(self):
        """
            Test case:
                        - Device kết nối đến server
                        - Device đã được đăng ký trên server
                        - Không có lệnh nào được gửi tới device
            Return:
                        - Kết nối thành công
                        - kết quả trả về là ký tự 'OK'
        """
        serial = 'serial_12345678'
        url_server = '/iclock/getrequest?SN={}'.format(serial)
        method = 'GET'
        res = self.connection(url_server, method)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, 'OK')

    def test_process_getrequest_03(self):
        """
            Test case:
                        - Device kết nối đến server
                        - Device đã được đăng ký trên server
                        - Có lệnh nào được gửi tới device
            Return:
                        - Kết nối thành công
                        - kết quả trả về là chuỗi lệnh cần thực hiện
        """
        self.env['attendance.command.device'].create({
            'name': 'CHECK',
            'device_id': self.device_icloud.id,
            'return_value': 'N/A'
        })
        serial = 'serial_12345678'
        url_server = '/iclock/getrequest?SN={}'.format(serial)
        method = 'GET'
        res = self.connection(url_server, method)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text, 'C:1:CHECK \n')

    def test_post_data_user_info_01(self):
        """
            Test case:
                        - Gửi data từ device tới server
                        - Data là thông tin người dùng
            Return:
                        - Kết nối thành công
                        - Kiểm tra kết quả data đã được cập nhập vào cơ sở dữ liệu chưa
        """
        serial = 'serial_12345678'
        table = 'OPERLOG'
        url_server = '/iclock/cdata?SN={}&table={}'.format(serial, table)
        method = 'POST'
        res = self.connection(url_server, method, self.data_user_info)
        self.assertEqual(res.status_code, 200)
        user_device = self.env['attendance.device.user'].search([
            ('name', '=', 'Nv1'),
            ('device_id', '=', self.device_icloud.id),
            ('user_id', '=', '1'),
            ('password', '=', '1234'),
        ])
        self.assertTrue(user_device)

    def test_post_data_user_finger_01(self):
        """
            Test case:
                        - Gửi data từ device tới server
                        - Data là thông tin vân tay
            Return:
                        - Kết nối thành công
                        - Kiểm tra kết quả data đã được cập nhập vào cơ sở dữ liệu chưa
        """
        self.env['attendance.device.user'].create({
            'name': 'Nv1',
            'device_id': self.device_icloud.id,
            'user_id': '1',
            'password': '1234',
        })
        serial = 'serial_12345678'
        table = 'OPERLOG'
        url_server = '/iclock/cdata?SN={}&table={}'.format(serial, table)
        method = 'POST'
        res = self.connection(url_server, method, self.data_user_finger)
        self.assertEqual(res.status_code, 200)
        user_finger = self.env['finger.template'].search([
            ('device_id', '=', self.device_icloud.id),
            ('user_id', '=', '1'),
            ('fid', '=', 6),
        ])
        self.assertTrue(user_finger)

    def test_post_data_user_attendance_01(self):
        """
            Test case:
                        - Gửi data từ device tới server
                        - Data là thông tin chấm công
            Return:
                        - Kết nối thành công
                        - Kiểm tra kết quả data đã được cập nhập vào cơ sở dữ liệu chưa
        """
        self.env['attendance.device.user'].create({
            'name': 'Nv1',
            'device_id': self.device_icloud.id,
            'user_id': '1',
            'password': '1234',
        })
        self.env['finger.template'].create({
            'device_id': self.device_icloud.id,
            'user_id': '1',
            'fid': 6,
        })
        serial = 'serial_12345678'
        table = 'OPERLOG'
        url_server = '/iclock/cdata?SN={}&table={}'.format(serial, table)
        method = 'POST'
        res = self.connection(url_server, method, self.data_user_attendance)
        self.assertEqual(res.status_code, 200)
        user_attendance = self.env['user.attendance'].search([
            ('device_id', '=', self.device_icloud.id),
        ])
        self.assertEqual(len(user_attendance), 3)

    def test_process_returned_command_results_01(self):
        """
            Test case:
                        - Gửi kết quả lệnh thực hiện về server
            Return:
                        - Kết nối thành công
                        - kết quả cập nhập kết quả lệnh
        """
        cmd = self.env['attendance.command.device'].create({
            'name': 'CHECK',
            'device_id': self.device_icloud.id,
            'return_value': 'N/A'
        })
        serial = 'serial_12345678'
        url_server = '/iclock/getrequest?SN={}'.format(serial)
        method = 'GET'
        # Check to get new command
        res = self.connection(url_server, method)
        url_server = '/iclock/devicecmd?SN={}'.format(serial)
        method = 'POST'
        # Send command results to the server
        res = self.connection(url_server, method, self.data_response)
        self.assertEqual(res.status_code, 200)
        domain = [
            ('device_id.serialnumber', '=', serial),
            ('device_id.protocol', '=', 'icloud'),
            ('create_date', '=', cmd.create_date),
            ]
        cmd_device = self.env['attendance.command.device'].search(domain, limit=1)
        self.assertEqual(cmd_device.state, 'done')
