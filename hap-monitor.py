#/bin/python

# Copyright European Organization for Nuclear Research (CERN)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Authors:
# - Ralph Vigne, <ralph.vigne@cern.ch>, 2014

import ConfigParser
import urllib2
import base64
import time
import traceback
import socket


from pystatsd import Client

__config = ConfigParser.ConfigParser()
__config.read('hap-monitor.cfg')

metric_cache = {}

def load_proxy_settings():
    proxies =  {}
    for proxy in __config.items('haproxies'):
        if proxy[0] == 'interval':
            continue
        proxies[proxy[0]] = settings = {}
        for s in __config.items(proxy[0]):
            settings[s[0]] = s[1]
    return proxies

def get_stats_http(settings):
    request = urllib2.Request(settings['url'])
    base64string = base64.encodestring('%s:%s' % (settings['user'], settings['pwd'])).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)   
    return urllib2.urlopen(request ).read().split('\n')

def get_stats_socket(settings):
    # show stats
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(settings['socket'])
    s.send('show stat\n')
    ret = s.recv(2048)
    s.close()
    return ret.split('\n')

def get_info_socket(settings):
    # show stats
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(settings['socket'])
    s.send('show info\n')
    ret = s.recv(2048)
    s.close()
    return ret

def connect_node_js():
    server = __config.get('carbon', 'carbon_server')
    port = __config.get('carbon', 'carbon_port')
    scope = __config.get('carbon', 'user_scope')
    return Client(host=server, port=port, prefix=scope)
    

def main():
        proxies = load_proxy_settings()
        pystatsd_client = connect_node_js()
        sleep_interval = float(__config.get('haproxies', 'interval'))
        if sleep_interval < 1:
            sleep_intervall = 1
        while True:
            for proxy in proxies:
                try:  # General purpose try-exectp to enusre execution
                    if 'socket' in proxies[proxy]:
                        try:  # If GET requests for HAProxy stats fails e.g. proxy down
                            stats = get_stats_socket(proxies[proxy])
                            info = parse_info(get_info_socket(proxies[proxy]), proxy)
                            for metric in info:
                                pystatsd_client.gauge(metric, info[metric])
                        except urllib2.URLError as e:
                            print 'Failed requesting stats %s' % proxies[proxy]['url'] 
                            print proxies[proxy]
                            reset_gauage_values(proxy, pystatsd_client)
                            continue
                    else:
                        try:  # If GET requests for HAProxy stats fails e.g. proxy down
                            stats = get_stats_http(proxies[proxy])
                        except urllib2.URLError as e:
                            print 'Failed requesting stats %s' % proxies[proxy]['url'] 
                            print proxies[proxy]
                            reset_gauage_values(proxy, pystatsd_client)
                            continue
                    stats = parse_stats(stats, proxy)
                    for metric in stats:
                        pystatsd_client.gauge(metric, stats[metric])
                except Exception as e:
                    print traceback.format_exc(e)
                    continue
                print 'Reported stats from  %s' % proxy
            time.sleep(sleep_interval)

def parse_stats(raw_stats, proxy):
    parsed_stats = {}
    headers = raw_stats.pop(0).split(',')[2:-1]  # Get the column headers and remove pxname and svname
    for stat in raw_stats[0:-1]:  # Parse each line, except the last one as it is empty
        stat = stat.split(',')
        if len(stat) != 2 or stat[0] == '':
            continue
        prefix = '%s.%s.%s' % (proxy, stat.pop(0), stat.pop(0)) # Build metric prefix using pxname and svname
        for column in range(len(headers)):
            try:
                parsed_stats[prefix+'.'+headers[column]] = float(stat[column])
            except:
                parsed_stats[prefix+'.'+headers[column]] = 0.0
    return parsed_stats

def parse_info(raw_info, proxy):
    ret = {}
    for l in raw_info.split('\n'):
        str = l.split(': ')
        try:
            ret[proxy+'.'+str[0]] = float(str[1])
        except:
            pass
    return ret

def reset_gauage_values(proxy, pystatsd_client):
    for metric in metric_cache:
        if metric.startswith(proxy):
            pystatsd_client.gauge(metric, 0.0)


if __name__ == "__main__":  main()
