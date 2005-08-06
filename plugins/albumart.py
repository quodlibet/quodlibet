#Copyright 2005 Eduardo Gonzalez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import gtk, gobject
import util
import qltk
import config
import urllib
import tempfile

PLUGIN_NAME = "Download Album art"
PLUGIN_DESC = "Downloads album covers from Amazon.com"
PLUGIN_ICON = gtk.STOCK_FIND
PLUGIN_VERSION = "0.13"

#amazon.py
"""Python wrapper


for Amazon web APIs

This module allows you to access Amazon's web APIs,
to do things like search Amazon and get the results programmatically.
Described here:
  http://www.amazon.com/webservices

You need a Amazon-provided license key to use these services.
Follow the link above to get one.  These functions will look in
several places (in this order) for the license key:
- the "license_key" argument of each function
- the module-level LICENSE_KEY variable (call setLicense once to set it)
- an environment variable called AMAZON_LICENSE_KEY
- a file called ".amazonkey" in the current directory
- a file called "amazonkey.txt" in the current directory
- a file called ".amazonkey" in your home directory
- a file called "amazonkey.txt" in your home directory
- a file called ".amazonkey" in the same directory as amazon.py
- a file called "amazonkey.txt" in the same directory as amazon.py

Sample usage:
>>> import amazon
>>> amazon.setLicense('...') # must get your own key!
>>> pythonBooks = amazon.searchByKeyword('Python')
>>> pythonBooks[0].ProductName
u'Learning Python (Help for Programmers)'
>>> pythonBooks[0].URL
...
>>> pythonBooks[0].OurPrice
...

Other available functions:
- browseBestSellers
- searchByASIN
- searchByUPC
- searchByAuthor
- searchByArtist
- searchByActor
- searchByDirector
- searchByManufacturer
- searchByListMania
- searchSimilar
- searchByWishlist

Other usage notes:
- Most functions can take product_line as well, see source for possible values
- All functions can take type="lite" to get less detail in results
- All functions can take page=N to get second, third, fourth page of results
- All functions can take license_key="XYZ", instead of setting it globally
- All functions can take http_proxy="http://x/y/z" which overrides your system setting
"""

__author__ = "Mark Pilgrim (f8dy@diveintomark.org)"
__version__ = "0.64.1"
__cvsversion__ = "$Revision: 1.4 $"[11:-2]
__date__ = "$Date: 2005/01/30 18:35:10 $"[7:-2]
__copyright__ = "Copyright (c) 2002 Mark Pilgrim"
__license__ = "Python"
# Powersearch and return object type fix by Joseph Reagle <geek@goatee.net>

# Locale support by Michael Josephson <mike@josephson.org>

# Modification to _contentsOf to strip trailing whitespace when loading Amazon key
# from a file submitted by Patrick Phalen.

# Support for specifying locale and associates ID as search parameters and 
# internationalisation fix for the SalesRank integer conversion by
# Christian Theune <ct@gocept.com>, gocept gmbh & co. kg

# Support for BlendedSearch contributed by Alex Choo

from xml.dom import minidom
import os, sys, getopt, cgi, urllib, string
try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(10)
except ImportError:
    pass

LICENSE_KEY = "0RKH4ZH1JCFZHMND91G2"
ASSOCIATE = "webservices-20"
HTTP_PROXY = None
LOCALE = "us"

