from zope import interface, schema
from zope.formlib import form
from Products.Five.formlib import formbase
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from zope.app.form.browser.itemswidgets import MultiSelectWidget as _MultiSelectWidget
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from Products.validation import validation

from uwosh.groupmailer import groupmailerMessageFactory as _


# Begin monkey patch
# Source: http://athenageek.wordpress.com/2008/01/08/contentproviderlookuperror-plonehtmlhead/
def _getContext(self):
    self = self.aq_parent
    while getattr(self, '_is_wrapperish', None):
        self = self.aq_parent
    return self

ViewPageTemplateFile._getContext = _getContext
# End monkey patch


def MultiSelectWidget(field, request):
    vocabulary = field.value_type.vocabulary
    return _MultiSelectWidget(field, vocabulary, request)

def availableGroups(context):
    portal_groups = getToolByName(context, 'portal_groups')
    groups = portal_groups.getGroupIds()
    groups.remove('AuthenticatedUsers')
    return SimpleVocabulary.fromValues(groups)

def isEmail(input):
    validator = validation.validatorFor('isEmail')
    return validator(str(input)) == 1


class ISendGroupMailSchema(interface.Interface):
    fromAddress = schema.TextLine(
        title=u'From Address',
        required=True,
        constraint=isEmail
        )

    groups = schema.List(
        title=u'Recipient Groups',
        required=True,
        value_type=schema.Choice(vocabulary='Available Groups'),
        constraint=lambda x: x != []
        )

    recipients = schema.TextLine(
        title=u'Other Recipients',
        description=u'Comma seperated list of email addresses',
        required=False
        )

    subject = schema.TextLine(
        title=u'Message Subject', 
        required=True
        )

    body = schema.Text(
        title=u'Message Body',
        required=True
        )


class SendGroupMail(formbase.PageForm):
    def _getBodyDefault(self):
        if hasattr(self.context, 'getText'):
            return str(self.portal_transforms.convert('html_to_web_intelligent_plain_text', self.context.getText()))
        elif hasattr(self.context, 'absolute_url'):
            return self.context.absolute_url()

    def _getSubjectDefault(self):
        if hasattr(self.context, 'Title'):
            return self.context.Title()
        elif hasattr(self.context, 'id'):
            return self.context.id
        
    def _getFromAddressDefault(self):
        if hasattr(self.context, 'email_from_address'):
            return self.context.email_from_address

    form_fields = form.FormFields(ISendGroupMailSchema)
    form_fields['groups'].custom_widget = MultiSelectWidget
    form_fields['body'].get_rendered = _getBodyDefault
    form_fields['subject'].get_rendered = _getSubjectDefault
    form_fields['fromAddress'].get_rendered = _getFromAddressDefault

    label = _(u'Send email to groups')
    description = _(u'')

    result_template = ViewPageTemplateFile('sendgroupmail_result.pt')

    @property
    def portal_transforms(self):
        return getToolByName(self.context, 'portal_transforms')

    @property
    def portal_groups(self):
        return getToolByName(self.context, 'portal_groups')

    @property
    def plone_utils(self):
        return getToolByName(self.context, 'plone_utils')

    @property
    def MailHost(self):
        return getToolByName(self.context, 'MailHost')

    @form.action('Send')
    def actionSend(self, action, data):
        self.groups = data['groups']
        self.body = data['body']
        self.subject = data['subject']
        self.recipients = data['recipients']
        self.fromAddress = data['fromAddress']
        
        self._parseRecipientsList()
        self._addEmailAddressesFromGroupsToRecipientsList()

        self.MailHost.secureSend(self.body, mto=self.recipients, mfrom=self.fromAddress, subject=self.subject)
        return self.result_template()

    def _parseRecipientsList(self):
        if self.recipients is not None:
            self.recipients = filter(self.plone_utils.validateSingleEmailAddress, map(lambda x: str(x).strip(), self.recipients.split(',')))
        else:
            self.recipients = []

    def _addEmailAddressesFromGroupsToRecipientsList(self):
        recipientsSet = set(self.recipients)
        for groupId in self.groups:
            group = self.portal_groups.getGroupById(groupId)
            members = group.getAllGroupMembers()
            emailAddresses = [member.getProperty('email') for member in members if member.getProperty('email') != '']
            recipientsSet = recipientsSet.union(emailAddresses)
        self.recipients = list(recipientsSet)

    @form.action('Cancel', validator=lambda *a: [])
    def actionCancel(self, action, data):
        self.request.response.redirect(self.context.absolute_url())

    @property
    def recipientsAsCSVString(self):
        return ', '.join(self.recipients)
    
    @property
    def bodyAsHTML(self):
        return self.portal_transforms.convert('web_intelligent_plain_text_to_html', self.body)
