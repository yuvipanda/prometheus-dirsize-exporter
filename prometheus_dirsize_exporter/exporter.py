import os
import time
import argparse
from typing import Optional
from collections import namedtuple
from prometheus_client import start_http_server
from . import metrics

DirInfo = namedtuple(
    "DirInfo", ["path", "size", "latest_mtime", "oldest_mtime", "entries_count", "processing_time"]
)

ONE_S_IN_NS = 1_000_000_000


class BudgetedDirInfoWalker:
    def __init__(self, iops_budget=100):
        """
        iops_budget is number of io operations allowed every second.
        """
        self.iops_budget = iops_budget
        # Use _ns to avoid subtractive messiness possible when using floats
        self._last_iops_reset_time = time.monotonic_ns()
        self._io_calls_since_last_reset = 0

    def do_iops_action(self, func, *args, **kwargs):
        """
        Perform an action that does IO, waiting if necessary so it is within budget.

        All IO performed should be wrapped with this function, so we do not exceed
        our budget. Each call to this function is treated as one IO.
        """
        if time.monotonic_ns() - self._last_iops_reset_time > ONE_S_IN_NS:
            # One second has passed since last time we reset the budget clock
            # So we reset it again now, regardless of how many iops have happened
            self._io_calls_since_last_reset = 0
            self._last_iops_reset_time = time.monotonic_ns()

        if self._io_calls_since_last_reset > self.iops_budget:
            # We are over budget, so we wait for 1s + 1ns since last reset
            # IO can be performed once this is wait is done. We reset the budget clock
            # after our wait.
            wait_period_in_s = (
                ONE_S_IN_NS - (time.monotonic_ns() - self._last_iops_reset_time) + 1
            ) / ONE_S_IN_NS
            time.sleep(wait_period_in_s)
            self._io_calls_since_last_reset = 0
            self._last_iops_reset_time = time.monotonic_ns()

        return_value = func(*args, **kwargs)
        self._io_calls_since_last_reset += 1
        return return_value

    def get_dir_info(self, path: str) -> Optional[DirInfo]:
        start_time = time.monotonic()
        try:
            self_statinfo = os.stat(path)
        except FileNotFoundError:
            # Directory was deleted from the time it was listed and now
            return None

        # Get absolute path of all children of directory
        children = [
            os.path.abspath(os.path.join(path, c))
            for c in self.do_iops_action(os.listdir, path)
        ]
        # Split into files and directories for different kinds of traversal.
        # We count symlinks as files, but do not resolve them when checking size -
        # but do include them in the mtime calculation.
        files = [
            c
            for c in children
            if self.do_iops_action(os.path.isfile, c)
            or self.do_iops_action(os.path.islink, c)
        ]
        dirs = [c for c in children if self.do_iops_action(os.path.isdir, c)]

        total_size = self_statinfo.st_size
        latest_mtime = self_statinfo.st_mtime
        oldest_mtime = self_statinfo.st_mtime
        entries_count = len(files) + 1  # Include this directory as an entry

        for f in files:
            # Do not follow symlinks, as that may lead to double counting a symlinked
            # file's size.
            try:
                stat_info = self.do_iops_action(os.stat, f, follow_symlinks=False)
            except FileNotFoundError:
                # File might have been deleted from the time we listed it anda now
                continue
            total_size += stat_info.st_size
            if latest_mtime < stat_info.st_mtime:
                latest_mtime = stat_info.st_mtime
            if oldest_mtime > stat_info.st_mtime:
                oldest_mtime = stat_info.st_mtime

        for d in dirs:
            dirinfo = self.get_dir_info(d)
            if dirinfo is None:
                # The directory was deleted between the time the listing
                # was done and now.
                continue
            total_size += dirinfo.size
            entries_count += dirinfo.entries_count
            if latest_mtime < dirinfo.latest_mtime:
                latest_mtime = dirinfo.latest_mtime
            if oldest_mtime > dirinfo.latest_mtime:
                oldest_mtime = dirinfo.latest_mtime

        return DirInfo(
            os.path.basename(path),
            total_size,
            latest_mtime,
            oldest_mtime,
            entries_count,
            time.monotonic() - start_time,
        )

    def get_subdirs_info(self, dir_path):
        try:
            children = [
                os.path.abspath(os.path.join(dir_path, c))
                for c in self.do_iops_action(os.listdir, dir_path)
            ]

            dirs = [c for c in children if self.do_iops_action(os.path.isdir, c)]

            for c in dirs:
                yield self.get_dir_info(c)
        except OSError as e:
            if e.errno == 116:
                # See https://github.com/yuvipanda/prometheus-dirsize-exporter/issues/6
                # Stale file handle, often because the file we were looking at
                # changed in the NFS server via another client in such a way that
                # a new inode was created. This is a race, so let's just ignore and
                # not report any data for this file. If this file was recreated,
                # our next run should catch it
                return None
            # Any other errors should just be propagated
            raise
        except PermissionError as e:
            if e.errno == 13:
                # See https://github.com/yuvipanda/prometheus-dirsize-exporter/issues/5
                # A file we are trying to open is owned in such a way that we don't have
                # access to it. Ideally this should not really happen, but when it does,
                # we just ignore it and continue.
                return None
            # Any other permission error should be propagated
            raise

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "parent_dir",
        help="The directory to whose subdirectories will have their information exported",
    )
    argparser.add_argument(
        "iops_budget", help="Number of IO operations allowed per second", type=int
    )
    argparser.add_argument(
        "wait_time_minutes",
        help="Number of minutes to wait before data collection runs",
        type=int,
    )
    # Don't report amount of time it took to process each directory by
    # default. This is highly variable, and probably causes prometheus to
    # not compress metrics very well. Not particularly useful outside of
    # debugging the exporter itself.
    argparser.add_argument(
        "--enable-detailed-processing-time-metric",
        help="Report amount of time it took to process each directory",
        action="store_true"
    )
    argparser.add_argument(
        "--port", help="Port for the server to listen on", type=int, default=8000
    )

    args = argparser.parse_args()

    start_http_server(args.port)
    while True:
        walker = BudgetedDirInfoWalker(args.iops_budget)
        for subdir_info in walker.get_subdirs_info(args.parent_dir):
            metrics.TOTAL_SIZE.labels(subdir_info.path).set(subdir_info.size)
            metrics.LATEST_MTIME.labels(subdir_info.path).set(subdir_info.latest_mtime)
            metrics.OLDEST_MTIME.labels(subdir_info.path).set(subdir_info.oldest_mtime)
            metrics.ENTRIES_COUNT.labels(subdir_info.path).set(
                subdir_info.entries_count
            )
            if args.enable_detailed_processing_time_metric:
                metrics.PROCESSING_TIME.labels(subdir_info.path).set(
                    subdir_info.processing_time
                )
            metrics.LAST_UPDATED.labels(subdir_info.path).set(time.time())
            print(f"Updated values for {subdir_info.path}")
        time.sleep(args.wait_time_minutes * 60)


if __name__ == "__main__":
    main()
