
from Products.CMFCore.permissions import setDefaultRoles
from zope.i18nmessageid import MessageFactory

groupmailerMessageFactory = MessageFactory('uwosh.groupmailer')

def initialize(context):
    """Initializer called when used as a Zope 2 product."""

    setDefaultRoles('uwosh.groupmailer: Send Mail', ('Manager', 'GroupMailer'))
