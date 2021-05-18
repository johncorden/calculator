from unittest import TestCase
import sys
import pytest

sys.path.append("/home/darkskylo/Projects/PiniParser/src")

from pini_parser import mark_file

PATH_TO_TEST_FILES = "/home/darkskylo/Projects/PiniParser/tests/c_files/"

class TestMe(TestCase):
    def test_simple_if_case(self):
        marked_vars = mark_file(PATH_TO_TEST_FILES + "Test_if_1.c", ["main@x"])
        print(marked_vars)
        assert set(marked_vars) == set(['main@else[1]@a', 'main@x'])

    def test_nested_if(self):
        marked_vars = mark_file(PATH_TO_TEST_FILES + "Test_if_2.c", ["main@x"])
        assert (set(marked_vars)) == set(['main@if[1]@a', 'main@x'])

    def test_nested_if_with_piniata_decalred_outside(self):
        marked_vars = mark_file(PATH_TO_TEST_FILES + "Test_if_3.c", ["main@x"])
        print(marked_vars)
        assert set(marked_vars) == set(['main@a', 'main@else[1]@if[3]@r', 'main@else[1]@if[3]@z', 'main@x'])

    def test_simple_for(self):
        marked_vars = mark_file(PATH_TO_TEST_FILES + "Test_for_1.c", ["main@x"])
        assert set(marked_vars) == set(['main@for[1]@i', "main@z", "main@x"])

    def test_netsed_for(self):
        marked_vars = mark_file(PATH_TO_TEST_FILES + "Test_for_2.c", ["main@x"])
        print(marked_vars)
        assert set(marked_vars) == set(['main@p', "main@for[2]@z", "main@for[1]@i", "main@x"])

