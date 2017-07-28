# -*- coding: utf8 -*-

"""
Utility methods for use in running workflows.
This module is responsible for the inner structure of the .tuttle directory
"""
from glob import glob
from multiprocessing import Pool, cpu_count
import multiprocessing
from shutil import rmtree
from os import remove, makedirs, getcwd
from os.path import join, isdir, isfile
from traceback import format_exception

from tuttlelib.error import TuttleError
from tuttlelib.utils import EnvVar
from tuttlelib.log_follower import LogsFollower
from time import sleep, time
import sys
import logging
import psutil


LOGGER = logging.getLogger(__name__)


def print_process_header(process, logger):
    pid = multiprocessing.current_process().pid
    msg = "{}\nRunning process {} (pid={})".format("=" * 60, process.id, pid)
    logger.info(msg)


def resources2list(resources):
    res = "\n".join(("* {}".format(resource.url) for resource in resources))
    return res


def output_signatures(process):
    result = {resource.url : str(resource.signature()) for resource in process.iter_outputs()}
    return result


# This is a free method, because it will be serialized and passed
# to another process, so it must not be linked to objects nor
# capture closures
def run_process_without_exception(process):
    print("run_process_without_exception Ok")
    multiprocessing.current_process().name = process.id
    print("After process name Ok")
    try:
        print_process_header(process, LOGGER)
        print("After print_process_header Ok")
        process._processor.run(process, process._reserved_path, process.log_stdout, process.log_stderr)
    except TuttleError as e:
        return False, str(e), None
    except Exception:
        exc_info = sys.exc_info()
        stacktrace = "".join(format_exception(*exc_info))
        error_msg = "An unexpected error have happen in tuttle processor {} : \n" \
                    "{}\n" \
                    "Process {} will not complete.".format(process._processor.name, stacktrace, process.id)
        return False, error_msg, None
    try:
        missing_outputs = process.missing_outputs()
    except Exception:
        exc_info = sys.exc_info()
        stacktrace = "".join(format_exception(*exc_info))
        error_msg = "An unexpected error have happen in tuttle while checking existence of output resources " \
                    "after process {} has run: \n" \
                    "{}\n" \
                    "Process cannot be considered complete.".format(process.id, stacktrace)
        return False, error_msg, None
    if missing_outputs:
        msg = "After execution of process {} : these resources " \
              "should have been created : \n{} ".format(process.id, resources2list(missing_outputs))
        return False, msg, None
    try:
        signatures = output_signatures(process)
    except Exception:
        exc_info = sys.exc_info()
        stacktrace = "".join(format_exception(*exc_info))
        error_msg = "An unexpected error have happen in tuttle while retrieving signature after process {} has run: " \
                    "\n{}\n" \
                    "Process cannot be considered complete.".format(process.id, stacktrace)
        return False, error_msg, None
    return True, None, signatures


def tuttle_dir(*args):
    return join('.tuttle', *args)


