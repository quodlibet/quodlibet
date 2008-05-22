"""Python wrapper for AWS E-Commerce Serive APIs.

Based upon pyamazon (http://www.josephson.org/projects/pyamazon/) with 
efforts to meet the latest AWS specification.

The Amazon's web APIs specication is described here:
http://www.amazon.com/webservices

You need a Amazon-provided license key to use these services.
Follow the link above to get one.  These functions will look in
several places (in this order) for the license key:
        - the "license_key" argument of each function
        - the module-level LICENSE_KEY variable (call setLicense once to set it)
        - an environment variable called AMAZON_LICENSE_KEY
        - foo would return the python object, XMLfoo returns the DOM object

License: Python Software Foundation License
"""


import os, urllib, string, inspect
from xml.dom import minidom

__author__ = "Kun Xi < kunxi@kunxi.org >"
__version__ = "0.2.0"
__license__ = "Python Software Foundation"


"""Package-wide variables:
"""
LICENSE_KEY = None;
HTTP_PROXY = None
LOCALE = "us"
VERSION = "2007-02-22"

__supportedLocales = {
                None : "webservices.amazon.com",  
                "us" : "webservices.amazon.com",   
                "uk" : "webservices.amazon.co.uk",
                "de" : "webservices.amazon.de",
                "jp" : "webservices.amazon.co.jp",
                "fr" : "webservices.amazon.fr",
                "ca" : "webservices.amazon.ca"
        }

__licenseKeys = (
        (lambda key: key),
        (lambda key: LICENSE_KEY), 
        (lambda key: os.environ.get('AWS_LICENSE_KEY', None))
   )


class AWSException(Exception) : 
        '''Base class for all AWS exceptions'''
        pass

class NoLicenseKey(AWSException) : pass
class BadLocale(AWSException) : pass
# Runtime exception
class ExactParameterRequirement(AWSException): pass
class ExceededMaximumParameterValues(AWSException): pass
class InsufficientParameterValues(AWSException): pass
class InternalError(AWSException): pass
class InvalidEnumeratedParameter(AWSException): pass
class InvalidISO8601Time(AWSException): pass
class InvalidOperationForMarketplace(AWSException): pass
class InvalidOperationParameter(AWSException): pass
class InvalidParameterCombination(AWSException): pass
class InvalidParameterValue(AWSException): pass
class InvalidResponseGroup(AWSException): pass
class InvalidServiceParameter(AWSException): pass
class InvalidSubscriptionId(AWSException): pass
class InvalidXSLTAddress(AWSException): pass
class MaximumParameterRequirement(AWSException): pass
class MinimumParameterRequirement(AWSException): pass
class MissingOperationParameter(AWSException): pass
class MissingParameterCombination(AWSException): pass
class MissingParameters(AWSException): pass
class MissingParameterValueCombination(AWSException): pass
class MissingServiceParameter(AWSException): pass
class ParameterOutOfRange(AWSException): pass
class ParameterRepeatedInRequest(AWSException): pass
class RestrictedParameterValueCombination(AWSException): pass
class XSLTTransformationError(AWSException): pass

class Bag : 
        '''Wrapper class for DOM nodes'''
        pass



# Utilities functions

def setLocale(locale):
        """set locale
        
        if unsupported locale is set, BadLocale is raised."""
        global LOCALE
        if not __supportedLocales.has_key(locale):
                raise BadLocale, ("Unsupported locale. Locale must be one of: %s" %
                        ', '.join([x for x in __supportedLocales.keys() if x]))
        LOCALE = locale


def getLocale():
        """get locale"""
        return LOCALE


def setLicenseKey(license_key=None):
        """set license key

        license key can come from any number of locations;
        see module docs for search order.
        if no license key is specified, BadLocale is raised."""

        global LICENSE_KEY
        for get in __licenseKeys:
                rc = get(license_key)
                if rc: 
                        LICENSE_KEY = rc;
                        return;
        raise NoLicenseKey, ("Please get the license key from  http://www.amazon.com/webservices")


