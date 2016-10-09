#!/usr/bin/python
# -*- coding: utf-8 -*-

from pyroute2 import IPRoute
from subprocess import *
import time

isp1_if = 'ens33'
isp1_gw_ip = '172.16.0.254'
isp1_link_type = 'ethernet'
isp2_if = 'ens37'
isp2_gw_ip = '172.16.1.254'
isp2_link_type = 'pppoe'
testip1 = '94.198.134.60'
testip2 = '89.169.1.102'
testip3 = '8.8.8.8'
cmd = 'fping -I isp2_if testip3 testip1' 
health_counter = 0

ipr = IPRoute() #Get IPRoute object.

#Function to check which default route installed in routing table.
def check_def_routes():
    routes = ipr.get_routes(dst_len=0) #Obtain all default routes in routing table main. But we need to check return value to handle situation when there is no any default route installed.
#debug    print routes
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

def check_isp_links(isp_if, f_testip1, f_testip2, f_testip3, f_isp_gw):
    gw_alive = False
    internet_state = False
    health_counter = 0
    fping = Popen(['fping', '-I', isp_if, f_isp_gw, f_testip1, f_testip2, f_testip3], stdout=PIPE).communicate()
    result = [str(i) for i in fping[0].strip().split() if i != 'is']
    if result[1] == 'alive':
       gw_alive = True 
    else:
       gw_alive = False 
    for i in xrange(2,len(result)):
        if i%2 != 0 and result[i] != 'unreachable':
            health_counter += 1
        else:
            continue 
    if health_counter != 0:
        internet_state = True
    else:
        internet_state = False
    print health_counter
    return gw_alive, internet_state

while True:
    def_route = check_def_routes()
    
    isp1Link_state = check_isp_links(isp1_if, testip1, testip2, testip3, isp1_gw_ip)
    isp2Link_state = check_isp_links(isp2_if, testip1, testip2, testip3, isp2_gw_ip)
    print isp1Link_state
    print isp2Link_state

    if isp1Link_state[0] and isp2Link_state[0] and def_route[0] == 2:
        print "Trying to install multipath default route."
        ipr.route("add", dst="0.0.0.0/0", multipath=[{"gateway": isp1_gw_ip, "hops": 0},{"gateway": isp2_gw_ip, "hops": 0}]),
        continue
    
    if isp1Link_state[1] and isp2Link_state[1]: 
        print "Both links looks good."
        if def_route[0] == 1:
            ipr.route("del", dst="0.0.0.0/0")
            print "Installing multipath default."
            ipr.route("add", dst="0.0.0.0/0", multipath=[{"gateway": isp1_gw_ip, "hops": 0},{"gateway": isp2_gw_ip, "hops": 0}]) 
        elif def_route[0] == 2:
            ipr.route("add", dst="0.0.0.0/0", multipath=[{"gateway": isp1_gw_ip, "hops": 0},{"gateway": isp2_gw_ip, "hops": 0}])

    elif isp1Link_state[1] and not isp2Link_state[1]:
        print "ISP2 link is dead."
        if def_route[0] == 0 or def_route[1] == isp2_gw_ip:
            ipr.route("del", dst="0.0.0.0/0")
        if def_route[1] != isp1_gw_ip:
            print "Adding default via ISP1 link."
            ipr.route("add", dst="0.0.0.0/0", gateway=isp1_gw_ip)

    elif not isp1Link_state[1] and isp2Link_state[1]:
        print "ISP1 link is dead."
        if def_route[0] == 0 or def_route[1] == isp1_gw_ip: 
            ipr.route("del", dst="0.0.0.0/0")
        if def_route[1] != isp2_gw_ip:
            print "Adding default via ISP2 link."
            ipr.route("add", dst="0.0.0.0/0", gateway=isp2_gw_ip)

    else:
        print "No one ISP links alive."
        if def_route[0] != 2:
            print "Removing default route."
            ipr.route("del", dst="0.0.0.0/0") 
    time.sleep(10)

'''
links = ipr.get_links()
addr = ipr.get_addr()

def get_int_state(isp_if):
        for i in xrange(len(links)):
                if links[i].get_attr('IFLA_IFNAME') == isp_if:
                        return i, str(links[i].get_attrs('IFLA_OPERSTATE')).strip('\'[]\''), str(addr[i].get_attrs('IFA_ADDRESS')).strip('\'[]\'') #, links[i].get_attrs('IFLA_

if ipr.link_lookup(ifname = isp1_if):
	isp1_ifState = get_int_state(isp1_if)
	print "The index of %s interface in list is %d, oper state is %s and ip-address is %s" % (isp1_if,isp1_ifState[0],isp1_ifState[1],isp1_ifState[2])
else:
	print "Interface %s not found in the system. Please check your configuration." % isp1_if

if ipr.link_lookup(ifname = isp2_if):
	isp2_ifState = get_int_state(isp2_if)
	print "The index of %s interface in list is %d, oper state is %s and ip-address is %s\n" % (isp2_if,isp2_ifState[0],isp2_ifState[1],isp2_ifState[2])
else:
        print "Interface %s not found in the system. Please check your configuration." % isp2_if

if isp1_ifState[1] == 'UP' and isp2_ifState[1] == 'UP' and isp2_ifState[2] == isp2_gw_ip:
	print "Both interfaces are up and working fine. Insert multipath default route in routing table main."
'''








