#!/usr/bin/env python

import sys
import pickle
import json
import argparse
from subprocess import call, check_call
from os import path
from helpers import CURRDIR, parse_run_stats


def gen_trace(bw):
    gen_trace_path = path.join(CURRDIR, 'generate_trace.py')
    traces_dir = path.join(CURRDIR, 'traces')

    bw = '%.2f' % bw
    cmd = ['python', gen_trace_path, '--bandwidth', bw,
           '--output-dir', traces_dir]
    sys.stderr.write('+ %s\n' % ' '.join(cmd))
    check_call(cmd)

    return path.join(traces_dir, '%smbps.trace' % bw)


def run_test(args):
    # remove contents in ~/pantheon/test/data
    data_dir = path.expanduser('~/pantheon/test/data')
    call('rm -rf %s/*' % data_dir, shell=True)

    # run test.py
    cmd = '~/pantheon/test/test.py local --pkill-cleanup'

    if args['flows'] > 1:
        cmd += ' -f %d' % args['flows']

        if args['interval'] > 0:
            cmd += ' --interval %d' % args['interval']

    cmd += ' --schemes "%s"' % args['schemes']
    cmd += ' --uplink-trace %s' % args['uplink_trace']

    extra_cmds = []
    if args['delay'] is not None:
        extra_cmds.append('mm-delay %d' % args['delay'])
    if args['uplink_loss'] is not None:
        extra_cmds.append('mm-loss uplink %s' % args['uplink_loss'])
    if extra_cmds:
        cmd += ' --prepend-mm-cmds "%s"' % ' '.join(extra_cmds)

    if args['uplink_queue'] is not None:
        cmd += (' --extra-mm-link-args "--uplink-queue=droptail '
                '--uplink-queue-args=packets=%d"' % args['uplink_queue'])

    sys.stderr.write('+ %s\n' % cmd)
    check_call(cmd, shell=True)


def run_analysis(args):
    # run plot.py and generate pantheon/test/data/perf_data.pkl
    cmd = '~/pantheon/analysis/plot.py --no-graphs'
    sys.stderr.write('+ %s\n' % cmd)
    check_call(cmd, shell=True)


def collect_data(args):
    # write cc, tput, delay to perf_data
    pickle_data_path = path.expanduser('~/pantheon/test/data/perf_data.pkl')
    if not path.isfile(pickle_data_path):
        return False

    with open(pickle_data_path) as fh:
        pickle_data = pickle.load(fh)

    perf_data_dict = {}

    for scheme in pickle_data:
        if len(pickle_data[scheme]) != 1:
            return False

        run_id = 1

        stats = pickle_data[scheme][run_id]
        if stats is None:
            return False

        flows = parse_run_stats(stats.split('\n'))
        perf_data_dict[scheme] = flows

    perf_data_path = path.expanduser('~/pantheon/test/data/perf_data.json')
    with open(perf_data_path, 'w') as fh:
        json.dump(perf_data_dict, fh)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--flows', type=int, default=1)
    parser.add_argument('--interval', type=int, default=0)
    parser.add_argument('--bandwidth', type=float, required=True)
    parser.add_argument('--delay', type=int)
    parser.add_argument('--uplink-queue', type=int)
    parser.add_argument('--uplink-loss', type=float)
    parser.add_argument('--schemes',
                        metavar='"SCHEME1 SCHEME2..."', required=True)
    prog_args = parser.parse_args()

    args = {}

    args['flows'] = prog_args.flows
    args['interval'] = prog_args.interval

    trace_path = gen_trace(prog_args.bandwidth)
    args['uplink_trace'] = trace_path
    args['downlink_trace'] = trace_path

    args['delay'] = prog_args.delay
    args['uplink_queue'] = prog_args.uplink_queue
    args['uplink_loss'] = prog_args.uplink_loss
    args['schemes'] = prog_args.schemes

    RERUN = 1
    for i in xrange(RERUN + 1):  # run tests at most twice
        run_test(args)
        run_analysis(args)
        if collect_data(args):
            break
        else:
            if i < RERUN:
                sys.stderr.write('worker.py: re-running test\n')


if __name__ == '__main__':
    main()
