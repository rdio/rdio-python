import unittest

from rdioapi import Rdio


class TestClientCreation(unittest.TestCase):
  def setUp(self):
    self.client_id = 'test_client_id'
    self.consumer_secret = 'test_consumer_secret'

  def test_creation(self):
    """Can the Rdio class be instantiated?"""
    state = {}
    rdio_client = Rdio(self.client_id, self.consumer_secret, state)
    self.assertIsInstance(rdio_client, Rdio)

  def test_creation_with_urls(self):
    """Can the Rdio class be instantiated with the optional urls param?"""
    state = {}
    rdio_client = Rdio(self.client_id, self.consumer_secret, state, {})
    self.assertIsInstance(rdio_client, Rdio)
