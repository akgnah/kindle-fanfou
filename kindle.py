#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import re
import os
import time
import poplib
import shelve
from email.parser import Parser
from email.header import decode_header

import fanfou

poplib._MAXLINE = 20480
curdir = os.path.dirname(os.path.abspath(__file__))
db = shelve.open(os.path.join(curdir, 'kindle-sent'))


class Inbox:
    def __init__(self, server, user, pass_):
        self.conn = poplib.POP3_SSL(server)
        self.conn.user(user)
        self.conn.pass_(pass_)
        self.mails = []
        self.inbox = []

    def fetch(self):
        resp, mails, octets = self.conn.uidl()
        mail_ids = [mail.split(' ')[1] for mail in mails]
        for mail_id in mail_ids:
            if not db.get(mail_id):
                pos = mail_ids.index(mail_id) + 1
                resp, lines, octets = self.conn.retr(pos)
                self.mails.append({'mail_id': mail_id, 'mail': '\r\n'.join(lines)})
        self.conn.quit()
        for mail in self.mails:
            self.parse(mail)
        return self.inbox

    def parse(self, mail):
        msg = Parser().parsestr(mail.get('mail'))
        text = None
        for part in msg.walk():
            if not part.is_multipart():
                if part.get_content_type() in ('text/plain', 'text/html'):
                    content = part.get_payload(decode=True)
                    charset = self.get_charset(part)
                    if charset:
                        content = content.decode(charset)
        templates = (
            u'Hi, I\'m reading this book, and wanted to share this quote with you\.[\r\n]+"([\s\S]+)" \(by',
            u'Hi, I\'m reading this book, and wanted to share this quote with you\.[\r\n]+"([\s\S]+)" \(from',
            u'Hi, I\'m reading this book, and wanted to share this quote with you\.[\r\n]+《([\s\S]+)》\(摘自由',
            u'您好，我觉得这本书值得一读，您怎么看？[\r\n]+"([\s\S]+)" by',
            u'嗨，我正在读这本书，想跟您分享一句名言。[\r\n]+"([\s\S]+)" \(from',
            u'嗨，我正在读这本书，想跟您分享一句名言。[\r\n]+《([\s\S]+)》\(摘自由',
        )
        for template in templates:
            matching = re.search(template, content)
            if matching:
                text = matching.group(1)
                break
        if text:
            self.inbox.append({'text': text, 'mail_id': mail['mail_id']})

    def get_charset(self, msg):
        charset = msg.get_charset()
        if charset is None:
            content_type = msg.get('Content-Type', '').lower()
            pos = content_type.find('charset=')
            if pos >= 0:
                charset = content_type[pos + 8:].strip()
        return charset

    def decode_str(self, s):
        value, charset = decode_header(s)[0]
        if charset:
            value = value.decode(charset)
        return value


if __name__ == '__main__':
    server = 'pop.qq.com'    # 邮箱 pop3 服务地址
    user = 'xxxxxx@qq.me'    # 邮箱地址
    pass_ = 'qwertyuiopz'    # 授权码
    consumer = {'key': '3a88d9337021d6589defce1879060d75',
                'secret': 'd5493ec89b9d9a6fa6578ca0a673d00c'}    # 你的 Consumer

    client = fanfou.XAuth(consumer, 'username', 'password')      # 你的用户名和密码
    fanfou.bound(client)

    for mail in Inbox(server, user, pass_).fetch():
        print 'update {0}'.format(mail['mail_id'])
        client.statuses.update({'status': mail['text']})
        db[mail['mail_id']] = 1
        time.sleep(0.5)
