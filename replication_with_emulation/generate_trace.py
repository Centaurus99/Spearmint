#!/usr/bin/env python

import argparse
import numpy as np
from os import path
from helpers import make_sure_path_exists


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bandwidth', metavar='Mbps', required=True,
                        help='constant bandwidth (Mbps)')
    parser.add_argument('--output-dir', metavar='DIR', required=True,
                        help='directory to output trace')
    args = parser.parse_args()

    # number of packets in 60 seconds
    num_packets = int(float(args.bandwidth) * 5000)
    ts_list = np.linspace(0, 60000, num=num_packets, endpoint=False)

    # trace path
    make_sure_path_exists(args.output_dir)
    trace_path = path.join(args.output_dir, '%smbps.trace' % args.bandwidth)

    # write timestamps to trace
    ts_base = 0
    with open(trace_path, 'w') as trace:
        for i in xrange(50):
            ts_base += 100
            trace.write('%d\n' % ts_base)

        for ts in ts_list:
            trace.write('%d\n' % (ts_base + ts))


if __name__ == '__main__':
    main()