def getLicenseKey():
        """get license key

        if no license key is specified, BadLocale is raised."""

        if not LICENSE_KEY:
                raise NoLicenseKey, ("Please get the license key from  http://www.amazon.com/webservices")
        return LICENSE_KEY
        

def getVersion():
        """get version"""
        return VERSION


def buildRequest(argv):
        """Build the REST request URL from argv,
        
        all key, value pairs in argv are quoted."""

        url = "http://" + __supportedLocales[getLocale()] + "/onca/xml?Service=AWSECommerceService&"
        return url + '&'.join(['%s=%s' % (k,urllib.quote(str(v))) for (k,v) in argv.items() if v]) 


def buildException(els):
        """Build the exception from the returned DOM node

        Only the first exception is raised."""

        error = els[0]
        class_name = error.childNodes[0].firstChild.data[4:]
        msg = error.childNodes[1].firstChild.data 

        e = globals()[ class_name ](msg)
        return e


def query(url):
        """Send the query url and return the DOM
        
        Exception is raised if there is errors"""
        u = urllib.FancyURLopener(HTTP_PROXY)
        usock = u.open(url)
        dom = minidom.parse(usock)
        usock.close()

        errors = dom.getElementsByTagName('Error')
        if errors:
                e = buildException(errors)
                raise e
        return dom


def rawObject(XMLSearch, arguments, kwItem, plugins=None):
        '''Return a unique object'''

        dom = XMLSearch(** arguments)
        return unmarshal(dom.getElementsByTagName(kwItem).item(0), plugins) 

        
def rawIterator(XMLSearch, arguments, kwItems, plugins=None):
        '''Return list of objects'''

        dom = XMLSearch(** arguments)
        items = unmarshal(dom.getElementsByTagName(kwItems).item(0), plugins, wrappedIterator())
        return items

class wrappedIterator(list):
        '''Return inherited list object, 
        
        we may add more attributes later'''
        
        pass
        

class pagedIterator:
        '''Return a page-based iterator'''

        def __init__(self, XMLSearch, arguments, kwPage, kwItems, plugins=None):
                """XMLSearch: the callback function that returns the DOM
                arguments: the arguments for XMLSearch
                kwPage, kwItems: Tag name of Page, Items to organize the object
                plugins: please check unmarshal
                """
                self.__search = XMLSearch 
                self.__arguments = arguments 
                self.__keywords ={'Page':kwPage, 'Items':kwItems} 
                self.__plugins = plugins
                self.__page = arguments[kwPage] or 1
                self.__index = 0
                dom = self.__search(** self.__arguments)
                self.__items = unmarshal(dom.getElementsByTagName(kwItems).item(0), plugins, wrappedIterator())
                try:
                        self.__len = int(dom.getElementsByTagName("TotalResults").item(0).firstChild.data)
                except AttributeError, e:
                        self.__len = len(self.__items)

        def __len__(self):
                return self.__len

        def __iter__(self):
                return self

        def next(self):
                if self.__index < self.__len:
                        self.__index = self.__index + 1
                        return self.__getitem__(self.__index-1)
                else:
                        raise StopIteration

        def __getitem__(self, key):
                try:
                        num = int(key)
                except TypeError, e:
                        raise e

                if num >= self.__len:
                        raise IndexError

                page = num / 10 + 1
                index = num % 10
                if page != self.__page:
                        self.__arguments[self.__keywords['Page']] = page
                        dom = self.__search(** self.__arguments)
                        self.__items = unmarshal(dom.getElementsByTagName(self.__keywords['Items']).item(0), self.__plugins, wrappedIterator())
                        self.__page = page

                return self.__items[index]


