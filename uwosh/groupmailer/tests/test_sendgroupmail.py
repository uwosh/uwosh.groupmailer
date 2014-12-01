import unittest
from Testing import ZopeTestCase as ztc
from base import FunctionalTestCase
from base import MockObject
from Products.CMFCore.utils import getToolByName

class TestSendGroupMail(FunctionalTestCase):
    def testParseRecipientsListMethod(self):
        from uwosh.groupmailer.browser.sendgroupmail import SendGroupMail
        mockView = SendGroupMail(self.portal, None)
    
        mockView.recipients = 'email@example.com  , asdf@example.com,jkl@example.com'
        mockView._parseRecipientsList()
        self.assertEqual(mockView.recipients, ['email@example.com', 'asdf@example.com', 'jkl@example.com'])

        mockView.recipients = 'asdf, email@example.com,, george, email@example'
        mockView._parseRecipientsList()
        self.assertEqual(mockView.recipients, ['email@example.com'])

    def testIsEmailValidator(self):
        from uwosh.groupmailer.browser.sendgroupmail import isEmail
        self.assertTrue(isEmail('asdf@example.com'))
        self.assertTrue(isEmail('asdfasdf+jkl@example.com'))
        self.assertTrue(isEmail('asdf.asdf@example.example.com'))
        self.assertFalse(isEmail('asdf@example'))
        self.assertFalse(isEmail('@example.com'))
        self.assertFalse(isEmail('asdf'))

    def testGettingAvailableGroupsVocabulary(self):
        from uwosh.groupmailer.browser.sendgroupmail import availableGroups
        portal_groups = getToolByName(self.portal, 'portal_groups')

        self.assertEqual(sorted(portal_groups.getGroupIds()), ['Administrators', 'AuthenticatedUsers', 'Reviewers'])

        vocabularyGroupIds = availableGroups(self.portal).by_value.keys()
        self.assertEqual(sorted(vocabularyGroupIds), ['Administrators', 'Reviewers'])

        portal_groups.addGroup('Fake Test Group')

        vocabularyGroupIds = availableGroups(self.portal).by_value.keys()
        self.assertEqual(sorted(vocabularyGroupIds), ['Administrators', 'Fake Test Group', 'Reviewers'])

    def testFieldsAreFilledInAutomatically(self):
        pageId = self.folder.invokeFactory('Document', 'test-document')
        page = self.folder[pageId]
        page.setTitle('Example subject')
        page.setText('<p>This is the body of a message<br />\n <strong>HTML and all</strong></p>')

        self.portal.email_from_address = 'email@example.com'
        self.browser.open(page.absolute_url() + '/@@sendgroupmail')
        self.assertEqual(self.browser.getControl('Message Subject').value, 'Example subject')
        self.assertEqual(self.browser.getControl('Message Body').value, 'This is the body of a message\r\n HTML and all\r\n\r\n')
        self.assertEqual(self.browser.getControl('From Address').value, 'email@example.com')
        self.assertEqual(sorted(self.browser.getControl('Recipient Groups').options), ['Administrators', 'Reviewers'] )

    def testAccessingOfDefaultValueHandlesMissingAttributesGracefully(self):
        del self.portal.email_from_address
        self.assertEqual(self.folder.Title(), '')
        self.browser.open(self.folder.absolute_url() + '/@@sendgroupmail')
        self.assertEqual(self.browser.getControl('Message Subject').value, '')
        self.assertEqual(self.browser.getControl('Message Body').value, 'http://nohost/plone/Members/test_user_1_')
        self.assertEqual(self.browser.getControl('From Address').value, '')

    def testUsersWithManagerRoleHaveActionLinkAndCanAccessView(self):
        self.setRoles(['Manager', 'Member', 'Authenticated'])
        self.browser.open(self.portal.absolute_url() + '/front-page')
        self.assertTrue('Send as email to groups' in self.browser.contents)
        self.assertTrue('/front-page/@@sendgroupmail' in self.browser.contents)
        self.browser.getLink('Send as email to groups').click()
        self.assertTrue('<h1 class="documentFirstHeading">Insufficient Privileges</h1>' not in self.browser.contents)

    def testUsersWithGroupMailerRoleHaveActionLinkAndCanAccessView(self):
        self.setRoles(['GroupMailer', 'Member', 'Authenticated'])
        self.browser.open(self.portal.absolute_url() + '/front-page')
        self.assertTrue('Send as email to groups' in self.browser.contents)
        self.assertTrue('/front-page/@@sendgroupmail' in self.browser.contents)
        self.browser.getLink('Send as email to groups').click()
        self.assertTrue('<h1 class="documentFirstHeading">Insufficient Privileges</h1>' not in self.browser.contents)

    def testUsersWithJustMemberRoleDoNotHaveActionLinkAndCannotAccessView(self):
        self.setRoles(['Member', 'Authenticated'])
        self.browser.open(self.portal.absolute_url() + '/front-page')
        self.assertTrue('Send as email to groups' not in self.browser.contents)
        self.assertTrue('/front-page/@@sendgroupmail' not in self.browser.contents)
        self.browser.open(self.portal.absolute_url() + '/front-page/@@sendgroupmail')
        self.assertTrue('<h1 class="documentFirstHeading">Insufficient Privileges</h1>' in self.browser.contents)

    def testCancelButtonRedirectsToOriginalObject(self):
        self.browser.open(self.portal.absolute_url() + '/front-page/@@sendgroupmail')
        self.assertTrue('Welcome to Plone' in self.browser.contents)
        self.assertTrue('<h1 class="documentFirstHeading">Send email to groups</h1>' in self.browser.contents)
        self.browser.getControl('Cancel').click()
        self.assertTrue('Welcome to Plone' in self.browser.contents)
        self.assertTrue('<h1 class="documentFirstHeading">Send email to groups</h1>' not in self.browser.contents)

    def testSendActionSendsEmailCorrectly(self):
        self.browser.open(self.portal.absolute_url() + '/front-page/@@sendgroupmail')
        self.browser.getControl('Recipient Groups').value = ['Reviewers', 'Administrators']
        self.browser.getControl('Other Recipients').value = 'otheremail@example.com, person@example.com'
        self.browser.getControl('From Address').value = 'me@example.com'
        self.browser.getControl('Message Subject').value = 'Subject'
        self.browser.getControl('Message Body').value = 'Body.....'
        self.browser.getControl('Send').click()

        mailHost = getToolByName(self.portal, 'MailHost')
        self.assertEqual(len(mailHost.sentEmail), 1)

        emailRecord = mailHost.sentEmail[0]
        self.assertEqual(sorted(emailRecord['mto']), ['otheremail@example.com', 'person@example.com'])
        self.assertEqual(emailRecord['subject'], 'Subject')
        self.assertEqual(emailRecord['message'], 'Body.....')
        self.assertEqual(emailRecord['mfrom'], 'me@example.com')

    def testRecipientsListIsCreatedCorrectly(self):
        self.setRoles(['Member', 'Authenticated', 'Manager'])
        portal_groups = getToolByName(self.portal, 'portal_groups')
        portal_groups.addGroup('TestGroup1')
        portal_groups.addGroup('TestGroup2')
        group1 = portal_groups.getGroupById('TestGroup1')
        group2 = portal_groups.getGroupById('TestGroup2')
        reviewersGroup = portal_groups.getGroupById('Reviewers')

        self.addUser('user1', 'User One', 'user1@example.com')
        self.addUser('user2', 'User Two', 'user2@example.com')
        self.addUser('user3', 'User Three', 'user3@example.com')
        self.addUser('user4', 'User Four', 'user4@example.com')
        self.addUser('user5', 'User Five', 'user5@example.com')

        self.assertEqual(group1.getMemberIds(), [])
        group1.addMember('user1')
        group1.addMember('user2')
        self.assertEqual(sorted(group1.getMemberIds()), ['user1', 'user2'])

        self.assertEqual(group2.getMemberIds(), [])
        group2.addMember('user2')
        group2.addMember('user3')
        self.assertEqual(sorted(group2.getMemberIds()), ['user2', 'user3'])

        reviewersGroup.addMember('user4')
        self.assertEqual(reviewersGroup.getMemberIds(), ['user4'])

        self.browser.open(self.portal.absolute_url() + '/front-page/@@sendgroupmail')
        self.browser.getControl('Recipient Groups').value = ['TestGroup1', 'TestGroup2']
        self.browser.getControl('Other Recipients').value = 'otheremail@example.com, user2@example.com, user5@example.com'
        self.browser.getControl('From Address').value = 'me@example.com'
        self.browser.getControl('Message Subject').value = 'Subject'
        self.browser.getControl('Message Body').value = 'Body.....'
        self.browser.getControl('Send').click()

        self.assertTrue('user5@example.com, otheremail@example.com, user1@example.com, user3@example.com, user2@example.com' in self.browser.contents)

        mailHost = getToolByName(self.portal, 'MailHost')
        self.assertEqual(len(mailHost.sentEmail), 1)
        self.assertEqual(sorted(mailHost.sentEmail[0]['mto']), ['otheremail@example.com', 'user1@example.com', 'user2@example.com', 
                                                                'user3@example.com', 'user5@example.com'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSendGroupMail))
    return suite
