HAP-Monitor
===========

Requests HAProxy statistics and reports them to a Graphite/NodeJS backend.
This version of the script is intedend to be executed as a cronjob.

A script doing the same, but runs as a daemon was created by P. Roberts and can be found here: https://github.com/phillipbroberts/HAP-Monitor

# Purpose

A simple Python script requesting the statistics of several HAProxies (http://www.haproxy.org/) and reports them into Graphite (http://graphite.wikidot.com/).

# Dependencies

In order to report data to Graphite, the Python module _py-statsd_ is used. The source code can be found here at GitHub in the repository https://github.com/sivy/py-statsd.git.
Installation instructions are given in according README.md file.

# Configuration

The script is configured solely by CLI argumets.

    usage: hap-monitor-cron.py [-h] [--backend B] [--sockets S [S ...]] [--verbose]

    optional arguments:
      -h, --help           show this help message and exit
      --backend B          Graphite server URL[:port][::scope] to which the script will report to. E.g. --backend graphite.host:8025::my.system.stats.haproxy
      --type T             Type of the backend server. Supported values are: G (Graphite) and S (statsd)
      --sockets S [S ...]  a list of socket files e.g. /var/run/haproxy_admin_process_no_1.sock
      --verbose            makes it chatty

To execute it in the desired interval define a cronjob on the host running HAProxy. For example, we want collect data with one minute intervall:

    */1 * * * * python /usr/local/bin/hap-monitor.py --backend graphite.host:8025::my.system.stats.haproxy --type G --sockets /var/run/haproxy_admin_process_no_1.sock /var/run/haproxy_admin_process_no_2.sock

Also note, that the example above assumes HAProxy running two processes reproting iwhich conequently report into two distinct sockets.

# License
Copyright European Organization for Nuclear Research (CERN)

Licensed under the Apache License, Version 2.0 (the "License");
You may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
