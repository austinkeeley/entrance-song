"""Code for playing music on spotify."""

from queue import Queue
from threading import Thread
from time import sleep
from datetime import datetime, timedelta
import logging

import spotipy
import spotipy.util
from spotipy.client import SpotifyException

SEARCH_LIMIT = 20
SPOTIPY_USER_NAME = 'spotipy_user'

# The default volume to set things to, in percent
DEFAULT_VOLUME = 50
FADE_DELTA=5

SCOPE = 'streaming user-read-playback-state user-read-currently-playing'

class MusicThread(Thread):
    """A thread to start music and sleep. This is a cheap way to implement playing
    a duration of a song since the Spotify API doesn't include that.
    """
    def __init__(self, sp_context, mp_context, uri, position_ms, duration=45, device_id=None):
        """Constructor
        Args
            sp_context - The spotify context
            mp_context - music player context
            uri - The URI to play
            position_ms - The position in ms to start from
            duration - The duration to play, in seconds
            device_id - The device to play on, or None to play on the default device
        """
        super().__init__()

        self.sp = sp_context
        self.mp = mp_context
        self.uri = uri
        self.position_ms = position_ms
        self.duration = duration
        self.device_id = device_id

    def run(self):
        """Runs the thread.
        Starts playback on the track, sleeps, and then fades out the track.
        """
        logging.info('Starting playback in new thread')
        try:
            self.sp.pause_playback()
        except SpotifyException as e:
            # This often happens if there is no current active device. We'll assume there's
            # device_id being used. The next try/catch block will handle it if not.
            pass
        try:
            self.sp.start_playback(device_id=self.device_id, uris=[self.uri], position_ms=self.position_ms)
        except SpotifyException as e:
            logging.error(e)
            return
        self.mp.set_volume(self.mp.default_volume)

        logging.info('Putting the thread to sleep for %s seconds', self.duration)
        sleep(self.duration)
        logging.info('Stopping playback')

        # Get the currently playing tack to be sure we're stopping this track and not
        # someone else's.
        current_track = self.sp.currently_playing()
        try:
            uri = current_track['item']['uri']
            if uri == self.uri:
                self.mp.fade_out()
                self.sp.pause_playback()
            else:
                logging.info('Attempted to stop song %s but it\'s not playing', self.uri)
        finally:
            return


class MusicPlayerException(Exception):
    """Thrown when things playing music go bad"""
    def __init__(self, msg):
        self.msg = msg


