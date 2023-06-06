import os
import time
from collections import namedtuple

DirInfo = namedtuple("DirInfo", ["size", "latest_mtime", "entries_count"])

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
            wait_period_in_s = (ONE_S_IN_NS - (time.monotonic_ns() - self._last_iops_reset_time) + 1) / ONE_S_IN_NS
            time.sleep(wait_period_in_s)
            self._io_calls_since_last_reset = 0
            self._last_iops_reset_time = time.monotonic_ns()

        return_value = func(*args, **kwargs)
        self._io_calls_since_last_reset += 1
        return return_value

    def get_dir_info(self, path: str) -> DirInfo:
        self_statinfo = os.stat(path)

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
        entries_count = len(files) + 1 # Include this directory as an entry

        for f in files:
            # Do not follow symlinks, as that may lead to double counting a symlinked
            # file's size.
            stat_info = self.do_iops_action(os.stat, f, follow_symlinks=False)
            total_size += stat_info.st_size
            if latest_mtime < stat_info.st_mtime:
                latest_mtime = stat_info.st_mtime

        for d in dirs:
            dirinfo = self.get_dir_info(d)
            total_size += dirinfo.size
            entries_count += dirinfo.entries_count
            if latest_mtime < dirinfo.latest_mtime:
                latest_mtime = dirinfo.latest_mtime

        return DirInfo(total_size, latest_mtime, entries_count)

d = BudgetedDirInfoWalker(10)
print(d.get_dir_info("."))
