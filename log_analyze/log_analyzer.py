#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import argparse
import json
import os
import sys
import re
from statistics import median
import gzip
from datetime import datetime
from string import Template
from log_analyze.definitions import ROOT_DIR

config = {
    'REPORT_SIZE': 1000,
    'REPORT_DIR': 'resources/REPORTS_DIR/',
    'REPORT_SAMPLE': 'resources/REPORT_SAMPLE/report.html',
    'LOG_DIR': 'resources/LOG_DIR/',
    'MAX_DROP': 5
}


def logger_setup(config_file):
    """logger initialization function.
    Args:
        config_file (dict): dict with parameters for logger.

    Returns:
        logger instance.

    """
    try:
        file = config_file['LOG_FILENAME']
    except KeyError:
        file = None
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(filename=file, format='[%(asctime)s] %(levelname).1s %(message)s', datefmt= '%Y.%m.%d %H:%M:%S')
    return logger


def find_latest_log(logger, config_file):
    """search function of the most current log in a given directory.
    Args:
        logger (instance): logger instance.
        config_file (dict): dict with parameters for searching.

    Returns:
        file name of latest log file.

    """
    latest_file_path = ''
    logger.info('parse config for LOG_DIR data...')
    log_dir = os.path.join(ROOT_DIR, config_file['LOG_DIR'])
    logger.info(f'set values LOG_DIR is {log_dir}')
    logger.info('looking for the latest nginx log...')
    try:
        regex = re.compile('nginx-access-ui.log-.*(?:gz|[0-9]{8}$)')
        files = [i for i in os.listdir(log_dir) if regex.match(i)]
        latest_file = max(files)
        latest_file_path = os.path.join(log_dir, latest_file)
        logger.info(f'found the new last file: {latest_file}')
    except ValueError:
        pass
    return latest_file_path


def parse_log(logger, file):
    """function of parsing the specified nginx file.
    Args:
        logger (instance): logger instance.
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


def aggregate_parse_values(logger, config_file, file):
    urls = {}
    requests_time = 0
    cnt = 0
    lines = 0
    for data, summary_lines, parsed_lines in parse_log(logger, file):
        lines = summary_lines
        cnt = parsed_lines
        datadict = data.groupdict()
        url = datadict["url"].decode('UTF-8')
        request_time = float(datadict["request_time"])
        requests_time += request_time
        try:
            urls[url].append(request_time)
        except KeyError:
            urls[url] = [request_time]
    dropped = round((lines-cnt) / lines * 100, 3)
    max_drop = config_file['MAX_DROP']
    if dropped > max_drop:
        logger.error(f'found more errors: {dropped}% than allowed:{max_drop}%')
        raise ValueError
    else:
        logger.info(f'founded {dropped}% errors, it is ok, allowed:{max_drop}%')
    return urls, lines, requests_time


def calculate_report_metrics(logger, config_file, urls, summary_lines, requests_time):
    """function that calculates different metrics for each url.
    Args:
        logger (instance): logger instance.
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


def generate_report(logger, config_file, table, file_name):
    """function that generate report with bad request time urls.
    Args:
        logger (instance): logger instance.
        config_file (dict): dict with parameters for searching.
        table (list): with dicts of urls and their metrics values.
        file_name (str): file name of latest log file.

    """
    logger.info('start generate report')
    file = generate_report_name(file_name)
    sample_path = os.path.join(ROOT_DIR, config_file['REPORT_SAMPLE'])
    report_path = os.path.join(ROOT_DIR, config_file['REPORT_DIR'], file)
    with open(sample_path, 'r') as f:
        with open(report_path, "w") as f1:
            content = f.read()
            tpl = Template(content)
            new_report = tpl.safe_substitute(table_json=table)
            f1.write(new_report)
            logger.info(f'have successfully formed a report to the path {report_path}')


def generate_report_name(file_name):
    file = re.findall('\d+', file_name)
    date_obj = datetime.strptime(file[0], '%Y%m%d')
    file = f'report-{date_obj.strftime("%Y")}.{date_obj.strftime("%m")}.{date_obj.strftime("%d")}.html'
    return file


def report_is_exist(config_file, file_name):
    file = generate_report_name(file_name)
    return os.path.exists(os.path.join(ROOT_DIR, config_file['REPORT_DIR'], file))


def main(config_file, logger):
    config_file = config_file
    latest_file = find_latest_log(logger, config_file)
    if not latest_file:
        logger.info('No log files')
        return
    if report_is_exist(config_file, latest_file):
        logger.info('have already analyzed the latest log')
        return
    urls, summary_lines, requests_time = aggregate_parse_values(logger, config_file, latest_file)
    metrics = calculate_report_metrics(logger, config_file, urls, summary_lines, requests_time)
    generate_report(logger, config_file, metrics, latest_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='?', const=os.path.join(ROOT_DIR, 'default_config'))
    args = parser.parse_args()
    with open(args.config, 'r') as f:
        try:
            new_config = json.load(f)
            for key, value in new_config.items():
                config[key] = value
        except (SyntaxError, json.decoder.JSONDecodeError):
            pass
    logger = logger_setup(config)
    try:
        main(config, logger)
    except Exception as e:
        logger.exception(f"Exception occurred during program execution, reason: {e}")
