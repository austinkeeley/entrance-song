"""Entrance song"""

from datetime import datetime
from scapy.all import *

import data
from util import log

def dhcp_monitor_callback(pkt):
    if not pkt.haslayer(DHCP):
        return
    if pkt[DHCP].options[0][1] != 3:
        return

    mac_addr = pkt[Ether].src
    log('DHCP request from {}'.format(mac_addr))
    device = data.get_device_by_mac_addr(mac_addr)
    if not device:
        log('This isn\'t a device I know about... Adding it to the database')
        data.insert_device(mac_addr)



if __name__ == '__main__':
    log('Entrance song')
    sniff(prn=dhcp_monitor_callback, filter='udp and (port 67 or 68)', store=0)
