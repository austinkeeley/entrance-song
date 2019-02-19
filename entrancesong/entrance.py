"""Entrance song"""

from datetime import datetime
import logging

from scapy.all import Ether, DHCP, sniff

from music_player import MusicPlayer
import data


class EntranceController(object):
    """Class that starts listening for DHCP connections and playing music"""
    def __init__(self):
        self.player = MusicPlayer()
        self.last_entrance = (None, None)

    def start(self):
        """Starts sniffing"""
        logging.info('Starting sniffing for DHCP traffic')
        sniff(prn=self.dhcp_monitor_callback, filter='udp and (port 67 or 68)', store=0)


    def dhcp_monitor_callback(self, pkt):
        """Callback for DHCP requests"""
        if not pkt.haslayer(DHCP):
            return
        if pkt[DHCP].options[0][1] != 3:
            return

        mac_addr = pkt[Ether].src
        logging.info('DHCP request from %s', mac_addr)
        device = data.get_device_by_mac_addr(mac_addr)
        if not device:
            logging.info('This isn\'t a device I know about... Adding it to the database')
            data.insert_device(mac_addr)
            return

        if self.last_entrance[0] is not None and self.last_entrance[0].name == device.owner.name:
            logging.info('%s was the last person to enter. Has enough time passed to go again?', device.owner.name)
            now = datetime.now()
            if self.last_entrance[1] is not None and (now - self.last_entrance[1]).seconds < 30:
                logging.info('Nope. Hasn\'t been long enough')
                return
        else:

            now = datetime.now()
            self.last_entrance = (device.owner, now)
            logging.info(self.last_entrance)



        if device.owner.song:
            song = device.owner.song
            logging.info('%s is about to enter! playing %s by %s', device.owner.name, song.title, song.artist)
        else:
            logging.info('Device owner %s doesn\'t have a song. Doing nothing...', device.owner.name)
            return

        uri, _ = self.player.search(song.artist, song.title)
        if uri:
            self.player.play_song(uri, duration=song.duration)
        else:
            logging.info('No search results found...')

    def playback(self):
        pass
        # Save the old track, volume, postion, etc.
        # Fade out the old track
        # Begin playing the new track
        # wait for the thread to complete

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s %(levelname)s] %(message)s',
                        datefmt='%Y %b %d %H:%M:%S')
    logging.info('Starting entrance song application')

    entrance = EntranceController()
    entrance.start()
