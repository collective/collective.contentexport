# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.contentexport.testing import COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING  # noqa
from plone import api

import unittest


class TestSetup(unittest.TestCase):
    """Test that collective.contentexport is properly installed."""

    layer = COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if collective.contentexport is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'collective.contentexport'))

    def test_browserlayer(self):
        """Test that ICollectiveContentexportLayer is registered."""
        from collective.contentexport.interfaces import (
            ICollectiveContentexportLayer)
        from plone.browserlayer import utils
        self.assertIn(ICollectiveContentexportLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.uninstallProducts(['collective.contentexport'])

    def test_product_uninstalled(self):
        """Test if collective.contentexport is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'collective.contentexport'))

    def test_browserlayer_removed(self):
        """Test that ICollectiveContentexportLayer is removed."""
        from collective.contentexport.interfaces import (
            ICollectiveContentexportLayer)
        from plone.browserlayer import utils
        self.assertNotIn(
            ICollectiveContentexportLayer, utils.registered_layers())
