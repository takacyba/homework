import unittest
from log_analyze.log_analyzer import *
from log_analyze.definitions import ROOT_DIR


class TestLogAnalyzer(unittest.TestCase):

    def setUp(self):
        with open(os.path.join(ROOT_DIR, 'tests/resources/configs/config'), 'r') as f:
            self.config = json.load(f)
        self.file_name = 'nginx-access-ui.log-20170630'
        self.log_parser = parse_log(os.path.join(ROOT_DIR, self.config['LOG_DIR'], self.file_name))
        self.file_date = datetime.datetime.strptime('20170630', '%Y%m%d').date()
        self.file_date_not = datetime.datetime.strptime('20170701', '%Y%m%d').date()

    def test_logger_setup_method_return(self):
        logger = logger_setup(self.config)
        assert isinstance(logger, logging.Logger)

    def test_report_is_exist_true(self):
        assert report_is_exist(self.config, self.file_date)

    def test_report_is_exist_false(self):
        assert not report_is_exist(self.config, self.file_date_not)

    def test_find_latest_log_no_files(self):
        conf = self.config
        conf['LOG_DIR'] = 'tests/resources/LOG_DIR_2/'
        assert not find_latest_log(conf)

    def test_find_latest_log_success(self):
        assert find_latest_log(self.config).name == \
               os.path.join(ROOT_DIR, self.config['LOG_DIR'], self.file_name)

    def test_aggregate_parse_values_assert_value_error(self):
        conf = self.config
        conf['MAX_DROP'] = 0
        with self.assertRaises(RuntimeError):
            aggregate_parse_values(conf, self.log_parser)

    def test_aggregate_parse_values_urls(self):
        test_urls = {'/api/v2/banner/25019354 ': [0.39, 0.39, 0.39],
                     '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ': [0.133],
                     '/api/v2/banner/16852664 ': [0.199]}
        urls, summary_lines, requests_time = \
            aggregate_parse_values(self.config, self.log_parser)
        assert urls == test_urls

    def test_aggregate_parse_values_summary_lines(self):

        urls, summary_lines, requests_time = aggregate_parse_values(
            self.config, self.log_parser)
        assert summary_lines is 6

    def test_aggregate_parse_values_request_time(self):
        urls, summary_lines, requests_time = aggregate_parse_values(
            self.config, self.log_parser)
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
        result = calculate_report_metrics(self.config, urls, summary_lines, request_time)
        assert result_table == result

    def test_calculate_report_metrics_len(self):
        urls = {'/api/v2/banner/25019354 ': [0.39, 0.39, 0.39],
                '/api/1/photogenic_banners/list/?server_name=WIN7RB4 ': [0.133],
                '/api/v2/banner/16852664 ': [0.199]}
        summary_lines = 6
        request_time = 1.5020000000000002
        conf = self.config
        conf['REPORT_SIZE'] = 2
        result = calculate_report_metrics(self.config, urls, summary_lines, request_time)
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
        generate_report(self.config, table, self.file_date)
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

    def test_parse_log(self):
        gen = parse_log(os.path.join(ROOT_DIR, self.config['LOG_DIR'], self.file_name))
        summary_lines = parsed_lines = 0
        for i, j, x in gen:
            summary_lines = j
            parsed_lines = x
        assert summary_lines == 6 and parsed_lines == 5

    def test_update_config(self):
        config = {
            'REPORT_SIZE': 50,
            'MAX_DROP': 5
        }
        update_config(os.path.join(ROOT_DIR, 'tests/resources/configs/config'), config)
        expected_config = \
            {'REPORT_SIZE': 1000, 'MAX_DROP': 20, 'REPORT_DIR': 'tests/resources/REPORTS_DIR/',
             'REPORT_SAMPLE': 'resources/REPORT_SAMPLE/report.html', 'LOG_DIR': 'tests/resources/LOG_DIR/'}
        assert config == expected_config