# don't touch the rest of these constants
class AmazonError(Exception): pass
class NoLicenseKey(Exception): pass
_amazonfile1 = ".amazonkey"
_amazonfile2 = "amazonkey.txt"
_licenseLocations = (
    (lambda key: key, 'passed to the function in license_key variable'),
    (lambda key: LICENSE_KEY, 'module-level LICENSE_KEY variable (call setLicense to set it)'),
    (lambda key: os.environ.get('AMAZON_LICENSE_KEY', None), 'an environment variable called AMAZON_LICENSE_KEY'),
    (lambda key: _contentsOf(os.getcwd(), _amazonfile1), '%s in the current directory' % _amazonfile1),
    (lambda key: _contentsOf(os.getcwd(), _amazonfile2), '%s in the current directory' % _amazonfile2),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _amazonfile1), '%s in your home directory' % _amazonfile1),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _amazonfile2), '%s in your home directory' % _amazonfile2),
    (lambda key: _contentsOf(_getScriptDir(), _amazonfile1), '%s in the amazon.py directory' % _amazonfile1),
    (lambda key: _contentsOf(_getScriptDir(), _amazonfile2), '%s in the amazon.py directory' % _amazonfile2)
    )
_supportedLocales = {
        "us" : (None, "xml.amazon.com"),   
        "uk" : ("uk", "xml-eu.amazon.com"),
        "de" : ("de", "xml-eu.amazon.com"),
        "jp" : ("jp", "xml.amazon.co.jp")
    }

## administrative functions
def version():
    print """PyAmazon %(__version__)s
%(__copyright__)s
released %(__date__)s
""" % globals()

def setAssociate(associate):
    global ASSOCIATE
    ASSOCIATE=associate

def getAssociate(override=None):
    return override or ASSOCIATE

## utility functions

def _checkLocaleSupported(locale):
    if not _supportedLocales.has_key(locale):
        raise AmazonError, ("Unsupported locale. Locale must be one of: %s" %
            string.join(_supportedLocales, ", "))

def setLocale(locale):
    """set locale"""
    global LOCALE
    _checkLocaleSupported(locale)
    LOCALE = locale

def getLocale(locale=None):
    """get locale"""
    return locale or LOCALE

def setLicense(license_key):
    """set license key"""
    global LICENSE_KEY
    LICENSE_KEY = license_key

def getLicense(license_key = None):
    """get license key

    license key can come from any number of locations;
    see module docs for search order"""
    for get, location in _licenseLocations:
        rc = get(license_key)
        if rc: return rc
    raise NoLicenseKey, 'get a license key at http://www.amazon.com/webservices'

def setProxy(http_proxy):
    """set HTTP proxy"""
    global HTTP_PROXY
    HTTP_PROXY = http_proxy

def getProxy(http_proxy = None):
    """get HTTP proxy"""
    return http_proxy or HTTP_PROXY

def getProxies(http_proxy = None):
    http_proxy = getProxy(http_proxy)
    if http_proxy:
        proxies = {"http": http_proxy}
    else:
        proxies = None
    return proxies

def _contentsOf(dirname, filename):
    filename = os.path.join(dirname, filename)
    if not os.path.exists(filename): return None
    fsock = open(filename)
    contents =  fsock.read().strip()
    fsock.close()
    return contents

def _getScriptDir():
    if __name__ == '__main__':
        return os.path.abspath(os.path.dirname(sys.argv[0]))
    else:
        return os.path.abspath(os.path.dirname(sys.modules[__name__].__file__))

class Bag: pass

def unmarshal(element):
    rc = Bag()
    if isinstance(element, minidom.Element) and (element.tagName == 'Details'):
        rc.URL = element.attributes["url"].value
    childElements = [e for e in element.childNodes if isinstance(e, minidom.Element)]
    if childElements:
        for child in childElements:
            key = child.tagName
            if hasattr(rc, key):
                if type(getattr(rc, key)) <> type([]):
                    setattr(rc, key, [getattr(rc, key)])
                setattr(rc, key, getattr(rc, key) + [unmarshal(child)])
            elif isinstance(child, minidom.Element) and (child.tagName == 'Details'):
                # make the first Details element a key
                setattr(rc,key,[unmarshal(child)])
                #dbg: because otherwise 'hasattr' only tests
                #dbg: on the second occurence: if there's a
                #dbg: single return to a query, it's not a
                #dbg: list. This module should always
                #dbg: return a list of Details objects.
            else:
                setattr(rc, key, unmarshal(child))
    else:
        rc = "".join([e.data for e in element.childNodes if isinstance(e, minidom.Text)])
        if element.tagName == 'SalesRank':
            rc = rc.replace('.', '')
            rc = rc.replace(',', '')
            rc = int(rc)
    return rc

