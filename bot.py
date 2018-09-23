#!/usr/bin/env python
#
# bot.py:
# Twitter/Toot at points when something happens elsewhere
#
# Copyright (c) 2018 Matthew Somerville.
# http://www.dracos.co.uk/

import argparse
import os
import re
import sys
import requests
import arrow
from polybot import Bot


class Event(object):
    image = None
    status = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        return '%s %s' % (self.time, self.status)


class SchedulerBot(Bot):
    path = '/home/bots/scheduler/conf/'
    choices = ['fetch', 'post', 'test']

    def __init__(self, name):
        super().__init__(name)
        self.scheduler_parser = p = argparse.ArgumentParser()
        p.add_argument('action', choices=self.choices,
                       help='Action to perform; one of %s' % ', '.join(self.choices))
        self.scheduler_args, left = p.parse_known_args()
        sys.argv[1:] = left

    def fetch(self):
        """Fetch something external and save somewhere."""
        raise NotImplementedError()

    def fetch_save_file(self, data):
        f = open(self.localfile % self.name, 'w')
        f.write(data)
        f.close()
        try:
            os.remove('%s-override' % (self.localfile % self.name))
        except FileNotFoundError:
            pass

    def fetch_check_file(self, new):
        if not new:
            return False
        current = ''
        try:
            current = self.get_contents(self.localfile % self.name)
        except FileNotFoundError:
            pass
        if self.fetch_diff(current, new) and not re.search(self.not_got, new):
            self.fetch_save_file(new)
            return True
        return False

    def parse_get_file(self, warn=0):
        try:
            d = self.get_contents("%s-override" % (self.localfile % self.name))
        except IOError:
            try:
                d = self.get_contents(self.localfile % self.name)
            except IOError:
                if warn:
                    print('No downloaded schedule for %' % self.name)
                return None
        return d

    def parse(self, warn=0):
        """Parse external thing, return list of event objects."""
        raise NotImplementedError()

    def run(self):
        args = self.scheduler_args
        func = getattr(self, 'do_' + args.action, None)
        if func:
            func()
        else:
            self.scheduler_parser.print_help()

    def do_fetch(self):
        if self.fetch():
            print("New schedule downloaded")
            self.do_test()

    def do_test(self):
        for event in self.parse(warn=1):
            print(event)

    def do_post(self):
        now = arrow.utcnow()
        self.alert_on = [e for e in self.parse() if self.alert(e, now)]
        if self.alert_on or '--setup' in sys.argv:
            super().run()  # Kick off actual bot

    def main(self):
        self.log.info('Posting at ' + arrow.now().format())
        for event in self.alert_on:
            if event.image:
                self.post(event.status, imagefile=event.image, mime_type='image/jpeg', wrap=True)
            else:
                self.post(event.status, wrap=True)

    def get_contents(self, s, mode='text'):
        if 'http://' in s or 'https://' in s:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 ' +
                       '(KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'}
            try:
                r = requests.get(s, headers=headers)
                o = r.content if mode == 'binary' else r.text
            except requests.exceptions.ConnectionError:
                o = ''
        else:
            mode = 'rb' if mode == 'binary' else 'rt'
            o = open(s, newline='', mode=mode).read()
        return o

    def get_image(self, u):
        for i in range(3):
            try:
                f = self.get_contents(u, mode='binary')
                return f
            except IOError:
                pass
        raise
