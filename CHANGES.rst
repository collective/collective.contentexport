Changelog
=========


1.0 (2016-07-09)
----------------

- Fix tsv-Export
  [pbauer]

- Test compatibility with Plone 5.0.5
  [pbauer]


1.0b5 (2015-12-03)
------------------

- Fix UnicodeEncodeError in get_blob_url when filenames have special characters.
  [pbauer]

- Add path and review_state to exported data that is not part of the schema.
  [pbauer]


1.0b4 (2015-11-28)
------------------

- Allow to pass catalog-query to filter the exported content.
  [pbauer]


1.0b3 (2015-11-28)
------------------

- Move package to https://github.com/collective/collective.contentexport.
  [pbauer]

- No longer bind views to browserlayer to simplify package-use. Rename views
  to prevent unintended name-clashes since we no longer use the browser-layer.
  [pbauer]


1.0b2 (2015-11-06)
------------------

- Add whitelist (only export fields in the whitelist)
  [pbauer]

- Document extending and overriding the export.
  [pbauer]


1.0b1 (2015-11-05)
------------------

- Sort fieldnames in blacklist by alphabet.
  [pbauer]

- Add ability to provide additional export-methods for arbitrary data by
  extending ADDITIONAL_MAPPING.
  [pbauer]

- Add tests
  [pbauer]


1.0a2 (2015-11-04)
------------------

- Localize datetime
  [pbauer]

- Prevent uneven dimension of data-dict
  [pbauer]

- Fix blacklist
  [pbauer]


1.0a1 (2015-11-04)
------------------

- Get content from all languages.
  [pbauer]

- Add export for multiple images and files related with RelationList.
  [pbauer]

- Allow choosing blacklisted fields from the fields of the selected type.
  [pbauer]

- Use http://docs.python-tablib.org for most exports.
  [pbauer]

- Add German translations.
  [pbauer]

- Moved initial code from client-project to github.
  [pbauer]
