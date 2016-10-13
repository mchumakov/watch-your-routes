#!/usr/bin/python
# -*- coding: utf-8 -*-

from pyroute2 import IPRoute
from subprocess import *
import time

isp1_if = 'ens33'
isp1_gw_ip = '172.16.0.254'
isp1_link_type = 'ethernet'
isp1_addr = '172.16.0.253'
isp2_if = 'ens37'
isp2_gw_ip = '172.16.1.254'
isp2_link_type = 'pppoe'
isp2_addr = '172.16.1.253'
testip1 = '94.198.134.60'
testip2 = '89.169.1.102'
testip3 = '8.8.8.8'
cmd = 'fping -I isp2_if testip3 testip1' 
health_counter = 0
isp1_failed = False
isp2_failed = False

ipr = IPRoute() #Get IPRoute object to access Netlink data.
#Get installed ip addresses on ISP interfaces to ensure we can bind to them during further tests. 
def check_if_state(f_isp1_if, f_isp2_if):
    isp1_if_index = ipr.link_lookup(ifname = f_isp1_if)
    if len(isp1_if_index) == 0:
        print "Interface %s not found in the system." % f_isp1_if
        isp1_failed = True
    else:
        isp1_if_data = ipr.get_addr(family=2,index=isp1_if_index[0])
   
    isp2_if_index = ipr.link_lookup(ifname = f_isp2_if)
    if len(isp2_if_index) == 0:
        print "Interface %s not found in the system." % f_isp2_if
        isp2_failed = True
    else:
        isp2_if_data = ipr.get_addr(family=2,index=isp2_if_index[0])
   

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

#if_status = check_if_state(isp1_if, isp2_if)
#print if_status
#if if_status[0] == False or if_status[1] == False:
#   exit() 
        
#Function to check which default route installed in routing table.
def check_def_routes():
    if_state = check_if_state(isp1_if, isp2_if)
    routes = ipr.get_routes(dst_len=0, table=254) #Obtain all default routes in routing table main. But we need to check return value to handle situation when there is no any default route installed.
    try:
        routes_isp1 = ipr.get_routes(dst_len=0, table=216) #Obtain route information from table 216 - ISP1
        print len(routes_isp1)
    except pyroute2.netlink.exceptions.NetlinkError:
        print "Netlink exception!!!"
        routes_isp1 = [] 
    if len(routes_isp1) != '0': 
        isp1_cur_rt_gw = routes_isp1[0].get_attr('RTA_GATEWAY') 
    #else jj:
        
    routes_isp2 = ipr.get_routes(dst_len=0, table=217) #obtain route information from table 217 - ISP2
#then we check if there corresponding deafult routes installes in each of the ISP tables
#if there is no default route installes we insert it, if there is incorrect one we change it to correct one
    if len(routes_isp1) == '0' and if_state[0] != True: 
        ipr.route("add", dst="0.0.0.0/0", gateway=isp1_gw_ip, table=216) 
    elif isp1_cur_rt_gw != isp1_gw_ip and if_state[0] != True:
        ipr.route("del", dst="0.0.0.0/0", table=216)
        ipr.route("add", dst="0.0.0.0/0", gateway=isp2_gw_ip, table=216) 

    if len(routes_isp2) == 0 and if_state[1] != True:
        ipr.route("add", dst="0.0.0.0/0", gateway=isp2_gw_ip, table=217)
    elif routes_isp2[0].get_attr('RTA_GATEWAY') != isp2_gw_ip:
        ipr.route("del", dst="0.0.0.0/0", table=217)
        ipr.route("add", dst="0.0.0.0/0", gateway=isp2_gw_ip, table=217) 

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

def check_isp_links(isp_addr, f_testip1, f_testip2, f_testip3, f_isp_gw):
    gw_alive = False
    internet_state = False
    health_counter = 0
    fping = Popen(['fping', '-S', isp_addr, f_isp_gw, f_testip1, f_testip2, f_testip3], stdout=PIPE).communicate()
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
    
#    print "This link has %d hosts alive." % health_counter
    return gw_alive, internet_state

while True:
    if_state = check_if_state(isp1_if, isp2_if)
    print if_state

    def_route = check_def_routes()
#debug    print def_route
    if if_state[0] == False: 
        isp1Link_state = check_isp_links(isp1_addr, testip1, testip2, testip3, isp1_gw_ip)
    else:
        isp1Link_state = [False, False]

    if if_state[1] == False:
        isp2Link_state = check_isp_links(isp2_addr, testip1, testip2, testip3, isp2_gw_ip)
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