def unmarshal(element, plugins=None, rc=None):
        """Return the Bag object with attributes populated using DOM element

        element: the root of the DOM element we are interested in
        plugins: callback functions to fine-tune the object structure
        rc: parent object, used in the recursive call

        This core function is inspired by Mark Pilgrim (f8dy@diveintomark.org)
        with some enhancement. Each node.tagName is evalued by plugins' callback
        functions:
                
                if plugins['isBypassed'] is true:
                        this elment is ignored
                if plugins['isPivoted'] is true:
                        this children of this elment is moved to grandparents
                        this object is ignored.
                if plugins['isCollective'] is true:
                        this elment is mapped to []
                if plugins['isCollected'] is true:
                        this children of elment is appended to grandparent
                        this object is ignored.
        """

        if(rc == None):
                rc = Bag()

        if(plugins == None):
                plugins = {}

        childElements = [e for e in element.childNodes if isinstance(e, minidom.Element)]

        if childElements:
                for child in childElements:
                        key = child.tagName
                        if hasattr(rc, key):
                                if type(getattr(rc, key)) <> type([]):
                                        setattr(rc, key, [getattr(rc, key)])
                                setattr(rc, key, getattr(rc, key) + [unmarshal(child, plugins)])
                        elif isinstance(child, minidom.Element):
                                if plugins.has_key('isPivoted') and plugins['isPivoted'](child.tagName):
                                                unmarshal(child, plugins, rc)
                                elif plugins.has_key('isBypassed') and plugins['isBypassed'](child.tagName):
                                        continue
                                elif plugins.has_key('isCollective') and plugins['isCollective'](child.tagName):
                                        setattr(rc, key, unmarshal(child, plugins, wrappedIterator([])))
                                elif plugins.has_key('isCollected') and plugins['isCollected'](child.tagName):
                                        rc.append(unmarshal(child, plugins))
                                else:
                                        setattr(rc, key, unmarshal(child, plugins))
        else:
                rc = "".join([e.data for e in element.childNodes if isinstance(e, minidom.Text)])
        return rc


        
# User interfaces

def ItemLookup(ItemId, IdType=None, SearchIndex=None, MerchantId=None, Condition=None, DeliveryMethod=None, ISPUPostalCode=None, OfferPage=None, ReviewPage=None, VariationPage=None, ResponseGroup=None, AWSAccessKeyId=None): 
        '''ItemLookup in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isPivoted': lambda x: x == 'ItemAttributes', 
                'isCollective': lambda x: x == 'Items', 
                'isCollected': lambda x: x == 'Item'}
        return pagedIterator(XMLItemLookup, argv, 'OfferPage', 'Items', plugins)

        
def XMLItemLookup(ItemId, IdType=None, SearchIndex=None, MerchantId=None, Condition=None, DeliveryMethod=None, ISPUPostalCode=None, OfferPage=None, ReviewPage=None, VariationPage=None, ResponseGroup=None, AWSAccessKeyId=None): 
        '''DOM representation of ItemLookup in ECS'''

        Operation = "ItemLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


def ItemSearch(Keywords, SearchIndex="Blended", Availability=None, Title=None, Power=None, BrowseNode=None, Artist=None, Author=None, Actor=None, Director=None, AudienceRating=None, Manufacturer=None, MusicLabel=None, Composer=None, Publisher=None, Brand=None, Conductor=None, Orchestra=None, TextStream=None, ItemPage=None, Sort=None, City=None, Cuisine=None, Neighborhood=None, MinimumPrice=None, MaximumPrice=None, MerchantId=None, Condition=None, DeliveryMethod=None, ResponseGroup=None, AWSAccessKeyId=None):  
        '''ItemSearch in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isPivoted': lambda x: x == 'ItemAttributes',
                'isCollective': lambda x: x == 'Items', 
                'isCollected': lambda x: x == 'Item'}
        return pagedIterator(XMLItemSearch, argv, "ItemPage", 'Items', plugins)


