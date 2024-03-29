import argparse
import os
import re
import datetime
from dateutil.parser import parse
from pathlib import Path
import exiftool
from classes.validate_folder import ValidateFolder
import shutil


def log_message(message='', debug_only=False):
    if (verbose and not debug_only) or (debug and debug_only):
        print('[LOG]: %r' % message)


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

    parser.add_argument(
        '--move',
        help='flag to move the files instead of copying them',
        required=False,
        default=False,
        action='store_true'
    )

    parser.add_argument(
        '--replace-file',
        help='flag to replace the file if it already exists at the destination',
        required=False,
        default=False,
        action='store_true'
    )

    args = parser.parse_args()
    return getattr(args, 'source_dir'), getattr(args, 'dest_dir'), getattr(args, 'dry_run'), getattr(args, 'verbose'), \
           getattr(args, 'debug'), getattr(args, 'move'), getattr(args, 'replace_file')


def parse_folder(folder, batch_number, batch_size, callback):
    with os.scandir(folder) as it:
        chunk = list(zip(range(batch_size), it))
        chunk_len = len(chunk)

        while chunk_len != 0:
            log_message('Handling batch [%d-%d]' % (batch_number * min(batch_size, chunk_len), (batch_number * min(batch_size, chunk_len) + min(batch_size, chunk_len))), debug_only=True)
            list_of_files = list()
            for _, entry in chunk:
                log_message('Handling file %s' % entry.name, debug_only=True)
                if entry.name.startswith('.') or entry.is_dir():
                    log_message('Ignoring file %s' % entry.name, debug_only=True)
                    continue
                if entry.is_file():
                    log_message('Adding file %s' % entry.name, debug_only=True)
                    list_of_files.append(os.path.join(folder, entry.name))

            log_message('Calling callback', debug_only=True)
            callback(list_of_files)
            chunk = list(zip(range(batch_size), it))
            chunk_len = len(chunk)
            batch_number += 1

        it.close()
        return list_of_files


def generate_action_map(metadata, folder):
    action_map = {}
    for d in metadata:
        action_map[d['SourceFile']] = generate_path(d, folder)
    return action_map


def generate_path(d, folder):
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

    if not create_date:
        return

    year, month, day = create_date
    full_path = os.path.join(folder, str(year).zfill(2), str(month).zfill(2), str(day).zfill(2))
    log_message('creating destination path %s' % full_path)
    if dry_run is False:
        Path(full_path).mkdir(parents=True, exist_ok=True)
    return full_path


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


def handle_file(file, destination):
    dest_folder = os.path.join(destination, '')
    full_dest_file_path = os.path.join(dest_folder, os.path.basename(file))
    log_message('%s file %s to destination %s' % (action, file, dest_folder))

    if replace_file is False and os.path.isfile(full_dest_file_path):
        log_message('file %s already exists at destination %s' % (file, dest_folder))
        return

    if dry_run is False:
        if move is True:
            shutil.move(file, os.path.join(destination, ''))
        else:
            shutil.copy2(file, os.path.join(destination, ''))


def handle_files(files):
    if not files:
        return
    with exiftool.ExifTool() as et:
        log_message('Reading metadata for %r' % files)
        metadata = et.get_metadata_batch(files)

    move_map = generate_action_map(metadata, dest_dir)
    for file, destination in move_map.items():
        try:
            handle_file(file, destination)
        except shutil.Error as err:
            log_message(
                '%s file %s to destination %s failed with %r' % (action, file, destination, err),
                debug_only=True
            )
            pass


if __name__ == '__main__':
    source_dir, dest_dir, dry_run, verbose, debug, move, replace_file = parse_cli_arguments()
    if dry_run is True:
        verbose = True
    log_message("started sorter with the following arguments: %r" % {
        'source_dir': source_dir,
        'dest_dir': dest_dir,
        'dry_run': dry_run,
        'verbose': verbose,
        'debug': debug,
        'replace_file': replace_file
    })
    batch_number = 0
    batch_size = 100
    action = "Move" if move else "Copy"

    parse_folder(source_dir, batch_number, batch_size, handle_files)
