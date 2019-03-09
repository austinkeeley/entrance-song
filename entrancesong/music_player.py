"""Code for playing music on spotify."""

from queue import Queue
from threading import Thread
from time import sleep
from datetime import datetime, timedelta
import logging

import spotipy
import spotipy.util

SEARCH_LIMIT = 20
SPOTIPY_USER_NAME = 'spotipy_user'

# The default volume to set things to, in percent
DEFAULT_VOLUME = 50
# The volume to play MusicThreads at. This should generally be slightly louder
# than whatever else you're used to since we want to make an entrance.
ENTRANCE_VOLUME = 70
FADE_DELTA=5

SCOPE = 'streaming user-read-playback-state user-read-currently-playing'

# Spotify token timeout in minutes. Usually set by Spotify to 1 hour. Setting it a
# little under.
TOKEN_TIMEOUT = 50

class MusicThread(Thread):
    """A thread to start music and sleep. This is a cheap way to implement playing
    a duration of a song since the Spotify API doesn't include that.

    """
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

    def run(self):
        """Runs the thread.
        Plays the song, sleeps and then stops the track.
        """
        logging.info('Starting playback in new thread')
        self.sp.pause_playback()
        self.mp.set_volume(ENTRANCE_VOLUME)
        self.sp.start_playback(uris=[self.uri], position_ms=self.position_ms)
        if not self.duration:
            logging.info('No duration specified. Playing the whole track!')
            return

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
                #self.mp.set_volume(DEFAULT_VOLUME)
            else:
                logging.info('Attempted to stop song {} but it\'s not playing'.format(self.uri))
        finally:
            return




class MusicPlayer(Thread):
    """Wrapper around spotipy with some extra syntax sugar.

    This is in a thread because it uses a blocking queue and we don't want the whole
    application to block.
    """

    def check_token(func):
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

    def __init__(self):
        super().__init__()
        logging.info('Constructing music player... might need to authenticate')
        token, sp_auth = spotipy.util.prompt_for_user_token(SPOTIPY_USER_NAME, SCOPE)
        self.sp = spotipy.Spotify(auth=token)

        self.song_queue = Queue()

        self.original_playback = None
        self.original_volume = None
        self.sp_auth = sp_auth
        self.token = token

        self.token_refresh_datetime = datetime.now()


    @check_token
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

    @check_token
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
        # Save the currently playing song so we can resume it later

        t = MusicThread(self.sp, self, uri, position, duration)
        t.start()
        return t

    def fade_out(self, delta=FADE_DELTA):
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
            sleep(0.5)
            starting_volume = starting_volume - delta
            logging.debug('fade to {} '.format(starting_volume))

    def fade_in(self, volume=DEFAULT_VOLUME, delta=FADE_DELTA):
        """Fades out the music, not in a very smart way"""

        starting_volume = self.get_volume() # device['volume_percent']
        logging.info('Fading in... current volume is {}'.format(starting_volume))

        while starting_volume < volume:
            self.sp.volume(starting_volume)
            sleep(0.5)
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
        if not context:
            return

        uri = context.get('uri', '')
        position_ms = self.original_playback.get('progress_ms', 0)
        original_volume = self.original_playback.get('device', {}).get('volume_percent', DEFAULT_VOLUME)

        logging.info('Restoring playback to %s %s', context.get('type', ''), uri)

        if self.original_playback.get('is_playing', False):
            self.sp.start_playback(context_uri=uri, offset={'uri': item.get('uri', '')}, position_ms=position_ms)
            if fade:
                self.fade_in(volume=original_volume)


    def player_main(self):
        logging.info('Starting music player')
        while True:
            uri, start_minute, start_second, duration = self.song_queue.get(True)
            logging.info('Found a song on the queue!')
            logging.info('Playing %s at %d:%d duration %d', uri, start_minute, start_second, duration)
            current_playback = self.save_current_playback()
            t = self.play_song(uri, start_minute, start_second, duration)
            logging.info('Waiting for song to end...')
            t.join()
            self.restore_playback()
            logging.info('Song over... waiting for the next song on the queue')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s %(levelname)s] %(message)s', datefmt='%Y %b %d %H:%M:%S')
    logging.info('Authenticating account')
    player = MusicPlayer()

    #uri, _ = player.search('Papa Roach', 'Last Resort')
    #player.queue_song(uri, 0, 0, 15)
    #player.player_main()
    #player.play_song(uri, start_time_minute=1, start_time_second=30, duration=20)
    #player.fade_out()
    player.save_current_playback()
    sleep(1)
    player.restore_playback()

    #print(player.get_playlist_offset('spotify:user:12164336727:playlist:2sSwD0ElIwd62KM1UjoDrr', 'spotify:track:5Fwif6oyL2EjXAFTGL909U'))

