# -*- coding: utf-8 -*-
"""Export tests for this package."""
from collective.contentexport.testing import COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING  # noqa
from persistent.list import PersistentList
from plone import api
from plone.app.textfield.value import RichTextValue
from z3c.relationfield import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified
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
        doc2.subject = (u'❤', u'Plone')
        doc2.description = u'Ich mag Sönderzeichen'
        view = api.content.get_view('export_view', self.portal, self.request)
        results = view(export_type='json', portal_type='Document')
        results = json.loads(results)
        self.assertEquals(u'❤, Plone', results[1]['subjects'])
        self.assertEquals(doc2.description, results[1]['description'])

    def test_all_export_formats(self):
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

    def test_images_export(self):
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
        size = int(view.request.response.headers['content-length'])
        self.assertTrue(1500 < size < 1600)

    def test_files_export(self):
        file1 = api.content.create(
            self.portal,
            'File',
            'file1',
            u'❤︎ly Pløne File')
        file1.description = "This is my file."
        file1.file = dummy_image()
        view = api.content.get_view('export_view', self.portal, self.request)
        view(export_type='files', portal_type='File')
        self.assertEqual(
            view.request.response.headers['content-disposition'],
            'attachment; filename="files.zip"')
        size = int(view.request.response.headers['content-length'])
        self.assertTrue(1500 < size < 1600)

    def test_relations_export(self):
        image = api.content.create(
            self.portal,
            'Image',
            'image1',
            u'❤︎ly Pløne Image')
        image.description = "This is my image."
        image.image = dummy_image()
        file1 = api.content.create(
            self.portal,
            'File',
            'file1',
            u'❤︎ly Pløne File')
        file1.description = "This is my file."
        file1.file = dummy_image()
        file_without_blob = api.content.create(
            self.portal,
            'File',
            'file-without-blob',
            u'Pløne File without a blob')
        # Add relations
        doc = self.portal['doc1']
        intids = getUtility(IIntIds)
        doc.relatedItems = PersistentList()
        doc.relatedItems.append(RelationValue(intids.getId(image)))
        doc.relatedItems.append(RelationValue(intids.getId(file1)))
        doc.relatedItems.append(RelationValue(intids.getId(file_without_blob)))
        modified(doc)
        view = api.content.get_view('export_view', self.portal, self.request)
        view(export_type='related', portal_type='Document')
        self.assertEqual(
            view.request.response.headers['content-disposition'],
            'attachment; filename="related.zip"')
        size = int(view.request.response.headers['content-length'])
        self.assertTrue(3050 < size < 3150)
