#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Kaifu Wang
# @Date:   2015-10-04 10:25:55
# @Last Modified by:   Kaifu Wang
# @Last Modified time: 2015-10-04 22:48:51

from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection
from boto.ec2.autoscale import AutoScaleConnection
import time

conn = EC2Connection()
con_l = ELBConnection()
con_a = AutoScaleConnection()

res = conn.get_all_instances()
ids = []
for r in res:
    ids.append(r.instances[0].id)

for s in ids:
    try:
        conn.terminate_instances(instance_ids=[s])
    except:
        continue

try:
    con_l.delete_load_balancer('ELB')
    time.sleep(60)
except:
    pass
con_a.delete_auto_scaling_group('Project2.2_AutoSacling_Group', force_delete=True)
con_a.delete_launch_configuration('Project2.2_Lauch_Config')

while True:
    try:
        conn.delete_security_group(name='LBAS')
        conn.delete_security_group(name='Load_Generator')
        break
    except:
        time.sleep(5)
