"""Test setup for integration and functional tests.

When we import PloneTestCase and then call setupPloneSite(), all of
Plone's products are loaded, and a Plone site will be created. This
happens at module level, which makes it faster to run each test, but
slows down test runner startup.
"""

from Products.Five import zcml
from Products.Five import fiveconfigure

from Testing import ZopeTestCase as ztc

from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup
from Products.Five.testbrowser import Browser

from Products.MailHost.interfaces import IMailHost
from smtplib import SMTPRecipientsRefused
from Products.validation import validation
from Products.CMFCore.utils import getToolByName

# When ZopeTestCase configures Zope, it will *not* auto-load products
# in Products/. Instead, we have to use a statement such as:
#   ztc.installProduct('SimpleAttachment')
# This does *not* apply to products in eggs and Python packages (i.e.
# not in the Products.*) namespace. For that, see below.
# All of Plone's products are already set up by PloneTestCase.

@onsetup
def setup_product():
    """Set up the package and its dependencies.

    The @onsetup decorator causes the execution of this body to be
    deferred until the setup of the Plone site testing layer. We could
    have created our own layer, but this is the easiest way for Plone
    integration tests.
    """

    # Load the ZCML configuration for the example.tests package.
    # This can of course use <include /> to include other packages.

    fiveconfigure.debug_mode = True
    import uwosh.groupmailer
    zcml.load_config('configure.zcml', uwosh.groupmailer)
    fiveconfigure.debug_mode = False

    # We need to tell the testing framework that these products
    # should be available. This can't happen until after we have loaded
    # the ZCML. Thus, we do it here. Note the use of installPackage()
    # instead of installProduct().
    # This is *only* necessary for packages outside the Products.*
    # namespace which are also declared as Zope 2 products, using
    # <five:registerPackage /> in ZCML.

    # We may also need to load dependencies, e.g.:
    #   ztc.installPackage('borg.localrole')

    ztc.installPackage('uwosh.groupmailer')

# The order here is important: We first call the (deferred) function
# which installs the products we need for this product. Then, we let
# PloneTestCase set up this product on installation.

setup_product()
ptc.setupPloneSite(products=['uwosh.groupmailer'])

class MockObject:
    pass

class MockMailHost:
    """A mock mail host to avoid actually sending emails when testing."""
    validateSingleEmailAddress = lambda self, x: validation.validatorFor('isEmail')(x) == 1

    def __init__(self):
        self.sentEmail = []

    def getId(self):
        return 'MailHost'
        
    def secureSend(self, message, mto=None, mfrom=None, subject=None, encode=None):
        if isinstance(mto, str):
            mto = list(mto)

        for email in mto:            
            if not self.validateSingleEmailAddress(email):
                raise SMTPRecipientsRefused(email)
    
        self.sentEmail.append({'message':message,'mto':mto,'mfrom':mfrom,'subject':subject,'encode':encode})
        
    
class TestCase(ptc.PloneTestCase):
    """We use this base class for all the tests in this package. If
    necessary, we can put common utility or setup code in here. This
    applies to unit test cases.
    """

    def _setup(self):
        ptc.PloneTestCase._setup(self)
        self.portal.MailHost = MockMailHost()
        
        sm = self.portal.getSiteManager()
        sm.registerUtility(self.portal.MailHost, provided=IMailHost) 

    def addUser(self, username, fullname, email=None, roles=None):
        if roles is None:
            roles = ['Member', 'Authenticated']
        if email is None:
            email = ''

        portal_registration = getToolByName(self.portal, 'portal_registration')
        portal_registration.addMember(username, 'secret', properties={'email':email, 'fullname':fullname, 'username':username})
        

class FunctionalTestCase(ptc.FunctionalTestCase, TestCase):
    """We use this class for functional integration tests that use
    doctest syntax. Again, we can put basic common utility or setup
    code in here.
    """

    def afterSetUp(self):
        self.browser = Browser()
        self.loginThroughBrowser()
        self.setRoles(['Member', 'Authenticated', 'GroupMailer'])

    def loginThroughBrowser(self):
        browser = self.browser
        browser.open(self.portal.absolute_url() + '/login_form')
        browser.getLink('Log in').click()
        browser.getControl(name='__ac_name').value = 'test_user_1_'
        browser.getControl(name='__ac_password').value = 'secret'
        browser.getControl(name='submit').click()
        self.assertTrue('You are now logged in' in browser.contents)