def buildURL(search_type, keyword, product_line, type, page, license_key, locale, associate):
    _checkLocaleSupported(locale)
    url = "http://" + _supportedLocales[locale][1] + "/onca/xml3?f=xml"
    url += "&t=%s" % associate
    url += "&dev-t=%s" % license_key.strip()
    url += "&type=%s" % type
    if _supportedLocales[locale][0]:
        url += "&locale=%s" % _supportedLocales[locale][0]
    if page:
        url += "&page=%s" % page
    if product_line:
        url += "&mode=%s" % product_line
    url += "&%s=%s" % (search_type, urllib.quote(keyword))
    return url


## main functions


def search(search_type, keyword, product_line, type = "heavy", page = None,
           license_key=None, http_proxy = None, locale = None, associate = None):
    """search Amazon

    You need a license key to call this function; see
    http://www.amazon.com/webservices
    to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.

    Parameters:
    keyword - keyword to search
    search_type - in (KeywordSearch, BrowseNodeSearch, AsinSearch, UpcSearch, AuthorSearch, ArtistSearch, ActorSearch, DirectorSearch, ManufacturerSearch, ListManiaSearch, SimilaritySearch)
    product_line - type of product to search for.  restrictions based on search_type
        UpcSearch - in (music, classical)
        AuthorSearch - must be "books"
        ArtistSearch - in (music, classical)
        ActorSearch - in (dvd, vhs, video)
        DirectorSearch - in (dvd, vhs, video)
        ManufacturerSearch - in (electronics, kitchen, videogames, software, photo, pc-hardware)
    http_proxy (optional) - address of HTTP proxy to use for sending and receiving SOAP messages

    Returns: list of Bags, each Bag may contain the following attributes:
      Asin - Amazon ID ("ASIN" number) of this item
      Authors - list of authors
      Availability - "available", etc.
      BrowseList - list of related categories
      Catalog - catalog type ("Book", etc)
      CollectiblePrice - ?, format "$34.95"
      ImageUrlLarge - URL of large image of this item
      ImageUrlMedium - URL of medium image of this item
      ImageUrlSmall - URL of small image of this item
      Isbn - ISBN number
      ListPrice - list price, format "$34.95"
      Lists - list of ListMania lists that include this item
      Manufacturer - manufacturer
      Media - media ("Paperback", "Audio CD", etc)
      NumMedia - number of different media types in which this item is available
      OurPrice - Amazon price, format "$24.47"
      ProductName - name of this item
      ReleaseDate - release date, format "09 April, 1999"
      Reviews - reviews (AvgCustomerRating, plus list of CustomerReview with Rating, Summary, Content)
      SalesRank - sales rank (integer)
      SimilarProducts - list of Product, which is ASIN number
      ThirdPartyNewPrice - ?, format "$34.95"
      URL - URL of this item
    """
    license_key = getLicense(license_key)
    locale = getLocale(locale)
    associate = getAssociate(associate)
    url = buildURL(search_type, keyword, product_line, type, page, 
            license_key, locale, associate)
    proxies = getProxies(http_proxy)
    u = urllib.FancyURLopener(proxies)
    usock = u.open(url)
    xmldoc = minidom.parse(usock)

#     from xml.dom.ext import PrettyPrint
#     PrettyPrint(xmldoc)

    usock.close()
    if search_type == "BlendedSearch":
        data = unmarshal(xmldoc).BlendedSearch
    else:    
        data = unmarshal(xmldoc).ProductInfo        
        
    if hasattr(data, 'ErrorMsg'):
        raise AmazonError, data.ErrorMsg
    else:
        if search_type == "BlendedSearch":
            # a list of ProductLine containing a list of ProductInfo
            # containing a list of Details.
            return data 
        else:            
            return data.Details

