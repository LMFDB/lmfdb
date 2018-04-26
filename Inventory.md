# LMFDB Inventory Pages

## Overview

The new pages are intended to replace the previous github inventory repository. All descriptions etc from that repository have been imported into the new app and should be visible. The new pages allow editing of display names, descriptions and type information: canonical information such as key names, number of records, and indexes cannot be edited. There is also facility to rescan the database for inventory information.

Editing can only be done once you have logged in using your normal lmfdb web credentials. As with knowls, you cannot edit using a locally running copy of the lmfdb codebase.

**Javascript is essential to use the new pages. Browser local storage is used to hold your edits until they are successfully submitted, or the reset button on an editing page is pressed.**

For problems or requests please use the *inventory* tag on the LMFDB issue tracker.

## Basic Use
### Databases
Under /inventory you will now see a listing of all databases in the LMFDB. Each database has an additional name, a "nice name" intended to be a properly formatted, human readable, descriptive name. This can be edited using the button.

### Collections
Selecting a database by clicking on its name brings you to a page containing a list of all collections in it. These also each have an editable "nice name", as well as a tag. This tag can currently be "live" for normal collections, "beta" for collections which are not yet ready or are test data etc, "ops" (see below) or "old" for collections that are deprecated or out of date.

When scanning the database, we have tried to omit all "operational" collections which exist only for internal use, such as the "random" collections. Any such collections which weren't properly identified can be set to "ops" status, and then will not be displayed in the inventory pages.

### Basic Inventory
You can view the current inventory data for a collection by clicking its name. Buttons underneath allow you to also view a listing of all record types (sets of keys), and all indexes. If logged in, the inventory and records can be edited. On each view page is a button to download the relevant data in JSON format.

Clicking the collection name shows a table of information about the collection, plus a table of all keys appearing in it. The information includes the nice name, a description and information about who is responsible and where the collection code can be found. The date that the collection was last scanned is also shown. The main table lists all keys by name, along with their type, a brief description, and an example. Types were inferred from the entries, but this can be overridden or expanded on. The type information should allow somebody to understand what this item means. Examples are also selected at random from the database, and can be overridden on the editing page.

### Editing
On the edit page for the inventory data, you will see one [+] button for each key. This expands to show textboxes for the description, the example and the type for this key. The "Submit block" button will submit your edits for that specific key. At the very bottom of the page is a "Submit" button which submits all the information in the page. Beside the "type" box there is a dropdown button giving the known types, or you can type directly into this box.

Refreshing the page or losing your internet connection should not cause any problem, and your edits should still appear. They should remain even if you accidentally go back in your browser, your submission fails or you accidentally close the tab. In event of problems, you can download a machine readable file containing your changes using the "Export" button.

The "Import" button opens a file drag-and-drop region and a Text box you can use to import data previously downloaded into the page, as for example in the previous paragraph where there was an issue submitting changes.

### Records
Records list all of the unique sets of keys that exist in a collection (the schema). Where possible, these are shown as a base or basic record, and a set of additional keys. The "base" record is calculated as the intersection of all record types, and may not actually exist in the database, in which case it is tagged "dummy". The count of each record type is also shown. Records can be given names and descriptions, for instance if a type corresponds to some mathematical object, using the "edit records" facility.

### Indices
Finally, there is a page listing all indices for a collection, with their names, and a list of pairs showing the indexed field and the ordering used. Indices do not have editable information.

### Markdown
Currently description data is displayed as plain text. This means any markdown formatting carried over from the Inventory repository will appear inline. We hope at some stage to add markdown formatting to the new viewer, but this is a work in progress.

## Refreshing the Data

Tools to rescan the database have now been added. These are under inventory/rescrape. Either a single collection, or all collections in a database can be reprocessed. This has to access every record so can take some time. While it is in progress, inventory data on affected collections cannot be edited. Currently, rescrapes **cannot be aborted once begun**.

The progress page will monitor progress and display a summary once done. The current collection progress feature is experimental: it may show 0, even if the rescrape is running. Be patient.

If keys have been removed from a collection, they will be dropped from the inventory. If inventory descriptions had been added these will be available for download once the rescrape completes, on the summary page. If you don't download these files, the data will be lost after a short time.

## Extra Controls

A few extra control functions are available under inventory/controlpanel. These allow cleaning up of data and fixing issues with locked rescrapes. These are mainly useful to developers working with the inventory.

## Direct Data Access

Most of the view and edit pages fetch their information as JSON. You can access this data directly by adding /data to the URL. A rough outline of the JSON schema for each page follows, with <> used to indicate where data should appear and what this represents.

Plain inventory JSON example:

The "specials" section contains "INFO" and "NOTES". INFO gives general information on the collection. NOTES is intended for any collection-wide notes such as limitations or info on how records are stored.

```
{
  "data": {
    <Key name>: {
      "description": <Description of this key>,
      "example": <An example of this key>,
      "type": <The type of this key>
    }
  },
  "scrape_date": <Date collection was last scanned>,
  "specials": {
    "INFO": {
      "code": <URL for code>,
      "contact": <Name or github id of collection contact>,
      "description": <A description of the collection>,
      "nice_name": <Collection nice name>,
      "status": <Status i.e. old, testing, live>
    },
    "NOTES": {
      "description": <Any notes on the collection go here>
    }
  }
}
```

Records JSON example:

"data" contains a list of dicts, each of which has the format shown. One dict per record type

```
{
  "data": [
    {
      "base": <Whether this is the base record>,
      "count": <Count of occurrences of this record in the collection>,
      "diffed": <Whether this record is given as differences from the base>,
      "hash": <A hash identifying the record>,
      "oschema": <The diffed schema as a list of strings naming the keys it uses. If record is not diffed, an empty list>,
      "schema": <The full schema of the records, as a list of strings naming the keys it uses>
    }
  ],
  "scrape_date": <Date and time record counts etc were last updated>
}
```

Indices JSON example:

"data" contains a list of dicts, each of which has the format below, one per index. The "keys" entry for each index is a list of lists (pairs), each pair comprising the name of the indexed field and it's ordering. The index is over all entries in this list. The orderings are -1: descending, 1: ascending, 2d: using 2d ordering

```
{
  "data": [
    {
      "keys": [
        [
          <name of the indexed field>,
          <ordering of the field>
        ],
        [
          <name of the indexed field>,
          <ordering of the field>
        ]
      ],
      "name": <Name of the index>
    }
  ],
  "scrape_date": <Date indices were last scanned for>
}
```
