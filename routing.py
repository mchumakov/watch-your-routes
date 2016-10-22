#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
from subprocess import Popen, PIPE
from sys import argv
from pyroute2 import IPRoute

CONF_FILE = open(argv[1])
conf_data = []
const = {}

for line in CONF_FILE:
    conf_data.append([str(i) for i in line.strip().split() if i != '='])

for item in conf_data:
    const[item[0]] = item[1]

ISP1_IF = const['ISP1_IF']
ISP1_GW_IP = const['ISP1_GW_IP']
ISP1_LINK_TYPE = const['ISP1_LINK_TYPE']
ISP1_ADDR = const['ISP1_ADDR']
ISP1_NET = const['ISP1_NET']
ISP1_RT_TAB = int(const['ISP1_RT_TAB'])
ISP2_IF = const['ISP2_IF']
ISP2_GW_IP = const['ISP2_GW_IP']
ISP2_LINK_TYPE = const['ISP2_LINK_TYPE']
ISP2_ADDR = const['ISP2_ADDR']
ISP2_RT_TAB = int(const['ISP2_RT_TAB'])
TESTIP1 = const['TESTIP1']
TESTIP2 = const['TESTIP2']
TESTIP3 = const['TESTIP3']

CONF_FILE.close()

#Get IPRoute object to access Netlink data.
ipr = IPRoute()

#Get installed ip addresses on ISP interfaces to ensure we can bind to them during further tests.
def check_if_state(f_isp1_if, f_isp2_if):
    isp1_failed = False
    isp2_failed = False

    isp1_if_index = ipr.link_lookup(ifname=f_isp1_if)
    if len(isp1_if_index) == 0:
        print "Interface %s not found in the system." % f_isp1_if
        isp1_failed = True
    else:
        isp1_if_data = ipr.get_addr(family=2, index=isp1_if_index[0])

    isp2_if_index = ipr.link_lookup(ifname=f_isp2_if)
    if len(isp2_if_index) == 0:
        print "Interface %s not found in the system." % f_isp2_if
        isp2_failed = True
    else:
        isp2_if_data = ipr.get_addr(family=2, index=isp2_if_index[0])


    if len(isp1_if_data) == 0:
        #no ip address found on interface marking isp1 interface as failed
        isp1_failed = True
    else:
        isp1_failed = False

    if len(isp2_if_data) == 0:
       #no ip address found on interface marking isp2 interface as failed
        isp2_failed = True
    else:
        isp2_failed = False

    return isp1_failed, isp2_failed

#Function to check which default route installed in routing table.
def check_def_routes():
    if_state = check_if_state(ISP1_IF, ISP2_IF)
#Obtain all default routes in routing table main.
#But we need to check return value to handle situation when there is no any default route installed.
    routes = ipr.get_routes(dst_len=0, table=254)
    try:
#Obtain route information from table ISP1_RT_TAB - ISP1
        routes_isp1 = ipr.get_routes(dst_len=0, table=ISP1_RT_TAB)
        routes_isp1_net = ipr.get_routes(dst=ISP1_NET, table=ISP1_RT_TAB, family=2)
        print routes_isp1_net
        print len(routes_isp1)
    except Exception as e:
        print "Netlink exception!", type(e), e
        routes_isp1 = []
        routes_isp1_net = []

    if len(routes_isp1) != 0:
        isp1_cur_rt_gw = routes_isp1[0].get_attr('RTA_GATEWAY')
    else:
        isp1_cur_rt_gw = 0
    #else jj:

    try:
#obtain route information from table ISP2_RT_TAB - ISP2
        routes_isp2 = ipr.get_routes(dst_len=0, table=ISP2_RT_TAB)
        print len(routes_isp2)
    except Exception as e:
        print "Netlink exception!", type(e), e
        routes_isp2 = []

    if len(routes_isp2) != 0:
        isp2_cur_rt_gw = routes_isp2[0].get_attr('RTA_GATEWAY')
    else:
        isp2_cur_rt_gw = 0

#then we check if there are corresponding deafult routes installed in each of the ISP tables
#if there are no default routes installed we insert them,
#if there is incorrect one we change it to correct one

    if len(routes_isp1) == 0 and if_state[0] != True:
        ipr.route("add", dst="0.0.0.0/0", gateway=ISP1_GW_IP, table=ISP1_RT_TAB)
    elif isp1_cur_rt_gw != ISP1_GW_IP and if_state[0] != True:
        ipr.route("del", dst="0.0.0.0/0", table=ISP1_RT_TAB)
        ipr.route("add", dst="0.0.0.0/0", gateway=ISP2_GW_IP, table=ISP1_RT_TAB)
 
