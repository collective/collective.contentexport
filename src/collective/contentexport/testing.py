# -*- coding: utf-8 -*-
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.testing import z2

import collective.contentexport


class CollectiveContentexportLayer(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        self.loadZCML(package=collective.contentexport)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'collective.contentexport:default')
        portal.acl_users.userFolderAddUser(
            SITE_OWNER_NAME, SITE_OWNER_PASSWORD, ['Manager'], [])


COLLECTIVE_CONTENTEXPORT_FIXTURE = CollectiveContentexportLayer()


COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING = IntegrationTesting(
    bases=(COLLECTIVE_CONTENTEXPORT_FIXTURE,),
    name='CollectiveContentexportLayer:IntegrationTesting'
)


COLLECTIVE_CONTENTEXPORT_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(COLLECTIVE_CONTENTEXPORT_FIXTURE,),
    name='CollectiveContentexportLayer:FunctionalTesting'
)


COLLECTIVE_CONTENTEXPORT_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        COLLECTIVE_CONTENTEXPORT_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE
    ),
    name='CollectiveContentexportLayer:AcceptanceTesting'
)
