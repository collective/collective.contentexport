# -*- coding: utf-8 -*-
"""Export tests for this package."""
from collective.contentexport.testing import COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING  # noqa
from persistent.list import PersistentList
from plone import api
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import login
from plone.app.textfield.value import RichTextValue
from z3c.relationfield import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified
import json
import os
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
    image_file = os.path.join(os.path.dirname(__file__), u'image.png')
    return NamedBlobImage(
        data=open(image_file, 'r').read(),
        filename=u'image.png'
    )


class TestExport(unittest.TestCase):
    """Test that collective.contentexport is properly installed."""

    layer = COLLECTIVE_CONTENTEXPORT_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        login(self.portal, SITE_OWNER_NAME)

        document = api.content.create(
            self.portal,
            'Document',
            'doc1',
            u'I ❤︎ the Pløne')
        document.description = u'This is a ❤︎ document.'
        document.text = RichTextValue(
            u'<p>Lorem ❤︎ ipsum</p>',
            'text/html',
            'text/html')

    def test_export_form_renders(self):
        """Test if the export_form can be rendered."""
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        results = view()
        self.assertIn(
            '<form action="http://nohost/plone/@@collective_contentexport_view">', results)  # noqa
        self.assertIn(
            '<option value="Document" title="Page">Page (1)</option>', results)

    def test_simple_export(self):
        doc2 = api.content.create(
            self.portal,
            'Document',
            'doc2',
            u'I also ❤︎ the Pløne')
        doc2.text = RichTextValue(
            u'<h2>Lorem ❤︎ ipsum</h2>',
            'text/html',
            'text/html')
        doc2.subject = (u'❤', u'Plone')
        doc2.description = u'Ich mag Sönderzeichen'
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        results = view(
            export_type='json',
            portal_type='Document',
            richtext_format='text/plain')
        results = json.loads(results)
        self.assertEquals(u'❤, Plone', results[1]['subjects'])
        self.assertEquals(u' Lorem ❤︎ ipsum ', results[1]['text'])
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
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        for export_format in formats:
            results = view(export_type=export_format, portal_type='Document')
            self.assertTrue(results)

    def test_blob_formats(self):
        image = api.content.create(
            self.portal,
            'Image',
            'image1',
            u'❤︎ly Pløne Image')
        image.description = "This is my image."
        image.image = dummy_image()
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)

        results = view(
            export_type='json', portal_type='Image', blob_format='url')
        results = json.loads(results)
        self.assertEquals(len(results), 1)
        self.assertEquals(
            u'http://nohost/plone/image1/@@download/image',
            results[0]['image'])

        results = view(
            export_type='json', portal_type='Image', blob_format='zip_path')
        results = json.loads(results)
        self.assertEquals(
            u'{0}/image.png'.format(api.content.get_uuid(image)),
            results[0]['image'])

        results = view(
            export_type='json', portal_type='Image', blob_format='base64')
        results = json.loads(results)
        self.assertEquals(1580, len(results[0]['image']))

    def test_blacklist(self):
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        result = view('json', 'Document', blacklist=[])
        length = len(json.loads(result)[0])
        result = view('json', 'Document', blacklist=['id'])
        self.assertEqual(
            len(json.loads(result)[0]), length - 1)
        result = view('json', 'Document', blacklist=['id', 'text', 'subjects'])
        self.assertEqual(
            len(json.loads(result)[0]), length - 3)

    def test_whitelist(self):
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        result = view('json', 'Document', whitelist=['id'])
        self.assertEqual(len(json.loads(result)[0]), 1)

        result = view('json', 'Document', whitelist=['description', 'title'])
        self.assertEqual(len(json.loads(result)[0]), 2)

        result = view('images', 'Document', whitelist=['description', 'title'])
        self.assertEquals('No images found', result)

    def test_images_export(self):
        image = api.content.create(
            self.portal,
            'Image',
            'image1',
            u'❤︎ly Pløne Image')
        image.description = "This is my image."
        image.image = dummy_image()
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        view(export_type='images', portal_type='Image')
        self.assertEqual(
            view.request.response.headers['content-disposition'],
            'attachment; filename="images.zip"')
        size = int(view.request.response.headers['content-length'])
        self.assertTrue(1300 < size < 1400)

        result = view('images', 'Image', whitelist=['description', 'title'])
        self.assertEquals('No images found', result)

        result = view('images', 'Image', blacklist=['image'])
        self.assertEquals('No images found', result)

        # make sure the ADDITIONAL_MAPPING dict is always fresh
        result = json.loads(view('json', 'Image'))[0]
        self.assertIn('url', result)
        self.assertIn('id', result)
        self.assertIn('uid', result)

    def test_files_export(self):
        file1 = api.content.create(
            self.portal,
            'File',
            'file1',
            u'❤︎ly Pløne File')
        file1.description = "This is my file."
        file1.file = dummy_image()
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        view(export_type='files', portal_type='File')
        self.assertEqual(
            view.request.response.headers['content-disposition'],
            'attachment; filename="files.zip"')
        size = int(view.request.response.headers['content-length'])
        self.assertTrue(1300 < size < 1400)

    def test_overriding(self):
        image = api.content.create(
            self.portal,
            'Image',
            'image1',
            u'❤︎ly Pløne Image')
        image.description = "This is my image."
        image.image = dummy_image()
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)

        def _get_imagename(obj):
            if obj.image:
                return obj.image.filename

        additional = {'image': _get_imagename}
        result = view(
            export_type='json', portal_type='Image', additional=additional)
        self.assertEqual(json.loads(result)[0]['image'], u'image.png')

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
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        view(export_type='related', portal_type='Document')
        self.assertEqual(
            view.request.response.headers['content-disposition'],
            'attachment; filename="related.zip"')
        size = int(view.request.response.headers['content-length'])
        self.assertTrue(2750 < size < 2800)

        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        results = view(export_type='json', portal_type='Document')
        results = json.loads(results)
        related = results[0]['relatedItems']
        self.assertEquals(len(related.split(',')), 3)
        self.assertIn('http://nohost/plone/image1/@@download/image', related)
        self.assertIn('http://nohost/plone/file1/@@download/file', related)
        # TODO: Fix this
        self.assertIn(
            'http://nohost/plone/file-without-blob/@@download/file', related)

        # make sure blacklist and whitelist work for related
        results = view(
            export_type='related',
            portal_type='Document',
            blacklist=['relatedItems'])
        self.assertEqual('No related found', results)
        results = view(
            export_type='related',
            portal_type='Document',
            whitelist=['relatedItems'])
        self.assertIsNone(results)
        self.assertEqual(
            view.request.response.headers['content-disposition'],
            'attachment; filename="related.zip"')
        size = int(view.request.response.headers['content-length'])
        self.assertTrue(2750 < size < 2800)

    def test_iterables_fallback_format(self):
        query = [{
            'i': 'Title',
            'o': 'plone.app.querystring.operation.string.contains',
            'v': u'I ❤︎ the Pløne',
        }]
        coll = api.content.create(
            self.portal,
            'Collection',
            'coll1',
            u'❤︎ly Collection',
            query=query)
        self.assertEquals(
            [i for i in coll.results()][0].getObject(),
            self.portal['doc1'])
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        results = view(export_type='json', portal_type='Collection')
        results = json.loads(results)
        self.assertEquals(
            results[0]['query'],
            [{u'i': u'Title',
              u'o': u'plone.app.querystring.operation.string.contains',
              u'v': u'I \u2764\ufe0e the Pl\xf8ne'}])

    def test_dx_fields(self):
        view = api.content.get_view(
            'collective_contentexport_dx_fields', self.portal, self.request)
        results = view(portal_type='Document')
        self.assertIn(
            '<input type="checkbox" value="relatedItems" name="blacklist" id="relatedItems">',  # noqa
            results)

    def test_passed_query(self):
        folder = api.content.create(
            self.portal,
            'Folder',
            'folder1',
            u'I äm a folder')
        doc2 = api.content.create(
            folder,
            'Document',
            'doc2',
            u'I also ❤︎ the Pløne')
        api.content.transition(doc2, to_state='published')
        view = api.content.get_view(
            'collective_contentexport_view', self.portal, self.request)
        result = view('json', 'Document')
        self.assertEqual(len(json.loads(result)), 2)

        # passing a portal type is ignored
        result = view('json', 'Document', query={'portal_type': 'Folder'})
        self.assertEqual(len(json.loads(result)), 2)

        # filter by state
        result = view('json', 'Document', query={'review_state': 'published'})
        self.assertEqual(len(json.loads(result)), 1)
        result = view('json', 'Document', query={'review_state': 'private'})
        self.assertEqual(len(json.loads(result)), 1)

        # filter by path
        path = '/'.join(folder.getPhysicalPath())
        result = view('json', 'Document', query={'path': path})
        self.assertEqual(len(json.loads(result)), 1)
        result = view(
            'json', 'Document', query={'path': {'path': path, 'depth': 0}})
        self.assertEqual(len(json.loads(result)), 0)
