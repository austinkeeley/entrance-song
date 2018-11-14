"""Entrance song"""

from scapy.all import *

def dhcp_monitor_callback(pkt):
    if not pkt.haslayer(DHCP):
        return
    if pkt[DHCP].options[0][1] != 3:
        return

    mac_addr = pkt[Ether].src

    print('DHCP request from {}'.format(mac_addr))



if __name__ == '__main__':
    print('Entrance song')
    sniff(prn=dhcp_monitor_callback, filter='udp and (port 67 or 68)', store=0)
