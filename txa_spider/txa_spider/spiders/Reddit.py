# -*- coding: utf-8 -*-
"""
Start aus dem Top-Level-Verzeichnis der Crawlers auf Kommandozeile durch
scrapy crawl <spider name>
"""

import scrapy
import logging
import re
import sys
import time
from datetime import datetime


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


class RedditSpider(scrapy.Spider):
	# Scrapy: Name des Spiders
	name = 'reddit'

	# Scrapy: Nur innerhalb dieser Domain wird gecrawlt (kein http davor!)
	allowed_domains = ['reddit.com']
	#The User Agent used in subsequent requests
	user_agent = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
	# Scrapy: Startseiten: Auf diesen wird begonnen
	start_urls = [
		"https://www.reddit.com/r/DotA2/",
		'https://www.reddit.com/r/GlobalOffensive/',
		'https://www.reddit.com/r/leagueoflegends/',
		'https://www.reddit.com/r/darksouls3/',
		'https://www.reddit.com/r/Witcher3/',
		'https://www.reddit.com/r/Smite/',
		'https://www.reddit.com/r/aoe4/',
		'https://www.reddit.com/r/unrealtournament/',
		'https://www.reddit.com/r/battlefield_one/',
		'https://www.reddit.com/r/FIFA/',
		'https://www.reddit.com/r/WorldofTanks/',
		'https://www.reddit.com/r/FortNiteBR/',
		'https://www.reddit.com/r/PUBATTLEGROUNDS/',
		'https://www.reddit.com/r/starcraft/',
		'https://www.reddit.com/r/RocketLeague/',
		'https://www.reddit.com/r/CallOfDuty/',
		'https://www.reddit.com/r/tf2/',
		'https://www.reddit.com/r/skyrim/',
		'https://www.reddit.com/r/wow/',
		'https://www.reddit.com/r/Guildwars2/',
		'https://www.reddit.com/r/silenthill/',
		'https://www.reddit.com/r/civ/',
		'https://www.reddit.com/r/StreetFighter/',
		'https://www.reddit.com/r/smashbros/',
		'https://www.reddit.com/r/Mario/',
		'https://www.reddit.com/r/Breath_of_the_Wild/',
		'https://www.reddit.com/r/farcry/',
		'https://www.reddit.com/r/pokemon/',
		'https://www.reddit.com/r/Tetris/',
		'https://www.reddit.com/r/heroesofthestorm/',
		'https://www.reddit.com/r/Tekken/',
		'https://www.reddit.com/r/assassinscreed/',
		'https://www.reddit.com/r/mariokart/',
		'https://www.reddit.com/r/granturismo/',
		'https://www.reddit.com/r/forza/',
		'https://www.reddit.com/r/HeroesofNewerth/',
		'https://www.reddit.com/r/Minecraft/',
		'https://www.reddit.com/r/hearthstone/',
		'https://www.reddit.com/r/Terraria/',
		'https://www.reddit.com/r/halo/',
		'https://www.reddit.com/r/GodofWar/',
		'https://www.reddit.com/r/Kirby/',
		'https://www.reddit.com/r/gtaonline/',
		'https://www.reddit.com/r/Wolfenstein/'
	]

	# Scrapy: Steuerung des Log-Levels
	custom_settings = {
		# WARNING, INFO, DEBUG
		'LOG_LEVEL': 'INFO',
	}

	
	#sets the depth of the spider, has to be a multiple of 25, if it is not, the next multiple of 25 is used
	max_reddit_count = 100

	def parse(self, response):
		"""
		Parse-Callback for main pages, yields the Thread Pages
		Follows Link to next page if max_reddit_count not reached
		:param response:
		:return:
		"""

		logging.getLogger().info("VISITING PAGE " + response.url)
		#Find count value to termiante if needed
		find_count = re.findall("\?count=([0-9]+)",response.url)
		if(len(find_count) > 0):
			count = int(find_count[0])
			if(count >= self.max_reddit_count):
				return

		# Exception handling
		try:
			for thread in response.css("a.comments::attr(href)").extract():
				yield response.follow(thread, callback=self.parse_comments)

				next_page = response.css("span.next-button > a::attr(href)").extract_first()

				if next_page is not None:
					yield response.follow(next_page, callback=self.parse,headers={ "user-agent": self.user_agent })

		except:
			e = sys.exc_info()
			logging.getLogger().warning("Problems with PAGE" + response.url)
			logging.getLogger().warning(e)
	
	def parse_comments(self,response):
		"""
		Parse-Callback for thrads, yields the User Pages
		Yields comment-items
		:param response:
		:return:
		"""
		title = response.css("a.title::text").extract_first()	
		logging.getLogger().info("VISITING THREAD " + title)
		game = re.findall("https://www.reddit.com/r/([a-zA-Z0-9_-]+)/",response.url)[0]
		for comment in response.css("div.comment"):
			user = comment.css("div.entry > p.tagline > a.author::text").extract_first()
			user_link = comment.css("div.entry > p.tagline > a.author::attr(href)").extract_first()
			yield response.follow(user_link, callback=self.parse_user,headers={ "user-agent": self.user_agent })			
			
			points = comment.css("span.score::attr(title)").extract_first()
			if(not points):
				points = "0"
			points = int(points)
			try:
				full_comment = comment.css("div.usertext-body > div.md")[0]
				text = " ".join(full_comment.css("p::text").extract())
				text = re.sub('\s+',' ',text)
				text = re.sub(r'\\u[a-zA-Z0-9]{4}','',text)
				yield dict(game=game,
				score=points,
				thread=title,
				user=user,
				#url=response.url,
				content=text,
				table_type='comments'
				)
			except:
				e = sys.exc_info()
				logging.getLogger().warning("Problems with COMMENT" + title)
				logging.getLogger().warning(e)
			
	def parse_user(self,response):
		"""
		Parse-Callback for user pages, yields a user item
		:param response:
		:return:
		"""
		findname = response.css("a.ProfileSidebar__nameTitleLink::text").extract_first()
		if(findname):
			name = re.findall("u/(.*)",findname)[0]
			logging.getLogger().info("VISITING USER " + name)
			birthday = response.css("div.UserSpecialsListSidebar > div > ul > li > span.UserSpecialsListSidebar__date::text").extract_first()
			birthday = str(datetime.strptime(birthday, '%B %d, %Y'))
			karma = int(re.sub(r"[., ]|Karma","",str(response.css("div.ProfileSidebar__counters > span >span::text").extract_first())))
			yield dict(name=name,
			birthday=birthday,
			karma = karma,
			table_type='users'
			)
		else:
			name = response.css("div.titlebox > h1::text").extract_first()
			if( not name):
				return #ignore this user, this can occur due to +18 rating of the user
			birthday = response.css("span.age > time::attr(datetime)").extract_first()
			birthday = str(datetime.strptime(birthday, '%Y-%m-%dT%H:%M:%S+00:00'))
			karma_post = int(re.sub(r",","",response.css("span.karma::text").extract_first()))
			karma_comment = int(re.sub(r",","",response.css("span.comment-karma::text").extract_first()))
			yield dict(name=name,
			birthday=birthday,
			karma = karma_post + karma_comment,
			table_type='users'
			)