#    if len(routes_isp1_net) == 0 and if_state[0] != True:
#        try:
#            ipr.route("add", dst=ISP1_NET, table=ISP1_RT_TAB, src=ISP1_ADDR)
#        except Exception as e:
#            print "Netlink exception.", type(e), e
    
    if len(routes_isp2) == 0 and if_state[1] != True:
        ipr.route("add", dst="0.0.0.0/0", gateway=ISP2_GW_IP, table=ISP2_RT_TAB)
    elif isp2_cur_rt_gw != ISP2_GW_IP and if_state[1] != True:
        ipr.route("del", dst="0.0.0.0/0", table=ISP2_RT_TAB)
        ipr.route("add", dst="0.0.0.0/0", gateway=ISP2_GW_IP, table=ISP2_RT_TAB)

    if len(routes) != 0:
        if routes[0].get_attr('RTA_MULTIPATH') != None:
            print "\nThere is multipath default route installed.\n"
            return 0, None
        else:
            print "\nThere is single gateway default route installed."
            current_isp = routes[0].get_attr('RTA_GATEWAY')
            return 1, current_isp
    else:
        print "\nNo default routes found in routing table."
        return 2, None

def check_isp_links(isp_addr, f_testip1, f_testip2, f_testip3, f_isp_gw):
    gw_alive = False
    internet_state = False
    health_counter = 0
    fping = Popen(['fping', '-S', isp_addr, f_isp_gw, f_testip1, f_testip2, f_testip3]
                  , stdout=PIPE).communicate()
    result = [str(i) for i in fping[0].strip().split() if i != 'is']
    if result[1] == 'alive':
        gw_alive = True
    else:
        gw_alive = False
    for i in xrange(2, len(result)):
        if i%2 != 0 and result[i] != 'unreachable':
            health_counter += 1
        else:
            continue
    if health_counter != 0:
        internet_state = True
    else:
        internet_state = False

    return gw_alive, internet_state

#########################
# Main code starts here.#
#########################

while True:
    if_state = check_if_state(ISP1_IF, ISP2_IF)
    print if_state

    def_route = check_def_routes()
#debug    print def_route
    if if_state[0] is False:
        isp1Link_state = check_isp_links(ISP1_ADDR, TESTIP1, TESTIP2, TESTIP3, ISP1_GW_IP)
        print "ISP1: gw available %s, link state %s." % (isp1Link_state[0], isp1Link_state[1])
    else:
        isp1Link_state = (False, False)

    if if_state[1] is False:
        isp2Link_state = check_isp_links(ISP2_ADDR, TESTIP1, TESTIP2, TESTIP3, ISP2_GW_IP)
        print "ISP2: gw available %s, link state %s." % (isp2Link_state[0], isp2Link_state[1])
    else:
        isp2Link_state = (False, False)

    if isp1Link_state[0] and isp2Link_state[0] and def_route[0] == 2:
        print "Trying to install multipath default route."
        ipr.route("add", dst="0.0.0.0/0", multipath=[{"gateway": ISP1_GW_IP, "hops": 0},
                                                     {"gateway": ISP2_GW_IP, "hops": 0}])
        continue

    if isp1Link_state[1] and isp2Link_state[1]:
        print "Both links looks good."
        if def_route[0] == 1:
            ipr.route("del", dst="0.0.0.0/0")
            print "Installing multipath default."
            ipr.route("add", dst="0.0.0.0/0", multipath=[{"gateway": ISP1_GW_IP, "hops": 0},
                                                         {"gateway": ISP2_GW_IP, "hops": 0}])
        elif def_route[0] == 2:
            ipr.route("add", dst="0.0.0.0/0", multipath=[{"gateway": ISP1_GW_IP, "hops": 0},
                                                         {"gateway": ISP2_GW_IP, "hops": 0}])

    elif isp1Link_state[1] and not isp2Link_state[1]:
        print "ISP2 link is dead."
        if def_route[0] == 0 or def_route[1] == ISP2_GW_IP:
            ipr.route("del", dst="0.0.0.0/0")
        if def_route[1] != ISP1_GW_IP:
            print "Adding default via ISP1 link."
            ipr.route("add", dst="0.0.0.0/0", gateway=ISP1_GW_IP)

    elif not isp1Link_state[1] and isp2Link_state[1]:
        print "ISP1 link is dead."
        if def_route[0] == 0 or def_route[1] == ISP1_GW_IP:
            ipr.route("del", dst="0.0.0.0/0")
        if def_route[1] != ISP2_GW_IP:
            print "Adding default via ISP2 link."
            ipr.route("add", dst="0.0.0.0/0", gateway=ISP2_GW_IP)

    else:
        print "No one ISP links alive."
        if def_route[0] != 2:
            print "Removing default route."
            ipr.route("del", dst="0.0.0.0/0")
    time.sleep(10)
