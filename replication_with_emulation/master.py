#!/usr/bin/env python

import sys
import math
import json
import time
import pickle
import numpy as np
from os import path
from subprocess import Popen, check_call
from helpers import (CURRDIR, parse_settings, gce_worker_ips, parse_run_stats,
                     make_sure_path_exists, get_abs_diff, utc_date)


def collect_perf_data(args, ip_dict):
    perf_data_dir = path.join(CURRDIR, 'perf_data_dir')
    make_sure_path_exists(perf_data_dir)

    # scp perf_data
    scp_procs = []
    for ip in ip_dict:
        remote_perf_data = (
            '%s@%s:~/pantheon/test/data/perf_data' % (args['username'], ip))
        scp_cmd = ['scp', remote_perf_data,
                   path.join(perf_data_dir, '%s_%d' % ip_dict[ip])]
        scp_procs.append(Popen(scp_cmd))

    for proc in scp_procs:
        proc.wait()

    # parse perf_data
    perf = {}
    for cc in args['schemes']:
        for run_id in xrange(1, args['run_times'] + 1):
            perf_data_file = path.join(perf_data_dir, '%s_%d' % (cc, run_id))
            with open(perf_data_file) as perf_data_handle:
                perf_list = perf_data_handle.readline().split(',')
                friendly_cc = perf_list[0]

                if friendly_cc not in perf:
                    perf[friendly_cc] = {}
                    perf[friendly_cc]['tput'] = []
                    perf[friendly_cc]['delay'] = []

                perf[friendly_cc]['tput'].append(float(perf_list[1]))
                perf[friendly_cc]['delay'].append(float(perf_list[2]))

    for scheme in perf:
        tput_list = perf[scheme]['tput']
        perf[scheme]['tput'] = np.median(tput_list)

        delay_list = perf[scheme]['delay']
        perf[scheme]['delay'] = np.median(delay_list)

    return perf


def write_search_log(args, tput_loss, delay_loss, overall_loss):
    args['search_log'].write(
        'bandwidth=%.1f,delay=%d,uplink_queue=%d,uplink_loss=%.4f,'
        'tput_loss=%.2f,delay_loss=%.2f,overall_median_score=%.2f,'
        'time=%s\n'
        % (args['bandwidth'], args['delay'],
           args['uplink_queue'], args['uplink_loss'],
           tput_loss, delay_loss, overall_loss, utc_date()))


def compute_loss(args):
    tput_loss = 0.0
    delay_loss = 0.0
    cnt = 0
    for cc in args['candidate_cali_data']:
        new_tput = args['candidate_cali_data'][cc]['tput']
        new_delay = args['candidate_cali_data'][cc]['delay']

        orig_tput = args['orig_cali_data'][cc]['tput']
        orig_delay = args['orig_cali_data'][cc]['delay']

        tput_loss += get_abs_diff(orig_tput, new_tput)
        delay_loss += get_abs_diff(orig_delay, new_delay)
        cnt += 1

    tput_loss = tput_loss * 100.0 / cnt
    delay_loss = delay_loss * 100.0 / cnt
    overall_loss = (tput_loss + delay_loss) / 2.0

    write_search_log(args, tput_loss, delay_loss, overall_loss)
    return overall_loss


def run_experiment(args):
    worker = '~/Spearmint/replication_with_emulation/worker.py'

    worker_args = []
    worker_args += ['--bandwidth', '%.1f' % args['bandwidth']]
    worker_args += ['--delay', '%d' % args['delay']]
    worker_args += ['--uplink-queue', '%d' % args['uplink_queue']]
    worker_args += ['--uplink-loss', '%.4f' % args['uplink_loss']]
    base_cmd = 'python %s %s' % (worker, ' '.join(worker_args))

    ip_idx = 0
    ip_dict = {}
    worker_procs = []

    for cc in args['schemes']:
        for run_id in xrange(1, args['run_times'] + 1):
            ip = args['ips'][ip_idx]
            ip_idx += 1
            ip_dict[ip] = (cc, run_id)

            ssh_cmd = ['ssh', '%s@%s' % (args['username'], ip)]
            cmd_in_ssh = base_cmd + ' --schemes %s' % cc
            ssh_cmd += [cmd_in_ssh]

            sys.stderr.write('+ %s\n' % ' '.join(ssh_cmd))
            worker_procs.append(Popen(ssh_cmd))

    for proc in worker_procs:
        proc.wait()

    # collect perf_data
    perf = collect_perf_data(args, ip_dict)
    args['candidate_cali_data'] = perf

    return compute_loss(args)


