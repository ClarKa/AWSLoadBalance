#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Kaifu Wang
# @Date:   2015-10-03 03:16:56
# @Last Modified by:   Kaifu Wang
# @Last Modified time: 2015-10-04 22:44:38

import os
import urllib2
import ConfigParser
import time

import boto
from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection
from boto.ec2.elb import HealthCheck
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup
from boto.ec2.autoscale import ScalingPolicy
from boto.ec2.autoscale import Tag
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.cloudwatch import MetricAlarm

# ---------------------------General Configuration------------------------------
LG_IMAGE         = 'ami-312b5154'
LG_INSTANCE_TYPE = 'm3.medium'
# LG_INSTANCE_TYPE = 't2.micro'

DC_IMAGE         = 'ami-3b2b515e'
DC_INSTANCE_TYPE = 'm3.medium'
# DC_INSTANCE_TYPE = 't2.micro'
DETAIL_MON        = True

REGION           = 'us-east-1'
KEY_NAME         = 'Project1'
dc_dns           = ''
lg_dns           = ''
lb_dns           = ''
start_time       = 0

con_region = boto.ec2.connect_to_region(REGION)
zone_list = con_region.get_all_zones()
ZONE = []
for item in zone_list:
    ZONE.append(item.name)

conn = EC2Connection()
#create security groups for all traffic
sec_group1 = conn.create_security_group('Load_Generator', 'project 2.2')
sec_group1.authorize('-1',None,None,'0.0.0.0/0')
SECURITY_GROUP1 = [sec_group1.name]

sec_group2 = conn.create_security_group('LBAS', 'project 2.2')
sec_group2.authorize('-1',None,None,'0.0.0.0/0')
SECURITY_GROUP2 = [sec_group2.name]

# -------------------------Launch Load Generators-------------------------------
print 'Starting Load Generator instance of type {0} with image {1}'.format(LG_INSTANCE_TYPE, LG_IMAGE)
reservation = conn.run_instances(
        LG_IMAGE,
        key_name=KEY_NAME,
        instance_type=LG_INSTANCE_TYPE,
        placement=ZONE[0],
        security_groups=SECURITY_GROUP1)
lg = reservation.instances[0]
time.sleep(10)

while not lg.update() == 'running':
    time.sleep(5)

if lg.update() == 'running':
    lg_id = lg.id
    lg_dns = lg.public_dns_name
    print 'Load Generator running'
    lg.add_tag("Project","2.2")

# -------------------------Create Load Balancer---------------------------------
con_elb = ELBConnection()
elb = {
    'name': 'ELB',
    'zone': ZONE,
    'ports': [(80, 80, 'http')],
    'target': 'HTTP:80/heartbeat?lg=',
    'time_out': 3,
    'interval': 20
}

lb = con_elb.create_load_balancer(elb['name'],
                                  elb['zone'],
                                  listeners=elb['ports'],
                                  security_groups=sec_group2.id)
time.sleep(5)

lb_dns = lb.dns_name;
elb['target'] += lg_dns

hc = HealthCheck(interval=elb['interval'],
                 healthy_threshold=10,
                 unhealthy_threshold=2,
                 target=elb['target'],
                 timeout=elb['time_out'])

lb.configure_health_check(hc)

params = {"LoadBalancerNames.member.1": lb.name,
                      "Tags.member.1.Key": 'Project',
                      "Tags.member.1.Value": '2.2'}
s=lb.connection.get_status('AddTags', params, verb='POST')

print 'Load Balancer DNS: ' + lb_dns

# -------------------------Create Auto Scaling Group----------------------------
con_as = AutoScaleConnection()
lc = LaunchConfiguration(name='Project2.2_Lauch_Config',
                         image_id=DC_IMAGE,
                         key_name=KEY_NAME,
                         security_groups=SECURITY_GROUP2,
                         instance_type=DC_INSTANCE_TYPE,
                         instance_monitoring=DETAIL_MON)
con_as.create_launch_configuration(lc)