class MusicPlayer(Thread):
    """Wrapper around spotipy with some extra syntax sugar.

    This is in a thread because it uses a blocking queue and we don't want the whole
    application to block.
    """

    def check_token(func):
        """Decorator that forces the function to verify the token is still valid.
        By default, Spotify tokens last one hour, but can be refreshed.
        """
        def foo(*args, **kwargs):
            logging.debug('Checking if token is still good')

            myself = args[0]
            auth = myself.sp_auth

            token_info = auth.get_cached_token()
            if token_info['access_token'] != myself.token:
                new_token = token_info['access_token']
                logging.debug('Re-building sp')
                myself.sp = spotipy.Spotify(auth=new_token)
                myself.token = new_token

            return func(*args, **kwargs)
        return foo

    def __init__(self, default_volume=70, device_id=None):
        super().__init__()
        logging.info('Constructing music player... might need to authenticate')
        token, sp_auth = spotipy.util.prompt_for_user_token(SPOTIPY_USER_NAME, SCOPE)
        self.sp = spotipy.Spotify(auth=token)

        self.song_queue = Queue()

        self.original_playback = None
        self.original_volume = None
        self.sp_auth = sp_auth
        self.token = token
        self.default_volume = default_volume

        # If a device ID was provided, make sure it exists before we attempt to use it
        if device_id:
            logging.info('Making sure device %s actually exists', device_id)
            if not self._check_device(device_id):
                raise MusicPlayerException('Could not find device ID %s' % device_id)
        self.device_id = device_id

        self.token_refresh_datetime = datetime.now()

    def _check_device(self, device_id):
        """Checks if a device exists"""
        devices = self.sp.devices().get('devices', [])
        for device in devices:
            if device.get('id', '') == device_id:
                return True
        return False

    @check_token
    def search(self, artist, title):
        """Searches for a song by artist and title and gets the top result.

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

    def currently_playing(self):
        """Returns the current playing song.

        Returns a Spotify object (so it's probably way more than you need)"""
        return self.sp.currently_playing()

    def get_volume(self):
        """Gets the current volume"""
        playback = self.sp.current_playback()
        if not playback:
            return 0

        device = playback.get('device', None)
        if not device:
            logging.error('Could not get the current device')
            return
        volume = device['volume_percent']
        return volume

    def set_volume(self, volume, device_id=None):
        """Sets the volume"""
        self.sp.volume(volume, device_id=device_id)

    @check_token
    def _play_song(self, uri, start_time_minute=0, start_time_second=0, duration=30):
        """Plays a song by its URI, while starting it in its own thread.

        Args:
            uri (string) - Unique Spotify URI for the song (returned as a tuple member from self.search)
            start_time_minutes (number) - How long to skip ahead in the song (minutes)
            start_time_seconds (number) - How long to skip ahead in the song (seconds)
            duration (number) - How long to play the song. If None, plays the whole thing.

        Returns the MusicThread created by this method
        """
        position = (start_time_second * 1000) + (start_time_minute * 60 * 1000)

        logging.info('Playing song {}'.format(uri))
        # Save the currently playing song so we can resume it later

        t = MusicThread(self.sp, self, uri, position, duration, device_id=self.device_id)
        t.start()
        return t

    def fade_out(self, delta=FADE_DELTA):
        """Fades out the music on the current device, not in a very smart way"""
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
            sleep(0.5)
            starting_volume = starting_volume - delta
            logging.debug('fade to {} '.format(starting_volume))

    def fade_in(self, volume=DEFAULT_VOLUME, delta=FADE_DELTA):
        """Fades in the music on the current device, not in a very smart way"""

        starting_volume = self.get_volume() # device['volume_percent']
        logging.info('Fading in... current volume is {}'.format(starting_volume))

        while starting_volume < volume:
            self.sp.volume(starting_volume)
            sleep(0.5)
            starting_volume = starting_volume + delta
            logging.debug('fade to {} '.format(starting_volume))


    def queue_song(self, uri, start_minute=0, start_second=0, duration=30):
        """Queues a song"""
        logging.info('Queueing song %s', uri)
        self.song_queue.put((uri, start_minute, start_second, duration))

    def run(self):
        self.player_main()


    def save_current_playback(self, fade=True):
        """Stops the current playback and saves it

        Args:
            fade - If true, this fades the song out before saving it
        """
        # Is there already music playing? If so fade it out
        playback = self.sp.current_playback()

        # This means nothing is playing
        if not playback:
            return

        original_volume = self.get_volume()

        if playback.get('is_playing', False):
            logging.info('Fading out old music')
            if fade:
                self.fade_out()

        # Set the volume to the previous level so we're ready to play
        self.sp.pause_playback()
        self.set_volume(original_volume)

        # sleep for just a second to be sure things caught up
        sleep(1)

        logging.info('Saving previous playback to bring back later')
        self.original_playback = playback

    def restore_playback(self, fade=True):
        """Restores a saved playback

        Args:
            fade - If true, this fades the song in
        """
        if not self.original_playback:
            return
        context = self.original_playback.get('context', {})
        item = self.original_playback.get('item', {})
        device_id = self.original_playback.get('device', {}).get('id', None)
        if not context:
            return

        uri = context.get('uri', '')
        position_ms = self.original_playback.get('progress_ms', 0)
        original_volume = self.original_playback.get('device', {}).get('volume_percent', DEFAULT_VOLUME)

        logging.info('Restoring playback to %s %s', context.get('type', ''), uri)

        if self.original_playback.get('is_playing', False):
            self.sp.transfer_playback(device_id=device_id, force_play=False)
            sleep(1)
            self.set_volume(0, device_id=device_id)

            # Spotify has a a weird underdocumented thing where it can't resume playback of a
            # COLLECTION_ALBUM. I have no clue what that is, but it seems to be if you are playing
            # something from your saved collections.
            try:
                self.sp.start_playback(context_uri=uri, offset={'uri': item.get('uri', '')}, position_ms=position_ms)
            except spotipy.client.SpotifyException as e:
                logging.warn('Could not start playback. Maybe this is a COLLECTION_ALBUM?')
                self.sp.start_playback(context_uri=uri, position_ms=position_ms)
                #self.sp.pause_playback()
                i = 0
                track_number = self.original_playback.get('item', {}).get('track_number', 0)
                logging.warn('Skipping to track number %d', track_number)
                while (i + 1) < track_number:
                    i = i + 1
                    self.sp.next_track()
                self.sp.seek_track(position_ms)
                logging.warn('Done! Maybe try playing the full album next time.')

            if fade:
                self.fade_in(volume=original_volume)


    def player_main(self):
        logging.info('Starting music player')
        while True:
            uri, start_minute, start_second, duration = self.song_queue.get(True)
            logging.info('Found a song on the queue!')
            logging.info('Playing %s at %d:%d duration %d', uri, start_minute, start_second, duration)
            current_playback = self.save_current_playback()
            t = self._play_song(uri, start_minute, start_second, duration)
            logging.info('Waiting for song to end...')
            t.join()
            self.restore_playback()
            logging.info('Song over... waiting for the next song on the queue')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s %(levelname)s] %(message)s', datefmt='%Y %b %d %H:%M:%S')
    player = MusicPlayer()
    player.save_current_playback()
    sleep(1)
    player.restore_playback()


