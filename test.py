import unittest.mock as mock
from os import remove
from os.path import exists

import responses

import flymirror

root_body = """
<a href="/api/Thing/one">followme</a>
<a href="/api/Thing/two">followme</a>
<a href="/nowhere">but not me</a>
"""
thingone_body = """
<a href="/api/dl/one.zip" id="123">downloadme</a>
"""
thingtwo_body = """
<a href="/api/dl/two.zip" id="123">downloadme</a>
"""
dlbody = "I'm a zip file! Honest!"


@mock.patch('flymirror.argv', autospec=True)
@responses.activate
def test_main(mockargv):
    responses.add(responses.GET,
                  'http://example.com/api/Root',
                  body=root_body)
    responses.add(responses.GET,
                  'http://example.com/api/Thing/one',
                  body=thingone_body)
    responses.add(responses.GET,
                  'http://example.com/api/Thing/two',
                  body=thingtwo_body)
    responses.add(responses.GET,
                  'http://example.com/api/dl/one.zip',
                  body=dlbody)
    responses.add(responses.GET,
                  'http://example.com/api/dl/two.zip',
                  body=dlbody)

    mockargv.__len__.return_value = 2
    mockargv.__getitem__.return_value = "sample_conf.tsv"
    expected_files = [('test_one.txt', dlbody), ('test_two.txt', dlbody)]

    for file, _ in expected_files:
        if exists(file):
            remove(file)

    print("Does it work?")

    flymirror.main()

    for path, expected_content in expected_files:
        assert exists(path)
        with open(path) as f:
            content = str(f.read())
            assert content == expected_content

    print("It seems to work")

test_main()
