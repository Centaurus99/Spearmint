#!/usr/bin/env python

import argparse
from subprocess import Popen
from helpers import gce_worker_ips


def run_cmd(host, cmd):
    if cmd == 'setup':
        cmd = ('sudo sysctl -w net.core.default_qdisc=pfifo_fast; '
               'cd ~/pantheon && git checkout master && git pull && '
               './test/setup.py --all --setup')
    elif cmd == 'cleanup':
        cmd = ('rm -rf /tmp/pantheon-tmp; '
               'python ~/pantheon/helpers/pkill.py; '
               'pkill -f pantheon')
    elif cmd == 'pull_spearmint':
        cmd = 'cd ~/Spearmint && git pull'

    ssh_cmd = ['ssh', host, cmd]
    return Popen(ssh_cmd)


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
        procs.append(run_cmd(host, args.cmd))

    for proc in procs:
        proc.communicate()


if __name__ == '__main__':
    main()
