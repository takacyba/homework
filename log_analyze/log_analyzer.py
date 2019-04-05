#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import argparse
import json
import os
import re
from statistics import median
import gzip
import datetime
from collections import namedtuple
from string import Template
from log_analyze.definitions import ROOT_DIR


logger = logging.getLogger('DefaultLogger')
config = {
    'REPORT_SIZE': 1000,
    'REPORT_DIR': 'resources/REPORTS_DIR/',
    'REPORT_SAMPLE': 'resources/REPORT_SAMPLE/report.html',
    'LOG_DIR': 'resources/LOG_DIR/',
    'MAX_DROP': 5
}

LogFile = namedtuple('LogFile', ['name', 'date'])


def update_config(new_config_path, default_config):
    with open(new_config_path, 'r') as f:
        new_config = json.load(f)
        default_config.update(new_config)


def logger_setup(config_file):
    """logger initialization function.
    Args:
        config_file (dict): dict with parameters for logger.

    Returns:
        logger instance.

    """
    file = config_file.get('LOG_FILENAME')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(filename=file, format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    return logger


def find_latest_log(config_file):
    """search function of the most current log in a given directory.
    Args:
        config_file (dict): dict with parameters for searching.

    Returns:
        file name of latest log file.

    """
    logger.info('parse config for LOG_DIR data...')
    log_dir = os.path.join(ROOT_DIR, config_file['LOG_DIR'])
    logger.info(f'set values LOG_DIR is {log_dir}')
    logger.info('looking for the latest nginx log...')
    regex = re.compile('nginx-access-ui.log-(?P<date>\d+).*(?:gz|$)')
    latest_date = datetime.date.min
    latest_file = ''
    if os.path.exists(log_dir):
        for i in os.listdir(log_dir):
            data = re.search(regex, i)
            if data:
                date = datetime.datetime.strptime(data['date'], '%Y%m%d').date()
                if date > latest_date:
                    latest_date = date
                    latest_file = os.path.join(log_dir, i)
        if latest_date > datetime.date.min:

            last_log = LogFile(latest_file, latest_date)
            logger.info(f'found the new last file: {latest_file}')
            return last_log
    logger.info(f'directory {log_dir} does not exist')


def parse_log(file):
    """function of parsing the specified nginx file.
    Args:
        file (str): parsing file path.

    Returns:
        urls: dict with unique urls and their request times.
        summary_lines: count of lines in file
        requests_time: summary requests time of all urls in file.

    """
    logger.info(f'starting to parse the file {file}')
    opener = gzip.open if file.endswith('.gz') else open
    line_format = re.compile(
        b'.*((\"(GET|POST|PUT|HEAD) )(?P<url>.+)(http\/1\.[0-1]")).* (?P<request_time>\d+\.\d+)', re.IGNORECASE)
    with opener(file, 'rb') as f:
        logger.info('successfully read the file, start parsing')
        parsed_lines = 0
        summary_lines = 0
        for line in f:
            summary_lines += 1
            data = re.search(line_format, line)
            if data:
                parsed_lines += 1
                yield data, summary_lines, parsed_lines


def aggregate_parse_values(config_file, log_parser):
    urls = {}
    requests_time = 0
    parsed_lines = 0
    summary_lines = 0
    for data, summary_lines, parsed_lines in log_parser:
        datadict = data.groupdict()
        url = datadict["url"].decode('UTF-8')
        request_time = float(datadict["request_time"])
        requests_time += request_time
        try:
            urls[url].append(request_time)
        except KeyError:
            urls[url] = [request_time]
    dropped = round((summary_lines-parsed_lines) / summary_lines * 100, 3)
    max_drop = config_file['MAX_DROP']
    if dropped > max_drop:
        error_msg = f'found more errors: {dropped}% than allowed:{max_drop}%'
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    else:
        logger.info(f'founded {dropped}% errors, it is ok, allowed:{max_drop}%')
    return urls, summary_lines, requests_time


def calculate_report_metrics(config_file, urls, summary_lines, requests_time):
    """function that calculates different metrics for each url.
    Args:
        config_file (dict): dict with parameters for searching.
        urls (dict): dict with unique urls and their request times.
        summary_lines (int): count of lines in file
        requests_time (float): summary requests time of all urls in file.

    Returns:
        table list with dicts with urls and their metrics values.

    """

    logger.info('start calculating metrics')
    table = []
    for key, value in urls.items():
        metrics = {}
        counter = len(value)
        metrics['url'] = key
        metrics['count'] = counter
        metrics['time_sum'] = sum(value)
        metrics['time_avg'] = sum(value)/counter
        metrics['time_max'] = max(value)
        metrics['time_med'] = median(value)
        metrics['count_perc'] = round(counter / summary_lines * 100, 3)
        metrics['time_perc'] = round(sum(value) / requests_time * 100, 3)
        table.append(metrics)
    if len(table) > config_file['REPORT_SIZE']:
        logger.info("urls count more than report size settings, choose the highest priority")
        table = sorted(table, key=lambda i: i['time_avg'], reverse=True)[:config_file['REPORT_SIZE']]
    return table


def generate_report(config_file, table, file_date):
    """function that generate report with bad request time urls.
    Args:
        config_file (dict): dict with parameters for searching.
        table (list): with dicts of urls and their metrics values.
        file_date (date): date of latest log file.

    """
    logger.info('start generate report')
    file = f'report-{file_date.strftime("%Y")}.{file_date.strftime("%m")}.{file_date.strftime("%d")}.html'
    sample_path = os.path.join(ROOT_DIR, config_file['REPORT_SAMPLE'])
    report_path = os.path.join(ROOT_DIR, config_file['REPORT_DIR'], file)
    with open(sample_path, 'r') as f:
        with open(report_path, "w") as f1:
            content = f.read()
            tpl = Template(content)
            new_report = tpl.safe_substitute(table_json=table)
            f1.write(new_report)
            logger.info(f'have successfully formed a report to the path {report_path}')


def report_is_exist(config_file, file_date):
    file = f'report-{file_date.strftime("%Y")}.{file_date.strftime("%m")}.{file_date.strftime("%d")}.html'
    return os.path.exists(os.path.join(ROOT_DIR, config_file['REPORT_DIR'], file))


def main(config_file):
    last_log_tuple = find_latest_log(config_file)
    if not last_log_tuple:
        logger.info('No log files')
        return
    if report_is_exist(config_file, last_log_tuple.date):
        logger.info('have already analyzed the latest log')
        return
    log_parser = parse_log(last_log_tuple.name)
    urls, summary_lines, requests_time = aggregate_parse_values(config_file, log_parser)
    metrics = calculate_report_metrics(config_file, urls, summary_lines, requests_time)
    generate_report(config_file, metrics, last_log_tuple.date)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='?', const=os.path.join(ROOT_DIR, 'default_config'))
    args = parser.parse_args()
    update_config(args.config, config)
    logger = logger_setup(config)
    try:
        main(config)
    except Exception as e:
        logger.exception(f"Exception occurred during program execution, reason: {e}")
