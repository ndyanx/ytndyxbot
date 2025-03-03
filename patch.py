import os
import shutil

import aiopath
import jsbeautifier
import pyvideothumbnailer
import yt_dlp
import pymediainfo


def copy_modified_files(clon_path, main_path):
    for root, dirs, files in os.walk(clon_path):
        for file in files:
            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(root, clon_path)
            dest_dir = os.path.join(main_path, rel_path)
            dest_file = os.path.join(dest_dir, file)

            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            shutil.copy2(src_file, dest_file)
            print(f"Archivo {src_file} copiado a {dest_file}")


base_path = os.path.dirname(__file__)
libs = [aiopath, jsbeautifier, pyvideothumbnailer, yt_dlp, pymediainfo]
clon_paths = [os.path.join(base_path, "patch_libs", lib.__name__) for lib in libs]
main_paths = [lib.__path__[0] for lib in libs]

for clon_path, main_path in zip(clon_paths, main_paths):
    copy_modified_files(clon_path, main_path)
