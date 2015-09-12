#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import re
from cStringIO import StringIO

from bs4 import BeautifulSoup, Comment
from twisted.web import proxy, http
from twisted.internet import reactor
from twisted.python import log


class ProxyClient(proxy.ProxyClient):
    word_re = re.compile(r'(?<=\b)(?<!-)([^\W\d_]{6})(?!-)(?=\b)', re.I + re.U)

    def __init__(self, command, rest, version, headers, data, father):
        headers['accept-encoding'] = 'identity'
        proxy.ProxyClient.__init__(self, command, rest, version, headers, data,
                                   father)
        self.is_html = False
        self.buffer = StringIO()

    def handleHeader(self, key, value):
        if key.lower() == 'content-type' and value.startswith('text/html'):
            self.is_html = True
        proxy.ProxyClient.handleHeader(self, key, value)

    def handleResponsePart(self, buffer):
        if self.is_html:
            self.buffer.write(buffer)
        else:
            self.father.write(buffer)

    def handleResponseEnd(self):
        if not self._finished and self.is_html:
            self.buffer.seek(0, 0)
            raw = self.buffer.read()
            self.buffer.truncate()
            output = ProxyClient._transform_content(raw)
            self.father.responseHeaders.setRawHeaders('Content-Length',
                                                      [str(len(output))])
            self.father.write(output)
        proxy.ProxyClient.handleResponseEnd(self)

    @classmethod
    def _transform_content(cls, raw):
        soup = BeautifulSoup(raw, 'lxml')
        for tag in soup.body.find_all(
                string=lambda s: not isinstance(s, Comment)):
            if tag.parent.name in ('script', 'noscript'):
                continue
            text = tag.string.strip()
            if text:
                text_with_tm = cls.word_re.sub(ur'\1™', text)
                tag.string.replace_with(text_with_tm)
        return ''.join(x.encode('utf-8') for x in soup.prettify())


class ProxyClientFactory(proxy.ProxyClientFactory):
    protocol = ProxyClient


class ProxyRequest(proxy.ProxyRequest):
    protocols = {'http': ProxyClientFactory}


class Proxy(proxy.Proxy):
    requestFactory = ProxyRequest


class ProxyFactory(http.HTTPFactory):
    protocol = Proxy


def main():
    log.startLogging(sys.stdout)
    reactor.listenTCP(8080, ProxyFactory(), interface='127.0.0.1')
    reactor.run()


if __name__ == '__main__':
    main()
