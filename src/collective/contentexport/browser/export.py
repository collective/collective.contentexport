# -*- coding: utf-8 -*-
from Products.CMFPlone.utils import safe_callable
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from operator import itemgetter
from plone import api
from plone.app.textfield.interfaces import IRichTextValue
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import iterSchemataForType
from plone.namedfile.interfaces import INamed
from plone.namedfile.interfaces import INamedBlobFileField
from plone.namedfile.interfaces import INamedBlobImageField
from plone.namedfile.interfaces import INamedFileField
from plone.namedfile.interfaces import INamedImageField
from tempfile import NamedTemporaryFile
from z3c.relationfield.interfaces import IRelationChoice, IRelationList
from zope.i18n import translate
from zope.schema.interfaces import IDate
from zope.schema.interfaces import IDatetime
import base64
import json
import logging
import pkg_resources
import tablib
import zipfile

# Is there a multilingual addon?
try:
    pkg_resources.get_distribution('Products.LinguaPlone')
except pkg_resources.DistributionNotFound:
    HAS_MULTILINGUAL = False
else:
    HAS_MULTILINGUAL = True

if not HAS_MULTILINGUAL:
    try:
        pkg_resources.get_distribution('plone.app.multilingual')
    except pkg_resources.DistributionNotFound:
        HAS_MULTILINGUAL = False
    else:
        HAS_MULTILINGUAL = True

_marker = []
log = logging.getLogger(__name__)


