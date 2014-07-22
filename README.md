HAP-Monitor
===========

Poll several HAProxy instances and reports them to Graphite/Node.js

# Purpose

A simple Python script requesting the statistics of several HAProxies (http://www.haproxy.org/) and reports them into Graphite (http://graphite.wikidot.com/).

# Dependencies

In order to report data to Graphite, the Python module _py-statsd_ is used. The source code can be found here at GitHub in the repository https://github.com/sivy/py-statsd.git.
Installation instructions are given in according README.md file.

# Configuration

1. Copy hap-monitor.cfg.template to hap-monitor.cfg
2. In the cfg file: list every HAProxy instance you want to monitor e.g. demo_proxy and set the polling interval (seconds) to your likings.
3. Define a separate section for each instance listed in 2) and set up URI and user credentials. TIP: verifiy if the provided URI works in your browser (note the csv;norefresh query arguments in example URI). If you see CSV data after the basic authentication you're good to go. 
4. Enter URI, port and userscope of your Graphite instance in the carbon section of the config file

Start hap-monitor.py and data should be reported to Garphit now. Please note that values are provided as gauge values, resulting missleading data if for example a nodes is down. Maybe I'll address this issue in a future version, but for now it just like that.

# License
Copyright European Organization for Nuclear Research (CERN)

Licensed under the Apache License, Version 2.0 (the "License");
You may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
