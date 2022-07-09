import argparse
from os import path


class ValidateFolder(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(ValidateFolder, self).__init__(option_strings, dest, **kwargs)
        
    def __call__(self, parser, namespace, values, option_string=None):
        if not path.isdir(values):
            print("checking value %r" % values)
            raise ValueError("%r needs to be a folder" % self.dest)

        setattr(namespace, self.dest, values)
