import email.utils
import datetime
import logging
import webapp2
from google.appengine.ext import db
from google.appengine.api import urlfetch
from xml.dom.minidom import parseString
import tweepy
import twitter_token


def getText(nodelist):
  rc = []
  for node in nodelist:
    if node.nodeType == node.TEXT_NODE:
      rc.append(node.data)
  return ''.join(rc)

def getRssItemPubDateTime(item):
  pubDates = item.getElementsByTagName('pubDate')
  if len(pubDates) > 0:
    pubDate = getText(item.getElementsByTagName('pubDate')[0].childNodes)
    return datetime.datetime.fromtimestamp(email.utils.mktime_tz(email.utils.parsedate_tz(pubDate)))
  else:
    return None

def getRssItemTitle(item):
  return getText(item.getElementsByTagName('title')[0].childNodes)

def getRssItemLink(item):
  return getText(item.getElementsByTagName('link')[0].childNodes)

def getRssTitle(xml):
  return getText(xml.getElementsByTagName('title')[0].childNodes)

def getRssDocFromURL(url):
  logging.info('Fetching RSS xml from ' + url)
  xml = None
  # This can fail for a number of reasons: mal-formed XML, unresponsive server, ... 
  try:
    response = urlfetch.fetch(url)
    xml = parseString(response.content)
  except Exception as ex:
    logging.error('could not retrieve or parse content from ' + url)
  return xml

def tweetItem(feedTitle, title, link):
  # title = 140 max - 20 (url) - feedTitle length - 5 separation chars
  title = title[0:140 - 20 - len(feedTitle) - 5]
  message = feedTitle + ' > ' + title + ' ' + link
  
  logging.info('Tweeting message [' + message + ']')

  try:
    auth = tweepy.OAuthHandler(twitter_token.CONSUMER_KEY, twitter_token.CONSUMER_SECRET)
    auth.set_access_token(twitter_token.ACCESS_KEY, twitter_token.ACCESS_SECRET)
    api = tweepy.API(auth)
    api.update_status(message)
  except Exception as ex:
    logging.error('Could not tweet message [' + message + ']')


class Feed(db.Model):
  url = db.StringProperty(required=True)
  last_check = db.DateTimeProperty(required=True)


def init_db():
  feeds = [
    'http://feeds.feedburner.com/adequatelygood',
    'http://www.alertdebugging.com/feed/',
    'http://rss.badassjs.com/',
    'http://feeds.feedburner.com/chrisheilmann',
    'http://feeds.feedburner.com/codinghorror/',
    'http://feeds.feedburner.com/CssTricks',
    'http://feeds.feedburner.com/Bludice',
    'http://feeds.feedburner.com/WSwI',
    'http://feeds.feedburner.com/html5rocks',
    'http://blogs.msdn.com/b/ie/rss.aspx',
    'http://hacks.mozilla.org/feed/',
    'http://feeds.feedburner.com/nczonline ',
    'http://feeds.feedburner.com/PerfectionKills',
    'http://feeds.feedburner.com/SoftwareIsHard',
    'http://www.webmonkey.com/feed/',
    'http://feeds.feedburner.com/alistapart/main'
  ]

  for feed in feeds:
    # If feed not already in the DB, add it now
    if len(Feed.all().filter("url =", feed).fetch(1)) == 0:
      Feed(url=feed, last_check=datetime.datetime.now()).put()


class CheckFeedsHandler(webapp2.RequestHandler):
  def get(self):
    init_db()

    for feed in Feed.all():
      xml = getRssDocFromURL(feed.url)
      if xml:
        items = xml.getElementsByTagName('item')
        title = getRssTitle(xml)
        
        for item in items:
          pubDateTime = getRssItemPubDateTime(item)
          if pubDateTime and pubDateTime > feed.last_check:
            tweetItem(title, getRssItemTitle(item), getRssItemLink(item))
        
        feed.last_check = datetime.datetime.now()
        feed.put()

    self.response.write('done!')


class MainHandler(webapp2.RequestHandler):
  def get(self):
    self.response.write('Nothing to see here')


app = webapp2.WSGIApplication([
  ('/checkfeeds', CheckFeedsHandler),
  ('/', MainHandler)
], debug=True)