class ExportView(BrowserView):
    """Export data from dexterity-types in various formats.

    :param export_type: [required] The type of export
        Supported options:
        - 'xlsx': Excel Format
        - 'xls': Old Excel Format
        - 'csv': csv File
        - 'yaml': yaml File
        - 'json': json dump
        - 'html': html table
        - 'images': Export only images from image-fields as zip
        - 'files': Export only files from file-fields as zip
        - 'related': Export only related files and images as zip
    'images', 'files' and 'related' only export the blobs to a zip-file with
    this structure: {UID of object}/{name of the blob-field}
    :type export_type: string

    :param portal_type: [required] The content-type to export
    :type portal_type: string

    :param blob_format: The way to handle blobs
        url: absolute link (default)
        zip_path: location within the zip created when exporting blobs
        base64: base64-encoded string
    :type blob_format: string


    :param richtext_format: the mimetype to which to transform richtext
        html (default)
        plain/text:
    :type richtext_format: string

    :param blacklist: List of fieldnames to omit
    :type blacklist: list

    :param additional: Additional data to export (Not yet implemented)
        A dict with a name (for the heading) and a callable
        method to get additional data for the export from the obj.

        This is not yet implemented and so far only adds id, url and uid
        of the object
    :param additional: dict
        {'id': 'Name (string) of the exported value>,
         'method': <callable that takes the obj as sole argument>}

    """

    template = ViewPageTemplateFile('templates/export_form.pt')

    def __call__(
        self,
        export_type=None,
        portal_type=None,
        blob_format='url',
        richtext_format='html',
        blacklist=None,
        additional=None,
    ):
        """Export data in various formats."""
        if not export_type or not portal_type or not blob_format:
            return self.template()

        if not blacklist:
            blacklist = []

        if not additional:
            additional = []

        if export_type in ['images', 'files', 'related']:
            return self.export_blobs(
                portal_type, blob_type=export_type, blacklist=blacklist)

        all_fieldnames, data = self.get_export_data(
            portal_type,
            blob_format,
            richtext_format,
            blacklist)

        default_additional = ['id', 'url', 'uid']
        additional.extend(default_additional)

        all_fieldnames = list(set(additional + all_fieldnames))

        dataset = tablib.Dataset()
        dataset.dict = data

        if export_type == 'xlsx':
            result = dataset.xlsx
            return self.export_file(
                result,
                portal_type,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # noqa
                'xlsx')

        if export_type == 'xls':
            result = dataset.xls
            return self.export_file(
                result, portal_type, 'application/vnd.ms-excel', 'xls')

        if export_type == 'csv':
            result = dataset.csv
            return self.export_file(result, portal_type, 'text/csv', 'csv')

        if export_type == 'tsv':
            return dataset.tsv
            return self.export_file(
                result, portal_type, 'text/tab-separated-values', 'tsv')

        if export_type == 'yaml':
            result = dataset.yaml
            return self.export_file(result, portal_type, 'text/yaml', 'yaml')

        if export_type == 'html':
            return dataset.html

        if export_type == 'json':
            pretty = json.dumps(data, sort_keys=True, indent=4)
            self.request.response.setHeader('Content-type', 'application/json')
            return pretty

    def export_file(self, result, portal_type, mimetype, extension):
        filename = "{0}_export.{1}".format(portal_type, extension)
        with NamedTemporaryFile(mode='wb') as tmpfile:
            tmpfile.write(result)
            tmpfile.seek(0)
            self.request.response.setHeader('Content-Type', mimetype)
            self.request.response.setHeader(
                'Content-Disposition',
                'attachment; filename="%s"' % filename)
            return file(tmpfile.name).read()

    def get_export_data(
        self,
        portal_type,
        blob_format,
        richtext_format,
        blacklist
    ):
        """Return a tuple with:
        1. a list with the names of all values that are exported
        2. a list of dicts with a dict for each object. The key being the name
          of the value and the value the value.
        """
        all_fields = get_schema_info(portal_type, blacklist)
        all_fieldnames = [i[0] for i in all_fields]

        results = []
        catalog = api.portal.get_tool('portal_catalog')
        query = {'portal_type': portal_type}
        if HAS_MULTILINGUAL and 'Language' in catalog.indexes():
            query['Language'] = 'all'

        brains = catalog(portal_type=portal_type)
        for brain in brains:
            obj = brain.getObject()
            item_dict = dict()

            for fieldname, field in all_fields:
                value = field.get(field.interface(obj))
                if not value:
                    # set a value anyway to keep the dimensions of all
                    value = ''
                    # make sure we do no more transforms
                    field = None

                if IRichTextValue.providedBy(value):
                    value = transform_richtext(value, mimetype=richtext_format)

                if IRelationList.providedBy(field):
                    rel_val = []
                    for relation in value:
                        rel_val.append(get_url_for_relation(relation))
                    value = pretty_join(rel_val)

                if IRelationChoice.providedBy(field):
                    value = get_url_for_relation(value)

                if INamed.providedBy(value):
                    if blob_format == 'url':
                        value = '{0}/@@download/{1}'.format(
                            obj.absolute_url(), fieldname)
                    if blob_format == 'zip_path':
                        value = '{0}/{1}'.format(
                            api.content.get_uuid(obj),
                            str((value.filename).encode("utf8")))
                    if blob_format == 'base64':
                        value = base64.b64encode(value.data)

                if IDatetime.providedBy(field) or IDate.providedBy(field):
                    value = api.portal.get_localized_time(
                        value, long_format=True)

                if safe_callable(value):
                    value = value()

                if isinstance(value, list) or isinstance(value, tuple):
                    try:
                        value = pretty_join(value)
                    except:
                        # try using the original value
                        value = value

                item_dict[fieldname] = value

            # add some additional defaults
            # TODO: make that configurable
            all_fieldnames.append('id')
            item_dict['id'] = brain.id

            all_fieldnames.append('url')
            item_dict['url'] = brain.getURL()

            all_fieldnames.append('uid')
            item_dict['uid'] = brain.UID

            results.append(item_dict)
        return (all_fieldnames, results)

    def export_blobs(self, portal_type, blob_type, blacklist):
        """Return a zip-file with file and/or images  for the required export.
        """
        all_fields = get_schema_info(portal_type, blacklist)
        if blob_type == 'images':
            fields = [
                i for i in all_fields if
                INamedImageField.providedBy(i[1]) or
                INamedBlobImageField.providedBy(i[1])]
        elif blob_type == 'files':
            fields = [
                i for i in all_fields if
                INamedFileField.providedBy(i[1]) or
                INamedBlobFileField.providedBy(i[1])]
        elif blob_type == 'related':
            fields = [
                i for i in all_fields if
                IRelationChoice.providedBy(i[1]) or
                IRelationList.providedBy(i[1])]

        tmp_file = NamedTemporaryFile()
        zip_file = zipfile.ZipFile(tmp_file, 'w')

        catalog = api.portal.get_tool('portal_catalog')
        query = {'portal_type': portal_type}
        blobs_found = False
        if HAS_MULTILINGUAL and 'Language' in catalog.indexes():
            query['Language'] = 'all'
        for brain in catalog(query):
            obj = brain.getObject()
            for fieldname, field in fields:
                blobs = []
                value = field.get(field.interface(obj))
                if not value:
                    continue

                if blob_type != 'related':
                    blobs = [value]
                else:
                    if IRelationChoice.providedBy(field):
                        # manualy filter for fields
                        # if fieldname not in ['primary_picture']:
                        #     continue
                        rel = value
                        if rel and not rel.isBroken():
                            rel_obj = rel.to_object
                            if rel_obj.portal_type == 'Image':
                                blobs = [rel_obj.image]
                            elif rel_obj.portal_type == 'File':
                                blobs = [rel_obj.file]

                    if IRelationList.providedBy(field):
                        for rel in value:
                            if rel and not rel.isBroken():
                                rel_obj = rel.to_object
                                if rel_obj.portal_type == 'Image':
                                    blobs.append(rel_obj.image)
                                elif rel_obj.portal_type == 'File':
                                    blobs.append(rel_obj.file)

                for blob in blobs:
                    filename = str((blob.filename).encode('utf8'))
                    zip_file.writestr(
                        '{0}_{1}/{2}'.format(
                            brain.UID,  # or: brain.id.upper(),
                            fieldname,
                            filename),
                        str(blob.data)
                    )
                    blobs_found = True

        zip_file.close()
        if not blobs_found:
            return 'No {0} found'.format(blob_type)
        data = file(tmp_file.name).read()
        response = self.request.response
        response.setHeader('content-type', 'application/zip')
        response.setHeader('content-length', len(data))
        response.setHeader(
            'content-disposition',
            'attachment; filename="{0}.zip"'.format(blob_type))
        return response.write(data)

    def portal_types(self):
        """A list with info on all dexterity content types with existing items.
        """
        catalog = api.portal.get_tool('portal_catalog')
        portal_types = api.portal.get_tool('portal_types')
        results = []
        for fti in portal_types.listTypeInfo():
            if not IDexterityFTI.providedBy(fti):
                continue
            number = len(catalog(portal_type=fti.id))
            if number >= 1:
                results.append({
                    'number': number,
                    'value': fti.id,
                    'title': translate(
                        fti.title, domain='plone', context=self.request)
                })
        return sorted(results, key=itemgetter('title'))


