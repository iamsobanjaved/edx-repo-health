"""
Utility Functions
"""
import functools
import operator
import os
from datetime import datetime

GITHUB_DATETIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


def file_exists(repo_path, file_name):
    full_path = os.path.join(repo_path, file_name)
    return os.path.isfile(full_path)


def dir_exists(repo_path, dir_name):
    full_path = os.path.join(repo_path, dir_name)
    return os.path.isdir(full_path)


def parse_build_duration_response(json_response):
    """
    This function is responsible for parsing Github GraphQL API response and calculating build duration.

    Returns None when repo is uninitialized.
    """
    build_checks = []
    first_started_at = None
    last_completed_at = None
    total_duration = ''

    # Handle uninitialized repos (missing default branch, or no commits on branch)
    try:
        latest_commits = functools.reduce(
            operator.getitem, ["node", "defaultBranchRef", "target", "history", "edges"], json_response)
    except TypeError:
        return None

    if not latest_commits:
        return None
    else:
        latest_commit = latest_commits[0]

    for check_suite in functools.reduce(operator.getitem, ['node', 'checkSuites', 'edges'], latest_commit):

        all_check_runs = check_suite['node']['checkRuns']['edges']
        for check_run in all_check_runs:
            # If check is still in progress, skip it
            if not check_run['node']['completedAt']:
                continue

            name = check_run['node']['name']
            started_at = datetime.strptime(check_run['node']['startedAt'], GITHUB_DATETIME_FMT)
            completed_at = datetime.strptime(check_run['node']['completedAt'], GITHUB_DATETIME_FMT)

            if not first_started_at or started_at < first_started_at:
                first_started_at = started_at
            if not last_completed_at or completed_at > last_completed_at:
                last_completed_at = completed_at

            job_duration = completed_at - started_at
            total_seconds = job_duration.total_seconds()
            minutes, remaining_seconds = divmod(total_seconds, 60)

            build_checks.append({
                'name': name,
                'duration': f'{int(minutes)} minutes {int(remaining_seconds)} seconds',
                'seconds': total_seconds
            })

    if build_checks:
        # sorting checks into descending order of duration to get slowest check on top
        build_checks = sorted(build_checks, key=lambda k: k['seconds'], reverse=True)
        for check in build_checks:
            del check['seconds']

        build_duration = last_completed_at - first_started_at
        minutes, remaining_seconds = divmod(build_duration.total_seconds(), 60)

        total_duration = f'{int(minutes)} minutes {int(remaining_seconds)} seconds'

    return total_duration, build_checks
