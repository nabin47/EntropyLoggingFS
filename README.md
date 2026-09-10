# EntropyLoggingFS — FUSE Filesystem for Crypto-Ransomware Entropy Analysis

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![FUSE](https://img.shields.io/badge/FUSE-libfuse-orange.svg)](https://github.com/libfuse/libfuse)
[![Springer LNNS](https://img.shields.io/badge/Paper-Springer%20LNNS-brightgreen.svg)](#citation)

A transparent FUSE (Filesystem in Userspace) layer that intercepts file write and delete operations in real time, computes **Shannon entropy**, **block frequency randomness (NIST SP 800-22)**, and **chi-square byte distribution** metrics per file, and logs them to a structured CSV — forming the basis of a novel dataset for **crypto-ransomware behavioural detection**.

---

## Overview

Crypto-ransomware encrypts victim files, producing high-entropy ciphertext that is statistically distinct from plaintext. `EntropyLoggingFS` captures this signal at the filesystem layer without requiring kernel patches or privileged hooks. It mounts transparently over an existing directory: all reads and writes pass through normally, while the system silently records per-file statistical fingerprints.

This codebase underpins the dataset construction pipeline described in the paper listed under [Citation](#citation). If you use this code or the dataset derived from it, **you must cite that paper** (see below).

---

## Features

| Metric | Method | Description |
|---|---|---|
| **Shannon Entropy** | `_calculate_entropy` | Bit-level information density per file; high values indicate encryption or compression |
| **Block Frequency p-value** | `_block_frequency_test` | NIST SP 800-22 Block Frequency Test; p-values near 1.0 indicate uniform randomness consistent with ciphertext |
| **Chi-Square Score** | `_calculate_chi_square` | Byte-distribution uniformity; encrypted files approach uniform distribution (256-symbol flat histogram) |

All three metrics are logged on two events:
- **Write (`write`)** — captured at the start of a write (offset = 0) to snapshot the file's state early in the encryption lifecycle.
- **Delete (`unlink`)** — captured just before deletion, recording the final state.

---

## Architecture

```
Application
    │
    ▼
[ FUSE Mount Point ]          ← user interacts here normally
    │
    ▼
[ EntropyLoggingFS Layer ]    ← intercepts write / unlink
    │         │
    │         └──► _calculate_entropy()
    │         └──► _block_frequency_test()
    │         └──► _calculate_chi_square()
    │         └──► _log_metrics() ──► metrics_log.txt (CSV)
    │
    ▼
[ Underlying Root Directory ] ← actual data stored here
```

---

## Requirements

### System
- Linux (FUSE requires kernel FUSE support; present in all mainstream distributions)
- `libfuse` or `fuse3` installed:
  ```bash
  # Debian / Ubuntu
  sudo apt install fuse libfuse-dev

  # Fedora / RHEL
  sudo dnf install fuse fuse-devel
  ```

### Python
- Python 3.8+
- Dependencies:
  ```bash
  pip install fusepy scipy
  ```

> **Note:** `fusepy` is the Python binding for libfuse. On some systems you may need to use `pip install fuse-python` as an alternative if `fusepy` is unavailable.

---

## Installation

```bash
git clone https://github.com/<your-username>/EntropyLoggingFS.git
cd EntropyLoggingFS
pip install fusepy scipy
```

---

## Usage

```bash
python entropy_fs.py <root_directory> <mount_point>
```

| Argument | Description |
|---|---|
| `<root_directory>` | The real directory where files will actually be stored on disk |
| `<mount_point>` | The directory applications will see and interact with |

### Example

```bash
# Create directories
mkdir ~/real_storage ~/fuse_mount

# Mount the logging filesystem
python entropy_fs.py ~/real_storage ~/fuse_mount

# In another terminal — interact normally:
cp /some/file.docx ~/fuse_mount/
rm ~/fuse_mount/file.docx

# Metrics appear in metrics_log.txt in the working directory
cat metrics_log.txt
```

### Output Format (`metrics_log.txt`)

```
<full_file_path>,<shannon_entropy>,<block_frequency_p_value>,<chi_square_score>
```

Example line:
```
/home/user/real_storage/document.docx,3.812,0.041,14723.6
/home/user/real_storage/encrypted.docx,7.994,0.923,201.3
```

A high entropy value (approaching 8.0) combined with a block frequency p-value close to 1.0 and a low chi-square score is characteristic of AES- or RSA-encrypted content produced by ransomware.

### Unmounting

```bash
fusermount -u ~/fuse_mount
```

---

## Metric Details

### Shannon Entropy
Computed over the raw byte sequence of the file. Range: 0 (fully uniform, e.g. zero-filled) to 8.0 (maximally random — consistent with encryption). Plaintext English text typically scores 3.5–5.0; AES-encrypted files score 7.9–8.0.

### Block Frequency Test (NIST SP 800-22)
The file's byte content is converted to a binary string and divided into 128-bit blocks. The proportion of ones in each block is measured; the chi-square statistic against the expected 0.5 proportion yields a p-value. Values near 1.0 indicate randomness indistinguishable from a cryptographically strong source.

### Chi-Square Byte Distribution
The observed frequency of each of the 256 possible byte values is compared against the expected uniform frequency (`file_length / 256`). Encrypted files exhibit near-flat distributions; structured formats (PDF headers, executable preambles, natural language) show pronounced peaks.

---

## Known Limitations

- **Partial write coverage:** metrics are only recorded when a write begins at `offset == 0`. Appended writes or mid-file modifications in a multi-write sequence are not re-measured. This is intentional for dataset consistency but means incremental writes are not fully captured.
- **Double-write on `write`:** the current implementation writes data via both a direct `open`/`write` and the FUSE file handle. This is safe but redundant; a future refactor should unify to a single write path.
- **`metrics_log.txt` path:** the log is written to the working directory at launch time, not relative to the mount or root. Ensure you launch from a directory where you have write access.
- **Large files:** entropy computation loads the entire file into memory on each triggered event. This is suitable for typical document/dataset workloads but will be slow for multi-GB files.

---

## Contributing

Issues and pull requests are welcome. When contributing, please:
1. Preserve the existing metric interface (`_calculate_entropy`, `_block_frequency_test`, `_calculate_chi_square`) — these are part of the dataset specification.
2. Add tests for any new metrics before submitting.
3. Document any changes to the log format, as downstream dataset consumers depend on column ordering.

---

## Citation

> **If you use this code, dataset, or any derivative work in your research, you must cite the following paper:**

```bibtex
@inproceedings{ahmed2024novel,
  title={A novel file entropy dataset for Crypto-Ransomware detection using machine learning},
  author={Ahmed Nabin, Jubair and Haque, Md Mokammel},
  booktitle={International Conference on Machine Intelligence and Emerging Technologies},
  pages={299--314},
  year={2024},
  organization={Springer},
  doi={10.1007/978-981-96-2721-9_20}
}
```

> **Plain-text citation:**
> Jubair Ahmed Nabin. "A novel file entropy dataset for Crypto-Ransomware detection using machine learning." In *International Conference on Machine Intelligence and Emerging Technologies*, Lecture Notes in Networks and Systems. Springer, 2026. DOI: 10.1007/978-981-96-2721-9_20.

---

## License

This project is licensed under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license.

You are free to share and adapt this work for any purpose, including commercially, provided you give appropriate credit, link to the license, and indicate if changes were made.

See [LICENSE](LICENSE) for the full license text.

---

## Author

**Jubair Ahmed Nabin**  
Lecturer, Department of Computer Science and Engineering  
International University of Business Agriculture and Technology (IUBAT), Dhaka, Bangladesh  
B.Sc. in CSE, Chittagong University of Engineering & Technology (CUET)

*For research enquiries or dataset access requests, please open an issue on this repository.*
