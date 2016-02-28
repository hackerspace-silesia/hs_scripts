# -*- coding: utf-8 -*-
# Credits: Some code is based on: https://github.com/firemark/grazyna/blob/master/grazyna/plugins/hs_wiki.py
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import re

import dateparser
from lxml.html import fromstring as fromstring_to_html
import requests


URL = 'https://wiki.hs-silesia.pl/wiki'
URL_MEETS = '%s/Planowane_spotkania' % URL
LIST_XPATH = '//span[starts-with(@id,$id)]/../following-sibling::ul[1]/li'
MEETS_ID = "Najbli.C5.BCsze_spotkania_tematyczne"

re_date_range = re.compile(r"(\d\d+?)\s*-\s*(\d\d?)")
re_every = re.compile(r"^[Kk]a[żz]d[yaą]")


MESSAGE_TMPL = '''Hej,

W najbliższym tygodniu w naszym HSie odbędą się następujące spotkania:

{}

Poza tym zapraszamy wszystkich na "dzień otwarty" w każdy czwartek od godz. 18:00.

Lista wszystkich spotkań planowanych i odbytych znajduje się na wiki: https://wiki.hs-silesia.pl/wiki/Planowane_spotkania

Pozdrawiam
HSowy bot
'''


def get_html(url):
    raw_data = requests.get(url, verify=False)
    return fromstring_to_html(raw_data.text)


def parse_date(text):
    text = re_date_range.sub(r'\2', text)
    raw_date, _, _ = text.partition('-')
    raw_date = raw_date.strip()
    raw_date = re_every.sub('', raw_date)
    parsed = dateparser.parse(raw_date)
    return parsed.date() if parsed else None


def show_events(from_date, to_date):
    label = MEETS_ID
    html = get_html(URL_MEETS)
    nodes = html.xpath(LIST_XPATH, id=label)
    nodes = (node.text_content().strip() for node in nodes)

    parsed_nodes = ((node, parse_date(node))
             for node in nodes if node)
    list_data = sorted(
        (
            (text, date) for text, date in parsed_nodes
                if date is not None and from_date < date <= to_date
        )
    )
    return [text for text, date in list_data]


def next_weekday(weekday):
    d = datetime.date.today()
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


def send_mail():
    events = show_events(datetime.date.today(), next_weekday(6)) # 6 - sunday
    if not events:
        return
    events = ('- {}'.format(event) for event in events)
    events = '\n'.join(events)

    user = os.environ['BOT_MAIL_USER']
    password = os.environ['BOT_MAIL_PASSWORD']
    dest_address = os.environ['BOT_DEST_ADDRESS']

    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = dest_address
    msg['Subject'] = "Lista spotkań w najbliższym tygodniu"

    body = MESSAGE_TMPL.format(events)
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP_SSL('ssl0.ovh.net', 465)
    #server = smtplib.SMTP('smtp.hs-silesia.pl', 587)
    server.login(user, password)

    server.send_message(msg)
    server.quit()


if __name__ == '__main__':
    send_mail()
