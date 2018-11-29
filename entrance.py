"""Entrance song"""

from scapy.all import Ether, DHCP, sniff

from music_player import MusicPlayer
import data
from util import log


class EntranceController(object):
    """Class that starts listening for DHCP connections and playing music"""
    def __init__(self):
        self.player = MusicPlayer()

    def start(self):
        """Starts sniffing"""
        sniff(prn=self.dhcp_monitor_callback, filter='udp and (port 67 or 68)', store=0)


    def dhcp_monitor_callback(self, pkt):
        """Callback for DHCP requests"""
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
            return

        if device.owner.song:
            song = device.owner.song
            log('{} is about to enter! playing {} by {}'.format(device.owner.name, song.title, song.artist))
        else:
            log('Device owner {} doesn\'t have a song. Doing nothing...'.format(device.owner.name))
            return

        uri, _ = self.player.search(song.artist, song.title)
        if uri:
            self.player.play_song(uri, duration=song.duration)
        else:
            log('No search results found...')



if __name__ == '__main__':
    entrance = EntranceController()
    entrance.start()
