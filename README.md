flymirror.py
============

A reusable scraping/mirroring command-line tool. Will use provided "rules" to traverse and save anything you can GET with HTTP.

Requires Python 3.x and [Requests](http://docs.python-requests.org/en/latest/). Test script requires [responses](https://github.com/getsentry/responses).


General idea
------------

We download a page.

We find a bunch of URLs in that page and download them. Then we find URLs in *those* pages, and download them. Et cetera.

We only save the files that we want.

Because we do it all concurrently it can be quite fast.

Because we're just a single file with few dependencies, we're easy to use.


Usage
-----

This script is basically a configurable scraper, so unless you have a configuration, it doesn't do anything. Pass it the configuration to use as a command line parameter.

  flymirror.py sample_conf.tsv

The test script will use the existing sample_conf.tsv. To test, just run `test.py`.


Config file format
------------------

The config file format is intended to make it easier to write regular expressions without multiple layers of quoting and escaping. In fact, the config file format has no quoting or escaping at all. It is a TSV format. Multiple tabs in a row are considered a single tab, which allows you to align columns if you want.

The first row is special. It must contain a set of configuration options of the form `option=value`, separated by tabs.

  start=<no default>	url to start mirroring from (must match a rule or nothing will happen)
  workers=5				number of workers to use for mirroring

After the first row, each new row is a "rule" -- it must include the following fields, in order:

  urlmatch		regex	required	rule is used when this regex matches the page URL
  find			regex	optional	indicates where in the page to find more URLs to continue mirroring
  transform		string	optional	string to use to format the urls found with "find"
  saveas		string	optional	filename to save the downloaded document to

If a row starts with `URLMATCH`, it is ignored, assuming that the row is being used as a table header.

If a row starts with `DISCARD`, it is ignored, which can be used for comments.

If a row starts with `VARS`, all following `name=value` pairs will be stored as variables which can be used in the rules. This can prevent you from having to retype stuff a lot.

Some rules can "include" a variable using the `{name}` syntax from Python string formatting, as documented below:

* `urlmatch` can reference any declared `VARS`. Note that this conflicts with regex syntax. Rule substitution is applied before the regex is parsed.
* `find` cannot reference any variables.
* `transform` can reference any declared `VARS` as well as any named capture groups from `find`.
* `saveas` can reference any declared `VARS` as well as any named capture groups from `urlmatch`.