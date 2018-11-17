"""Code for playing music on spotify."""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy.util
from util import log, debug

SEARCH_LIMIT = 20
SPOTIPY_USER_NAME = 'spotipy_user'

# Test uris
# AC/DC - Dirty Deeds Done Dirt Cheap 'spotify:track:2d4e45fmUnguxh6yqC7gNT'
# Led Zeppelin - Immigrant Song 'spotify:track:78lgmZwycJ3nzsdgmPPGNx'

class MusicPlayer(object):
    """Wrapper around spotipy."""

    def __init__(self):
        log('Constructing music player')
        scope = 'streaming user-read-playback-state user-read-currently-playing'
        log('Constructing music player... might need to authenticate')
        token = spotipy.util.prompt_for_user_token(SPOTIPY_USER_NAME, scope)
        self.sp = spotipy.Spotify(auth=token)

    def search(self, artist, title):
        """Searches for a song by artist and title. 
        Returns the first result URI as a string or None if not found"""
        log('Searching for {} - {}'.format(artist, title))
        results = self.sp.search(q='{} {}'.format(artist, title), limit=SEARCH_LIMIT)
        log('Found {} results (limit {})'.format(len(results['tracks']['items']), SEARCH_LIMIT))
        for i, t in enumerate(results['tracks']['items']):
            debug('{} {} {}'.format(i, t['name'], t['uri']))

        if len(results['tracks']['items']) > 0:
            search_result_uri = results['tracks']['items'][0]['uri']
            search_result_name = results['tracks']['items'][0]['name']
        else:
            search_result_uri = None
            search_result_name = None
        log('Returning {} ({})'.format(search_result_name, search_result_uri))
        return search_result_uri, search_result_name

        #print(self.sp.currently_playing())
        #self.sp.start_playback(uris=['spotify:track:2d4e45fmUnguxh6yqC7gNT'])

    def current_song(self):
        """Returns the current playing song. This returns the Spotify object so it's probably way
        more than you need."""
        return self.sp.currently_playing()

    def play_song(self, uri, start_time_minute=0, start_time_second=0, duration=30):
        """Plays a song by its URI. 
        Args:
            uri (string) - Unique Spotify URI for the song (returned as a tuple member from self.search)
            start_time_minutes (number) - How long to skip ahead in the song (minutes)
            start_time_seconds (number) - How long to skip ahead in the song (seconds)
            duration (number) - How long to play the song. If None, plays the whole thing.
        """
        position = (start_time_second * 1000) + (start_time_minute * 60 * 1000)

        log('Playing song {}'.format(uri))
        # Save the currently playing song so we can resume it later


        self.sp.start_playback(uris=[uri])
        self.sp.seek_track(position)

if __name__ == '__main__':
    log('Authenticating account')
    player = MusicPlayer()
    uri, _ = player.search('AC/DC', 'Dirty Deeds Done Dirt Cheap')
    player.play_song(uri, start_time_minute=0, start_time_second=28)

