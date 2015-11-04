# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from collective.contentexport.testing import COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING  # noqa
from plone import api
from plone.app.textfield.value import RichTextValue

import os
import json
import unittest

formats = [
    'xlsx',
    'xls',
    'yaml',
    'html',
    'csv',
    'tsv',
    'json',
    'images',
    'files',
    'related',
]


def dummy_image():
    from plone.namedfile.file import NamedBlobImage
    filename = os.path.join(os.path.dirname(__file__), u'image.png')
    return NamedBlobImage(
        data=open(filename, 'r').read(),
        filename=filename
    )


class TestExport(unittest.TestCase):
    """Test that collective.contentexport is properly installed."""

    layer = COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        document = api.content.create(
            self.portal,
            'Document',
            'doc1',
            u'I ❤︎ the Pløne')
        document.description = u'This is a ❤︎ document.'
        document.text = RichTextValue(
            u"Lorem ❤︎ ipsum",
            'text/plain',
            'text/html')

    def test_export_form_renders(self):
        """Test if the export_form can be rendered."""
        view = api.content.get_view('export_view', self.portal, self.request)
        results = view()
        self.assertIn(
            '<form action="http://nohost/plone/@@export_view">', results)
        self.assertIn(
            '<option value="Document" title="Page">Page (1)</option>', results)

    def test_simple_export(self):
        doc2 = api.content.create(
            self.portal,
            'Document',
            'doc2',
            u'I also ❤︎ the Pløne')
        doc2.text = RichTextValue(
            u"Lorem ❤︎ ipsum",
            'text/plain',
            'text/html')
        view = api.content.get_view('export_view', self.portal, self.request)
        for export_format in formats:
            results = view(export_type=export_format, portal_type='Document')
            self.assertTrue(results)

    def test_blacklist(self):
        view = api.content.get_view('export_view', self.portal, self.request)
        result = view('json', 'Document', blacklist=[])
        length = len(json.loads(result)[0])
        result = view('json', 'Document', blacklist=['id'])
        self.assertEqual(
            len(json.loads(result)[0]), length - 1)
        result = view('json', 'Document', blacklist=['id', 'text', 'subjects'])
        self.assertEqual(
            len(json.loads(result)[0]), length - 3)

    def test_image_exports(self):
        image = api.content.create(
            self.portal,
            'Image',
            'image1',
            u'❤︎ly Pløne Image')
        image.description = "This is my image."
        image.image = dummy_image()
        view = api.content.get_view('export_view', self.portal, self.request)
        view(export_type='images', portal_type='Image')
        self.assertEqual(
            view.request.response.headers['content-disposition'],
            'attachment; filename="images.zip"')
        self.assertTrue(
            int(view.request.response.headers['content-length']) > 1500)
