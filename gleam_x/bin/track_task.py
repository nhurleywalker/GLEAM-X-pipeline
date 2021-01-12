#!/usr/bin/env python
from __future__ import print_function

__author__ = ["Paul Hancock", "Natasha Hurley-Walker", "Tim Galvin"]

import os
import sys

if "GXTRACK" not in os.environ.keys() or os.environ["GXTRACK"] != "track":
    print("Task process tracking is disabled. ")
    sys.exit(0)

import gleam_x.db.mysql_db as mdb

# This is the list of acceptable observation status' that are 'hard coded' in the
# gleam-x website data/ui models.
OBS_STATUS = ["unprocessed", "downloaded", "calibrated", "imaged", "archived"]

# Bit of record keeping for potential future use / sanity
BATCH_OBS_IDS_TASKS = ["queue_mosaic", "start_mosaic", "finish_mosaic"]


def queue_job(
    job_id,
    task_id,
    host_cluster,
    submission_time,
    obs_id,
    user,
    batch_file,
    stderr,
    stdout,
    task,
):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute(
        """
                INSERT INTO processing
                (job_id, task_id, host_cluster, submission_time, obs_id, user, batch_file, stderr, stdout, task, status)
                VALUES 
                ( %s,%s,%s,%s,%s,%s,%s,%s,%s, %s, 'queued')
                """,
        (
            job_id,
            task_id,
            host_cluster,
            submission_time,
            obs_id,
            user,
            batch_file,
            stderr,
            stdout,
            task,
        ),
    )
    conn.commit()
    conn.close()


def start_job(job_id, task_id, host_cluster, start_time):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute(
        """UPDATE processing 
                   SET status='started', start_time=%s 
                   WHERE job_id =%s AND task_id=%s and host_cluster=%s""",
        (start_time, job_id, task_id, host_cluster),
    )
    conn.commit()
    conn.close()


def finish_job(job_id, task_id, host_cluster, end_time):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute(
        """UPDATE processing 
                   SET status='finished', end_time=%s 
                   WHERE job_id =%s AND task_id=%s and host_cluster=%s""",
        (end_time, job_id, task_id, host_cluster),
    )
    conn.commit()
    conn.close()


def fail_job(job_id, task_id, host_cluster, time):
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute(
        """UPDATE processing 
                   SET status='failed', end_time=%s 
                   WHERE job_id =%s AND task_id=%s and host_cluster=%s""",
        (time, job_id, task_id, host_cluster),
    )
    conn.commit()
    conn.close()


def observation_status(obs_id, status):
    """Update the observation table to inform it that obsid has been downloaded

    Args:
        obs_id (int): observation id to update the status of
        status (str): the status to insert for the observation 
    """
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute(
        """
                UPDATE observation 
                SET status=%s 
                WHERE obs_id=%s
                """,
        (status.lower(), obs_id,),
    )
    conn.commit()
    conn.close()


def observation_calibrator_id(obs_id, cal_id):
    """A general update function that will modify a spectied key value for a specific observation ID

    Args:
        obs_id (int): observation id to update the status of
        cali_id (int): observation id of the calibrator to insert  
        value (str):  
    """
    conn = mdb.connect()
    cur = conn.cursor()
    cur.execute(
        """
                UPDATE observation 
                SET cal_obs_id=%s 
                WHERE obs_id=%s
                """,
        (cal_id, obs_id,),
    )
    conn.commit()
    conn.close()


