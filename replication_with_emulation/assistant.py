#!/usr/bin/env python

import sys
import argparse
import signal
from subprocess import Popen, call
from helpers import worker_ips, timeout_handler, TimeoutError


def run_cmd(host, cmd):
    if cmd == 'setup':
        cmd = ('cd ~/Spearmint && git fetch --all && '
               'git checkout colombia-no-delay; '
               'sudo sysctl -w net.core.default_qdisc=pfifo_fast; '
               'cd ~/pantheon && git fetch --all && '
               './test/setup.py --all --setup')
    elif cmd == 'cleanup':
        cmd = ('rm -rf /tmp/pantheon-tmp; '
               'python ~/pantheon/helpers/pkill.py')

    ssh_cmd = ['ssh', host, cmd]
    return Popen(ssh_cmd)


def remove_key(ip):
    cmd = 'ssh-keygen -f "/home/francisyyan/.ssh/known_hosts" -R ' + ip
    call(cmd, shell=True)


def test_ssh(host):
    cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=5',
            host, 'echo $HOSTNAME']
    call(cmd)


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

    ip_list = worker_ips()
    procs = []

    sys.stderr.write('%d IPs in total\n' % len(ip_list))

    for ip in ip_list:
        host = args.username + '@' + ip

        if args.cmd == 'remove_key':
            remove_key(ip)
        elif args.cmd == 'test_ssh':
            test_ssh(host)
        else:
            procs.append(run_cmd(host, args.cmd))

    for proc in procs:
        proc.communicate()


if __name__ == '__main__':
    main()
