import argparse
import os
import re
import datetime
from dateutil.parser import parse

import exiftool
from classes.validate_folder import ValidateFolder

def log_message(message=''):
    if verbose:
        print(message)


def debug_message(message=''):
    if debug:
        print(message)


def parse_cli_arguments():
    parser = argparse.ArgumentParser(
        prog='exif_sorter',
        description='reads images exif info and sorts them in chronological folder structure',
        add_help=True
    )

    parser.add_argument(
        '--source-dir',
        help='source folder of the media',
        required=True,
        type=str,
        action=ValidateFolder
    )

    parser.add_argument(
        '--dest-dir',
        help='destination folder of the new media and its generated structure',
        required=True,
        type=str,
        action=ValidateFolder
    )

    parser.add_argument(
        '--dry-run',
        help='does a dry run of the actions it will make but not doing any changes in the process',
        required=False,
        default=False,
        action='store_true'
    )

    parser.add_argument(
        '--verbose',
        help='lists all actions is takes to the stdout',
        required=False,
        default=False,
        action='store_true'
    )

    parser.add_argument(
        '--debug',
        help='lists all debug data to the stdout',
        required=False,
        default=False,
        action='store_true'
    )

    args = parser.parse_args()
    return getattr(args, 'source_dir'), getattr(args, 'dest_dir'), getattr(args, 'dry_run'), getattr(args, 'verbose'), \
           getattr(args, 'debug')


if __name__ == '__main__':
    source_dir, dest_dir, dry_run, verbose, debug = parse_cli_arguments()
    log_message("started sorter with the following arguments: %r" % {
        'source_dir': source_dir,
        'dest_dir': dest_dir,
        'dry_run': dry_run,
        'verbose': verbose,
        'debug': debug
    })

    def parse_folder(folder, batch_size, callback):
        with os.scandir(folder) as it:
            chunk = list(zip(range(batch_size), it))

            while len(chunk) != 0:
                list_of_files = list()
                for _, entry in chunk:
                    if entry.name.startswith('.'):
                        continue
                    if entry.is_file():
                        list_of_files.append(os.path.join(folder, entry.name))

                callback(list_of_files)
                chunk = list(zip(range(batch_size), it))

            it.close()
            return list_of_files

    def generate_paths(metadata):
        for d in metadata:
            generate_path(d)

    def generate_path(d):
        create_date = None
        try:
            create_date = get_date(str(d['EXIF:CreateDate']) + str(d['EXIF:OffsetTime']))
        except KeyError:
            pass

        if not create_date:
            try:
                create_date = get_date(str(d['File:FileModifyDate']))
            except KeyError:
                pass

        if not create_date:
            create_date = get_date(d['File:FileName'])

        print(create_date)

    def get_date(date_string):
        file_datetime = None

        match = re.search(r'^(\d{4}:\d{2}:\d{2})', date_string)
        if match:
            try:
                date_string = date_string[0:11].replace(':', '-') + date_string[12:]
                file_datetime = parse(date_string)
                return file_datetime.year, file_datetime.month, file_datetime.day
            except ValueError:
                pass

        match = re.search(r'((\d{8})|(\d{4}(-|\/)\d{2}(-|\/)\d{2}))', date_string)
        if not match:
            print(date_string)
            return None, None, None

        for regex in ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']:
            try:
                file_datetime = datetime.datetime.strptime(match.group(1), regex)
            except ValueError:
                pass

        if file_datetime:
            return file_datetime.year, file_datetime.month, file_datetime.day

        return None, None, None

    def print_metadata(files):
        if not files:
            return
        with exiftool.ExifTool() as et:
            metadata = et.get_metadata_batch(files)

        generate_paths(metadata)

    parse_folder(source_dir, 100, print_metadata)
