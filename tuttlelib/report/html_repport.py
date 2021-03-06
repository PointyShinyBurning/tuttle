# -*- coding: utf8 -*-

from jinja2 import Template
from os import path, error
from shutil import copytree
from time import strftime, localtime
from tuttlelib.report.dot_repport import dot
from os.path import dirname, join, relpath, abspath, split
import sys


def data_path(*path_parts):
    if getattr(sys, 'frozen', False):
        # The application is frozen
        datadir = join(dirname(sys.executable), "report")
    else:
        # The application is not frozen
        # Change this bit to match where you store your data files:
        datadir = dirname(__file__)
    return join(datadir, *path_parts)



def nice_size(size):
    if size < 1000:
        return "{} B".format(size)
    elif size < 1000 * 1000:
        return "{} KB".format(size / 1024)
    elif size < 1000 * 1000 * 1000:
        return "{} MB".format(size / (1024 * 1024))
    elif size < 1000 * 1000 * 1000 * 1000:
        return "{} GB".format(size / (1024 * 1024 * 1024))


def nice_file_size(filename):
    if not filename:
        return ""
    try:
        file_size = path.getsize(filename)
        if file_size == 0:
            return "empty"
        return nice_size(file_size)
    except error:
        return ""


def format_resource(resource, workflow):
    sig = workflow.signature(resource.url)
    return {
        'url': resource.url,
        'signature': sig,
    }


def workflow_status(workflow):
    for process in workflow.iter_processes():
        if process.start and not process.end:
            return "NOT_FINISHED"
        if process.success is False:
            return "FAILURE"
        if not process.start:
            return "NOT_FINISHED"
    return "SUCCESS"


def path2url(path, ref_path):
    if path is None:
        return
    abs_path = abspath(path)
    rel_path = relpath(abs_path, ref_path)
    parts = split(rel_path)
    return '/'.join(parts)


def format_process(process, workflow, report_dir):
    duration = ""
    start = ""
    end = ""
    if process.start:
        start = strftime("%a, %d %b %Y %H:%M:%S", localtime(process.start))
        if process.end:
            end = strftime("%a, %d %b %Y %H:%M:%S", localtime(process.end))
            duration = process.end - process.start

    return {
        'id': process.id,
        'processor': process.processor.name,
        'start': start,
        'end': end,
        'duration': duration,
        'log_stdout': path2url(process.log_stdout, report_dir),
        'log_stdout_size': nice_file_size(process.log_stdout),
        'log_stderr': path2url(process.log_stderr, report_dir),
        'log_stderr_size': nice_file_size(process.log_stderr),
        'outputs': (format_resource(resource, workflow) for resource in process.iter_outputs()),
        'inputs': (format_resource(resource, workflow) for resource in process.iter_inputs()),
        'code': process.code,
        'success': process.success,
        'error_message': process.error_message,
    }


def ensure_assets(dest_dir):
    assets_dir = path.join(dest_dir, 'html_report_assets')
    if not path.isdir(assets_dir):
        copytree(data_path('html_report_assets', ''), assets_dir)


def create_html_report(workflow, filename):
    """ Write an html file describing the workflow
    :param workflow:
    :param filename: path to the html fil to be generated
    :return: None
    """
    file_dir = path.dirname(filename)
    ensure_assets(file_dir)
    tpl_filename = data_path("report_template.html")
    with open(tpl_filename, 'rb') as ftpl:
        t = Template(ftpl.read().decode('utf8'))
    processes = [format_process(p, workflow, abspath(file_dir)) for p in workflow.iter_processes()]
    preprocesses = [format_process(p, workflow, abspath(file_dir)) for p in workflow.iter_preprocesses()]
    with open(filename, 'wb') as fout:
        content = t.render(processes=processes, preprocesses=preprocesses, dot_src=dot(workflow), status=workflow_status(workflow))
        fout.write(content.encode('utf8)'))
