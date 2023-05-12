import os
import sys
import errno
import math
from collections import Counter
from fuse import FUSE, FuseOSError, Operations
from scipy.stats import chi2

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
    
    def _block_frequency_test(self, data, block_size=128):
        if not data:
            return 1
        num_blocks = len(data) // block_size
        proportions = []
        for i in range(num_blocks):
            block = data[i * block_size:(i + 1) * block_size]
            ones_count = block.count('1')
            proportions.append(ones_count / block_size)
        chi_square = 4 * block_size * sum([(p - 0.5)**2 for p in proportions])
        p_value = chi2.sf(chi_square, num_blocks - 1)
        return p_value
    
    def _calculate_chi_square(self, data):
        if not data:
            return 0
        observed_freqs = Counter(data)
        expected_freq = len(data) / 256
        chi_square = sum([(observed_freq - expected_freq)**2 / expected_freq for observed_freq in observed_freqs.values()])
        return chi_square
    
    def _log_metrics(self, path, entropy, block_frequency_p_value, chi_square):
        with open("metrics_log.txt", "a") as f:
            f.write(f"{path}: Entropy={entropy}, Block Frequency p-value={block_frequency_p_value}, Chi-square={chi_square}\n")

    # def _log_entropy(self, path, entropy):
    #     with open("entropy_log.txt", "a") as f:
    #         f.write(f"{path}: {entropy}\n")

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
        block_frequency_p_value = self._block_frequency_test(format(int.from_bytes(data, 'big'), '08b'))
        chi_square = self._calculate_chi_square(data)
        self._log_metrics(full_path, entropy, block_frequency_p_value, chi_square)
        return len(data)

    def unlink(self, path):
        full_path = self._full_path(path)
        with open(full_path, 'rb') as f:
            data = f.read()
        entropy = self._calculate_entropy(data)
        block_frequency_p_value = self._block_frequency_test(format(int.from_bytes(data, 'big'), '08b'))
        chi_square = self._calculate_chi_square(data)
        self._log_metrics(full_path, entropy, block_frequency_p_value, chi_square)
        os.unlink(full_path)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'usage: {sys.argv[0]} <root> <mountpoint>')
        sys.exit(1)

    # fuse = FUSE(EntropyLoggingFS(sys.argv[1]), sys.argv[2], foreground=True)
    fuse = FUSE(EntropyLoggingFS(sys.argv[1]), sys.argv[2], foreground=True, allow_other=True, default_permissions=True)
