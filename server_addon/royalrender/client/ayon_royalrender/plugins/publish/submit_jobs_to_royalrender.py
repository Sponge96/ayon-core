# -*- coding: utf-8 -*-
"""Submit jobs to RoyalRender."""
import tempfile

import pyblish.api
from ayon_royalrender.api import (
    RRJob,
    Api as rrApi,
    SubmitterParameter
)
from ayon_core.pipeline.publish import KnownPublishError


class SubmitJobsToRoyalRender(pyblish.api.ContextPlugin):
    """Find all jobs, create submission XML and submit it to RoyalRender."""
    label = "Submit jobs to RoyalRender"
    order = pyblish.api.IntegratorOrder + 0.3
    targets = ["local"]

    def __init__(self):
        super(SubmitJobsToRoyalRender, self).__init__()
        self._rr_root = None
        self._rr_api = None
        self._submission_parameters = []

    def process(self, context):

        # iterate over all instances and try to find RRJobs
        jobs = []
        instance_rr_path = None
        for instance in context:
            if isinstance(instance.data.get("rrJob"), RRJob):
                jobs.append(instance.data.get("rrJob"))
            if instance.data.get("rrJobs"):
                if all(
                        isinstance(job, RRJob)
                        for job in instance.data.get("rrJobs")):
                    jobs += instance.data.get("rrJobs")
            if instance.data.get("rr_root"):
                instance_rr_path = instance.data["rr_root"]

        if jobs:
            self._rr_root = instance_rr_path
            if not self._rr_root:
                raise KnownPublishError(
                    ("Missing RoyalRender root. "
                     "You need to configure RoyalRender module."))
            self._rr_api = rrApi(self._rr_root)
            self._submission_parameters = self.get_submission_parameters()
            self.process_submission(jobs)
            return

        self.log.info("No RoyalRender jobs found")

    def process_submission(self, jobs):
        # type: ([RRJob]) -> None

        idx_pre_id = 0
        for job in jobs:
            job.PreID = idx_pre_id
            if idx_pre_id > 0:
                job.WaitForPreIDs.append(idx_pre_id - 1)
            idx_pre_id += 1

        submission = rrApi.create_submission(
            jobs,
            self._submission_parameters)

        xml = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
        with open(xml.name, "w") as f:
            f.write(submission.serialize())

        self.log.info("submitting job(s) file: {}".format(xml.name))
        self._rr_api.submit_file(file=xml.name)

    def create_file(self, name, ext, contents=None):
        temp = tempfile.NamedTemporaryFile(
            dir=self.tempdir,
            suffix=ext,
            prefix=name + '.',
            delete=False,
        )

        if contents:
            with open(temp.name, 'w') as f:
                f.write(contents)

        return temp.name

    def get_submission_parameters(self):
        return [SubmitterParameter("RequiredMemory", "0")]