def XMLItemSearch(Keywords, SearchIndex="Blended", Availability=None, Title=None, Power=None, BrowseNode=None, Artist=None, Author=None, Actor=None, Director=None, AudienceRating=None, Manufacturer=None, MusicLabel=None, Composer=None, Publisher=None, Brand=None, Conductor=None, Orchestra=None, TextStream=None, ItemPage=None, Sort=None, City=None, Cuisine=None, Neighborhood=None, MinimumPrice=None, MaximumPrice=None, MerchantId=None, Condition=None, DeliveryMethod=None, ResponseGroup=None, AWSAccessKeyId=None):  
        '''DOM representation of ItemSearch in ECS'''

        Operation = "ItemSearch"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


def SimilarityLookup(ItemId, SimilarityType=None, MerchantId=None, Condition=None, DeliveryMethod=None, ResponseGroup=None, AWSAccessKeyId=None):  
        '''SimilarityLookup in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isPivoted': lambda x: x == 'ItemAttributes',
                'isCollective': lambda x: x == 'Items',
                'isCollected': lambda x: x == 'Item'}
        return rawIterator(XMLSimilarityLookup, argv, 'Items', plugins)


def XMLSimilarityLookup(ItemId, SimilarityType=None, MerchantId=None, Condition=None, DeliveryMethod=None, ResponseGroup=None, AWSAccessKeyId=None):  
        '''DOM representation of SimilarityLookup in ECS'''

        Operation = "SimilarityLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


# List Operations

def ListLookup(ListType, ListId, ProductPage=None, ProductGroup=None, Sort=None, MerchantId=None, Condition=None, DeliveryMethod=None, ResponseGroup=None, AWSAccessKeyId=None):  
        '''ListLookup in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isPivoted': lambda x: x == 'ItemAttributes',
                'isCollective': lambda x: x == 'Lists', 
                'isCollected': lambda x: x == 'List'}
        return pagedIterator(XMLListLookup, argv, 'ProductPage', 'Lists', plugins)


def XMLListLookup(ListType, ListId, ProductPage=None, ProductGroup=None, Sort=None, MerchantId=None, Condition=None, DeliveryMethod=None, ResponseGroup=None, AWSAccessKeyId=None):  
        '''DOM representation of ListLookup in ECS'''

        Operation = "ListLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


def ListSearch(ListType, Name=None, FirstName=None, LastName=None, Email=None, City=None, State=None, ListPage=None, ResponseGroup=None, AWSAccessKeyId=None):
        '''ListSearch in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isPivoted': lambda x: x == 'ItemAttributes',
                'isCollective': lambda x: x == 'Lists', 
                'isCollected': lambda x: x == 'List'}
        return pagedIterator(XMLListSearch, argv, 'ListPage', 'Lists', plugins)


def XMLListSearch(ListType, Name=None, FirstName=None, LastName=None, Email=None, City=None, State=None, ListPage=None, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of ListSearch in ECS'''

        Operation = "ListSearch"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


#Remote Shopping Cart Operations
def CartCreate(Items, Quantities, ResponseGroup=None, AWSAccessKeyId=None):
        '''CartCreate in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return __cartOperation(XMLCartCreate, argv)


def XMLCartCreate(Items, Quantities, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of CartCreate in ECS'''

        Operation = "CartCreate"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        for x in ('Items', 'Quantities'):
                del argv[x]

        __fromListToItems(argv, Items, 'ASIN', Quantities)
        return query(buildRequest(argv))


def CartAdd(Cart, Items, Quantities, ResponseGroup=None, AWSAccessKeyId=None):
        '''CartAdd in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return __cartOperation(XMLCartAdd, argv)


def XMLCartAdd(Cart, Items, Quantities, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of CartAdd in ECS'''

        Operation = "CartAdd"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        CartId = Cart.CartId
        HMAC = Cart.HMAC
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        for x in ('Items', 'Cart', 'Quantities'):
                del argv[x]

        __fromListToItems(argv, Items, 'ASIN', Quantities)
        return query(buildRequest(argv))


