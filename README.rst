.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide_addons.html
   This text does not appear on pypi or github. It is a comment.

.. image:: https://travis-ci.org/starzel/collective.contentexport.svg?branch=master
    :target: https://travis-ci.org/starzel/collective.contentexport

==============================================================================
collective.contentexport
==============================================================================


Features
--------

Exports dexterity content in various formats:

- xlsx
- xls
- csv
- tsv
- json
- yaml
- html (a table)
- zip-file containing all images from image-fields
- zip-file containing all files from file-fields
- zip-file containing related files and images from relationfields


Usage
-----

Provides a form ``/@@export_view`` to configure the export.

The form allows you to:

- Select the export type
- Select the content type to export
- Choose fields from the selected type to be ignored
- Select the format of richtext-fields (html/plaintext)
- Select the format for files and images (url, base64, location within zip-file)

collective.contentexport uses `tablib <https://pypi.python.org/pypi/tablib>`_ for several export-formats.

Compatability
-------------

collective.contentexport is tested to work in Plone 4 and Plone 5.


Installation
------------

Install collective.contentexport by adding it to your buildout::

    [buildout]

    ...

    eggs =
        collective.contentexport


and then running ``bin/buildout``


Contribute
----------

- Issue Tracker: https://github.com/starzel/collective.contentexport/issues
- Source Code: https://github.com/starzel/collective.contentexport


Support
-------

If you are having issues, please let us know at https://github.com/starzel/collective.contentexport/issues.


License
-------

The project is licensed under the GPLv2.
