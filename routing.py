#!/usr/bin/python
# -*- coding: utf-8 -*-

from pyroute2 import IPRoute
#from subprocess import call
from subprocess import *
from os import devnull

isp1_if = 'ens33'
isp2_if = 'ens37'
isp1_gw_ip = '172.16.0.254'
isp2_gw_ip = '172.16.1.254'
testip1 = '94.198.134.60'
testip2 = '89.169.1.102'
testip3 = '8.8.8.8'
cmd = 'fping -I isp2_if testip3 testip1' 
health_counter = 0

ipr = IPRoute() #Get IPRoute object.

#Function to check if there is multipath default route installed in routing table.
def check_def_routes():
    routes = ipr.get_routes(dst_len=0) #Obtain all default routes in routing table main. But we need to check return value to handle situation when there is no any default route installed.
#debug    print routes
    if len(routes) != 0:
        if routes[0].get_attr('RTA_MULTIPATH') != None:
            print "There is multipath default route installed. Nothing to do.\n"
            return 0
        else:
            print "There is single gateway default route installed. Checking for ISP links."
            return 1
    else:
        print "No default routes found in routing table. Checking for ISP links"
        return 2

def check_isp_links(check_gw, isp_if, f_testip1, f_testip2, f_testip3, f_isp_gw):
    health_counter = 0
    if check_gw == 1:
        fping = Popen(['fping', f_isp_gw], stdout=PIPE).communicate()
        result = [str(i) for i in fping[0].strip().split() if i != 'is']
        print result
        return 'ok'
    else:
        fping = Popen(['fping', '-I', isp1_if, f_testip3, f_testip2, f_testip1], stdout=PIPE).communicate()
        result = [str(i) for i in fping[0].strip().split() if i != 'is']
        print result
        for i in xrange(len(result)):
            if i%2 != 0 and result[i] != 'unreachable':
                print result[i]
                health_counter += 1
        return health_counter

def_route = check_def_routes()
#In case we have single gateway default route installed we need to check if another ISP link is alive and if yes install multipath default.
if def_route == 1:
    print check_isp_links(isp1_if, testip1, testip2, testip3)
#In case we have no any defaults installed we need to check ISP links and istall multipath if both links are fine or single gateway default if one of the links alive.
elif def_route == 2:
    if check_isp_links(1, isp1_if, testip1, testip2, testip3, isp1_gw_ip) == 'ok' and check_isp_links(1, isp2_if, testip1, testip2, testip3, isp2_gw_ip) == 'ok':
        ipr.route("add", dst="0.0.0.0/0", multipath=[{"gateway": isp1_gw_ip, "hops": 0},{"gateway": isp2_gw_ip, "hops": 0}]), 
        print "Both links looks good. Insert multipath default route in table main."
        #ipr.route("add", dst="0.0.0.0/0", gateway=isp1_gw_ip)
        #Need to add code for route insertion 
#    else:
        #Insert routine to handle situation when only one ISP link alive


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









