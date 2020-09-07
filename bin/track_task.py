#!/usr/bin/env python
from __future__ import print_function

__author__ = "PaulHancock & Natasha Hurley-Walker"

import os
import sqlite3
import sys

db='/group/mwasci/nhurleywalker/GLEAM-X-pipeline/db/GLEAM-X.sqlite'

def queue_job(job_id, task_id, submission_time, obs_id, user, batch_file, stderr, stdout, task):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("""INSERT INTO processing
    ( job_id, task_id, submission_time, obs_id, user, batch_file, stderr, stdout, task, status)
    VALUES ( ?,?,?,?,?,?,?,?,?, 'queued')
    """, (job_id, task_id, submission_time, obs_id, user, batch_file, stderr, stdout, task))
    conn.commit()
    conn.close()


def start_job(job_id, task_id, start_time):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("""UPDATE processing SET status='started', start_time=? WHERE job_id =? AND task_id=?""", (start_time, job_id, task_id))
    conn.commit()
    conn.close()


def finish_job(job_id, task_id, end_time):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("""UPDATE processing SET status='finished', end_time=? WHERE job_id =? AND task_id=?""", (end_time, job_id, task_id))
    conn.commit()
    conn.close()


def fail_job(job_id, task_id, time):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("""UPDATE processing SET status='failed', end_time=? WHERE job_id =? AND task_id=?""", (time, job_id, task_id))
    conn.commit()
    conn.close()


def require(args, reqlist):
    """
    Determine if the the given requirements are met
    ie that the attributes in the reqlist are not None.
    """
    for r in reqlist:
        if not getattr(args, r):
            print("Directive {0} requires argument {1}".format(args.directive, r))
            sys.exit()
    return True

if __name__ == "__main__":

    import argparse
    ps = argparse.ArgumentParser(description='track tasks')
    ps.add_argument('directive', type=str, help='Directive', default=None)
    ps.add_argument('--jobid', type=int, help='Job id from slurm', default=None)
    ps.add_argument('--taskid', type=int, help='Task id from slurm', default=None)
    ps.add_argument('--task', type=str, help='task being run', default=None)
    ps.add_argument('--submission_time', type=int, help="submission time", default=None)
    ps.add_argument('--start_time', type=int, help='job start time', default=None)
    ps.add_argument('--finish_time', type=int, help='job finish time', default=None)
    ps.add_argument('--batch_file', type=str, help='batch file name', default=None)
    ps.add_argument('--obs_id', type=int, help='observation id', default=None)
    ps.add_argument('--stderr', type=str, help='standard error log', default=None)
    ps.add_argument('--stdout', type=str, help='standard out log', default=None)

    args = ps.parse_args()

    args.user = os.environ['USER']

    if args.directive.lower() == 'queue':
        require(args, ['jobid', 'taskid', 'submission_time', 'obs_id', 'user', 'batch_file', 'stderr', 'stdout', 'task'])
        queue_job(args.jobid, args.taskid, args.submission_time, args.obs_id, args.user, args.batch_file, args.stderr, args.stdout, args.task)
    elif args.directive.lower() == 'start':
        require(args, ['jobid', 'taskid', 'start_time'])
        start_job(args.jobid, args.taskid, args.start_time)
    elif args.directive.lower() == 'finish':
        require(args, ['jobid', 'taskid', 'finish_time'])
        finish_job(args.jobid, args.taskid, args.finish_time)
    elif args.directive.lower() == 'fail':
        require(args, ['jobid', 'taskid', 'finish_time'])
        fail_job(args.jobid, args.taskid, args.finish_time)
    else:
        print("I don't know what you are asking; please include a queue/start/finish/fail directive")
