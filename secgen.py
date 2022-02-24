#!/usr/bin/env python
#
# secgen.py:
# Twitter/Too the daily schedule of the UN Secretary-General
#
# Copyright (c) 2018 Matthew Somerville.
# http://www.dracos.co.uk/

import re
import html.entities
import arrow
from bs4 import BeautifulSoup
from bot import SchedulerBot, Event

REGEX_TIME = re.compile('(\*?(\d+)(?:(?::|\.)\s*(\d+)|\s*(a\.?m\.?|p\.?m\.?|noon))+\.?\s*\*?)')


def remove_changing_bits(s):
    return re.sub('(?s)^.*?view-content', '', s)


class SecgenBot(SchedulerBot):
    localfile = '/home/sympl/scheduler/data/%s-schedule'

    not_got = ('(?i)Proxy Error|urgent maintenance|Not Found|Service Temporarily Unavailable' +
               '|Internal server error|HTTP Error 50[17]|SQLState')

    def alert(self, event, now):
        return now >= event.time and now < event.time.shift(minutes=5)

    def fetch_diff(self, a, b):
        return remove_changing_bits(a) != remove_changing_bits(b)

    def fetch(self):
        new = self.get_contents('https://www.un.org/sg/en/content/sg/appointments-secretary-general')
        return self.fetch_check_file(new)

    def parse(self, warn=0):
        d = self.parse_get_file(warn)
        if not d:
            return []

        soup = BeautifulSoup(d, 'html.parser')
        table = soup.find('div', 'view-schedules')
        if not table:
            return []

        events = []
        pastnoon = False
        date = arrow.get(table.find('span', 'date-display-single')['content'], 'YYYY-MM-DDTHH:mm:ssZZ')
        for row in table('tr'):
            row = parsecell(row.renderContents().decode('utf-8'))
            m = REGEX_TIME.match(row)
            if not m:
                if row[0:2] in ('- ', 'Mr') or row[0:4] == 'Amb.':
                    event = parsecell(row, True)
                    last = events[-1]
                    events[-1] = (last[0], '%s %s' % (last[1], event))
                continue
            time = m.group(1)
            text = row.replace(time, '')
            time, pastnoon = parsetime(time, date, pastnoon)
            event = parsecell(text, True)
            event = prettify(event)
            events.append(Event(time=time, status=event))
        return events


def parsetime(time, date, pastnoon):
    m = REGEX_TIME.search(time)
    if m:
        (dummy, hour, min, pm) = m.groups()
        if min is None:
            min = 0
        if len(hour) == 3:
            hour, min = hour[0], hour[1:]
    elif time == 'noon':
        hour = 12
        min = 0
        pm = 'noon'
    hour = int(hour)
    min = int(min)
    if not pm and pastnoon:
        hour += 12
    if pm in ('pm', 'p.m', 'p.m.') and hour < 12:
        hour += 12
    if pm in ('am', 'a.m', 'a.m.') and hour == 12:
        hour -= 12
    if pm in ('pm', 'p.m', 'p.m.', 'noon'):
        pastnoon = True
    d = date.replace(hour=hour, minute=min)
    return d, pastnoon


def titlecaseifuppercase(s):
    if re.match('[A-Z]+$', s) and len(s) > 2:
        return s.title()
    if s == 'OF':
        return 'of'
    return s


