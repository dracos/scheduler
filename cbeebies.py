#!/usr/bin/env python
#
# cbeebies.py:
# Twitter/Toot when some CBeebies shows are on TV
#
# Copyright (c) 2018 Matthew Somerville.
# http://www.dracos.co.uk/

import json
import sys
import arrow
from bot import SchedulerBot, Event
from config import SHOWS


class Event(Event):
    def __str__(self):
        return '%s %s %s %s' % (self.bot.name, self.time, self.image_url, self.status)

    @property
    def image(self):
        return self.bot.get_image(self.image_url)

    @property
    def status(self):
        return '%s (s%se%s) starting shortly!\n\u201c%s\u201d' % (
            self.programme['title'],
            self.programme['programme']['position'],
            self.programme['position'],
            self.programme['short_synopsis'],
        )


class CBeebiesBot(SchedulerBot):
    localfile = '/home/bots/data/%s-schedule'

    not_got = 'Maintenance mode'

    def fetch(self):
        pid = SHOWS[self.name]
        url = 'http://www.bbc.co.uk/programmes/%s/episodes/upcoming.json'
        new = self.get_contents(url % pid)
        self.fetch_check_file(new)
        return False

    def fetch_diff(self, a, b):
        return a != b

    def parse(self, warn=0):
        d = self.parse_get_file(warn)
        if not d:
            return []

        try:
            j = json.loads(d)
        except ValueError:
            return []

        events = []
        for broadcast in j['broadcasts']:
            image_pid = broadcast['programme']['image']['pid']
            image_url = 'http://ichef.bbci.co.uk/images/ic/192x108/%s.jpg' % image_pid
            time = arrow.get(broadcast['start'])
            events.append(
                Event(bot=self, time=time, programme=broadcast['programme'],
                      image_url=image_url)
            )
        return sorted(events, key=lambda s: s.time)

    def alert(self, event, now):
        return now >= event.time.shift(minutes=-10) and now < event.time


for key in SHOWS.keys():
    argv = sys.argv.copy()
    CBeebiesBot(key).run()
    sys.argv = argv
