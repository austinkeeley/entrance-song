entrance-song
===============

Sniffs the local network for when a DHCP lease is assigned, identifies the device
owner, and plays their entrance song.

## Requires

* A DHCP server
* A Spotify premium account
* A Spotify developer key
* Python 3

## Usage

Install dependencies

    pip install -r requirements.txt

Create the database

    python models.py

If you haven't created a developer account and application, do so at https://developer.spotify.com/
For the return URL, you can use anything. I recommend just using http://localhost. We'll just need that
for completing the authentication using Spotipy.

Set the following environment variables

    SPOTIPY_CLIENT_ID=<your client ID>
    SPOTIPY_CLIENT_SECRET=<your client secret>
    SPOTIPY_REDIRECT_URI=http://localhost

Now run bin/entrancesong

**NOTE:** You might need to run this as root since it sniffs on your network interface.

If this is the first time authenticating, a web browser will open a prompt you to
authorize your account against the application. After authorizing, you will be
redirected to a http://localhost URL. Copy this entire URL and paste it back into the terminal.

You shouldn't need to re-authenticate unless the `.cache-spotipy-user` file is
deleted.

As devices connect to the network and make DHCP requests, they will appear in the
database's `device` table. You'll need to add a row to the `owner` table and the
`song` table and link them using the `owner_id` keys.


## Features

* Can set a song to start at a certain minute and second. Sometime the best part of a song
  isn't at the beginning.
* Can set a duration to play so you don't have to listen to a whole track when you just
  want the awesome part.


## Optional Arguments

* `--volume` The volume percentage to play entrance songs, integer. Defaults to 70.
* `--device` The device to play the entrance song out of. Defaults to using the device 
  currently playing music.

## Helpful Utilities

* There's a stand-alone Python script `bin/devices` that that will list your devices.

## Known Issues

* Can't fade out music played on certain devices (smartphones, tablets). You will get the
  following exception on these:

        Player command failed: Cannot control device volume

* Can only return playback to albums and static playlists. Trying to return playback to
  something like an artist will raise the following exception:

        Can't have offset for context type: ARTIST

* If no devices are currently playing and the `--device` option isn't specified, the
  following exception will be raised:

        Player command failed: No active device found

* Probably a lot of other weird bugs. I mostly wrote this for myself to allow friends
  to have their own custom entrance themes when they come over to watch a movie.
