#!/usr/bin/env python
#
# iss.py:
# Twitter/Toot when the ISS is overhead.
#
# Copyright (c) 2018 Matthew Somerville.
# http://www.dracos.co.uk/

import json
import re
import arrow
from bot import SchedulerBot, Event
from config import LATITUDE, LONGITUDE, ALTITUDE, FORECASTIO_KEY


localfile = '/home/sympl/scheduler/data/%s'


class Event(Event):
    @property
    def status(self):
        text = "ISS pass: magnitude %.1f, %s\u2013%s from %s to %s, maximum altitude %s at %s in %s. Weather: %s."
        return (text % (float(self.magnitude), self.start_time, self.end_time, self.start_az, self.end_az,
                        self.max_alt, self.max_time, self.max_az, self.weather))


def get_timestamp(s):
    s = arrow.get(s, ['MMM D, HH:mm:ss', 'MMM DD HH:mm:ss a', 'DD MMM HH:mm:ss'])
    now = arrow.now()
    s = s.replace(year=now.year, tzinfo='Europe/London')
    # Deal with around New Year time
    if s < now:
        s = s.shift(years=1)
    return str(s.int_timestamp)


class ISSBot(SchedulerBot):
    choices = SchedulerBot.choices + ['weather']

    def __init__(self, name, latitude, longitude, altitude, forecastio_key):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.forecastio_key = forecastio_key
        super().__init__(name)

    def do_weather(self):
        url = 'https://api.forecast.io/forecast/%s/%s,%s?units=uk2&exclude=minutely,hourly,daily,alerts,flags'
        url = url % (self.forecastio_key, self.latitude, self.longitude)
        fp = self.get_contents(url)
        weather = json.loads(fp)
        json.dump(weather['currently'], open(localfile % 'weather.json', 'w'))

    def fetch(self):
        url = 'http://www.heavens-above.com/PassSummary.aspx?satid=25544&lat=%f&lng=%f&alt=%d&tz=GMT'
        url = url % (self.latitude, self.longitude, self.altitude)
        iss = self.get_contents(url)
        rows = re.findall('<tr class="clickableRow"[^>]*>\s*<td><a href="[^"]*" title="[^"]*">(.*?)</a></td>' +
                          ('<td[^>]*>\s*(.*?)\s*</td>' * 11), iss)
        fp = open(localfile % 'iss.tsv', 'w')
        for row in rows:
            date, mag, start_time, start_alt, start_az, max_time, max_alt, max_az, \
                end_time, end_alt, end_az, pass_type = row
            timestamp = get_timestamp('%s %s' % (date, start_time))
            out = (timestamp, mag, start_time, end_time, start_az, end_az, max_time, max_alt, max_az)
            fp.write("\t".join(out) + "\n")
        fp.close()

    def parse(self, warn=0):
        weather = json.load(open(localfile % 'weather.json'))
        if not weather:
            return []  # Problem with weather file
        weather_desc = weather['summary']

        events = []

        iss = open(localfile % 'iss.tsv')
        for row in iss:
            epoch, mag, start_time, end_time, start_az, end_az, max_time, max_alt, max_az = row.strip().split("\t")
            epoch = arrow.get(epoch, 'X').to('Europe/London')
            events.append(
                Event(time=epoch,
                      magnitude=mag, start_time=start_time, end_time=end_time, start_az=start_az, end_az=end_az,
                      max_time=max_time, max_alt=max_alt, max_az=max_az, weather=weather_desc)
            )

        return sorted(events, key=lambda s: s.time)

    def alert(self, event, now):
        soon = now.shift(minutes=30)
        return soon >= event.time and soon < event.time.shift(minutes=5)


ISSBot('abovebrum', LATITUDE, LONGITUDE, ALTITUDE, FORECASTIO_KEY).run()