class WorkflowRuner:

    _processes_dir = tuttle_dir('processes')
    _logs_dir = tuttle_dir('processes', 'logs')
    _extensions_dir = tuttle_dir('extensions')

    @staticmethod
    def tuttle_dir(*args):
        return join('.tuttle', *args)

    @staticmethod
    def resources2list(resources):
        res = "\n".join(("* {}".format(resource.url) for resource in resources))
        return res

    def __init__(self, nb_workers):
        self._lt = LogsFollower()
        self._logger = WorkflowRuner.get_logger()
        self._pool = None
        if nb_workers == -1:
            self._nb_workers = int( (cpu_count() + 1) / 2)
        else :
            self._nb_workers = nb_workers
        self._free_workers = None
        self._completed_processes = []

    def start_process_in_background(self, process):
        self.acquire_worker()

        def process_run_callback(result):
            success, error_msg, signatures = result
            process.set_end(success, error_msg)
            self.release_worker()
            self._completed_processes.append((process, signatures))

        process.set_start()
        resp = self._pool.apply_async(run_process_without_exception, [process], callback = process_run_callback)
        print resp.get()

    def run_parallel_workflow(self, workflow, keep_going=False):
        """ Runs a workflow by running every process in the right order
        :return: success_processes, failure_processes :
        list of processes ended with success, list of processes ended with failure
        """
        print("run_parallel_workflow Ok")
        sleep(1)
        print("Slept 1s ok")
        sys.stdin.flush()
        # TODO create tuttle dirs only once
        WorkflowRuner.create_tuttle_dirs()
        for process in workflow.iter_processes():
            WorkflowRuner.prepare_and_assign_paths(process)
            self._lt.follow_process(process.log_stdout, process.log_stderr, process.id)

        print("Added logs to follow ok")
        sys.stdin.flush()

        failure_processes, success_processes = [], []
        print("Before starting to trace in bg ok")
        sys.stdin.flush()
        sleep(1)
        print("Slept 1s ok")
        sys.stdin.flush()
        with self._lt.trace_in_background():
            print("After starting to trace in bg ok")
            sys.stdin.flush()
            sleep(1)
            print("Slept 1s ok")
            sys.stdin.flush()
            self.init_workers()
            print("After workers are initialized in bg ok")
            sys.stdin.flush()
            sleep(1)
            print("Slept 1s ok")
            sys.stdin.flush()
            runnables = workflow.runnable_processes()
            failures = False
            while (keep_going or not failures) and (self.active_workers() or self._completed_processes or runnables):
                print("keep_going = {}".format(keep_going))
                print("failures = {}".format(failures))
                print("self.active_workers() = {}".format(self.active_workers()))
                print("self._completed_processes = {}".format(self._completed_processes))
                print("runnables = {}".format(runnables))
                print("self.workers_available() = {}".format(self.workers_available()))
                started_a_process = False
                while self.workers_available() and runnables:
                    # No error
                    process = runnables.pop()
                    print("Before start_process_in_background ok")
                    sys.stdin.flush()
                    self.start_process_in_background(process)
                    raise Exception("Stop")
                    print("After start_process_in_background ok")
                    sys.stdin.flush()
                    started_a_process = True

                handled_completed_process = False
                while self._completed_processes:
                    completed_process, signatures = self._completed_processes.pop()
                    if completed_process.success:
                        success_processes.append(completed_process)
                        workflow.update_signatures(signatures)
                        new_runnables = workflow.discover_runnable_processes(completed_process)
                        runnables.update(new_runnables)
                    else:
                        failure_processes.append(completed_process)
                        failures = True
                    handled_completed_process = True
                if handled_completed_process:
                    workflow.dump()
                    workflow.create_reports()

                if not (handled_completed_process or started_a_process):
                    sleep(1)
                    print("Slept 1s instead of 0.1 ok")
                    sys.stdin.flush()
            self.terminate_workers_and_clean_subprocesses()
        if failure_processes:
            WorkflowRuner.mark_unfinished_processes_as_failure(workflow)

        return success_processes, failure_processes

    def init_workers(self):
        self._pool = Pool(self._nb_workers)
        self._free_workers = self._nb_workers

    def terminate_workers_and_clean_subprocesses(self):
        direct_procs = set(psutil.Process().children())
        all_procs = set(psutil.Process().children(recursive=True))
        sub_procs = all_procs - direct_procs

        # Terminate cleanly direct procs instanciated by multiprocess
        self._pool.terminate()
        self._pool.join()

        # Then terminate subprocesses that have not been terminated
        for p in sub_procs:
            p.terminate()
        gone, still_alive = psutil.wait_procs(sub_procs, timeout=2)
        for p in still_alive:
            p.kill()


    def acquire_worker(self):
        assert self._free_workers > 0
        self._free_workers -= 1

    def release_worker(self):
        self._free_workers += 1

    def workers_available(self):
        return self._free_workers

    def active_workers(self):
        return self._free_workers != self._nb_workers

    @staticmethod
    def mark_unfinished_processes_as_failure(workflow):
        for process in workflow.iter_processes():
            if process.start and not process.end:
                error_msg = "This process was canceled because another process has failed"
                process.set_end(False, error_msg)
        workflow.dump()
        workflow.create_reports()

    @staticmethod
    def prepare_and_assign_paths(process):
        log_stdout = join(WorkflowRuner._logs_dir, "{}_stdout.txt".format(process.id))
        log_stderr = join(WorkflowRuner._logs_dir, "{}_err.txt".format(process.id))
        # It would be a good idea to clean up all directories before
        # running the whole workflow
        # For the moment we clean here : before folowing the logs
        if isfile(log_stdout):
            remove(log_stdout)
        if isfile(log_stderr):
            remove(log_stderr)
        reserved_path = join(WorkflowRuner._processes_dir, process.id)
        if isdir(reserved_path):
            rmtree(reserved_path)
        elif isfile(reserved_path):
            remove(reserved_path)
        process.assign_paths(reserved_path, log_stdout, log_stderr)

    @staticmethod
    def create_tuttle_dirs():
        if not isdir(WorkflowRuner._processes_dir):
            makedirs(WorkflowRuner._processes_dir)
        if not isdir(WorkflowRuner._logs_dir):
            makedirs(WorkflowRuner._logs_dir)

    @staticmethod
    def empty_extension_dir():
        if not isdir(WorkflowRuner._extensions_dir):
            makedirs(WorkflowRuner._extensions_dir)
        else:
            rmtree(WorkflowRuner._extensions_dir)
            makedirs(WorkflowRuner._extensions_dir)

    @staticmethod
    def print_preprocess_header(process, logger):
        logger.info("-" * 60)
        logger.info("Preprocess : {}".format(process.id))
        logger.info("-" * 60)

    @staticmethod
    def print_preprocesses_header():
        print("=" * 60)
        print("Running preprocesses for this workflow")
        print("=" * 60)

    @staticmethod
    def print_preprocesses_footer():
        print("=" * 60)
        print("End of preprocesses... Running the workflow")
        print("=" * 60)

    @staticmethod
    def list_extensions():
        path = join(WorkflowRuner._extensions_dir, '*')
        return glob(path)

    @staticmethod
    def get_logger():
        logger = logging.getLogger(__name__)
        formater = logging.Formatter("%(message)s")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formater)
        handler.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        return logger



class TuttleEnv(EnvVar):
    """
    Adds the 'TUTTLE_ENV' environment variable so subprocesses can find the .tuttle directory.
    """
    def __init__(self):
        directory = join(getcwd(), '.tuttle')
        super(TuttleEnv, self).__init__('TUTTLE_ENV', directory)
