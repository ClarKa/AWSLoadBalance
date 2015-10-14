#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Kaifu Wang
# @Date:   2015-09-27 03:16:56
# @Last Modified by:   Kaifu Wang
# @Last Modified time: 2015-09-27 22:22:17

import os
import urllib2
import ConfigParser
from boto.ec2.connection import EC2Connection
import time

LG_IMAGE         = 'ami-4389fb26'
LG_INSTANCE_TYPE = 'm3.medium'
# LG_INSTANCE_TYPE = 't2.micro'
DC_IMAGE         = 'ami-abb8cace'
# DC_INSTANCE_TYPE = 't2.micro'
DC_INSTANCE_TYPE = 'm3.medium'
ZONE             = 'us-east-1'
KEY_NAME         = 'Project1'
dc_dns           = ''
lg_dns           = ''
start_time       = 0

conn = EC2Connection()

#create security group for all traffic
sec_group = conn.create_security_group('All_Traffic', 'project 2.1')
sec_group.authorize('-1',None,None,'0.0.0.0/0')

SECURITY_GROUPS = ['All_Traffic']

#launch load generators
print 'Starting Load Generator instance of type {0} with image {1}'.format(LG_INSTANCE_TYPE, LG_IMAGE)
reservation = conn.run_instances(
        LG_IMAGE,
        key_name=KEY_NAME,
        instance_type=LG_INSTANCE_TYPE,
        security_groups=SECURITY_GROUPS)
lg = reservation.instances[0]
time.sleep(10)

while not lg.update() == 'running':
    time.sleep(5)

if lg.update() == 'running':
    lg_dns = lg.public_dns_name
    print 'Load Generator running'
    lg.add_tag("Project","2.1")

#launch first data center
def addDataCenter():
    global dc_dns
    print 'Starting Data Center instance of type {0} with image {1}'.format(DC_INSTANCE_TYPE, DC_IMAGE)
    reservation = conn.run_instances(
            DC_IMAGE,
            key_name=KEY_NAME,
            instance_type=DC_INSTANCE_TYPE,
            security_groups=SECURITY_GROUPS)
    dc = reservation.instances[0]

    start_time = time.time()

    while not dc.update() == 'running':
        time.sleep(10)

    if dc.update() == 'running':
        print 'Data center running'
        dc.add_tag("Project","2.1")
        dc_dns = dc.public_dns_name
        time.sleep(100)

addDataCenter()

#submit submission pwd to load generator
sub_pwd = 'c4tymYhLipn0VJR3T9WMqBo9tBnXjJhz'
sub_url = 'http://' + lg_dns + '/password?passwd=' + sub_pwd
print 'submitting pwd @' + sub_url
while True:
    try:
        urllib2.urlopen(sub_url)
        print 'submission password submitted'
        break
    except:
        time.sleep(5)

#submit data center's dns to load generator to start the test
test_url = 'http://' + lg_dns + '/test/horizontal?dns=' + dc_dns
print 'submitting test request @' + test_url
while True:
    try:
        res = urllib2.urlopen(test_url)
        print 'Test has been started'
        break
    except:
        time.sleep(5)

#get log url
res = urllib2.urlopen('http://' + lg_dns + '/log')
s = res.read()
log_url = 'http://' + lg_dns + s[s.find('/log'):s.find('.log')+4]
print 'test log url @' + log_url


#trace log data
config = ConfigParser.SafeConfigParser()
total_rps = 0

while(total_rps<4000):
    total_rps = 0
    res = urllib2.urlopen(log_url)
    config.readfp(res,log_url)
    print config.sections()
    if config.has_section('Minute 1') == False:
        time.sleep(1)
        continue

    last = config.sections()[-1]

    for item in config.items(last):
        total_rps += float(item[1])

    if total_rps >= 4000:
        break;

    interval = time.time() - start_time
    if interval > 100:
        addDataCenter()
        while True:
            try:
                res = urllib2.urlopen('http://' + lg_dns + '/test/horizontal/add?dns=' + dc_dns)
                print 'New Data Center instance added'
                break
            except:
                time.sleep(10)
    else:
        time.sleep(20)
