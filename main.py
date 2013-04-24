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
  pubDate = getText(item.getElementsByTagName('pubDate')[0].childNodes)
  return datetime.datetime.fromtimestamp(email.utils.mktime_tz(email.utils.parsedate_tz(pubDate)))

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
  except:
    pass
  return xml

def tweetItem(feedTitle, title, link):
  auth = tweepy.OAuthHandler(twitter_token.CONSUMER_KEY, twitter_token.CONSUMER_SECRET)
  auth.set_access_token(twitter_token.ACCESS_KEY, twitter_token.ACCESS_SECRET)
  api = tweepy.API(auth)
  api.update_status(feedTitle + ' > ' + title + ' ' + link)


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
    'http://www.webmonkey.com/feed/'
  ]

  for feed in feeds:
    Feed(url=feed, last_check=datetime.datetime.now()).put()


class CheckFeedsHandler(webapp2.RequestHandler):
  def get(self):
    feeds = Feed.all()
    
    if feeds.count() == 0:
      init_db()

    for feed in feeds:
      xml = getRssDocFromURL(feed.url)
      if xml:
        items = xml.getElementsByTagName('item')
        title = getRssTitle(xml)
        
        for item in items:
          pubDateTime = getRssItemPubDateTime(item)
          if pubDateTime > feed.last_check:
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
