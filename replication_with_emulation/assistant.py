#!/usr/bin/env python

import sys
import argparse
import signal
from subprocess import Popen, call
from helpers import gce_worker_ips, timeout_handler, TimeoutError


def run_cmd(host, cmd):
    if cmd == 'setup':
        cmd = ('cd ~/Spearmint && git pull; '
               'sudo sysctl -w net.core.default_qdisc=pfifo_fast; '
               'cd ~/pantheon && git checkout master && git pull && '
               './test/setup.py --all --setup')
    elif cmd == 'cleanup':
        cmd = ('rm -rf /tmp/pantheon-tmp; '
               'python ~/pantheon/helpers/pkill.py')

    ssh_cmd = ['ssh', host, cmd]
    return Popen(ssh_cmd)


def test_ssh(host):
    cmd = ['ssh', '-oStrictHostKeyChecking=no', host, 'echo $HOSTNAME']

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)

    try:
        if call(cmd) != 0:
            sys.stderr.write('Error connecting %s\n' % host)
    except TimeoutError:
        sys.stderr.write('Timed out connecting %s\n' % host)
    else:
        signal.alarm(0)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--username', default='francisyyan',
        help='username used in ssh (default: francisyyan)')
    parser.add_argument(
        '--pantheon-dir', metavar='DIR', default='~/pantheon',
        help='path to pantheon/ (default: ~/pantheon)')
    parser.add_argument('cmd', metavar='CMD')
    args = parser.parse_args()

    ip_list = gce_worker_ips()
    procs = []

    for ip in ip_list:
        host = args.username + '@' + ip

        if args.cmd == 'test_ssh':
            test_ssh(host)
        else:
            procs.append(run_cmd(host, args.cmd))

    for proc in procs:
        proc.communicate()


if __name__ == '__main__':
    main()
