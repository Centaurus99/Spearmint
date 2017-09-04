import sys
import os
from os import path
import re
import yaml
import shutil
import errno
from datetime import datetime
from subprocess import check_output

CURRDIR = path.abspath(path.join(path.dirname(path.abspath(__file__))))


def parse_settings():
    with open(path.join(CURRDIR, 'settings.yml')) as settings:
        return yaml.load(settings)


def gce_worker_ips():
    table = path.join(CURRDIR, 'TABLE')
    cmd = 'grep -E -o "([0-9]{1,3}[\.]){3}[0-9]{1,3}" ' + table
    ip_list = check_output(cmd, shell=True).split()

    internal_ips = []
    for i in xrange(0, len(ip_list), 2):
        internal_ips.append(ip_list[i])

    return internal_ips


def make_sure_path_exists(target_path):
    try:
        os.makedirs(target_path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def parse_run_stats(stats):
    """ Takes in a list of stats split by line seen in pantheon_report.pdf,
    describing a run's statistics. Returns a dictionary in the form of
    {flow#: (tput, delay, rate)}

    Assumes the stats list is well-formed.
    For multiple flows, the sentinel flow # of 0 represents the total stats.
    """
    flow_stats = {}

    re_total = lambda x: re.match(r'-- Total of (.*?) flow', x)
    re_flow = lambda x: re.match(r'-- Flow (.*?):', x)
    re_tput = lambda x: re.match(r'Average throughput: (.*?) Mbit/s', x)
    re_delay = lambda x: re.match(
        r'95th percentile per-packet one-way delay: (.*?) ms', x)
    re_loss = lambda x: re.match(r'Loss rate: (.*?)%', x)

    flow_num = 0
    total_flows = 1
    idx = -1
    while idx < len(stats) - 1 and flow_num < total_flows:
        idx += 1
        line = stats[idx]

        flow_ret = re_total(line) or re_flow(line)
        if flow_ret is None or (re_total(line) is not None
                                and flow_ret.group(1) == '1'):
            continue

        if re_flow(line) is not None:
            flow_num = int(flow_ret.group(1))
        else:
            total_flows = int(flow_ret.group(1))

        if idx + 3 >= len(stats):
            break

        avg_tput_ret = re_tput(stats[idx + 1])
        if avg_tput_ret is None:
            continue

        owd_ret = re_delay(stats[idx + 2])
        if owd_ret is None:
            continue

        loss_ret = re_loss(stats[idx + 3])
        if loss_ret is None:
            continue

        flow_stats[flow_num] = (float(avg_tput_ret.group(1)),
                                float(owd_ret.group(1)),
                                float(loss_ret.group(1)))
    return flow_stats


def get_abs_diff(metric_1, metric_2):
     return 1.0 * abs(metric_2 - metric_1) / metric_1


def utc_date():
    return datetime.utcnow().strftime('%Y-%m-%dT%H-%M')


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError()
