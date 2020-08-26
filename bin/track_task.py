#!/usr/bin/env python

__author__ = ["Paul Hancock", 
              "Natasha Hurley-Walker",
              "Tim Galvin"]

import os
import sys
import mysql_db as mdb

# This is the list of acceptable observation status' that are 'hard coded' in the 
# gleam-x website data/ui models. 
OBS_STATUS = ['unprocessed' , 'downloaded', 'calibrated', 'imaged', 'archived']

def queue_job(job_id, task_id, host_cluster,  submission_time, obs_id, user, batch_file, stderr, stdout, task):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO processing
    (job_id, task_id, host_cluster, submission_time, obs_id, user, batch_file, stderr, stdout, task, status)
    VALUES ( %s,%s,%s,%s,%s,%s,%s,%s,%s, %s, 'queued')
    """, (job_id, task_id, host_cluster, submission_time, obs_id, user, batch_file, stderr, stdout, task))
    conn.commit()
    conn.close()


def start_job(job_id, task_id, host_cluster, start_time):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute("""UPDATE processing 
                   SET status='started', start_time=%s 
                   WHERE job_id =%s AND task_id=%s and host_cluster=%s""", 
                (start_time, job_id, task_id, host_cluster))
    conn.commit()
    conn.close()


def finish_job(job_id, task_id, host_cluster, end_time):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute("""UPDATE processing 
                   SET status='finished', end_time=%s 
                   WHERE job_id =%s AND task_id=%s and host_cluster=%s""", 
                (end_time, job_id, task_id, host_cluster))
    conn.commit()
    conn.close()


def fail_job(job_id, task_id, host_cluster, time):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute("""UPDATE processing 
                   SET status='failed', end_time=%s 
                   WHERE job_id =%s AND task_id=%s and host_cluster=%s""", 
               (time, job_id, task_id, host_cluster))
    conn.commit()
    conn.close()

def observation_status(obs_id, status):
    """Update the observation table to inform it that obsid has been downloaded

    Args:
        obs_id (int): observation id to update the status of
        status (str): the status to insert for the observation 
    """
    conn = mdb.connect()
    cur = con.cursor()
    cur.execute("""
                UPDATE observation 
                SET status='%s' 
                WHERE obs_id=%s
                """,
                (status.lower(), obs_id, )
               )
    conn.commit()
    con.close()


def require(args, reqlist):
    """
    Determine if the the given requirements are met
    ie that the attributes in the reqlist are not None.
    """
    for r in reqlist:
        if not getattr(args, r):
            print "Directive {0} requires argument {1}".format(args.directive, r)
            sys.exit()
        
        # an sqlite to mysql change
        if isinstance(args.__dict__[r], str) and 'date +%s' in args.__dict__[r]:
            args.__dict__[r] = args.__dict__[r].replace('date +%s', 'NOW()')
            
        if r == 'status' and r.lower() not in OBS_STATUS:
            print "Observation status {0} is not in the allowed list {1}".format(args.__dict__[r], OBS_STATUS)
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
    ps.add_argument('--status', type=str, help='observation status, must belong to {0}'.format(OBS_STATUS), default=None)

    args = ps.parse_args()

    args.user = os.environ['USER']
    # This try will be removed completely at some point soon
    try:
        args.host_cluster = os.environ['HOST_CLUSTER']
    except KeyError:
        args.host_cluster = os.environ['HOST']

    if args.directive.lower() == 'queue':
        require(args, ['jobid', 'taskid', 'host_cluster', 'submission_time', 'obs_id', 'user', 'batch_file', 'stderr', 'stdout', 'task'])
        queue_job(args.jobid, args.taskid, args.host_cluster, args.submission_time, args.obs_id, args.user, args.batch_file, args.stderr, args.stdout, args.task)
    
    elif args.directive.lower() == 'start':
        require(args, ['jobid', 'taskid', 'host_cluster', 'start_time'])
        start_job(args.jobid, args.taskid, args.host_cluster, args.start_time)
    
    elif args.directive.lower() == 'finish':
        require(args, ['jobid', 'taskid', 'host_cluster', 'finish_time'])
        finish_job(args.jobid, args.taskid, args.host_cluster, args.finish_time)
    
    elif args.directive.lower() == 'fail':
        require(args, ['jobid', 'taskid', 'host_cluster', 'finish_time'])
        fail_job(args.jobid, args.taskid, args.host_cluster, args.finish_time)
    
    elif args.directive.lower() == 'obs_status':
        require(args, ['obs_id','status'])
        observation_status(args.obs_id, args.status)
    
    else:
        print "I don't know what you are asking; please include a queue/start/finish/fail directive"