def add_normalized_params(args, params):
    bounds = []
    bounds.append((args['bandwidth_bounds']['min'],
                   args['bandwidth_bounds']['max']))
    bounds.append((args['delay_bounds']['min'],
                   args['delay_bounds']['max']))
    bounds.append((args['uplink_queue_bounds']['min'],
                   args['uplink_queue_bounds']['max']))
    bounds.append((args['uplink_loss_bounds']['min'],
                   args['uplink_loss_bounds']['max']))

    units = []
    units.append(params['bandwidth'][0])
    units.append(params['delay'][0])
    units.append(params['uplink_queue'][0])
    units.append(params['uplink_loss'][0])

    entropy = 0.0
    norm = []
    for i in xrange(len(units)):
        unit_x = float(units[i])
        min_x, max_x = bounds[i]

        eps = pow(2, -15)
        if unit_x > 1 - eps:
            unit_x = 1 - eps
        elif i <= 2 and unit_x < eps:
            unit_x = eps

        if unit_x > 1.0 - 1.0 / 32.0:
            entropy += -10 * (5 + math.log(1 - unit_x, 2))
        elif i <= 2 and unit_x < 1.0 / 32.0:
            entropy += -10 * (5 + math.log(unit_x, 2))

        if i <= 2:
            x = unit_x * (max_x - min_x) + min_x
        else:
            c = math.log(max_x * pow(10, 4) + 1, 10)
            x = pow(10, -4) * ((pow(10, c * unit_x)) - 1)

        norm.append(x)

    args['bandwidth'] = max(0.0, norm[0])
    args['delay'] = max(0, int(math.ceil(norm[1])))
    args['uplink_queue'] = max(0, int(math.ceil(norm[2])))
    args['uplink_loss'] = min(1.0, max(0.0, norm[3]))

    return entropy


def prepare_args():
    args = parse_settings()

    args['ips'] = gce_worker_ips()

    # sanity check on # of workers
    num_workers = len(args['ips'])
    correct_num_workers = args['run_times'] * len(args['schemes'])
    if num_workers != correct_num_workers:
        sys.exit('Wrong number of workers %d, should be %d' %
                 (num_workers, correct_num_workers))

    args['search_log'] = open(args['location'] + '_search_log', 'a', 0)

    return args


def process_replicate_logs(args):
    replicate_logs_parent = path.join(CURRDIR, 'replicate_logs')
    make_sure_path_exists(replicate_logs_parent)
    replicate_logs = path.join(replicate_logs_parent, args['replicate_logs'])

    cali_data = path.join(replicate_logs, 'cali_data.json')
    if path.isfile(cali_data):
        sys.stderr.write('Skip processing %s as cali_data.json already '
                         'exists\n' % replicate_logs)
        with open(cali_data) as cali_data_f:
            cali_data_dict = json.load(cali_data_f)
        return cali_data_dict

    # run plot.py and generate perf_data.pkl
    cmd = ('~/pantheon/analysis/plot.py --no-graphs --data-dir %s '
           '--schemes "%s"' % (replicate_logs, ' '.join(args['schemes'])))
    sys.stderr.write('+ %s\n' % cmd)
    check_call(cmd, shell=True)

    # generate cali_data.json
    pickle_data_path = path.join(replicate_logs, 'perf_data.pkl')

    with open(pickle_data_path) as pickle_data_file:
        pickle_data = pickle.load(pickle_data_file)

    cali_data_dict = {}

    for scheme in pickle_data:
        cali_data_dict[scheme] = {}
        cali_data_dict[scheme]['tput'] = []
        cali_data_dict[scheme]['delay'] = []
        for run_id in pickle_data[scheme]:
            stats = pickle_data[scheme][run_id]
            if stats is None:
                continue

            flows = parse_run_stats(stats.split('\n'))
            assert len(flows) == 1
            f = 1

            tput = flows[f][0]
            delay = flows[f][1]
            cali_data_dict[scheme]['tput'].append(float(tput))
            cali_data_dict[scheme]['delay'].append(float(delay))

    for scheme in cali_data_dict:
        tput_list = cali_data_dict[scheme]['tput']
        cali_data_dict[scheme]['tput'] = np.median(tput_list)

        delay_list = cali_data_dict[scheme]['delay']
        cali_data_dict[scheme]['delay'] = np.median(delay_list)

    with open(cali_data, 'w') as cali_data_f:
        json.dump(cali_data_dict, cali_data_f)

    return cali_data_dict


def main(job_id, params):
    args = prepare_args()

    # process replicate_logs
    orig_cali_data = process_replicate_logs(args)
    args['orig_cali_data'] = orig_cali_data

    # fill args with normalized parameters and return an extra loss "entropy"
    entropy = add_normalized_params(args, params)

    loss = run_experiment(args) + entropy

    if args['search_log']:
        args['search_log'].close()

    return loss


# debug
if __name__ == '__main__':
    job_id = 0
    params = {}
    params['bandwidth'] = [0.0]
    params['delay'] = [0.0]
    params['uplink_queue'] = [0.0]
    params['uplink_loss'] = [0.0]
    main(job_id, params)
