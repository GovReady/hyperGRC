# app/tests/test_users.py

import unittest
import urllib2
from flask import Flask
from flask_testing import TestCase
from flask_testing import LiveServerTestCase
import string
import random


class MyTest(TestCase):

    def create_app(self):
        app = Flask(__name__)
        # app = Flask("hypergrc")
        # app.config.from_object('config.TestConfig')

        app.config['TESTING'] = True
        return app

    def test_test(self):
        val = 1
        self.assertEqual(val, 1)
        self.assertFalse(val == 2)


class OutputsTest(TestCase):

    def create_app(self):
        # app = Flask(__name__)
        app = Flask("hypergrc")
        app.config['TESTING'] = True
        return app

    def test_fedramp_cis_report_listed(self):
        val = 1
        self.assertEqual(val, 1)
        self.assertFalse(val == 2)


class DataTest(LiveServerTestCase):

    def create_app(self):
        # app = Flask(__name__)
        app = Flask("hypergrc")
        app.config['TESTING'] = True
        # Default port is 5000
        app.config['LIVESERVER_PORT'] = 5050
        # Default timeout is 5 seconds
        app.config['LIVESERVER_TIMEOUT'] = 10
        app.config['FLASK_DEBUG'] = 1
        return app


    def test_update_component_file(self):

        random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(7))

        # Create test data
        component = "AWS"
        control_key = "AT-01"
        control_key_part = "a"
        summary = "New summary " + random_string

        data = {"component": component,
                "control_key": control_key,
                "control_key_part": control_key_part,
                "summary": summary
                }

        # url = self.get_server_url() + "/organization/project/index"
        # url = self.get_server_url() + "/DNFSB/DNFSB.gov/800-53r4/control/CM-2"
        url = "http://127.0.0.1:5050/DNFSB/DNFSB.gov/800-53r4/control/CM-2"
        print "url", url

        response = urllib2.urlopen(self.get_server_url())
        print "********** response", response.read()
        self.assertEqual(response.code, 200)

if __name__ == '__main__':
	unittest.main()

