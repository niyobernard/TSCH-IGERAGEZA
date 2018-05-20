# Overview

This project contains the measurement traces of 802.15.4e Time Slotted Channel Hopping wireless sensor network, and tools for extracting the data from them.
Evaluation results of these traces have been used in the publication:

- M. Vilgelm, M. Gürsu, S. Zoppi, W. Kellerer, **Time Slotted Channel Hopping for Smart Metering: Measurements and Analysis of Medium Access**, IEEE SmartGridComm, Sydney, Australia, November 2016 (accepted for publication)

The data is distributed under the GNU GPLv3 license. If the data is used in a publication, we ask you to cite the above paper.
If you find any bugs or inconsistencies, please contact the authors.

# Project structure:

  `data/` - traces. Every file correspond to an experiment. Packets are recorded after their reception on the DAG root.
- `json/` - files in self-explained json notation
- `raw/` - raw data, as recorded. For the structure see below.
- `misc/`

`dataprocessing/` - python package containing tools and scripts for processing the traces. See doxygen documentation inside.
- `sgdata.yml` - anaconda environment for using the package
- `requirements.txt` - packages required (for pip users)

`matlab/` - matlab scripts

# Requirements

Required packages can be found in `dataprocessing/sgdata.yml` or `dataprocessing/requirements.txt`

# Usage

To reproduce the results of the paper, you can use provided script `dataprocessing/scripts/plot_results.py`. For example, to plot figure #8:

```bash
python plot_results.py --figure 8
```

Note that reproducing figures 4, 6 (both generated with different tools), and 7 (exemplary figure, essentially part of figure 10) is not supported in the script.

# Raw traces

Raw data files structure:

[byte #1, byte #2, ..., byte #38]\tTIMESTAMP\n
[byte #1, byte #2, ..., byte #38]\tTIMESTAMP\n

Packet structure:

|Last sender addr |last ASN     |first ASN    | sequence Nr |padding| hop #1 addr | hop #1 retx | hop #1 frequency | hop #1 RSSI | hop #2 .... until hop #6 |
|-----------------|-------------|-------------|-------------|-------|-------------|-------------|------------------|-------------|--------------------------|
| 1               | 2-6 	| 7-11        | 12-13       | 14    | 15          | 16          | 17               | 18          | 19-38                    |