def queue_mosaic(
    batch_obs_ids, job_id, task_id, host_cluster, submission_time, user, subband
):
    """Creates a new item in the `mosaic` table to signify that a new batch
    of `obs_ids` are being `swarp`ed together
    """
    conn = mdb.connect()
    cur = conn.cursor()

    for obs_id in batch_obs_ids:
        cur.execute(
            """ 
                    INSERT INTO mosaic
                    (obs_id, job_id, task_id, host_cluster, submission_time, user, subband, status)
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
            (
                obs_id,
                job_id,
                task_id,
                host_cluster,
                submission_time,
                user,
                subband,
                "queued",
            ),
        )

    conn.commit()
    conn.close()


def start_mosaic(job_id, task_id, host_cluster, start_time):
    """Update all rows that form a `mos_id` job that their mosaic operation has started
    """
    conn = mdb.connect()
    cur = conn.cursor()

    cur.execute(
        """
                UPDATE mosaic
                SET status='started', start_time=%s
                WHERE job_id=%s AND task_id=%s AND host_cluster=%s
                """,
        (start_time, job_id, task_id, host_cluster),
    )

    conn.commit()
    conn.close()


def finish_mosaic(job_id, task_id, host_cluster, end_time):
    """Update all rows that form a `mos_id` job that their mosaic operation has started
    """
    conn = mdb.connect()
    cur = conn.cursor()

    cur.execute(
        """
                UPDATE mosaic
                SET status='finished', end_time=%s
                WHERE job_id=%s AND task_id=%s AND host_cluster=%s
                """,
        (end_time, job_id, task_id, host_cluster),
    )

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
            sys.exit(1)

        # an sqlite to mysql change
        if isinstance(args.__dict__[r], str) and "date +%s" in args.__dict__[r]:
            args.__dict__[r] = args.__dict__[r].replace("date +%s", "NOW()")

        if r == "status" and args.status.lower() not in OBS_STATUS:
            print(
                "Observation status `{0}` is not in the allowed list {1}. Exiting without updating. \n".format(
                    args.status, OBS_STATUS
                )
            )
            sys.exit(1)

    return True


if __name__ == "__main__":

    import argparse

    ps = argparse.ArgumentParser(description="track tasks")
    ps.add_argument("directive", type=str, help="Directive", default=None)
    ps.add_argument("--jobid", type=int, help="Job id from slurm", default=None)
    ps.add_argument("--taskid", type=int, help="Task id from slurm", default=None)
    ps.add_argument("--task", type=str, help="task being run", default=None)
    ps.add_argument("--submission_time", type=int, help="submission time", default=None)
    ps.add_argument("--start_time", type=int, help="job start time", default=None)
    ps.add_argument("--finish_time", type=int, help="job finish time", default=None)
    ps.add_argument("--batch_file", type=str, help="batch file name", default=None)
    ps.add_argument("--obs_id", type=int, help="observation id", default=None)
    ps.add_argument(
        "--cal_id", type=int, help="observation id of calibration data", default=None
    )
    ps.add_argument(
        "--batch_obs_ids",
        type=int,
        nargs="+",
        help="collection of observation ids, used only for {0} directives".format(
            BATCH_OBS_IDS_TASKS
        ),
        default=None,
    )
    ps.add_argument("--stderr", type=str, help="standard error log", default=None)
    ps.add_argument("--stdout", type=str, help="standard out log", default=None)
    ps.add_argument(
        "--status",
        type=str,
        help="observation status, must belong to {0}".format(OBS_STATUS),
        default=None,
    )
    ps.add_argument(
        "--subband",
        type=str,
        help="subband of images that are being mosaiced together",
        default=None,
    )

    args = ps.parse_args()

    args.user = os.environ["GXUSER"]
    args.host_cluster = os.environ["GXCLUSTER"]

    if args.directive.lower() == "queue":
        require(
            args,
            [
                "jobid",
                "taskid",
                "host_cluster",
                "submission_time",
                "obs_id",
                "user",
                "batch_file",
                "stderr",
                "stdout",
                "task",
            ],
        )
        queue_job(
            args.jobid,
            args.taskid,
            args.host_cluster,
            args.submission_time,
            args.obs_id,
            args.user,
            args.batch_file,
            args.stderr,
            args.stdout,
            args.task,
        )

    elif args.directive.lower() == "start":
        require(args, ["jobid", "taskid", "host_cluster", "start_time"])
        start_job(args.jobid, args.taskid, args.host_cluster, args.start_time)

    elif args.directive.lower() == "finish":
        require(args, ["jobid", "taskid", "host_cluster", "finish_time"])
        finish_job(args.jobid, args.taskid, args.host_cluster, args.finish_time)

    elif args.directive.lower() == "fail":
        require(args, ["jobid", "taskid", "host_cluster", "finish_time"])
        fail_job(args.jobid, args.taskid, args.host_cluster, args.finish_time)

    elif args.directive.lower() == "obs_status":
        require(args, ["obs_id", "status"])
        observation_status(args.obs_id, args.status)

    elif args.directive.lower() == "obs_calibrator":
        require(args, ["obs_id", "cal_id"])
        observation_calibrator_id(args.obs_id, args.cal_id)

    elif args.directive.lower() == "queue_mosaic":
        require(
            args,
            [
                "jobid",
                "taskid",
                "host_cluster",
                "submission_time",
                "batch_obs_ids",
                "user",
                "subband",
            ],
        )
        queue_mosaic(
            args.batch_obs_ids,
            args.jobid,
            args.taskid,
            args.host_cluster,
            args.submission_time,
            args.user,
            args.subband,
        )

    elif args.directive.lower() == "start_mosaic":
        require(args, ["jobid", "taskid", "host_cluster", "start_time"])
        start_mosaic(args.jobid, args.taskid, args.host_cluster, args.start_time)

    elif args.directive.lower() == "finish_mosaic":
        require(args, ["jobid", "taskid", "host_cluster", "finish_time"])
        finish_mosaic(args.jobid, args.taskid, args.host_cluster, args.finish_time)

    else:
        print(
            "I don't know what you are asking; please include a queue/start/finish/fail directive"
        )

