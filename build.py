import glob, os, zipfile
from datetime import datetime
import sys

def make_pyz():
    if not os.path.exists('bin'):
        os.mkdir('bin')

    outname = './bin/wwiser.pyz'
    zf = zipfile.ZipFile(outname, mode='w')
    zf.write('wwiser.py', arcname='__main__.py', compress_type=zipfile.ZIP_DEFLATED)

    filenames =  ['README.md']
    filenames += glob.glob('./**/*.py', recursive=True)
    filenames += glob.glob('./**/*.md')
    filenames += glob.glob('./**/viewer/resources/*')
    filenames += glob.glob('./**/viewer/resources/**/*')
    for filename in filenames:
        if 'wversion.py' in filename: #rewritten below (zipfile can't overwrite)
            continue
        zf.write(filename, compress_type=zipfile.ZIP_DEFLATED)

    if len(sys.argv) > 1: # Accept version from cli
        strdate = sys.argv[1]
        strdate = strdate.lstrip("v")
    else:
        strdate = datetime.today().strftime('%Y%m%d')
    #zf.writestr('VERSION', strdate, compress_type=zipfile.ZIP_DEFLATED)
    version = 'WWISER_VERSION = "v%s"' % (strdate)
    zf.writestr('wwiser/wversion.py', version, compress_type=zipfile.ZIP_DEFLATED) # './...' fails here

    #for viewer
    zf.write('./README.md', arcname='wwiser/viewer/resources/doc/README.md', compress_type=zipfile.ZIP_DEFLATED)
    zf.write('./doc/WWISER.md', arcname='wwiser/viewer/resources/doc/WWISER.md', compress_type=zipfile.ZIP_DEFLATED)


    zf.close()

if __name__ == "__main__":
    make_pyz()
