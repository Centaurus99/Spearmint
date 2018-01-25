#!/usr/bin/env python

import sys
import argparse
from subprocess import Popen


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--num', metavar='N', type=int, default=1,
        help='number of instances to create (default: 1)')
    parser.add_argument(
        '--start-num', metavar='N', type=int, default=1,
        help='starting prefix to use (default: 1)')
    parser.add_argument(
        '--prefix', default='worker-',
        help='prefix for each instance (default: worker-)')
    parser.add_argument(
        '--zone', metavar='ZONE', default='us-central1-c',
        help='zone to create in (default: us-central1-c)')
    parser.add_argument(
        '--type', metavar='TYPE', default='n1-standard-2',
        help='machine type to use (default: n1-standard-2, 2 cores, 7.5 GB)')
    parser.add_argument(
        '--image', metavar='IMG', default='pantheon-ubuntu-1710',
        help='disk img to use (pantheon-ubuntu-1710)')
    parser.add_argument(
        '--disk-size', metavar='SIZE', type=int, default='10',
        help='disk size (default: 10 GB)')
    args = parser.parse_args()

    num_instances = args.num
    start_num = args.start_num
    prefix = args.prefix
    zone = args.zone
    machine_type = args.type
    img = args.image
    disk_size = args.disk_size

    general_cmd = ('gcloud beta compute --project "edgect-1155" '
                   'instances create "%s%d" --zone "%s" --machine-type "%s" '
                   '--network "default" --maintenance-policy "MIGRATE" '
                   '--service-account "489191239473-compute@developer.gserviceaccount.com" '
                   '--scopes '
                   '"https://www.googleapis.com/auth/devstorage.read_only",'
                   '"https://www.googleapis.com/auth/logging.write",'
                   '"https://www.googleapis.com/auth/monitoring.write",'
                   '"https://www.googleapis.com/auth/servicecontrol",'
                   '"https://www.googleapis.com/auth/service.management.readonly",'
                   '"https://www.googleapis.com/auth/trace.append" '
                   '--min-cpu-platform "Automatic" --image "%s" '
                   '--image-project "edgect-1155" --boot-disk-size "%d" '
                   '--boot-disk-type "pd-standard" '
                   '--boot-disk-device-name "%s%d"')

    procs = []

    for i in xrange(start_num, start_num + num_instances):
        cmd = general_cmd % (prefix, i, zone, machine_type,
                             img, disk_size, prefix, i)
        procs.append(Popen(cmd, shell=True))

    for proc in procs:
        proc.wait()


if __name__ == '__main__':
    main()