def CartGet(Cart, ResponseGroup=None, AWSAccessKeyId=None):
        '''CartGet in ECS'''
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return __cartOperation(XMLCartGet, argv)


def XMLCartGet(Cart, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of CartGet in ECS'''

        Operation = "CartGet"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        CartId = Cart.CartId
        HMAC = Cart.HMAC
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        del argv['Cart']
        return query(buildRequest(argv))


def CartModify(Cart, Items, Actions, ResponseGroup=None, AWSAccessKeyId=None):
        '''CartModify in ECS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return __cartOperation(XMLCartModify, argv)


def XMLCartModify(Cart, Items, Actions, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of CartModify in ECS'''
        Operation = "CartModify"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        CartId = Cart.CartId
        HMAC = Cart.HMAC
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        for x in ('Cart', 'Items', 'Actions'):
                del argv[x]

        __fromListToItems(argv, Items, 'CartItemId', Actions)
        return query(buildRequest(argv))

        
def CartClear(Cart, ResponseGroup=None, AWSAccessKeyId=None):
        '''CartClear in ECS'''
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return __cartOperation(XMLCartClear, argv)


def XMLCartClear(Cart, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of CartClear in ECS'''

        Operation = "CartClear"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        CartId = Cart.CartId
        HMAC = Cart.HMAC
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        del argv['Cart']

        return query(buildRequest(argv))


def __fromListToItems(argv, items, id, actions):
        '''Convert list to AWS REST arguments'''

        for i in range(len(items)):
                argv["Item.%d.%s" % (i+1, id)] = getattr(items[i], id);
                action = actions[i]
                if isinstance(action, int):
                        argv["Item.%d.Quantity" % (i+1)] = action
                else:
                        argv["Item.%d.Action" % (i+1)] = action


def __cartOperation(XMLSearch, arguments):
        '''Generic cart operation'''

        plugins = {'isBypassed': lambda x: x == 'Request',
                'isCollective': lambda x: x in ('CartItems', 'SavedForLaterItems'),
                'isCollected': lambda x: x in ('CartItem', 'SavedForLaterItem') }
        return rawObject(XMLSearch, arguments, 'Cart', plugins)


# Seller Operation
def SellerLookup(Sellers, ResponseGroup=None, AWSAccessKeyId=None):
        '''SellerLookup in AWS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request',
                'isCollective': lambda x: x == 'Sellers',
                'isCollected': lambda x: x == 'Seller'}
        return rawIterator(XMLSellerLookup, argv, 'Sellers', plugins)


def XMLSellerLookup(Sellers, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of SellerLookup in AWS'''

        Operation = "SellerLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        SellerId = ",".join(Sellers)
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        del argv['Sellers']
        return query(buildRequest(argv))


def SellerListingLookup(SellerId, Id, IdType="Listing", ResponseGroup=None, AWSAccessKeyId=None):
        '''SellerListingLookup in AWS

        Notice: although the repsonse includes TotalPage, TotalResults, 
        there is no ListingPage in the request, so we have to use rawIterator
        instead of pagedIterator. Hope Amazaon would fix this inconsistance'''
        
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request',
                'isCollective': lambda x: x == 'SellerListings', 
                'isCollected': lambda x: x == 'SellerListing'}
        return rawIterator(XMLSellerListingLookup, argv, "SellerListings", plugins)


def XMLSellerListingLookup(SellerId, Id, IdType="Listing", ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of SellerListingLookup in AWS'''

        Operation = "SellerListingLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


def SellerListingSearch(SellerId, Title=None, Sort=None, ListingPage=None, OfferStatus=None, ResponseGroup=None, AWSAccessKeyId=None):
        '''SellerListingSearch in AWS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request',
                'isCollective': lambda x: x == 'SellerListings', 
                'isCollected': lambda x: x == 'SellerListing'}
        return pagedIterator(XMLSellerListingSearch, argv, "ListingPage", "SellerListings", plugins)


def XMLSellerListingSearch(SellerId, Title=None, Sort=None, ListingPage=None, OfferStatus=None, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of SellerListingSearch in AWS'''

        Operation = "SellerListingSearch"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


def CustomerContentSearch(Name=None, Email=None, CustomerPage=1, ResponseGroup=None, AWSAccessKeyId=None):
        '''CustomerContentSearch in AWS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request',
                'isCollective': lambda x: x in ('Customers', 'CustomerReviews'),
                'isCollected': lambda x: x in ('Customer', 'Review')}
        return rawIterator(XMLCustomerContentSearch, argv, 'Customers', plugins)


def XMLCustomerContentSearch(Name=None, Email=None, CustomerPage=1, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of CustomerContentSearch in AWS'''

        Operation = "CustomerContentSearch"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        for x in ('Name', 'Email'):
                if not argv[x]:
                        del argv[x]
        return query(buildRequest(argv))


def CustomerContentLookup(CustomerId, ReviewPage=1, ResponseGroup=None, AWSAccessKeyId=None):
        '''CustomerContentLookup in AWS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request',
                'isCollective': lambda x: x == 'Customers',
                'isCollected': lambda x: x == 'Customer'}
        return rawIterator(XMLCustomerContentLookup, argv, 'Customers', plugins)


def XMLCustomerContentLookup(CustomerId, ReviewPage=1, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of CustomerContentLookup in AWS'''

        Operation = "CustomerContentLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


# BrowseNode
def BrowseNodeLookup(BrowseNodeId, ResponseGroup=None, AWSAccessKeyId=None):
        '''BrowseNodeLookup in AWS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request',
                'isCollective': lambda x: x == 'Children',
                'isCollected': lambda x: x == 'BrowseNode'}
        return rawIterator(XMLBrowseNodeLookup, argv, 'BrowseNodes', plugins)


def XMLBrowseNodeLookup(BrowseNodeId, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of BrowseNodeLookup in AWS'''
        
        Operation = "BrowseNodeLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


# Help
def Help(HelpType, About, ResponseGroup=None, AWSAccessKeyId=None):
        '''Help in AWS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request', 
                'isCollective': lambda x: x in ('RequiredParameters', 
                        'AvailableParameters', 'DefaultResponseGroups',
                        'AvailableResponseGroups'),
                'isCollected': lambda x: x in ('Parameter', 'ResponseGroup') }
        return rawObject(XMLHelp, argv, 'Information', plugins)


def XMLHelp(HelpType, About, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of Help in AWS'''

        Operation = "Help"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))


# Transaction
def TransactionLookup(TransactionId, ResponseGroup=None, AWSAccessKeyId=None):
        '''TransactionLookup in AWS'''

        argv = inspect.getargvalues(inspect.currentframe())[-1]
        plugins = {'isBypassed': lambda x: x == 'Request', 
                'isCollective': lambda x: x in ('Transactions', 'TransactionItems', 'Shipments'),
                'isCollected': lambda x: x in ('Transaction', 'TransactionItem', 'Shipment')}
                        
        return rawIterator(XMLTransactionLookup, argv, 'Transactions', plugins)
        

def XMLTransactionLookup(TransactionId, ResponseGroup=None, AWSAccessKeyId=None):
        '''DOM representation of TransactionLookup in AWS'''

        Operation = "TransactionLookup"
        AWSAccessKeyId = AWSAccessKeyId or LICENSE_KEY
        argv = inspect.getargvalues(inspect.currentframe())[-1]
        return query(buildRequest(argv))



if __name__ == "__main__" :
        setLicenseKey("YOUR-LICENSE-HERE");
        sll = SellerListingLookup("A3ENSIQ3ZA4FFN", "1106K206331")
        print dir(sll[0])
        