asg = AutoScalingGroup(name='Project2.2_AutoSacling_Group',
                       load_balancers=[elb['name']],
                       availability_zones=ZONE,
                       health_check_period='120',
                       health_check_type='ELB',
                       launch_config=lc,
                       min_size=1,
                       max_size=5,
                       tags=[Tag(key='Project', value='2.2',propagate_at_launch=True,resource_id='Project2.2_AutoSacling_Group')])
con_as.create_auto_scaling_group(asg)

# -------------------------Create Scaling Policies------------------------------
scaleOut = ScalingPolicy(name='ScaleOut',
                         adjustment_type='ChangeInCapacity',
                         as_name=asg.name,
                         scaling_adjustment=1,
                         cooldown=100)

scaleIn = ScalingPolicy(name='ScaleIn',
                        adjustment_type='ChangeInCapacity',
                        as_name=asg.name,
                        scaling_adjustment=-1,
                        cooldown=100)

con_as.create_scaling_policy(scaleOut)
con_as.create_scaling_policy(scaleIn)

scaleOut_policy = con_as.get_all_policies(
            as_group=asg.name, policy_names=['ScaleOut'])[0]
scaleIn_policy = con_as.get_all_policies(
            as_group=asg.name, policy_names=['ScaleIn'])[0]

# -------------------------Create CloudWatch Alarm------------------------------
con_cw = CloudWatchConnection()

alarm_dimensions = {"AutoScalingGroupName": asg.name}

scaleOut_alarm = MetricAlarm(name='scaleOut_on_cpu',
                             namespace='AWS/EC2',
                             metric='CPUUtilization',
                             statistic='Average',
                             comparison='>',
                             threshold='70',
                             period='120',
                             evaluation_periods=1,
                             alarm_actions=[scaleOut_policy.policy_arn],
                             dimensions=alarm_dimensions)

scaleIn_alarm = MetricAlarm(name='scaleIn_on_cpu',
                            namespace='AWS/EC2',
                            metric='CPUUtilization',
                            statistic='Average',
                            comparison='<',
                            threshold='30',
                            period='180',
                            evaluation_periods=1,
                            alarm_actions=[scaleIn_policy.policy_arn],
                            dimensions=alarm_dimensions)

con_cw.create_alarm(scaleOut_alarm)
con_cw.create_alarm(scaleIn_alarm)

# -------------------------Submit submission password---------------------------
sub_pwd = 'c4tymYhLipn0VJR3T9WMqBo9tBnXjJhz'
sub_url = 'http://' + lg_dns + '/password?passwd=' + sub_pwd
print 'submitting pwd to' + sub_url
while True:
    try:
        urllib2.urlopen(sub_url)
        print 'submission password submitted'
        break
    except:
        time.sleep(5)

# -------------------------Warm Up Load Balancer--------------------------------
warmup_url = 'http://' + lg_dns + '/warmup?dns=' + lb_dns
print 'send warm up request to' + warmup_url
while True:
    try:
        urllib2.urlopen(warmup_url)
        print 'warmup request submitted'
        break
    except:
        time.sleep(5)
time.sleep(320)

# ---------------------------Start test-----------------------------------------
test_url = 'http://' + lg_dns + '/junior?dns=' + lb_dns
print 'send test request to' + test_url
urllib2.urlopen(test_url)
print 'Test request submitted'
time.sleep(2900);

# ---------------------------Clean UP-------------------------------------------
res = conn.get_all_instances()
ids = []
for r in res:
    ids.append(r.instances[0].id)

for s in ids:
    if s == lg_id:
        continue
    try:
        conn.terminate_instances(instance_ids=[s])
    except:
        continue

time.sleep(100);

con_elb.delete_load_balancer('ELB')
time.sleep(100)

con_as.delete_auto_scaling_group('Project2.2_AutoSacling_Group', force_delete=True)
con_as.delete_launch_configuration('Project2.2_Lauch_Config')

while True:
    try:
        conn.delete_security_group(name='LBAS')
        conn.delete_security_group(name='Load_Generator')
        break
    except:
        time.sleep(5)

