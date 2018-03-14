#!/usr/bin/env python
# Copyright European Organization for Nuclear Research (CERN) 2013
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
#
# Authors:
# - Ralph Vigne <ralph.vigne@cern.ch>, 2014
# - Alex Typaldos, 2016
#   This was modified from the original hap-monitor-cron.py by above author to send Stats to Graphite via TCP instead of UDP

import argparse
import socket
import traceback
import logging
import sys
import time

from sys import stdout

# Define logger
logging.basicConfig(stream=stdout,
                    level=logging.ERROR,
                    format='%(asctime)s\t%(process)d\t%(levelname)s\t%(message)s')

logger = logging.getLogger(__name__)


def monitor_haproxy(socket_name):
    data = {}
    INCLUDE_INFO = ['Process_num', 'Idle_pct']
    INCLUDE_STAT = ['scur', 'qcur', 'chkfail', 'status', 'hrsp_1xx', 'hrsp_2xx', 'hrsp_3xx', 'hrsp_4xx', 'hrsp_5xx', 'req_rate', 'qtime', 'ctime', 'rtime', 'ttime', 'rate']

    # Request data from socket
    logger.debug('Connecting to socket: %s' % socket_name)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(socket_name)
        logger.debug('Requesting info')
        s.send('show info\n')
        raw_info = s.recv(4096)
        s.close()  # Note: socket is not reusable
        logger.debug('Requesting stat')
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(socket_name)
        s.send('show stat\n')
        raw_stat = s.recv(8192)
        s.close()
    except Exception as e:
        logger.error('Failed requesting data from socket %s with execption %s' % (socket_name, e))
        logger.debug(traceback.format_exc(e))
        return None
    logger.debug('Successfully requested data from socket.')

    # Transforming info response into dictonary
    logger.debug('Parsing info response')
    for entry in raw_info.split('\n'):
        tmp = entry.split(': ')
        try:
            if tmp[0] in INCLUDE_INFO:
                data[tmp[0]] = float(tmp[1])
        except Exception as e:
            logger.error('Entry: %s failed with exception: %s' % (tmp, e))
            logger.debug(traceback.format_exc(e))
    logger.debug('Done parsing info response.')

    # Transforming stat response into dictonary
    logger.debug('Parsing stat response')
    raw_stat = raw_stat.split('\n')
    headers = raw_stat.pop(0).split(',')[2:-1]  # Get the column headers and remove pxname and svname
    for stat in raw_stat:
        stat = stat.split(',')
        if len(stat) == 1:
            logger.debug('Ignored line: %s' % stat[0])
            continue  # Line is something else than stats
        prefix = '%s.%s' % (stat.pop(0), stat.pop(0))  # Build metric prefix using pxname and svname
        for column in range(len(headers)):
            try:
                if headers[column] in INCLUDE_STAT:
                    if (headers[column] == 'status') and (stat[column] in ['UP', 'DOWN', 'MAINT']) and (data['Process_num'] == 1.0):
                        for s in ['UP', 'DOWN', 'MAINT']:
                            data[prefix+'.'+headers[column]+'.'+s] = 0  # set all status to zero to support gauge values
                        data[prefix+'.'+headers[column]+'.'+stat[column]] = 1
                    else:
                        data[prefix+'.'+headers[column]] = float(stat[column])
            except Exception as e:
                logger.warning('Ignoring data: %s -> %s' % (headers[column], stat[column]))
    logger.debug('Done parsing stat response.')
    return data


def backend_graphite(url, stats, prefix):
    process_num = stats['Process_num']
    del(stats['Process_num'])
    server_name = socket.getfqdn().split('.')[0]
    prefix = '%s.%s.%s' % (prefix, server_name, int(process_num))
    logger.debug('Reporting to prefix: %s' % prefix)
    server, port = url.split(':')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server, int(port)))
    except Exception, e:
        logger.error('Unable to connect to Graphite backend %s: %s' % (url, e))
        raise

    for s in stats:
        try:
            sock.send('%s.%s %s %s\n' % (prefix, s, float(stats[s]), int(time.time())))
            logger.debug('Message: %s.%s %s %s\n' % (prefix, s, float(stats[s]), int(time.time())))
        except Exception as e:
            logger.error('Failed reporting %s.%s %s %s\n' % (prefix, s, float(stats[s]), time.time()))
            logger.error(traceback.format_exc(e))
    sock.close()


def backend_statsd(url, stats, prefix):
    from pystatsd import Client
    process_num = stats['Process_num']
    del(stats['Process_num'])
    server_name = socket.getfqdn().split('.')[0]
    prefix = '%s.%s.%s' % (prefix, server_name, int(process_num))
    logger.debug('Reporting to prefix: %s' % prefix)
    server, port = url.split(':')
    try:
        pystatsd_client = Client(host=server, port=port, prefix=prefix)
    except Exception, e:
        logger.error('Unable to connect to statsd backend %s: %s' % (url, e))
        raise

    for s in stats:
        try:
            pystatsd_client.gauge(s, float(stats[s]))
            logger.debug('%s.%s => %s' % (prefix, s, float(stats[s])))
        except Exception as e:
            logger.error('Failed reporting %s (%s): %s' % (s, stats[s], e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', metavar='B', type=str, nargs=1,  help='Backend server URL[:port][::scope] to which the script will report to. E.g. --backend my.graphite.host:8025/listen/now::rucio.loadbalancer')
    parser.add_argument('--type', metavar='T', type=str, nargs=1,  help='Type of the backend server. Supported values are: G (Graphite) and S (statsd)')
    parser.add_argument('--sockets', metavar='S', type=str, nargs='+',  help='a list of socket files e.g. /var/run/haproxy_admin_process_no_1.sock')
    parser.add_argument('--verbose', help='makes it chatty', action="store_true")

    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(level=logging.DEBUG)

    if args.sockets is None:
        print 'At least one input socket must be defined. Run --help for further information.'
        sys.exit(1)

    if args.backend is None:
        print 'No backend information provided. Run --help for further information.'
        sys.exit(1)
    print args
    type = 'g' if ((args.type is not None) and (args.type[0].lower() == 'g')) else 's'  # If not Graphite, statsd is used

    args = vars(args)

    try:
        url, prefix = args['backend'][0].split('::')
        logger.debug('Reporting to backend (type: %s) => URL: %s\tPrefix: %s' % (type, url, prefix))
    except ValueError:
        logger.critical('Can not unpack backend information: %s' % args['backend'][0])
        sys.exit(1)

    for socket_name in args['sockets']:
        try:
            data = monitor_haproxy(socket_name)
            if type == 'g':
                backend_graphite(url, data, prefix)
            else:
                backend_statsd(url, data, prefix)
        except Exception as e:
            logger.error(e)
            sys.exit(1)
    sys.exit(0)