def prettify(s):
    s = re.sub('^approx\. ', '', s)
    s = ''.join(map(titlecaseifuppercase, re.split('([() ])', s)))
    s = s.replace('Secretery', 'Secretary')
    if (re.match('Addressing|Meeting (with|on)|Visiting|Visit to|Trilateral Meeting', s)
            and not re.search('Secretary-General (will|to) make remarks', s)):
        return s
    if re.match('Chairing of the ', s):
        return re.sub('Chairing of the ', 'Chairing the ', s)
    if re.match('Joint press encounter by the Secretary-General with: ', s):
        return re.sub('Joint press encounter by the Secretary-General with: ', 'Joint press encounter with ', s)
    if re.match('Joint Declaration on (.*?) by the Secretary-General and ', s):
        return re.sub('Joint (.*?) by the Secretary-General and ', r'Joint \1 with ', s)
    if re.match('(The )?Secretary-General[^a-zA-Z]*(to|will) address ', s):
        return re.sub('(The )?Secretary-General[^a-zA-Z]*(to|will) address ', 'Addressing ', s)
    if re.match('(The )?Secretary-General (to|will) make ', s):
        return re.sub('(The )?Secretary-General (to|will) make ', 'Making ', re.sub(r'\bhis\b', 'my', s))
    if re.match('Secretary-General to attend ', s):
        return re.sub('Secretary-General to attend ', 'Attending ', s)
    if re.match('.*? hosted by the Secretary-General ', s):
        return re.sub('(.*?) hosted by the Secretary-General ', r'Hosting \1 ', s)
    if re.match('Secretary-General to host ', s):
        return re.sub('Secretary-General to host ', 'Hosting ', s)
    if re.match('The Secretary-General departs ', s):
        return re.sub('The Secretary-General departs ', 'Departing ', s)
    if re.match('Secretary-General to brief ', s):
        return re.sub('Secretary-General to brief ', 'Briefing ', s)
    if re.search('to hear a briefing by the Secretary-General', s):
        return 'Briefing a ' + re.sub('to hear a briefing by the Secretary-General ', '', s)
    if re.match('Secretary-General&rsquo;s briefing to ', s):
        return re.sub('Secretary-General&rsquo;s briefing to ', 'Briefing to ', s)
    if re.match('Secretary-General to speak at ', s):
        return re.sub('Secretary-General to speak at ', 'Speaking at ', s)
    if re.match('Secretary-General to speak to ', s):
        return re.sub('Secretary-General to speak to ', 'Speaking to ', s)
    if re.match('Secretary-General\'s opening statement at ', s):
        return re.sub('Secretary-General\'s opening statement at his ', 'Making opening statement at my ', s)
    if re.match('Secretary-General\'s closing statement at ', s):
        return re.sub('Secretary-General\'s closing statement at his ', 'Making closing statement at my ', s)
    if re.match('Secretary-General to deliver ', s):
        return re.sub('Secretary-General to deliver ', 'Delivering ', s)
    if re.match('Secretary-General will hold ', s):
        return re.sub('Secretary-General will hold ', 'Holding ', s)
    if re.match('Secretary-General to give ', s):
        return re.sub('Secretary-General to give ', 'Giving ', s)
    if re.match('Drop by at ', s):
        return re.sub('Drop by at ', 'Dropping by ', s)
    if re.match('Remarks by the Secretary-General |SG remarks at|' +
                'Secretary(-| )General\'?s? (to (make|give) )?remarks |Welcoming Remarks ', s):
        return re.sub(('Remarks by the Secretary-General |SG remarks |' +
                       'Secretary(-| )General\'?s? (to (make|give) )?remarks |Welcoming Remarks '),
                      'Making remarks ', s)
    m = re.search(' (?:.\200\223 |- |\[|{|\()(?:The )?Secretary-General (?:to|will) (?:make|deliver) ' +
                  '([Oo]pening |closing )?[rR]emarm?ks(\]|}|\))?\.?$', s)
    if m:
        new = 'Making %sremarks at ' % (m.group(1) or '').lower()
        s = re.sub('^Addressing ', '', s)
        if not re.match('(?i)The ', s):
            new += 'the '
        return re.sub('^(.*) (?:.\200\223 |- |\[|{|\()(?:The )?Secretary-General (?:to|will) (?:make|deliver) ' +
                      '([Oo]pening |closing )?[rR]emarm?ks(\]|}|\))?', new + r'\1', s)
    if re.match('\[Remarks at\] ', s):
        return re.sub('\[Remarks at\] ', 'Making remarks at ', s)
    if (re.search('(?i)Presentation of credential', s) or re.match('Remarks at', s) or re.match('Election of', s)
            or re.match('Swearing[ -]in Ceremony', s)):
        pass
    elif (re.search('(?<!on )Youth$|^Sages Group|Messengers$|^Group of Friends|^Leaders|^Chairmen|' +
                    '^Permanent Representatives?|^Executive Secretaries|Board members|Contact Group|Envoys|Team$|' +
                    '^Honou?rable|Interns|Order|Board of Trustees|Journalists$|Committee( of the .*Parliament)$|' +
                    'Fellows$|^(UN )?Youth Delegates', s)
          and not re.search('(president|photo opportunity|concert|luncheon|breakfast|event)(?i)', s)
          and not re.match('Meeting of|Joint meeting|Mr', s)):
        s = 'Meeting the %s' % s
    elif re.match(r'- Mr|His (Royal|Serene) Highness|President|Association of|Vuk|Queen|Prince|Major-General|' +
                  'His Excellency|His Eminence|His Holiness|His Majesty|Her Majesty|Their Majesties|Ambassador\b|' +
                  'H\.?R\.?H|H\. ?M\.|H\. ?H\.|H\.? ?E\.?|S\. ?E\.|Rev\.|The Very Rev|Sir|General (?!Assembly)|' +
                  'H\.S\.H|\.?Mr\.?|Mrs\.|Prof\.|Dr\.?\b|Lord|Lady|Justice|Professor|Ms\.?|Amb\.?\b|Mayor|Messrs\.|' +
                  'Senator|(The )?R(igh)?t\.? Hon(ou?rable)?\.?|The Hon\.|Hon\.|U\.S\. House|U\.S\. Senator|' +
                  'US Congressman|Judge|Cardinal|Archbishop|The Honou?rable|Rabbi|Lt\.|Major General|Lieutenant|' +
                  'Excelent|Metropolitan|Psy|Thura|Lang Lang|Bahey|Antti|Bishop|Pastor|Shaykh|Srgjan|Michel|' +
                  'Commissioner', s) and not re.search('(?i)luncheon', s):
        s = re.sub('Amb\.', 'Ambassador', s)
        s = re.sub('^Amb ', 'Ambassador ', s)
        if re.match('The ', s):
            s = re.sub('^The', 'the', s)
        s = 'Meeting %s' % s
    elif (re.search('(?i)Delegation|Members', s)
            and not re.search('(?i)(Joint.*Meeting|Group Meeting|concert|luncheon|breakfast)', s)):
        s = 'Meeting the %s' % s
    elif (re.search(r'Elder|High Representative|Chairman\b|Secretary-General of the League|Senior Adviser|' +
                    'Special Adviser|Special Representative|Permanent Representative|Minister of|' +
                    'Secretary of State for|Administrator|CEO|National Adviser|Ambassador|students|Students', s) and
          not re.search('(?i)(concert|conversation|luncheon|breakfast|hosted by|hand-over|meeting|conference)', s)):
        s = 'Meeting %s' % s
    elif re.match('The ', s):
        s = re.sub('^The ', 'Attending the ', s)
    else:
        s = 'Attending the %s' % s
    return s


def parsecell(s, d=False):
    s = re.sub('^REV.1 ', '', s)
    s = re.sub('\xc2\xa0', ' ', s)
    s = re.sub(u'\xa0', ' ', s)
    if d:
        s = re.sub("<br />", ", ", s)
        s = re.sub("</p>", " ", s)
    s = re.sub("<[^>]*>", "", s)
    s = re.sub("&nbsp;", " ", s)
    s = re.sub("&quot;", '"', s)
    s = re.sub("\s+", " ", s)
    s = s.strip(" ")
    s = unescape(s)
    return s


def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(html.entities.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


SecgenBot('secgen').run()
