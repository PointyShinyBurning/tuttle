from tuttlelib.error import TuttleError
from tuttlelib.invalidation import prep_for_invalidation
from tuttlelib.project_parser import ProjectParser
from tuttlelib.workflow import Workflow
from tuttlelib.workflow_builder import WorkflowBuilder
from tuttlelib.workflow_runner import WorkflowRuner



def load_project(tuttlefile):
    pp = ProjectParser()
    workflow = pp.parse_and_check_file(tuttlefile)
    return workflow


def print_missing_input(missing):
    error_msg = "Missing the following resources to launch the workflow :\n"
    for mis in missing:
        error_msg += "* {}\n".format(mis.url)
    print(error_msg)


def print_failing_process(failing_process):
    msg = "Workflow already failed on process '{}'. Fix the process and run tuttle again.".format(failing_process.id)
    msg += "\n\nIf failure has been caused by an external factor like a connection breakdown, " \
           'use "tuttle invalidate" to reset execution then "tuttle run" again.'
    print(msg)


def print_failures(failure_processes):
    print("\nSummary : {} processe(s) have failed:".format(len(failure_processes)))
    for process in failure_processes:
        header = "== Process : {} ==".format(process.id)
        print(header)
        print(process.error_message)


def print_success():
    print("====")
    print("Done")


def print_nothing_to_do():
    print("Nothing to do")


def print_updated():
    print("Report has been updated to reflect tuttlefile")


def parse_invalidate_and_run(tuttlefile, threshold=-1, nb_workers=-1, keep_going=False):
    print("parse_invalidate_and_run Ok")

    try:
        workflow = load_project(tuttlefile)
    except TuttleError as e:
        print(e)
        return 2

    print("load_project Ok")
    workflow.discover_resources()

    missing = workflow.primary_inputs_not_available()
    if missing:
        print_missing_input(missing)
        return 2

    print("Workflow.load Ok")
    previous_workflow = Workflow.load()

    inv_collector = prep_for_invalidation(workflow, previous_workflow, [])
    print("prep_for_invalidation Ok")

    failing_process = workflow.pick_a_failing_process()
    if failing_process:
        # check before invalidate
        print_failing_process(failing_process)
        return 2

    if inv_collector.warn_and_abort_on_threshold(threshold):
        return 2
    # We have to remove resources, even if there is no previous workflow,
    # because of resources that may not have been produced by tuttle
    inv_collector.remove_resources(workflow)
    inv_collector.reset_execution_info()
    inv_collector.straighten_out_availability(workflow)
    workflow.create_reports()
    workflow.dump()
    print("invalidation Ok")

    wr = WorkflowRuner(nb_workers)
    success_processes, failure_processes = wr.run_parallel_workflow(workflow, keep_going)
    if failure_processes:
        print_failures(failure_processes)
        return 2

    if success_processes:
        print_success()
    elif inv_collector.something_to_invalidate():
        print_updated()
    else:
        print_nothing_to_do()

    return 0


def get_resources(urls):
    result = []
    pb = WorkflowBuilder()
    for url in urls:
        resource = pb.build_resource(url)
        if resource is None:
            print("Tuttle cannot understand '{}' as a valid resource url".format(url))
            return False
        result.append(resource)
    return result


def filter_invalidable_urls(workflow, urls):
    """ Returns a list of url that can be invalidated and warns about illegal urls"""
    to_invalidate = []
    for url in urls:
        resource = workflow.find_resource(url)
        if not resource:
            msg = "Ignoring {} : this resource does not belong to the workflow.".format(url)
            print(msg)
        elif not workflow.resource_available(url):
            msg = "Ignoring {} : this resource has not been produced yet.".format(url)
            print(msg)
        elif resource.is_primary():
            msg = "Ignoring {} : primary resources can't be invalidated.".format(url)
            print(msg)
        else:
            to_invalidate.append(url)
    return to_invalidate


def invalidate_resources(tuttlefile, urls, threshold=-1):
    resources = get_resources(urls)
    if resources is False:
        return 2
    previous_workflow = Workflow.load()
    if previous_workflow is None:
        print("Tuttle has not run yet ! It has produced nothing, so there is nothing to invalidate.")
        return 2
    try:
        workflow = load_project(tuttlefile)
        # TODO : add preprocessors to invalidation
    except TuttleError as e:
        print("Invalidation has failed because tuttlefile is has errors (a valid project is needed for "
              "clean invalidation) :")
        print(e)
        return 2

    workflow.discover_resources()

    to_invalidate = filter_invalidable_urls(workflow, urls)

    inv_collector = prep_for_invalidation(workflow, previous_workflow, to_invalidate)

    if inv_collector.resources_to_invalidate():
        if inv_collector.warn_and_abort_on_threshold(threshold):
            return 2
        # availability has already been cleared in rep_for_inv
        inv_collector.remove_resources(workflow)
        inv_collector.reset_execution_info()
        inv_collector.straighten_out_availability(workflow)
    reseted_failures = workflow.reset_failures()
    if inv_collector.resources_to_invalidate() or reseted_failures:
        workflow.dump()
        workflow.create_reports()

    if not inv_collector.resources_to_invalidate():
        if reseted_failures or inv_collector.something_to_invalidate():
            print_updated()
        else:
            print_nothing_to_do()
    return 0
