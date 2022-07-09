import argparse
import os

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
    batch_size = 2

    source_dir, dest_dir, dry_run, verbose, debug = parse_cli_arguments()
    log_message("started sorter with the following arguments: %r" % {
        'source_dir': source_dir,
        'dest_dir': dest_dir,
        'dry_run': dry_run,
        'verbose': verbose,
        'debug': debug
    })

    def get_batch(it, size, prefix, list_of_files = list()):
        chunk = list(zip(range(size), it))
        if len(chunk) == 0:
            it.close()
            return

        for _, entry in chunk:
            if entry.name.startswith('.'):
                continue
            if entry.is_file():
                list_of_files.append(os.path.join(prefix, entry.name))
            if entry.is_dir():
                dir_path = os.path.join(prefix, entry.name)
                with os.scandir(dir_path) as it:
                    batch = get_batch(it, size, dir_path)
                    if batch:
                        list_of_files.extend(batch)

        return list_of_files

    with os.scandir(source_dir) as source_it:
        files_batch = get_batch(source_it, batch_size, source_dir)

        while files_batch:
            with exiftool.ExifTool() as et:
                metadata = et.get_metadata_batch(files_batch)
            for d in metadata:
                print("{:20.20} {:20.20}".format(d["SourceFile"], d["File:FileModifyDate"]))

            files_batch = list()
            get_batch(source_it, batch_size, source_dir, files_batch)