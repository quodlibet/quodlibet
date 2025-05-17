# Copyright (c) 2018 Philipp Wolfer <ph.wolfer@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import logging
import os
import ssl
import time
from http.client import HTTPConnection, HTTPSConnection

HOST_NAME: str | None = "api.listenbrainz.org"
PATH_SUBMIT = "/1/submit-listens"
SSL_CONTEXT: ssl.SSLContext | None = ssl.create_default_context()

# to run against a local dev server
if os.getenv("QL_LISTENBRAINZ_DEV_SERVER") is not None:
    HOST_NAME = os.getenv("QL_LISTENBRAINZ_DEV_SERVER")
    SSL_CONTEXT = None


class Track:
    """
    Represents a single track to submit.

    See https://listenbrainz.readthedocs.io/en/latest/dev/json.html
    """

    def __init__(
        self, artist_name, track_name, release_name=None, additional_info=None
    ):
        """
        Create a new Track instance
        @param artist_name as str
        @param track_name as str
        @param release_name as str
        @param additional_info as dict
        """
        self.artist_name = artist_name
        self.track_name = track_name
        self.release_name = release_name
        self.additional_info = additional_info or {}

    @staticmethod
    def from_dict(data):
        return Track(
            data["artist_name"],
            data["track_name"],
            data.get("release_name", None),
            data.get("additional_info", {}),
        )

    def to_dict(self):
        return {
            "artist_name": self.artist_name,
            "track_name": self.track_name,
            "release_name": self.release_name,
            "additional_info": self.additional_info,
        }

    def __repr__(self):
        return f"Track({self.artist_name}, {self.track_name})"


class ListenBrainzClient:
    """
    Submit listens to ListenBrainz.org.

    See https://listenbrainz.readthedocs.io/en/latest/dev/api.html
    """

    def __init__(self, logger=None):
        logger = logger or logging.getLogger(__name__)
        self.__next_request_time = 0
        self.user_token = None
        self.logger = logger

    def listen(self, listened_at, track):
        """
        Submit a listen for a track
        @param listened_at as int
        @param entry as Track
        """
        payload = _get_payload(track, listened_at)
        return self._submit("single", [payload])

    def playing_now(self, track):
        """
        Submit a playing now notification for a track
        @param track as Track
        """
        payload = _get_payload(track)
        return self._submit("playing_now", [payload])

    def import_tracks(self, tracks):
        """
        Import a list of tracks as (listened_at, Track) pairs
        @param track as [(int, Track)]
        """
        payload = _get_payload_many(tracks)
        return self._submit("import", payload)

    def _submit(self, listen_type, payload, retry=0):
        self._wait_for_ratelimit()
        self.logger.debug("ListenBrainz %s: %r", listen_type, payload)
        data = {"listen_type": listen_type, "payload": payload}
        headers = {
            "Authorization": f"Token {self.user_token}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data)
        print(f"submit: {body}")
        if SSL_CONTEXT is not None:
            conn = HTTPSConnection(HOST_NAME, context=SSL_CONTEXT)
        else:
            conn = HTTPConnection(HOST_NAME)
        # XXX TODO, catch errors?
        conn.request("POST", PATH_SUBMIT, body, headers)
        response = conn.getresponse()
        response_text = response.read()
        try:
            response_data = json.loads(response_text)
        # Python3
        # except json.JSONDecodeError:
        #    response_data = response_text
        # Python2
        except ValueError as e:
            if str(e) != "No JSON object could be decoded":
                raise e
            response_data = response_text

        self._handle_ratelimit(response)
        log_msg = f"Response {response.status}: {response_data!r}"
        if response.status == 429 and retry < 5:  # Too Many Requests
            self.logger.warning(log_msg)
            return self._submit(listen_type, payload, retry + 1)
        if response.status == 200:
            self.logger.debug(log_msg)
        else:
            self.logger.error(log_msg)
        return response

    def _wait_for_ratelimit(self):
        now = time.time()
        if self.__next_request_time > now:
            delay = self.__next_request_time - now
            self.logger.debug("Rate limit applies, delay %d", delay)
            time.sleep(delay)

    def _handle_ratelimit(self, response):
        remaining = int(response.getheader("X-RateLimit-Remaining", 0))
        reset_in = int(response.getheader("X-RateLimit-Reset-In", 0))
        self.logger.debug("X-RateLimit-Remaining: %i", remaining)
        self.logger.debug("X-RateLimit-Reset-In: %i", reset_in)
        if remaining == 0:
            self.__next_request_time = time.time() + reset_in


def _get_payload_many(tracks):
    payload = []
    for listened_at, track in tracks:
        data = _get_payload(track, listened_at)
        payload.append(data)
    return payload


def _get_payload(track, listened_at=None):
    data = {"track_metadata": track.to_dict()}
    if listened_at is not None:
        data["listened_at"] = listened_at
    return data
