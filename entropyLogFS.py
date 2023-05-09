import os
import sys
import errno
import math
from collections import Counter
from fuse import FUSE, FuseOSError, Operations

class EntropyLoggingFS(Operations):
    def __init__(self, root):
        self.root = root

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def _calculate_entropy(self, data):
        if not data:
            return 0
        entropy = 0
        for x in set(data):
            p_x = float(data.count(x)) / len(data)
            entropy += -p_x * math.log2(p_x)
        return entropy

    def _log_entropy(self, path, entropy):
        with open("entropy_log.txt", "a") as f:
            f.write(f"{path}: {entropy}\n")

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                   'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
    
    def create(self, path, mode, fi=None):
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def mkdir(self, path, mode):
        full_path = self._full_path(path)
        return os.mkdir(full_path, mode)


    # Other FUSE methods like readdir, mkdir, etc. should be implemented here.
    def readdir(self, path, fh):
        full_path = self._full_path(path)
        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def open(self, path, flags):
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, data, offset, fh):
        full_path = self._full_path(path)
        with open(full_path, 'rb+') as f:
            f.seek(offset)
            f.write(data)
        os.lseek(fh, offset, os.SEEK_SET)
        os.write(fh, data)
        entropy = self._calculate_entropy(data)
        self._log_entropy(full_path, entropy)
        return len(data)

    def unlink(self, path):
        full_path = self._full_path(path)
        with open(full_path, 'rb') as f:
            data = f.read()
        entropy = self._calculate_entropy(data)
        self._log_entropy(full_path, entropy)
        os.unlink(full_path)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'usage: {sys.argv[0]} <root> <mountpoint>')
        sys.exit(1)

    # fuse = FUSE(EntropyLoggingFS(sys.argv[1]), sys.argv[2], foreground=True)
    fuse = FUSE(EntropyLoggingFS(sys.argv[1]), sys.argv[2], foreground=True, allow_other=True, default_permissions=True)
