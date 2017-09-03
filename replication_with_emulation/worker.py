#!/usr/bin/env python

import sys
import pickle
import shutil
import argparse
from subprocess import check_call
from os import path
from helpers import CURRDIR, parse_run_stats


def gen_trace(bw):
    gen_trace_path = path.join(CURRDIR, 'generate_trace.py')
    traces_dir = path.join(CURRDIR, 'traces')

    bw = '%.1f' % bw
    cmd = ['python', gen_trace_path, '--bandwidth', bw,
           '--output-dir', traces_dir]
    sys.stderr.write('+ %s\n' % ' '.join(cmd))
    check_call(cmd)

    return path.join(traces_dir, '%smbps.trace' % bw)


def run_test(args):
    # remove ~/pantheon/test/data
    data_dir = path.expanduser('~/pantheon/test/data')
    shutil.rmtree(data_dir, ignore_errors=True)

    # run test.py
    cmd = '~/pantheon/test/test.py local --pkill-cleanup'

    cmd += ' --schemes "%s"' % args['schemes']
    cmd += ' --uplink-trace %s' % args['uplink_trace']
    cmd += ' --downlink-trace %s' % args['downlink_trace']

    extra_cmds = []
    if args['delay'] > 0:
        extra_cmds.append('mm-delay %d' % args['delay'])
    if args['uplink_loss'] > 0:
        extra_cmds.append('mm-loss uplink %s' % args['uplink_loss'])
    if extra_cmds:
        cmd += ' --prepend-mm-cmds "%s"' % ' '.join(extra_cmds)

    cmd += (' --extra-mm-link-args "--uplink-queue=droptail '
            '--uplink-queue-args=packets=%d"' % args['uplink_queue'])

    sys.stderr.write('+ %s\n' % cmd)
    check_call(cmd, shell=True)


def run_analysis(args):
    # run plot.py and generate pantheon/test/data/perf_data.pkl
    cmd = '~/pantheon/analysis/plot.py --no-graphs'
    check_call(cmd, shell=True)


def collect_data(args):
    # write cc, tput, delay to perf_data
    pickle_data_path = path.expanduser('~/pantheon/test/data/perf_data.pkl')
    perf_data_path = path.expanduser('~/pantheon/test/data/perf_data')

    with open(pickle_data_path) as pickle_data_file:
        pickle_data = pickle.load(pickle_data_file)

    perf_data_f = open(perf_data_path, 'w')

    for scheme in pickle_data:
        assert len(pickle_data[scheme]) == 1
        run_id = 1

        stats = pickle_data[scheme][run_id]
        if stats is None:
            continue

        flows = parse_run_stats(stats.split('\n'))
        assert len(flows) == 1
        f = 1

        tput = flows[f][0]
        delay = flows[f][1]
        perf_data_f.write('%s,%.2f,%.2f\n' % (scheme, tput, delay))

    perf_data_f.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bandwidth', type=float, required=True)
    parser.add_argument('--delay', type=int, required=True)
    parser.add_argument('--uplink-queue', type=int, required=True)
    parser.add_argument('--uplink-loss', type=float, required=True)
    parser.add_argument('--schemes',
                        metavar='"SCHEME1 SCHEME2..."', required=True)
    prog_args = parser.parse_args()

    args = {}

    trace_path = gen_trace(prog_args.bandwidth)
    args['uplink_trace'] = trace_path
    args['downlink_trace'] = trace_path

    args['delay'] = prog_args.delay
    args['uplink_queue'] = prog_args.uplink_queue
    args['uplink_loss'] = prog_args.uplink_loss
    args['schemes'] = prog_args.schemes

    run_test(args)
    run_analysis(args)
    collect_data(args)


if __name__ == '__main__':
    main()
