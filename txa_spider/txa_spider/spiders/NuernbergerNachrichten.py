# -*- coding: utf-8 -*-
"""
Run from project's toplevel directory with
scrapy crawl NN
"""

import scrapy
import logging
import re
from datetime import datetime
from datetime import timedelta
import sys


def parse_int(s, base=10, val=None):
    """
    Hilfsmethode für das fehlertolerante Parsen von Integers.
    :param s:
    :param base:
    :param val:
    :return:
    """
    if s.isdigit():
        return int(s, base)
    else:
        return val


class NNSpider(scrapy.Spider):
    """
    Scrapy Spider für Nürnberger Nachrichten
    Die Feld-Namen der Klasse sind größtenteils von scrapy.Spider geerbt und damit vorgegeben.
    Siehe Scrapy Doku https://doc.scrapy.org/en/latest/topics/spiders.html
    """

    # Scrapy: Name des Spiders
    name = 'nn'

    # Scrapy: Nur innerhalb dieser Domain wird gecrawlt
    allowed_domains = ['www.nordbayern.de']

    # Scrapy: Startseiten: Auf diesen wird begonnen
    start_urls = [
        #"http://www.nordbayern.de/",
        "http://www.nordbayern.de/politik",
        "http://www.nordbayern.de/wirtschaft",
        "http://www.nordbayern.de/kultur",
        "http://www.nordbayern.de/region",
        "http://www.nordbayern.de/sport",
        # "http://www.nordbayern.de/amateurfu%C3%9Fball",
        # "http://www.nordbayern.de/freizeit-events",
        # "http://www.nordbayern.de/essen-trinken/gastro-guide",
        # "http://www.nordbayern.de/termine/veranstaltungen",
        "http://www.nordbayern.de/panorama",
        # "http://www.nordbayern.de/spiele"
    ]

    # Scrapy: Steuerung des Log-Levels
    custom_settings = {
        # WARNING, INFO, DEBUG
        'LOG_LEVEL': 'INFO',
    }

    # Eigener Wert zum Eexperimentieren: steuert, wie viele "Next Pages" verfolgt werden
    max_next_pages = 3

    def parse(self, response):
        """
        Parse-Callback von Scrapy
        Wird standardmäßig beim Besuchen einer Seite aufgerufen
        :param response:
        :return:
        """

        # Extrahiere Links auf Artikel
        # Set-Objekt wird für Eindeutigkeit verwendet, da Links mehrfach
        # auf einer Seite auftreten können
        article_links = set()
        for href in response.css("section.grid_40 p.teaser a"):
            text = href.css('::text').extract_first()
            if text == '[mehr...]':
                article_links.add(href.css('a::attr(href)').extract_first())

        # Folge den Artikel-Links
        for link in article_links:
            # logging.getLogger().info("Article link " + link)
            yield response.follow(link, callback=self.parse_article)

        # Extrahiere Link auf die Nachfolge-Seite ("Next") und folge ihm
        # sofern noch nicht max_next_pages erreicht ist
        next_link, page_num = NNSpider.get_next_link(response)
        if next_link and page_num <= self.max_next_pages:
            logging.getLogger().info("Next link " + next_link)
            yield response.follow(next_link, callback=self.parse)

    def parse_article(self, response):
        """
        Parse-Callback für Artikel zur Extraktion der Artikel-Texte
        :param response: Scrapy Response
        :return:
        """

        page_type = response.css("meta[property='og:type']::attr(content)").extract_first()

        if page_type == 'article':
            try:
                # URL bestimmen (wird später für richtige Implementierung benötigt)
                url = response.url
                logging.getLogger().info("Parsing " + url)

                # Category bestimmen
                category = response.css("ul.nav li.selnav a::text").extract_first()

                # Titel bestimmen
                title = response.css("div.article-content h1::text").extract_first()

                # Artikel-Teaser und Ort extrahieren
                teaser = " ".join(response.css("div.article-content p.article-teaser::text").extract())
                teaser = teaser.strip('\n\t -')

                place = response.css("div.article-content p.article-teaser span::text").extract_first()
                place = place.strip('\n\t -')

                # Untertitel extrahieren
                subtitle = response.css("div.article-content p.article-dachzeile::text").extract_first()
                subtitle = subtitle.strip(' \n\t-')

                # Autor extrahieren
                author = response.css("div.article-content p.autor span::text").extract_first()

                # Text extrahieren
                text = " ".join(response.css("div.article-content > p:not([class]) *::text").extract())
                # Zerrissene Tokens wie "Nato -Staaten" wieder zusammmensetzen.
                text = text.replace(' -', '-')
                # Wiederholungen von Whitespaces durch Leehrzeichen ersetzen
                text = re.sub('\s+', ' ', text)
                text = text.strip(' \n')

                # Datum extrahieren
                created_at = response.css("div.article-content p.article-dachzeile span::text").extract_first()
                # Versuch das Format "vor XXX Stunden/Minuten" zu erkennen
                match = re.search(r"vor ([0-9]+) ([A-Za-z]+)", created_at)
                if match:  # wenn relatives Format erkannt
                    dt = datetime.now()
                    if match.group(2) in ["Stunden", "Stunde"]:
                        dt -= timedelta(hours=int(match.group(1)))
                    else:
                        dt -= timedelta(minutes=int(match.group(1)))
                else:  # absolutes Format
                    dt = datetime.strptime(created_at, '%d.%m.%Y\xa0%H:%M\xa0Uhr')
                created_at = datetime.strftime(dt, '%Y-%m-%d %H:%M:%S')

                item = dict(table_type='nn_article',
                            category=category,
                            title=title,
                            subtitle=subtitle,
                            teaser=teaser,
                            text=text,
                            author=author,
                            created_at=created_at)

                yield item

            except:
                e = sys.exc_info()
                logging.getLogger().warning("Problems with " + response.url)
                logging.getLogger().warning(e)

    @staticmethod
    def get_next_link(response):
        """
        Extrahiert den Link auf die nächste Seite von einer Überblicksseite,
        z.B. http://www.nordbayern.de/politik

        As the link is generated by JavaScript/JQuery function, it cannot simply be
        extracted but must be constructed from the javascript logic.

        The returned URL only requests the AJAX update to the current page, e.g.
        http://www.nordbayern.de/cmlink/innenpolitik-7.2447402?offset=1&siteId=2.244

        :param response
        :return: link auf nächste Seite
        """

        # Extraktion der Onclick-Aktion, z.B. onclick="clickNumPage_72447402('1')"
        next_onclick = response.xpath(
            '(//div[contains(@class, "pager")])[1]//a//i[@class="icon-forward"]/../../@onclick').extract_first()

        # wenn es die letzte Seite ist ...
        if not next_onclick:
            return None, None

        # Extraktion des Funktionsnames und des Parameters, z.B. 'clickNumPage_72447402' and '1'
        match = re.match(r"(.*)\('(.*)'\)", next_onclick)
        js_func = match.group(1)
        js_func_param = match.group(2)

        # Suche nach der JavaScript-Funktion im Code
        for script in response.css('script::text').extract():
            if js_func in script:
                break

        # extract url from javascript function code
        match = re.search(r'url: "(.*)"', script)
        url = match.group(1)

        # Extraktion der URL aus dem JavaScript code
        match = re.search(r'url: "(.*)"', script)
        url = match.group(1)

        # Extraktion der Parameter
        match = re.search(r'data: (".*")', script)
        data = match.group(1)

        # Aufbau des Links
        next_link = url + "?" + eval(data, {"index": js_func_param})

        return next_link, parse_int(js_func_param)
