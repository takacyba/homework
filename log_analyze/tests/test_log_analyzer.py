import unittest
from log_analyze.log_analyzer import *
from log_analyze.definitions import ROOT_DIR


class TestLogAnalyzer(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(ROOT_DIR, 'tests/resources/configs/config'), 'r') as f:
            self.config = eval(f.read())
        self.file_name = 'nginx-access-ui.log-20170630'
        self.logger = logger_setup(self.config)

    def test_logger_setup_method_return(self):
        logger = logger_setup(self.config)
        assert isinstance(logger, logging.Logger)

    def test_find_latest_log_no_new_logs(self):
        assert find_latest_log(self.logger, self.config) is 0

    def test_find_latest_log_no_files(self):
        conf = self.config
        conf['LOG_DIR'] = 'tests/resources/LOG_DIR_2/'
        assert find_latest_log(self.logger, conf) is 0

    def test_find_latest_log_success(self):
        conf = self.config
        conf['LAST_CHECKED_FILE_DIR'] = 'tests/resources/checked_files/last_checked_file_2'
        open(os.path.join(ROOT_DIR, conf['LAST_CHECKED_FILE_DIR']), 'w').close()
        assert find_latest_log(self.logger, conf) == os.path.join(ROOT_DIR, conf['LOG_DIR'], self.file_name)

    def test_parse_log_assert_value_error(self):
        conf = self.config
        conf['MAX_DROP'] = 0
        with self.assertRaises(ValueError):
            parse_log(self.logger, conf, os.path.join(ROOT_DIR, conf['LOG_DIR'], self.file_name))

    def test_parse_log_urls(self):
        test_urls = {'/api/v2/banner/25019354 ': [0.39, 0.39, 0.39],
                     '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ': [0.133],
                     '/api/v2/banner/16852664 ': [0.199]}
        urls, summary_lines, requests_time = \
            parse_log(self.logger, self.config, os.path.join(ROOT_DIR, self.config['LOG_DIR'], self.file_name))
        assert urls == test_urls

    def test_parse_log_summary_lines(self):

        urls, summary_lines, requests_time = \
            parse_log(self.logger, self.config, os.path.join(ROOT_DIR, self.config['LOG_DIR'], self.file_name))
        assert summary_lines is 6

    def test_parse_log_request_time(self):
        urls, summary_lines, requests_time = \
            parse_log(self.logger, self.config, os.path.join(ROOT_DIR, self.config['LOG_DIR'], self.file_name))
        assert requests_time == 1.5020000000000002

    def test_calculate_report_metrics_success(self):
        urls = {'/api/v2/banner/25019354 ': [0.39, 0.39, 0.39],
                '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ': [0.133],
                '/api/v2/banner/16852664 ': [0.199]}
        summary_lines = 6
        request_time = 1.5020000000000002
        result_table = \
            [{'url': '/api/v2/banner/25019354 ', 'count': 3, 'time_sum': 1.17, 'time_avg': 0.38999999999999996,
             'time_max': 0.39, 'time_med': 0.39, 'count_perc': 50.0, 'time_perc': 77.896},
             {'url': '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ', 'count': 1, 'time_sum': 0.133,
             'time_avg': 0.133, 'time_max': 0.133, 'time_med': 0.133, 'count_perc': 16.667, 'time_perc': 8.855},
             {'url': '/api/v2/banner/16852664 ', 'count': 1, 'time_sum': 0.199, 'time_avg': 0.199, 'time_max': 0.199,
             'time_med': 0.199, 'count_perc': 16.667, 'time_perc': 13.249}]
        result = calculate_report_metrics(self.logger, self.config, urls, summary_lines, request_time)
        assert result_table == result

    def test_calculate_report_metrics_len(self):
        urls = {'/api/v2/banner/25019354 ': [0.39, 0.39, 0.39],
                '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ': [0.133],
                '/api/v2/banner/16852664 ': [0.199]}
        summary_lines = 6
        request_time = 1.5020000000000002
        conf = self.config
        conf['REPORT_SIZE'] = 2
        result = calculate_report_metrics(self.logger, self.config, urls, summary_lines, request_time)
        assert len(result) is 2

    def test_generate_report_success(self):
        table = \
            [{'url': '/api/v2/banner/25019354 ', 'count': 3, 'time_sum': 1.17, 'time_avg': 0.38999999999999996,
             'time_max': 0.39, 'time_med': 0.39, 'count_perc': 50.0, 'time_perc': 77.896},
             {'url': '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ', 'count': 1, 'time_sum': 0.133,
             'time_avg': 0.133, 'time_max': 0.133, 'time_med': 0.133, 'count_perc': 16.667, 'time_perc': 8.855},
             {'url': '/api/v2/banner/16852664 ', 'count': 1, 'time_sum': 0.199, 'time_avg': 0.199, 'time_max': 0.199,
             'time_med': 0.199, 'count_perc': 16.667, 'time_perc': 13.249}]
        result_report = os.path.join(ROOT_DIR, self.config['REPORT_DIR'], 'report-2017.06.30.html')
        if os.path.exists(result_report):
            os.remove(result_report)
        generate_report(self.logger, self.config, table, os.path.join(ROOT_DIR, self.config['LOG_DIR'], self.file_name))
        assert os.path.exists(result_report)

    def test_generate_report_table_substitution(self):
        result_report = os.path.join(ROOT_DIR, self.config['REPORT_DIR'], 'report-2017.06.30.html')
        value = "var table = [{'url': '/api/v2/banner/25019354 ', 'count': 3, 'time_sum': 1.17, "\
                "'time_avg': 0.38999999999999996, 'time_max': 0.39, 'time_med': 0.39, 'count_perc': 50.0, " \
                "'time_perc': 77.896}, {'url': '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ', 'count': 1, " \
                "'time_sum': 0.133, 'time_avg': 0.133, 'time_max': 0.133, 'time_med': 0.133, 'count_perc': 16.667, " \
                "'time_perc': 8.855}, {'url': '/api/v2/banner/16852664 ', 'count': 1, 'time_sum': 0.199, " \
                "'time_avg': 0.199, 'time_max': 0.199, 'time_med': 0.199, 'count_perc': 16.667, 'time_perc': 13.249}];"
        with open(result_report, 'r') as f:
            assert value in f.read()