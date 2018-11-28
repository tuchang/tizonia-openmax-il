# Copyright (C) 2011-2018 Aratelia Limited - Juan A. Rubio
#
# This file is part of Tizonia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""@package tizspotifyproxy
Simple Spotify API proxy/wrapper.

Access Spotify servers to retrieve audio track URIs and create a playback queue.

"""

from __future__ import print_function, unicode_literals

import sys
import os
import logging
import random
import unicodedata
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from fuzzywuzzy import process
from fuzzywuzzy import fuzz

# For use during debugging
from pprint import pprint

FORMAT = '[%(asctime)s] [%(levelname)5s] [%(thread)d] ' \
         '[%(module)s:%(funcName)s:%(lineno)d] - %(message)s'

logging.captureWarnings(True)
logging.getLogger().setLevel(logging.DEBUG)

if os.environ.get('TIZONIA_SPOTIFYPROXY_DEBUG'):
    logging.basicConfig(format=FORMAT)
    from traceback import print_exception
else:
    logging.getLogger().addHandler(logging.NullHandler())

class _Colors:
    """A trivial class that defines various ANSI color codes.

    """
    BOLD = '\033[1m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

# This code is here for debugging purposes
def pretty_print(color, msg=""):
    """Print message with color.

    """
    print(color + msg + _Colors.ENDC)

def print_msg(msg=""):
    """Print a normal message.

    """
    pretty_print(_Colors.OKGREEN + msg + _Colors.ENDC)

def print_nfo(msg=""):
    """Print an info message.

    """
    pretty_print(_Colors.OKBLUE + msg + _Colors.ENDC)

def print_wrn(msg=""):
    """Print a warning message.

    """
    pretty_print(_Colors.WARNING + msg + _Colors.ENDC)

def print_err(msg=""):
    """Print an error message.

    """
    pretty_print(_Colors.FAIL + msg + _Colors.ENDC)

def exception_handler(exception_type, exception, traceback):
    """A simple handler that prints the exception message.

    """

    print_err("[Spotify] (%s) : %s" % (exception_type.__name__, exception))

    if os.environ.get('TIZONIA_SPOTIFYPROXY_DEBUG'):
        print_exception(exception_type, exception, traceback)

sys.excepthook = exception_handler

class TizEnumeration(set):
    """A simple enumeration class.

    """
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError

def to_ascii(msg):
    """Unicode to ascii helper.

    """

    return unicodedata.normalize('NFKD', unicode(msg)).encode('ASCII', 'ignore')

class TrackInfo(object):
    """ Class that represents a Spotify track in the queue.

    """

    def __init__(self, track, album_name=None):
        """ class members. """
        self.title = track['name']
        self.artist = track['artists'][0]['name']
        self.album = track['album']['name'] if track.get('album') else album_name;
        self.release_date = track['album']['release_date'] if track.get('album') else 'n/a';
        self.duration = track['duration_ms'] / 1000 if track['duration_ms'] else 0;
        self.uri = track['uri']
        self.thumb_url = track['album']['images'][0]['url'] if track.get('album') else None;

class tizspotifyproxy(object):
    """A class that accesses Spotify servers, retrieves track URLs and creates and
    manages a playback queue.

    """
    SPOTIPY_CLIENT_SECRET = '69a32dec47b34e42a72e6a1bde457d65'
    SPOTIPY_CLIENT_ID = 'a86ba5bbc8484c56b13c01491aa80edc'
    SPOTIPY_REDIRECT_URI = 'http://tizonia.org'

    def __init__(self):
        self.queue = list()
        self.queue_index = -1
        self.play_queue_order = list()
        self.play_modes = TizEnumeration(["NORMAL", "SHUFFLE"])
        self.current_play_mode = self.play_modes.NORMAL
        self.now_playing_track = None
        credentials = SpotifyClientCredentials(client_id=self.SPOTIPY_CLIENT_ID, client_secret=self.SPOTIPY_CLIENT_SECRET)
        self._spotify = spotipy.Spotify(client_credentials_manager=credentials)

    def set_play_mode(self, mode):
        """ Set the playback mode.

        :param mode: current valid values are "NORMAL" and "SHUFFLE"

        """
        self.current_play_mode = getattr(self.play_modes, mode)
        self.__update_play_queue_order()

    def enqueue_tracks(self, arg):
        """Search Spotify for audio tracks and add them to the playback queue.

        :param arg: a search string

        """
        arg_dec = arg.decode('utf-8')
        logging.info('arg : %s', arg_dec)
        print_msg("[Spotify] [Track search] '{0}'.".format(arg_dec))
        try:
            count = len(self.queue)
            results = self._spotify.search(arg_dec, limit=20, offset=0, type='track')
            tracks = results['tracks']
            for i, track in enumerate(tracks['items']):
                self.__enqueue_track(track)

            if count == len(self.queue):
                logging.info('no tracks found arg : %s', arg_dec)
                raise ValueError

            self.__update_play_queue_order()

        except ValueError:
            raise ValueError(str("Track not found : %s" % to_ascii(arg_dec)))

    def enqueue_artist(self, arg):
        """Obtain an artist from Spotify and add all the artist's audio tracks
        to the playback queue.

        :param arg: an artist search term

        """
        arg_dec = arg.decode('utf-8')
        logging.info('arg : %s', arg_dec)
        print_msg("[Spotify] [Artist search] '{0}'.".format(arg_dec))
        try:
            artist = None
            artist_name = None
            artist_dict = dict()
            artist_names = list()
            count = len(self.queue)
            results = self._spotify.search(arg_dec, limit=20, offset=0, type='artist')
            artists = results['artists']
            for i, art in enumerate(artists['items']):
                name = art['name']
                print_wrn("[Spotify] [Artist] '{0}'.".format(name))
                if arg_dec.lower() == name.lower():
                    artist_name = name
                    artist = art
                    break
                if fuzz.partial_ratio(arg_dec, name) > 50:
                    artist_dict[name] = art
                    artist_names.append(name)

            if not artist_name:
                if len(artist_names) > 1:
                    artist_name = process.extractOne(arg, artist_names)[0]
                    artist = artist_dict[artist_name]
                elif len(artist_names) == 1:
                    artist_name = artist_names[0]
                    artist = artist_dict[artist_name]

            if artist:
                self.__enqueue_artist(artist)

            if count == len(self.queue):
                logging.info('not tracks found arg : %s', arg_dec)
                raise ValueError

            self.__update_play_queue_order()

        except ValueError:
            raise ValueError(str("Artist not found : %s" % to_ascii(arg_dec)))

    def enqueue_album(self, arg):
        """Obtain an album from Spotify and add all its tracks to the playback
        queue.

        :param arg: an album search term

        """
        arg_dec = arg.decode('utf-8')
        logging.info('arg : %s', arg_dec)
        print_msg("[Spotify] [Album search] '{0}'.".format(arg_dec))
        try:
            count = len(self.queue)
            results = self._spotify.search(arg_dec, limit=10, offset=0, type='album')
            albums = results['albums']
            for i, album in enumerate(albums['items']):
                if album:
                    self.__enqueue_album(album)
                break

            if count == len(self.queue):
                raise ValueError

            self.__update_play_queue_order()

        except ValueError:
            raise ValueError(str("Album not found : %s" % to_ascii(arg_dec)))

    def enqueue_playlist(self, arg, owner):
        """Add all audio tracks in a Spotify playlist to the playback queue.

        :param arg: a playlist search term

        """
        arg_dec = arg.decode('utf-8')
        logging.info('arg : %s', arg_dec)
        print_msg("[Spotify] [Playlist search] '{0}' (owner: {1})." \
                  .format(arg_dec, owner.decode('utf-8')))
        try:
            count = len(self.queue)
            playlist = None
            playlist_name = None
            playlist_dict = dict()
            playlist_names = list()
            playlist_count = 0
            playlists = self._spotify.user_playlists(owner)
            while playlists:
                for i, plist in enumerate(playlists['items']):
                    playlist_count+=1
                    print_nfo("[Spotify] [Playlist {0}] '{1}' ({2} tracks)." \
                              .format(playlist_count, to_ascii(plist['name']), plist['tracks']['total']))
                    name = plist['name']
                    if arg_dec.lower() == name.lower():
                        playlist_name = name
                        playlist = plist
                        break
                    if fuzz.partial_ratio(arg_dec, name) > 50:
                        playlist_dict[name] = plist
                        playlist_names.append(name)

                if not playlist_name:
                    if playlists['next']:
                        playlists = self._spotify.next(playlists)
                    else:
                        playlists = None
                else:
                    break

            if not playlist_name:
                if len(playlist_names) > 1:
                    playlist_name = process.extractOne(arg, playlist_names)[0]
                    playlist = playlist_dict[playlist_name]
                elif len(playlist_names) == 1:
                    playlist_name = playlist_names[0]
                    playlist = playlist_dict[playlist_name]

            if playlist_name:
                if arg_dec.lower() != playlist_name.lower():
                    print_wrn("[Spotify] '{0}' not found. " \
                              "Playing '{1}' instead." \
                              .format(arg_dec, playlist_name))

                results = self._spotify.user_playlist(owner, playlist['id'],
                                                      fields="tracks,next")
                self.__enqueue_playlist(results)

            if count == len(self.queue):
                raise ValueError

            self.__update_play_queue_order()

        except (ValueError):
            raise ValueError(str("Playlist not found or no audio tracks in playlist : %s" % to_ascii(arg_dec)))

    def enqueue_track_id(self, id):
        """Add an audio track to the playback queue.

        :param id: an track ID, URI, or URL

        """
        logging.info('id : %s', id)
        print_msg("[Spotify] [Track id] '{0}'.".format(id))
        try:
            count = len(self.queue)
            track = self._spotify.track(id)

            if track:
                self.__enqueue_track(track)

            if count == len(self.queue):
                logging.info('track not found with id : %s', id)
                raise ValueError

            self.__update_play_queue_order()

        except ValueError:
            raise ValueError(str("Track not found : %s" % to_ascii(id)))

    def enqueue_artist_id(self, id):
        """Obtain an artist from Spotify and add all the artist's audio tracks
        to the playback queue.

        :param id: an artist ID, URI, or URL

        """
        logging.info('id : %s', id)
        print_msg("[Spotify] [Artist id] '{0}'.".format(id))
        try:
            count = len(self.queue)
            artist = self._spotify.artist(id)

            if artist:
                self.__enqueue_artist(artist)

            if count == len(self.queue):
                logging.info('artist not found with id : %s', id)
                raise ValueError

            self.__update_play_queue_order()

        except ValueError:
            raise ValueError(str("Artist not found : %s" % to_ascii(id)))

    def enqueue_album_id(self, id):
        """Obtain an album from Spotify and add all its audio tracks to the playback
        queue.

        :param id: an album ID, URI, or URL

        """
        logging.info('id : %s', id)
        print_msg("[Spotify] [Album id] '{0}'.".format(id))
        try:
            count = len(self.queue)
            album = self._spotify.album(id)

            if album:
                self.__enqueue_album(album)

            if count == len(self.queue):
                raise ValueError

            self.__update_play_queue_order()

        except ValueError:
            raise ValueError(str("Album not found : %s" % to_ascii(id)))

    def enqueue_playlist_id(self, id, owner):
        """Add all audio items from a playlist to the playback queue.

        :param id: an playlist ID, URI, or URL

        """
        logging.info('id : %s', id)
        print_msg("[Spotify] [Playlist id] '{0}' (owner: {1})." \
                  .format(id, owner.decode('utf-8')))
        try:
            count = len(self.queue)
            playlist = self._spotify.user_playlist(owner, id)

            if playlist:
                self.__enqueue_playlist(playlist)

            if count == len(self.queue):
                logging.info('no playlist found with id : %s', id)
                raise ValueError

            self.__update_play_queue_order()

        except ValueError:
            raise ValueError(str("Playlist not found : %s" % to_ascii(id)))

    def current_track_title(self):
        """ Retrieve the current track's title.

        """
        track = self.now_playing_track
        title = ''
        if track:
            title = to_ascii(track.title).encode("utf-8")
        return title

    def current_track_artist(self):
        """ Retrieve the current track's artist.

        """
        track = self.now_playing_track
        artist = ''
        if track:
            artist = to_ascii(track.artist).encode("utf-8")
        return artist

    def current_track_album(self):
        """ Retrieve the current track's album.

        """
        track = self.now_playing_track
        album = ''
        if track:
            album = to_ascii(track.album).encode("utf-8")
        return album

    def current_track_release_date(self):
        """ Retrieve the current track's publication date.

        """
        track = self.now_playing_track
        date = ''
        if track:
            date = to_ascii(track.release_date).encode("utf-8")
        return date

    def current_track_duration(self):
        """ Retrieve the current track's duration.

        """
        track = self.now_playing_track
        duration = 0
        if track:
            duration = track.duration
        return duration


    def current_track_album_art(self):
        """ Retrieve the current track's album_art.

        """
        track = self.now_playing_track
        album_art = ''
        if track:
            album_art = to_ascii(track.thumb_url).encode("utf-8")
        return album_art

    def current_track_queue_index_and_queue_length(self):
        """ Retrieve index in the queue (starting from 1) of the current track and the
        length of the playback queue.

        """
        return self.play_queue_order[self.queue_index] + 1, len(self.queue)

    def clear_queue(self):
        """ Clears the playback queue.

        """
        self.queue = list()
        self.queue_index = -1

    def remove_current_uri(self):
        """Remove the currently active uri from the playback queue.

        """
        logging.info("")
        if len(self.queue) and self.queue_index:
            track = self.queue[self.queue_index]
            print_nfo("[Spotify] [Track] '{0}' removed." \
                      .format(to_ascii(track['i'].title).encode("utf-8")))
            del self.queue[self.queue_index]
            self.queue_index -= 1
            if self.queue_index < 0:
                self.queue_index = 0
            self.__update_play_queue_order()

    def next_uri(self):
        """ Retrieve the uri of the next track in the playback queue.

        """
        logging.info("")
        try:
            if len(self.queue):
                self.queue_index += 1
                if (self.queue_index < len(self.queue)) \
                   and (self.queue_index >= 0):
                    next_track = self.queue[self.play_queue_order \
                                            [self.queue_index]]
                    return self.__retrieve_track_uri(next_track)
                else:
                    self.queue_index = -1
                    return self.next_uri()
            else:
                return ''
        except (KeyError, AttributeError):
            # TODO: We don't remove this for now
            # del self.queue[self.queue_index]
            logging.info("exception")
            return self.next_uri()

    def prev_uri(self):
        """ Retrieve the uri of the previous track in the playback queue.

        """
        logging.info("")
        try:
            if len(self.queue):
                self.queue_index -= 1
                if (self.queue_index < len(self.queue)) \
                   and (self.queue_index >= 0):
                    prev_track = self.queue[self.play_queue_order \
                                            [self.queue_index]]
                    return self.__retrieve_track_uri(prev_track)
                else:
                    self.queue_index = len(self.queue)
                    return self.prev_uri()
            else:
                return ''
        except (KeyError, AttributeError):
            # TODO: We don't remove this for now
            # del self.queue[self.queue_index]
            logging.info("exception")
            return self.prev_uri()

    def __enqueue_track(self, track):
        """ Add a track to the playback queue.

        :param track: a track object

        """
        if track:
            track_info = TrackInfo(track)
            self.add_to_playback_queue(track_info)

    def __enqueue_artist(self, artist):
        """ Add an artist tracks to the playback queue.

        :param artist: a artist object

        """
        if artist:
            artist_name = artist['name']
            print_wrn("[Spotify] [Artist top tracks] '{0}'." \
                      .format(artist_name))

            track_results = self._spotify.artist_top_tracks(artist['id'])
            tracks = track_results['tracks']
            for i, track in enumerate(tracks):
                track_info = TrackInfo(track)
                self.add_to_playback_queue(track_info)

            # now enqueue albums
            try:
                album_results = self._spotify.artist_albums(artist['id'], limit=30)
                album_items = album_results['items']
                for i, album in enumerate(album_items):
                    print_wrn("[Spotify] [Album] '{0}'.".format(album['name']))
                    tracks = self._spotify.album_tracks(album['id'], limit=50, offset=0)
                    for j, track in enumerate(tracks['items']):
                        track_info = TrackInfo(track, album['name'])
                        self.add_to_playback_queue(track_info)
            except:
                pass

    def __enqueue_album(self, album):
        """ Add an album tracks to the playback queue.

        :param album: a album object

        """
        if album:
            album_name = album['name']
            print_wrn("[Spotify] [Album] '{0}'.".format(album_name))
            try:
                tracks = self._spotify.album_tracks(album['id'], limit=50, offset=0)
                for j, track in enumerate(tracks['items']):
                    track_info = TrackInfo(track, album_name)
                    self.add_to_playback_queue(track_info)
            except:
                pass

    def __enqueue_playlist(self, playlist):
        """ Add an playlist tracks to the playback queue.

        :param playlist: a playlist object

        """
        if playlist:
            tracks = playlist['tracks']
            while tracks:
                for i, item in enumerate(tracks['items']):
                    track = item['track']
                    track_info = TrackInfo(track)
                    self.add_to_playback_queue(track_info)
                if tracks['next']:
                    tracks = self._spotify.next(tracks)
                else:
                    tracks = None

    def __update_play_queue_order(self):
        """ Update the queue playback order.

        A sequential order is applied if the current play mode is "NORMAL" or a
        random order if current play mode is "SHUFFLE"

        """
        total_tracks = len(self.queue)
        if total_tracks:
            if not len(self.play_queue_order):
                # Create a sequential play order, if empty
                self.play_queue_order = range(total_tracks)
            if self.current_play_mode == self.play_modes.SHUFFLE:
                random.shuffle(self.play_queue_order)
            print_nfo("[Spotify] [Tracks in queue] '{0}'." \
                      .format(total_tracks))

    def __retrieve_track_uri(self, track):
        """ Retrieve a track uri

        """
        try:
            self.now_playing_track = track
            return track.uri.encode("utf-8")

        except AttributeError:
            logging.info("Could not retrieve the track uri!")
            raise

    def add_to_playback_queue(self, track):
        """ Add to the playback queue. """

        print_nfo("[Spotify] [Track] '{0}' [{1}]." \
                  .format(to_ascii(track.title).encode("utf-8"), \
                          to_ascii(track.artist).encode("utf-8")))
        queue_index = len(self.queue)
        self.queue.append(track)

if __name__ == "__main__":
    tizspotifyproxy()