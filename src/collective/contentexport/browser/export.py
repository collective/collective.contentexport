# -*- coding: utf-8 -*-
from Products.CMFPlone.utils import safe_callable
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from StringIO import StringIO
from openpyxl import Workbook
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
import unicodecsv
import zipfile

_marker = []
log = logging.getLogger(__name__)


class ExportView(BrowserView):
    """Export data from dexterity-types in various formats.

    :param export_type: [required] The type of export
        Supported options:
        - 'xlsx': Excel 2010 Format
        - 'csv': csv File
        - 'json': json dump
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

        if export_type == 'xlsx':
            result = make_xslx(all_fieldnames, data)
            filename = "%s_export.xlsx" % portal_type
            with NamedTemporaryFile() as tmpfile:
                result.save(tmpfile.name)
                tmpfile.seek(0)
                self.request.response.setHeader('Content-Type', 'text/xlsx')
                self.request.response.setHeader(
                    'Content-Disposition',
                    'attachment; filename="%s"' % filename)
                return file(tmpfile.name).read()

        if export_type == 'csv':
            result = make_csv(all_fieldnames, data)
            filename = "%s_export.csv" % portal_type
            self.request.response.setHeader('Content-Type', 'text/csv')
            self.request.response.setHeader(
                'Content-Disposition',
                'attachment; filename="%s"' % filename)
            return result.getvalue()

        if export_type == 'json':
            pretty = json.dumps(data, sort_keys=True, indent=4)
            self.request.response.setHeader('Content-type', 'application/json')
            return pretty

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
        brains = catalog(portal_type=portal_type)
        for brain in brains:
            obj = brain.getObject()
            item_dict = dict()

            for fieldname, field in all_fields:
                if getattr(obj, fieldname, _marker) is _marker:
                    continue
                else:
                    value = getattr(obj, fieldname)
                    if not value:
                        continue

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
                    value = value().fCommon()

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
            item_dict['id'] = brain.id
            item_dict['url'] = brain.getURL()
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
        brains = catalog(portal_type=portal_type)
        blobs_found = False
        for brain in brains:
            obj = brain.getObject()
            for fieldname, field in fields:
                blob = None
                value = field.get(field.interface(obj))
                if not value:
                    continue

                if blob_type == 'related':
                    if IRelationChoice.providedBy(field):
                        # manualy filter for fields
                        # if fieldname not in ['primary_picture']:
                        #     continue
                        if value and not value.isBroken():
                            rel_obj = value.to_object
                            if rel_obj.portal_type == 'Image':
                                blob = rel_obj.image
                            elif rel_obj.portal_type == 'File':
                                blob = rel_obj.file
                else:
                    blob = value
                if blob:
                    zip_file.writestr(
                        '{0}_{1}/{2}'.format(
                            brain.UID,  # or: brain.id.upper(),
                            fieldname,
                            str((blob.filename).encode("utf8"))),
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


def make_csv(all_fieldnames, data):
    """Transform a list of strings (header) and a dict to a csv.
    """
    result = StringIO()
    writer = unicodecsv.DictWriter(
        result,
        fieldnames=sorted(all_fieldnames),
        delimiter=';',
        quoting=unicodecsv.QUOTE_MINIMAL
    )
    writer.writeheader()
    for data_dict in data:
        writer.writerow(data_dict)
    return result


def excel_style(col):
    """ Convert number to excel-style cell name.
    """
    LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = []
    while col:
        col, rem = divmod(col-1, 26)
        result[:0] = LETTERS[rem]
    return ''.join(result)


def make_xslx(all_fieldnames, data):
    """Transform a list of strings (header) and a dict to a xlsx-workbook.
    """
    columnname_mapping = dict()
    for index, name in enumerate(all_fieldnames, start=1):
        col = excel_style(index)
        columnname_mapping[name] = col

    wb = Workbook(guess_types=True)
    ws = wb.active
    ws.title = "Export"
    ws.append(all_fieldnames)
    for row, data_dict in enumerate(data, start=2):
        for k, v in data_dict.items():
            cellname = '%s%s' % (columnname_mapping[k], row)
            ws[cellname] = v
    return wb


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
