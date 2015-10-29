"""A Python library for accessing the Rdio web service API with OAuth.

Copyright (c) 2010-2011 Rdio Inc
See individual source files for other copyrights.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import base64
import json
import time
import urllib
import urllib2
import logging

__author__ = "Rdio <api@rd.io>"
__copyright__ = (
  "Copyright 2010-2015, Rdio Inc. httplib2 copyright Joe Gregorio."
  " oauth copyright Leah Culver, Joe Stump, Mark Paschal, Vic Fryzel")
__contributors__ = ['Ian McKellar']
__version__ = "2.0.0"
__license__ = "MIT"

LOGGER = logging.getLogger(__name__)


class RdioException(BaseException):
  """Our base exception class."""

  pass


class RdioAPIException(RdioException):
  """A problem with the rdio api."""

  pass


class RdioProtocolException(RdioException):
  """A problem with the rdio api that has some explanation."""

  def __init__(self, code, content):
    """Instantiate the exception."""
    RdioException.__init__(self)
    self.code = code
    self.content = content

  def __str__(self):
    """Render the exception into a string."""
    return 'RdioProtocolException %s: %s' % (self.code, self.content)


class AuthStore(object):
  """A wrapper around the persistant storage that must be passed in."""

  _KEYS = ['device_code', 'device_expires', 'device_interval', 'refresh_token', 'access_token', 'access_token_expires']

  def __init__(self, storage):
    """Wrap the passed-in storage (which should behave like a dict) in some convenience methods."""
    self._storage = storage

  @property
  def device_code(self):
    """Return a valid device code or None."""
    device_code = None
    needs = ('device_code', 'device_expires')

    if all(x in self._storage for x in needs):
      if self._storage['device_expires'] >= time.time():
        device_code = self._storage['device_code']
    return device_code

  @property
  def refresh_token(self):
    """Return a valid refresh token or None."""
    refresh_token = None
    if 'refresh_token' in self._storage:
      refresh_token = self._storage['refresh_token']
    return refresh_token

  @property
  def access_token(self):
    """Return a valid access token or None."""
    access_token = None
    needs = ('access_token', 'access_token_expires')
    if all(x in self._storage for x in needs):
      if self._storage['access_token_expires'] >= time.time():
        access_token = self._storage['access_token']
    return access_token

  @property
  def authenticating(self):
    """Determine if the library is in the middle of authenticating."""
    return self.device_code is not None and self.refresh_token is None

  @property
  def refreshing(self):
    """Determine if the library is in the middle of refreshing a refresh token."""
    return self.refresh_token is not None and self.access_token is None

  @property
  def authenticated(self):
    """Determine if the library is fully authenticated."""
    return self.access_token is not None

  def logout(self):
    """Clear authentication information."""
    for key in self._KEYS:
      del self[key]

  def __contains__(self, key):
    """Pass through to the storage member's method."""
    return key in self._storage

  def __getitem__(self, key):
    """Pass through to the storage member's method."""
    return self._storage[key]

  def __setitem__(self, key, value):
    """Set the store to the value for the key."""
    if value is None:
      raise RdioAPIException('Invalid %s: %r' % (key, value))
    self._storage[key] = value

  def __delitem__(self, key):
    """Remove an item from the storage -- suppresses errors."""
    if key in self._storage:
      del self._storage[key]


class HTTPDefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
  def __init__(self):
    pass

  # pylint: disable=too-many-arguments
  def http_error_default(self, req, rsp, code, msg, hdrs):
    return rsp


