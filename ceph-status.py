#!/usr/bin/python
#
# ceph-status.py Zabbix plugin for Ceph monitoring
# Copyright (c) 2014 Marcos Amorim <marcosmamorim@gmail.com>
# 
# This code is based in ceph-status.sh develped by Julien Recurt <julien@recurt.fr>
#

import sys
import json
import getopt

# ceph binary path
ceph="/usr/bin/ceph"

# rados binary path
rados="/usr/bin/rados"

script_name="%s" % sys.argv[0]

states_count = { "creating": 0,
        "active": 0,
        "clean": 0,
        "osd_down": 0,
        "replay": 0,
        "splitting": 0, 
        "scrubbing" :0,
        "degraded": 0,
        "inconsistent": 0,
        "peering": 0,
        "repair": 0,
        "recovering": 0,
        "backfill" :0,
        "backfilling" :0,
        "wait-backfill": 0,
        "incomplete": 0,
        "stale": 0,
        "remapped" : 0, 
        "deep" : 0, 
        "health": 1,
        "osd_in": 0,
        "osd_up": 0,
        "active": 0,
        "backfill": 0,
        "clean": 0,
        "creating": 0,
        "degraded": 0,
        "degraded_percent": 0,
        "incomplete": 0,
        "inconsistent": 0,
        "peering": 0,
        "recovering": 0,
        "remapped": 0,
        "repair": 0,
        "replay": 0,
        "stale": 0,
        "pgtotal": 0,
        "waitBackfill": 0,
        "mon": 0,
        "rados_objects": 0,
        "rados_total": 0,
        "rados_used": 0,
        "rados_free": 0,
        "wrbps": 0,
        "rdbps": 0,
        "ops": 0
        }

'''Util to calculate percents values'''
def percentUtil(v1, v2):
    if v1 == 0:
        return 0

    return round(float(v1)*100/float(v2), 2)

'''Create zabbix_ceph.conf'''
def CreateZabbix():
    for i in sorted(states_count):
        print "UserParameter=ceph.%s, %s %s" % (i, script_name, i)

'''Show help and options'''
def Usage():
    print "Help %s" % sys.argv[0]
        for i in sorted(states_count):
            print "\t%s %s" % (script_name, i)

        print "\t%s zabbix-conf\tCreate zabbix_ceph.conf" % script_name


'''Get ceph health'''
def Health():
    import subprocess 
        p = subprocess.Popen([ceph, 'health', '-f', 'json-pretty'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        try:
            out, err = p.communicate()

        except ValueError:
            print 'Cannot execute command'

        data = json.loads(out)

        # default health is 1, the cluster is OK, we are check if not OK only
        if data['overall_status'] == 'HEALTH_WARN':
            states_count['health'] = 2
        elif data['overall_status'] == 'HEALTH_ERR':
            states_count['health'] = 3

'''Get all monitors status'''
def Monitors():
    import subprocess 
        p = subprocess.Popen([ceph, 'status', '-f', 'json-pretty'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        try:
            out, err = p.communicate()

        except ValueError:
            print 'Cannot execute command'

        data = json.loads(out)

        # TODO: Get all monitors and running monitors
        states_count['mon'] = len(data['quorum_names'])

'''Check OSDs status'''
def GetOsd():
    import subprocess 
        p = subprocess.Popen([ceph, 'osd', 'dump', '-f', 'json-pretty'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        try:
            out, err = p.communicate()

        except ValueError:
            print 'Cannot execute command'

        data = json.loads(out)

        max_osd = data['max_osd']
        states_count['in'] = data['max_osd']
        up = 0
        ok = 0
        down = 0
        for o in data['osds']:
            if o['in'] == 1:
                ok += 1

                if o['up'] == 1:
                    up += 1
                else:
                    down += 1

        states_count['osd_down'] = percentUtil(down, max_osd)
        states_count['osd_up'] = percentUtil(up, max_osd)
        states_count['osd_in'] = percentUtil(ok, max_osd)

'''Get all information about cluster utilisation'''
def SpaceRados():
    import subprocess 
        p = subprocess.Popen([rados, 'df', '-f', 'json-pretty'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        try:
            out, err = p.communicate()

        except ValueError:
            print 'Cannot execute command'

        data = json.loads(out)

        states_count['rados_objects'] = data['total_objects']
        states_count['rados_used'] = data['total_used']
        states_count['rados_free'] = data['total_avail']
        states_count['rados_total'] = data['total_space']

'''Get pg stat'''
def Info():
    global ceph, rados

        import subprocess 
        p = subprocess.Popen([ceph, 'pg', 'stat', '-f', 'json-pretty'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        try:
            out, err = p.communicate()

        except ValueError:
            print 'Cannot execute command'

        data = json.loads(out)

        # Foreach all pgs state to count how is the values
        # possible values: http://ceph.com/docs/master/rados/operations/pg-states/
        for s in data['num_pg_by_state']:
            states = s['name'].split('+')
                for state in states:
                    if state in states_count:
                        states_count[state] = states_count[state] + s['num']
                    else:
                        states_count.append(state)

        if states_count['clean'] == states_count['active']:
            states_count['pgstat'] = 0
        else:
            states_count['pgstat'] = 1

        states_count['pgtotal'] = data['num_pgs']

        states_count['rdbps'] = 0
        if 'read_bytes_sec' in data:
            states_count['rdbps'] = data['read_bytes_sec'] * 8

        states_count['wrbps'] = 0
        if 'write_bytes_sec' in data:
            states_count['wrbps'] = data['write_bytes_sec'] * 8

        states_count['ops'] = 0
        if 'io_sec' in data:
            states_count['ops'] = data['io_sec'] * 8

'''Main'''
def main():
    #TODO: Best options to call function where will be use
        try:
            opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
        except getopt.error, msg:
            print msg
                print "for help use --help"
                sys.exit(2)

        # process options
        for o, a in opts:
            if o in ("-h", "--help"):
                Usage()
                        sys.exit(0)

        if len(args) == 0:
            Usage()

        for arg in args:
            if arg == "zabbix-conf":
                CreateZabbix()
            elif arg in states_count:
                Info()
                        Health()
                        Monitors()
                        GetOsd()
                        SpaceRados()
                        print "%s" % (states_count[arg])

if __name__ == "__main__":
    main()