def get_schema_info(portal_type, blacklist=None):
    """Get a flat list of all fields in all schemas for a content-type.
    """
    if blacklist is None:
        blacklist = []
    fields = []
    for schema in iterSchemataForType(portal_type):
        for fieldname in schema:
            if fieldname not in blacklist:
                fields.append((fieldname, schema.get(fieldname)))
    return fields


def get_url_for_relation(rel):
    """Get a useful URL from a relationitem.
    """
    if rel.isBroken():
        return
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog(
        path={'query': rel.to_path, 'depth': 0})
    if not brains:
        return
    brain = brains[0]
    if brain.portal_type == 'Image':
        return '{0}/@@download/image'.format(
            brain.getURL())
    elif brain.portal_type == 'File':
        return '{0}/@@download/file'.format(
            brain.getURL())
    else:
        return brain.getURL()


def transform_richtext(value, mimetype):
    """Transform RichtextValue object to a useable output-format.
    """
    if mimetype == 'html':
        return safe_unicode(value.output)
    else:
        transforms = api.portal.get_tool('portal_transforms')
        value = transforms.convertTo(
            target_mimetype=mimetype,
            orig=value.raw_encoded,
            encoding=value.encoding,
            mimetype=value.mimeType)
        return safe_unicode(value.getData())


def pretty_join(iterable):
    if iterable:
        items = [unicode(i) for i in iterable if i]
        return ', '.join(items)


class DXFields(BrowserView):

    def __call__(self, portal_type=None):
        '''Return schema fields (name and type) for the given DX typename.'''
        if not portal_type:
            self.fields = []
            return self.index()
        results = []
        for fieldname, field in get_schema_info(portal_type):
            translated_title = translate(
                field.title, domain='plone', context=self.request)
            class_name = field.__class__.__name__
            results.append({
                'id': fieldname,
                'title': '%s (%s)' % (translated_title, class_name),
                'type': class_name
            })
        self.fields = results
        return self.index()