class Rdio(object):
  """The API adapter."""

  API_ENDPOINT = 'https://services.rdio.com/api/1/'
  DEVICE_CODE_URL = 'https://services.rdio.com/oauth2/device/code/generate'
  TOKEN_URL = 'https://services.rdio.com/oauth2/token'

  POLL_INTERVAL = 2.0  # seconds
  POLL_LIMIT = 600.0  # seconds

  def __init__(self, client_id, client_secret, data_store, urls=None):
    """Set up the adapter as needed."""
    if urls is None:
      urls = {}
    self.urls = {
      'api_endpoint': self.API_ENDPOINT,
      'device_code_url': self.DEVICE_CODE_URL,
      'token_url': self.TOKEN_URL
    }
    for key in self.urls:
      if key in urls and urls[key] is not None:
        self.urls[key] = urls[key]
    self.client_id = client_id
    self.client_secret = client_secret
    self._store = AuthStore(data_store)

    opener = urllib2.build_opener(HTTPDefaultErrorHandler)
    urllib2.install_opener(opener)

  def _basic(self):
    """Generate a basic auth string with the client id and secret."""
    return 'Basic ' + base64.encodestring('%s:%s' % (self.client_id, self.client_secret)).replace('\n', '')

  def _bearer(self):
    """Generate a bearer auth string with the access token."""
    return 'Bearer %s' % self._store['access_token']

  def _check_device_code(self):
    """Check the device code to see if it has been approved."""
    body = urllib.urlencode({'grant_type': 'device_code', 'device_code': self._store['device_code']})
    return self._check_token(body)

  def _refresh_token(self):
    """Try to get a fresh access token."""
    body = urllib.urlencode({'grant_type': 'refresh_token', 'refresh_token': self._store['refresh_token']})
    return self._check_token(body)

  def _check_token(self, body):
    """Check a device code or refresh the refresh token."""
    response, content = self._request(self.urls['token_url'], body)
    if response.code == 200:
      api_response = json.loads(content) or {}
      self._store['token_type'] = api_response.get('token_type')
      self._store['access_token'] = api_response.get('access_token')
      self._store['refresh_token'] = api_response.get('refresh_token')
      expires = api_response.get('expires_in') + time.time()
      self._store['access_token_expires'] = expires
      LOGGER.debug('Successfully authenticated')
    else:
      LOGGER.debug('Token response: %s %s', response.code, content)
    return response.code, content

  def _request(self, url, body, headers=None):
    """Have the client make a direct request with the appropriate header."""
    if headers is None:
      headers = {}
    if self._store.access_token is not None:
      headers['Authorization'] = self._bearer()
    else:
      headers['Authorization'] = self._basic()

    request = urllib2.Request(url, data=body, headers=headers)
    response = urllib2.urlopen(request)
    return response, response.read()

  def begin_authentication(self):
    """
    Begin the authentication process.

    Returns a url for a user to visit, and a device code that must be
    entered on the form on that page. It is expected that command line
    applications will print this out and then call
    complete_authentication.
    """
    if self._store.authenticating or self._store.authenticated:
      LOGGER.info('Beginning authentication while already logged in')
      self._store.logout()

    LOGGER.debug('Requesting a new device token')
    body = urllib.urlencode({'client_id': self.client_id})
    response, content = self._request(self.urls['device_code_url'], body)

    if response.code != 200:
      raise RdioProtocolException(response.code, content)

    api_response = json.loads(content) or {}
    device_code = api_response.get('device_code')
    url = api_response.get('verification_url')
    if url is None:
      raise RdioAPIException('Response is missing verification_url')

    self._store['device_code'] = device_code
    expires = api_response.get('expires_in_s') + time.time()
    self._store['device_expires'] = expires
    if 'http://' not in url and 'https://' not in url:
      url = 'https://%s' % url
    return url, device_code

  def complete_authentication(self):
    """
    Complete the authentication process.

    This will block and poll the token url for several minutes or until the user
    enters the device number into the correct form.
    """
    if self._store.device_code is None:
      raise RdioException('Cannot finish authenticating without a valid device id.')

    LOGGER.debug('Checking if the device id has been authorized')
    if 'device_interval' in self._store:
      interval = self._store['device_interval'] or self.POLL_INTERVAL
    else:
      interval = self.POLL_INTERVAL
    limit = self.POLL_LIMIT / interval
    while (not self._store.authenticated) and limit > 0:
      limit -= 1
      response_code, content = self._check_device_code()
      if not self._store.authenticated:
        time.sleep(interval)

    if not self._store.authenticated:
      raise RdioProtocolException(response_code, content)

  def call(self, service_method, **args):
    """
    Call a service_method on the Rdio service_method and return the result as a Python dictionary.

    If there's an error then raise an appropriate exception.
    """
    response, content = self.call_raw(service_method, **args)
    if response.code != 200:
      raise RdioProtocolException(response.code, content)
    json_response = json.loads(content) or {}
    if json_response['status'] == 'ok':
      return json_response['result']
    else:
      raise RdioAPIException(json_response['message'])

  def call_raw(self, service_method, **args):
    """
    Call a service_method on the Rdio service_method and return the raw HTTP result.

    A response object and the content object. See the httplib2 request method for examples
    """
    args['method'] = service_method
    args['client_id'] = self.client_id
    access_token = self._store.access_token
    refresh_token = self._store.refresh_token
    if access_token is None and refresh_token is not None:
      self._refresh_token()
    body = urllib.urlencode(args)
    return self._request(self.urls['api_endpoint'], body)

  def __getattr__(self, name):
    """Translate missing methods into API calls."""

    return lambda **kwargs: self.call(name, **kwargs)
