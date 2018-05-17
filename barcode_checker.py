import os
import sys
from pyzbar import pyzbar
from PIL import Image
import json
import logging
import glob
import re
import subprocess
import zxing


def _atoi(text):
    return int(text) if text.isdigit() else text


def _natural_keys(text):
    """
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    """

    return [_atoi(c) for c in re.split(r'(\d+)', text)]


def get_pages(parent_folder, filename_pattern):
    def either(c):
        return '[%s%s]'%(c.lower(),c.upper()) if c.isalpha() else c
    cwd = os.getcwd()
    os.chdir(parent_folder)
    pages = glob.glob(''.join(either(char) for char in filename_pattern))
    pages.sort(key=_natural_keys)
    os.chdir(cwd)

    return pages


def _error(msg):
    # print("ERROR: %s" % msg)
    logging.error("ERROR: %s" % msg)
    raise ValueError("ERROR: %s" % msg)


def cmd(cmd_list, show_output=False):
    if isinstance(cmd_list, list):
        cmd_list = ' '.join(cmd_list)

    logging.debug("Running cmd: %s" % cmd_list)

    try:
        out = subprocess.check_output(cmd_list, stderr=subprocess.STDOUT, shell=True)
        if show_output:
            print('Output of the above command: %s' % out)
        return out
    except subprocess.CalledProcessError as e:
        logging.debug('ERROR: exception output: %s' % e.output)
        logging.error("ERROR: Could not run command %s" % cmd_list)
        # _error("Could not run command %s" % cmd_list)
        raise


def get_qr_data(image_path):
    qr_codes = pyzbar.decode(Image.open(image_path), symbols=[pyzbar.ZBarSymbol.QRCODE])

    if len(qr_codes) > 0:
        # Pick only the first QR code. We expect only one to be there.
        qr_code = qr_codes[0]
        qr_data = json.loads(qr_code.data.decode("utf-8"))
    else:
        qr_data = {'rb_id': None, 'set_id': None, 'name': None, 'page': None}

    return qr_data


def get_zxing_qr_data(image_path):
    zxing_reader = zxing.BarCodeReader()
    zxing_qr_data = zxing_reader.decode(image_path, try_harder=True)

    if zxing_qr_data is not None:
        qr_data = json.loads(zxing_qr_data.parsed)
    else:
        qr_data = {'rb_id': None, 'set_id': None, 'name': None, 'page': None}

    return qr_data


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Scan barcodes in the images in a folder.')
    parser.add_argument('-f', '--folder',
                        help='Folder with images to scan.')

    args = parser.parse_args()

    if not args.folder:
        print('Specifying a working folder to scan files is mandatory')
        logging.error('Specifying a working folder to scan files is mandatory')
        sys.exit(2)

    scan_output_directory = args.folder

    jpg_pages = get_pages(scan_output_directory, '*.jpg')
    num_images_with_zbar_qr_detected = 0
    num_images_with_zxing_qr_detected = 0

    for image_filename in jpg_pages:
        qr_data = None
        image_path = os.path.join(scan_output_directory, image_filename)
        zbar_qr_data = get_qr_data(image_path)

        if zbar_qr_data['page'] is not None:
            qr_data = zbar_qr_data
            num_images_with_zbar_qr_detected += 1
            print('++++ ZBAR: {}: {}'.format(image_filename, zbar_qr_data))
        else:
            print('==== ZBAR: {}: No QR found!!!'.format(image_filename))

        zxing_qr_data = get_zxing_qr_data(image_path)

        if zxing_qr_data['page'] is not None:
            qr_data = zxing_qr_data
            num_images_with_zxing_qr_detected += 1
            print('oooo ZXING: {}: {}'.format(image_filename, zxing_qr_data))
        else:
            print('xxxx ZXING: {}: No QR found!!!'.format(image_filename))

        if qr_data and qr_data['page'] is not None:
            name_and_ext = os.path.splitext(image_filename)
            student_name = qr_data['name'].replace(' ', '_')
            new_image_filename_wo_ext = '{}_{}_set{}_p{}'.format(student_name, qr_data['rb_id'], qr_data['set_id'], qr_data['page'])
            new_image_filename = '{}{}'.format(new_image_filename_wo_ext, name_and_ext[1])
            new_image_path = os.path.join(scan_output_directory, new_image_filename)

            i = 1
            while (image_filename != new_image_filename) and os.path.exists(new_image_path):
                new_image_filename = '{}_copy{}{}'.format(new_image_filename_wo_ext, i, name_and_ext[1])
                new_image_path = os.path.join(scan_output_directory, new_image_filename)
                i += 1

            if image_filename != new_image_filename:
                os.rename(image_path, os.path.join(scan_output_directory, new_image_filename))

        print('\n')

    print('Total number of images scanned: %d' % len(jpg_pages))
    print('\n')
    print('Num images with ZBAR QR detected: %d' % num_images_with_zbar_qr_detected)
    print('Num images ZBAR FAILED: %d' % (len(jpg_pages) - num_images_with_zbar_qr_detected))
    print('\n')
    print('Num images with ZXING QR detected: %d' % num_images_with_zxing_qr_detected)
    print('Num images ZXING FAILED: %d' % (len(jpg_pages) - num_images_with_zxing_qr_detected))
