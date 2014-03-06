import unittest

from rdioapi import Rdio


class TestClientCreation(unittest.TestCase):
    def setUp(self):
        self.CONSUMER_KEY = 'test_consumer_key'
        self.CONSUMER_SECRET = 'test_consumer_secret'

    def test_creation(self):
        state = {}
        rdio_client = Rdio(self.CONSUMER_KEY, self.CONSUMER_SECRET, state)
        self.assertIsInstance(rdio_client, Rdio)
