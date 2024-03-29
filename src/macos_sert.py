import os
import ssl
import stat
import sys

STAT_0o775 = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
              | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP
              | stat.S_IROTH | stat.S_IXOTH)


def sert():
    if sys.platform != 'darwin':
        return

    openssl_dir, openssl_cafile = os.path.split(
        ssl.get_default_verify_paths().openssl_cafile)

    import certifi

    # change working directory to the default SSL directory
    os.chdir(openssl_dir)
    relpath_to_certifi_cafile = os.path.relpath(certifi.where())
    print(" -- removing any existing file or link")
    try:
        os.remove(openssl_cafile)
    except FileNotFoundError:
        pass
    print(" -- creating symlink to certifi certificate bundle")
    os.symlink(relpath_to_certifi_cafile, openssl_cafile)
    print(" -- setting permissions")
    os.chmod(openssl_cafile, STAT_0o775)
    print(" -- update complete")