def searchByKeyword(keyword, product_line="books", type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("KeywordSearch", keyword, product_line, type, page, license_key, http_proxy, locale, associate)

def browseBestSellers(browse_node, product_line="books", type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("BrowseNodeSearch", browse_node, product_line, type, page, license_key, http_proxy, locale, associate)

def searchByASIN(ASIN, type="heavy", license_key=None, http_proxy=None, locale=None, associate=None):
    return search("AsinSearch", ASIN, None, type, None, license_key, http_proxy, locale, associate)

def searchByUPC(UPC, type="heavy", license_key=None, http_proxy=None, locale=None, associate=None):
    return search("UpcSearch", UPC, None, type, None, license_key, http_proxy, locale, associate)

def searchByAuthor(author, type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("AuthorSearch", author, "books", type, page, license_key, http_proxy, locale, associate)

def searchByArtist(artist, product_line="music", type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    if product_line not in ("music", "classical"):
        raise AmazonError, "product_line must be in ('music', 'classical')"
    return search("ArtistSearch", artist, product_line, type, page, license_key, http_proxy, locale, associate)

def searchByActor(actor, product_line="dvd", type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    if product_line not in ("dvd", "vhs", "video"):
        raise AmazonError, "product_line must be in ('dvd', 'vhs', 'video')"
    return search("ActorSearch", actor, product_line, type, page, license_key, http_proxy, locale, associate)

def searchByDirector(director, product_line="dvd", type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    if product_line not in ("dvd", "vhs", "video"):
        raise AmazonError, "product_line must be in ('dvd', 'vhs', 'video')"
    return search("DirectorSearch", director, product_line, type, page, license_key, http_proxy, locale, associate)

def searchByManufacturer(manufacturer, product_line="pc-hardware", type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    if product_line not in ("electronics", "kitchen", "videogames", "software", "photo", "pc-hardware"):
        raise AmazonError, "product_line must be in ('electronics', 'kitchen', 'videogames', 'software', 'photo', 'pc-hardware')"
    return search("ManufacturerSearch", manufacturer, product_line, type, page, license_key, http_proxy, locale, associate)

def searchByListMania(listManiaID, type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("ListManiaSearch", listManiaID, None, type, page, license_key, http_proxy, locale, associate)

def searchSimilar(ASIN, type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("SimilaritySearch", ASIN, None, type, page, license_key, http_proxy, locale, associate)

def searchByWishlist(wishlistID, type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("WishlistSearch", wishlistID, None, type, page, license_key, http_proxy, locale, associate)

def searchByPower(keyword, product_line="books", type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("PowerSearch", keyword, product_line, type, page, license_key, http_proxy, locale, associate)
    # >>> RecentKing = amazon.searchByPower('author:Stephen King and pubdate:2003')
    # >>> SnowCrash = amazon.searchByPower('title:Snow Crash')

def searchByBlended(keyword, type="heavy", page=1, license_key=None, http_proxy=None, locale=None, associate=None):
    return search("BlendedSearch", keyword, None, type, page, license_key, http_proxy, locale, associate)

def PluginPreferences(parent):
    b = gtk.Button("Visit Amazon.com")
    b.connect('clicked', lambda s: util.website('http://www.amazon.com/'))
    return b

def plugin_album(songs):
    artist = songs[0]('artist')
    album = songs[0]('album')
    fn = songs[0]('~filename')
    fn = os.path.join(os.path.dirname(fn), ".folder.jpg")
    print fn
    
    bags = searchByKeyword(artist+'+'+album, type="lite", product_line="music")
    sock = urllib.urlopen(bags[0].ImageUrlLarge)
    f = open(fn, 'wB')
    f.write(sock.read())

