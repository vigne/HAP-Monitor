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


from pystatsd import Client

__config = ConfigParser.ConfigParser()
__config.read('hap-monitor.cfg')

def load_proxy_settings():
    proxies =  {}
    for proxy in __config.items('haproxies'):
        if proxy[0] == 'interval':
            continue
        proxies[proxy[0]] = settings = {}
        for s in __config.items(proxy[0]):
            settings[s[0]] = s[1]
    return proxies

def get_stats(settings):
    request = urllib2.Request(settings['url'])
    base64string = base64.encodestring('%s:%s' % (settings['user'], settings['pwd'])).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)   
    return urllib2.urlopen(request).read().split('\n')

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
		print 'Checking instance: %s' % proxy
                try:
                    stats = get_stats(proxies[proxy])
                    headers = stats[0].split(',')
                    num_cols = len(headers)
                    for stat in stats[1:-1]:
                        stat = stat.split(',')
                        prefix = '%s.%s' % (stat[0], stat[1])
                        pos = 2
                        while pos < num_cols:
                            # If required, check if col is in list of interesting cols
                            if stat[pos].isdigit():
                                pystatsd_client.gauge(prefix+'.'+headers[pos], float(stat[pos]))
                            pos += 1
                except Exception as a:
		    print traceback.format_exc(e)
                    continue
            time.sleep(sleep_interval)
    

if __name__ == "__main__":  main()
