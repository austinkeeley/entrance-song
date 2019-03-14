"""Entrance song entry controller.

Sniffs for DHCP requests and queues up the music.

"""
import argparse
from datetime import datetime
import logging
import random

from scapy.all import Ether, DHCP, sniff

from .music_player import MusicPlayer, MusicPlayerException
from spotipy import SpotifyException
from . import data


class EntranceController(object):
    """Class that starts listening for DHCP connections and playing music"""
    def __init__(self, default_volume=70, device_id=None, virtual_mac=False):
        self.virtual_mac = virtual_mac
        self.player = MusicPlayer(default_volume=default_volume, device_id=device_id)
        self.last_entrance = (None, None)

    def start(self):
        """Starts sniffing"""
        logging.info('Starting sniffing for DHCP traffic')
        self.player.start()
        sniff(prn=self.dhcp_monitor_callback, filter='udp and (port 67 or 68)', store=0)

    def get_dhcp_option_value(self, options, key):
        for option in options:
            if key == option[0]:
                return option[1]
        return None

    def dhcp_monitor_callback(self, pkt):
        """Callback for DHCP requests"""
        if not pkt.haslayer(DHCP):
            return
        if pkt[DHCP].options[0][1] != 3:
            return

        mac_addr = pkt[Ether].src
        hostname = self.get_dhcp_option_value(pkt[DHCP].options, 'hostname').decode('utf-8')
        ip = self.get_dhcp_option_value(pkt[DHCP].options, 'requested_addr')

        logging.info('DHCP request from %s for %s', mac_addr, ip)
        device = data.get_device_by_mac_addr(mac_addr, self.virtual_mac)
        if not device:
            logging.info('This isn\'t a device I know about... Adding it to the database')
            data.insert_device(mac_addr, hostname)
            return

        if self.last_entrance[0] is not None and self.last_entrance[0].name == device.owner.name:
            logging.info('%s was the last person to enter. Has enough time passed to go again?', device.owner.name)
            now = datetime.now()
            elapsed = (now - self.last_entrance[1]).seconds
            logging.info('Elapsed time since %s entered: %d seconds', device.owner.name, elapsed)
            if self.last_entrance[1] is not None and (now - self.last_entrance[1]).seconds < 30:
                logging.info('Nope. Hasn\'t been long enough')
                return
            self.last_entrance = (device.owner, now)
        else:
            now = datetime.now()
            self.last_entrance = (device.owner, now)

        if device.owner.song:
            song = random.choice(device.owner.song)
            logging.info('################################################################################')
            logging.info('%s is about to enter (%s)! playing %s by %s', device.owner.name, device.friendly_name, song.title, song.artist)
            logging.info('################################################################################')
        else:
            logging.info('Device owner %s doesn\'t have a song. Doing nothing...', device.owner.name)
            return

        uri, _ = self.player.search(song.artist, song.title)
        if uri:
            self.player.queue_song(uri, duration=song.duration, start_minute=song.start_minutes, start_second=song.start_seconds)
        else:
            logging.info('No search results found...')

    def playback(self):
        pass
        # Save the old track, volume, postion, etc.
        # Fade out the old track
        # Begin playing the new track
        # wait for the thread to complete

def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s %(levelname)s] %(message)s',
                        datefmt='%Y %b %d %H:%M:%S')
    logging.info('Starting entrance song application')

    parser = argparse.ArgumentParser(description='Listens for DHCP traffic and plays music')
    parser.add_argument('--volume', dest='default_volume', action='store', default=70, type=int)
    parser.add_argument('--device', dest='device_id', action='store', default=None, type=str)
    parser.add_argument('--virtualmac', dest='virtual_mac', action='store_true')
    args = parser.parse_args()

    if args.default_volume > 100 or args.default_volume < 0:
        print('Volume must be between 0 and 100')
        exit(1)

    if args.device_id:
        logging.info('Using device %s', args.device_id)
    else:
        logging.info('Using the default device')

    if args.virtual_mac:
        logging.info('Using virtual MAC address filtering')

    try:
        entrance = EntranceController(default_volume=args.default_volume, device_id=args.device_id, virtual_mac=args.virtual_mac)
        entrance.start()
    except MusicPlayerException as e:
        logging.error(e.msg)
        exit(1)
    except SpotifyException as e:
        logging.error(e.msg)
        exit(1)

if __name__ == '__main__':
    main()
