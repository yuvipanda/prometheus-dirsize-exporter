# prometheus-dirsize-exporter

[![PyPI version](https://badge.fury.io/py/prometheus-dirsize-exporter.svg)](https://badge.fury.io/py/prometheus-dirsize-exporter)

Export directory size metrics efficiently.

## Why?

When providing multi-user interactive computing services (with a HPC cluster
or with JupyterHub), it's very helpful to know the home directory sizes of
each user over time. However, as NFS is often used, running `du` constantly
takes a long time, uses too many IOPS that we may not have many of, and is
plain inefficient.

This project provides a way to keep track of directory sizes with a *budgeted*
amount of IOPS. You can ask it to take however much time it needs but not
use more than 100 IOPS, and it will do that. We do not necessarily need very
up to date directory size metrics, so this is ok.

## Installation

Install the package from PyPI:

```bash
pip install prometheus-dirsize-exporter
```

## Running

You can start the process from the commandline:

```bash
dirsize-exporter <path-to-parent-directory> <iops-budget> <wait-time-in-minutes>
```

For example, to export metrics about directories under `/home`, using no more
than 200 IO operations per second, updating every 60minutes, you would run:

```bash
dirsize-exporter /home 200 60
```

You can check out the metrics by hitting `http://localhost:8000`. The port can
be controlled via a `--port` argument.

## Metrics recorded

The following metrics are recorded for all top level subidrectories of the
parent directory:

- Total Size (in bytes)
- Last Modified (including all the descendents)
- Total Number of Entries (Files, directories & symlinks)
- Processing Time required to gather this information
  This is only reported if `--enable-detailed-processing-time-metric` flag is
  passed, to prevent possible explosion of stored size of prometheus metrics
  when collected. This information is also not particularly useful outside
  of debugging this exporter, and as it varies each run, compresses poorly.
- Last updated

## Limitations

- As directory contents might change in the course of a single run as we wait
  for budgets to become available, information about a directory may not be
  exactly correct immediately.
- Because we do not spread the IOPS through time, the IO usage is 'spiky' -
  all IOPS get done at the beginning of a second, and then it goes silent.
  If you have a big IOPS budget, this can cause performance degradation.
