"""Code for playing music on spotify."""

from queue import Queue
from threading import Thread
from time import sleep
import logging

import spotipy
import spotipy.util

SEARCH_LIMIT = 20
SPOTIPY_USER_NAME = 'spotipy_user'

DEFAULT_VOLUME = 50

# Test uris
# AC/DC - Dirty Deeds Done Dirt Cheap 'spotify:track:2d4e45fmUnguxh6yqC7gNT'
# Led Zeppelin - Immigrant Song 'spotify:track:78lgmZwycJ3nzsdgmPPGNx'

class MusicThread(Thread):
    """A thread to start music and sleep until the duration so we don't block"""
    def __init__(self, sp_context, mp_context, uri, position_ms, duration):
        """Constructor
        Args
            sp_context - The spotify context
            mp_context - music player context
            uri - The URI to play
            position_ms - The position in ms to start from
            duration - The duration to play
        """
        super().__init__()

        self.sp = sp_context
        self.mp = mp_context
        self.uri = uri
        self.position_ms = position_ms
        self.duration = duration

    def save_current_playback(self):
        # Is there already music playing? If so fade it out
        playback = self.sp.current_playback()
        original_volume = self.mp.get_volume()

        if playback.get('is_playing', False):
            logging.info('Fading out old music')
            self.mp.fade_out(delta=10)

        # Set the volume to the previous level so we're ready to play
        self.sp.pause_playback()
        self.mp.set_volume(original_volume)


    def restore_previous_playback(self):
        pass

    def run(self):
        self.save_current_playback()

        logging.info('Starting playback in new thread')
        self.sp.start_playback(uris=[self.uri], position_ms=self.position_ms)
        self.mp.set_volume(DEFAULT_VOLUME)
        if not self.duration:
            logging.info('No duration specified. Playing the whole track!')
            return

        sleep(self.duration)
        logging.info('Stopping playback')
        self.sp.in_entrance_song = False

        # Get the currently playing tack to be sure we're stopping this track and not
        # someone else's.
        current_track = self.sp.currently_playing()
        try:
            uri = current_track['item']['uri']
            if uri == self.uri:
                self.mp.fade_out(delta=10)
                self.sp.pause_playback()
                self.mp.set_volume(DEFAULT_VOLUME)
            else:
                logging.info('Attempted to stop song {} but it\'s not playing'.format(self.uri))
        finally:
            return




class MusicPlayer(Thread):
    """Wrapper around spotipy.
    This is in a thread because it uses a blocking queue and we don't want the whole
    application to block.
    """

    def __init__(self):
        super().__init__()
        logging.info('Constructing music player... might need to authenticate')
        scope = 'streaming user-read-playback-state user-read-currently-playing'
        token = spotipy.util.prompt_for_user_token(SPOTIPY_USER_NAME, scope)
        self.sp = spotipy.Spotify(auth=token)

        self.in_entrance_song = False

        self.song_queue = Queue()


    def search(self, artist, title):
        """Searches for a song by artist and title.

        Args:
            artist - The song artist
            title - The song title

        Returns a tuple of the (uri, title) or None if not found
        """
        logging.info('Searching for {} - {}'.format(artist, title))
        results = self.sp.search(q='{} {}'.format(artist, title), limit=SEARCH_LIMIT)
        logging.info('Found {} results (limit {})'.format(len(results['tracks']['items']), SEARCH_LIMIT))
        for i, t in enumerate(results['tracks']['items']):
            logging.debug('{} {} {}'.format(i, t['name'], t['uri']))

        if len(results['tracks']['items']) > 0:
            search_result_uri = results['tracks']['items'][0]['uri']
            search_result_name = results['tracks']['items'][0]['name']
        else:
            search_result_uri = None
            search_result_name = None
        logging.info('Returning {} ({})'.format(search_result_name, search_result_uri))
        return search_result_uri, search_result_name

        #print(self.sp.currently_playing())
        #self.sp.start_playback(uris=['spotify:track:2d4e45fmUnguxh6yqC7gNT'])

    def currently_playing(self):
        """Returns the current playing song.

        Returns a Spotify object (so it's probably way more than you need)"""
        return self.sp.currently_playing()

    def get_volume(self):
        """Gets the current volume
        """
        playback = self.sp.current_playback()
        if not playback:
            return 0

        device = playback.get('device', None)
        if not device:
            logging.error('Could not get the current device')
            return
        volume = device['volume_percent']
        return volume

    def set_volume(self, volume):
        self.sp.volume(volume)

    def play_song(self, uri, start_time_minute=0, start_time_second=0, duration=30):
        """Plays a song by its URI.
        Args:
            uri (string) - Unique Spotify URI for the song (returned as a tuple member from self.search)
            start_time_minutes (number) - How long to skip ahead in the song (minutes)
            start_time_seconds (number) - How long to skip ahead in the song (seconds)
            duration (number) - How long to play the song. If None, plays the whole thing.
        Returns the MusicThread created by this method
        """
        position = (start_time_second * 1000) + (start_time_minute * 60 * 1000)

        logging.info('Playing song {}'.format(uri))
        self.in_entrance_song = True
        # Save the currently playing song so we can resume it later

        t = MusicThread(self.sp, self, uri, position, duration)
        t.start()
        return t

    def fade_out(self, delta=2):
        """Fades out the music, not in a very smart way"""
        playback = self.sp.current_playback()

        if not playback:
            # Likely nothing is playing
            return

        device = playback['device']
        if not device:
            logging.error('Could not get the current device')

        starting_volume = self.get_volume() # device['volume_percent']
        logging.info('Fading out... current volume is {}'.format(starting_volume))

        while starting_volume > 0:
            self.sp.volume(starting_volume)
            sleep(1)
            starting_volume = starting_volume - delta
            logging.debug('fade to {} '.format(starting_volume))

    def fade_in(self, volume=DEFAULT_VOLUME, delta=2):
        """Fades out the music, not in a very smart way"""

        starting_volume = self.get_volume() # device['volume_percent']
        logging.info('Fading in... current volume is {}'.format(starting_volume))

        while starting_volume < volume:
            self.sp.volume(starting_volume)
            sleep(1)
            starting_volume = starting_volume + delta
            logging.debug('fade to {} '.format(starting_volume))


    def queue_song(self, uri, start_minute=0, start_second=0, duration=30):
        """
        Queues a song up
        """
        logging.info('Queueing song %s', uri)
        self.song_queue.put((uri, start_minute, start_second, duration))

    def run(self):
        self.player_main()

    def player_main(self):
        logging.info('Starting music player')
        while True:
            uri, start_minute, start_second, duration = self.song_queue.get(True)
            logging.info('Found a song on the queue!')
            logging.info('Playing %s at %d:%d duration %d', uri, start_minute, start_second, duration)
            t = self.play_song(uri, start_minute, start_second, duration)
            logging.info('Waiting for song to end...')
            t.join()
            logging.info('Song over... waiting for the next song on the queue')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s %(levelname)s] %(message)s', datefmt='%Y %b %d %H:%M:%S')
    logging.info('Authenticating account')
    player = MusicPlayer()
    uri, _ = player.search('AC/DC', 'Dirty Deeds Done Dirt Cheap')
    player.queue_song(uri, 1, 30, 20)

    player.player_main()
    #player.play_song(uri, start_time_minute=1, start_time_second=30, duration=20)
    #player.fade_out()

