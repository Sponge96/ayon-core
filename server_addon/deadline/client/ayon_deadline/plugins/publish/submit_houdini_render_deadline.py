import os
import attr
import getpass
from datetime import datetime

import pyblish.api

from ayon_core.pipeline import AYONPyblishPluginMixin
from ayon_core.lib import (
    is_in_tests,
    TextDef,
    NumberDef
)
from ayon_deadline import abstract_submit_deadline
from ayon_deadline.abstract_submit_deadline import DeadlineJobInfo


@attr.s
class DeadlinePluginInfo():
    SceneFile = attr.ib(default=None)
    OutputDriver = attr.ib(default=None)
    Version = attr.ib(default=None)
    IgnoreInputs = attr.ib(default=True)


@attr.s
class ArnoldRenderDeadlinePluginInfo():
    InputFile = attr.ib(default=None)
    Verbose = attr.ib(default=4)


@attr.s
class MantraRenderDeadlinePluginInfo():
    SceneFile = attr.ib(default=None)
    Version = attr.ib(default=None)


@attr.s
class VrayRenderPluginInfo():
    InputFilename = attr.ib(default=None)
    SeparateFilesPerFrame = attr.ib(default=True)


@attr.s
class RedshiftRenderPluginInfo():
    SceneFile = attr.ib(default=None)
    # Use "1" as the default Redshift version just because it
    # default fallback version in Deadline's Redshift plugin
    # if no version was specified
    Version = attr.ib(default="1")


class HoudiniSubmitDeadline(
    abstract_submit_deadline.AbstractSubmitDeadline,
    AYONPyblishPluginMixin
):
    """Submit Render ROPs to Deadline.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE.

    Target "local":
        Even though this does *not* render locally this is seen as
        a 'local' submission as it is the regular way of submitting
        a Houdini render locally.

    """

    label = "Submit Render to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["houdini"]
    families = ["usdrender",
                "redshift_rop",
                "arnold_rop",
                "mantra_rop",
                "karma_rop",
                "vray_rop"]
    targets = ["local"]
    settings_category = "deadline"
    use_published = True

    # presets
    export_priority = 50
    export_chunk_size = 10
    export_group = ""
    priority = 50
    chunk_size = 1
    group = ""

    @classmethod
    def get_attribute_defs(cls):
        return [
            NumberDef(
                "priority",
                label="Priority",
                default=cls.priority,
                decimals=0
            ),
            NumberDef(
                "chunk",
                label="Frames Per Task",
                default=cls.chunk_size,
                decimals=0,
                minimum=1,
                maximum=1000
            ),
            TextDef(
                "group",
                default=cls.group,
                label="Group Name"
            ),
            NumberDef(
                "export_priority",
                label="Export Priority",
                default=cls.export_priority,
                decimals=0
            ),
            NumberDef(
                "export_chunk",
                label="Export Frames Per Task",
                default=cls.export_chunk_size,
                decimals=0,
                minimum=1,
                maximum=1000
            ),
            TextDef(
                "export_group",
                default=cls.export_group,
                label="Export Group Name"
            ),
        ]

    def get_job_info(self, dependency_job_ids=None):

        instance = self._instance
        context = instance.context

        attribute_values = self.get_attr_values_from_data(instance.data)

        # Whether Deadline render submission is being split in two
        # (extract + render)
        split_render_job = instance.data.get("splitRender")

        # If there's some dependency job ids we can assume this is a render job
        # and not an export job
        is_export_job = True
        if dependency_job_ids:
            is_export_job = False

        job_type = "[RENDER]"
        if split_render_job and not is_export_job:
            # Convert from family to Deadline plugin name
            # i.e., arnold_rop -> Arnold
            plugin = (
                instance.data["productType"].replace("_rop", "").capitalize()
            )
        else:
            plugin = "Houdini"
            if split_render_job:
                job_type = "[EXPORT IFD]"

        job_info = DeadlineJobInfo(Plugin=plugin)

        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)
        job_info.Name = "{} - {} {}".format(filename, instance.name, job_type)
        job_info.BatchName = filename

        job_info.UserName = context.data.get(
            "deadlineUser", getpass.getuser())

        if is_in_tests():
            job_info.BatchName += datetime.now().strftime("%d%m%Y%H%M%S")

        # Deadline requires integers in frame range
        start = instance.data["frameStartHandle"]
        end = instance.data["frameEndHandle"]
        frames = "{start}-{end}x{step}".format(
            start=int(start),
            end=int(end),
            step=int(instance.data["byFrameStep"]),
        )
        job_info.Frames = frames

        # Make sure we make job frame dependent so render tasks pick up a soon
        # as export tasks are done
        if split_render_job and not is_export_job:
            job_info.IsFrameDependent = True

        job_info.Pool = instance.data.get("primaryPool")
        job_info.SecondaryPool = instance.data.get("secondaryPool")

        if split_render_job and is_export_job:
            job_info.Priority = attribute_values.get(
                "export_priority", self.export_priority
            )
            job_info.ChunkSize = attribute_values.get(
                "export_chunk", self.export_chunk_size
            )
            job_info.Group = self.export_group
        else:
            job_info.Priority = attribute_values.get(
                "priority", self.priority
            )
            job_info.ChunkSize = attribute_values.get(
                "chunk", self.chunk_size
            )
            job_info.Group = self.group

        job_info.Comment = context.data.get("comment")

        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "OPENPYPE_SG_USER",
            "AYON_PROJECT_NAME",
            "AYON_FOLDER_PATH",
            "AYON_TASK_NAME",
            "AYON_WORKDIR",
            "AYON_APP_NAME",
            "AYON_LOG_NO_COLORS",
        ]

        environment = {
            key: os.environ[key]
            for key in keys
            if key in os.environ
        }

        for key in keys:
            value = environment.get(key)
            if value:
                job_info.EnvironmentKeyValue[key] = value

        # to recognize render jobs
        job_info.add_render_job_env_var()

        for i, filepath in enumerate(instance.data["files"]):
            dirname = os.path.dirname(filepath)
            fname = os.path.basename(filepath)
            job_info.OutputDirectory += dirname.replace("\\", "/")
            job_info.OutputFilename += fname

        # Add dependencies if given
        if dependency_job_ids:
            job_info.JobDependencies = ",".join(dependency_job_ids)

        return job_info

    def get_plugin_info(self, job_type=None):
        # Not all hosts can import this module.
        import hou

        instance = self._instance
        context = instance.context

        hou_major_minor = hou.applicationVersionString().rsplit(".", 1)[0]

        # Output driver to render
        if job_type == "render":
            product_type = instance.data.get("productType")
            if product_type == "arnold_rop":
                plugin_info = ArnoldRenderDeadlinePluginInfo(
                    InputFile=instance.data["ifdFile"]
                )
            elif product_type == "mantra_rop":
                plugin_info = MantraRenderDeadlinePluginInfo(
                    SceneFile=instance.data["ifdFile"],
                    Version=hou_major_minor,
                )
            elif product_type == "vray_rop":
                plugin_info = VrayRenderPluginInfo(
                    InputFilename=instance.data["ifdFile"],
                )
            elif product_type == "redshift_rop":
                plugin_info = RedshiftRenderPluginInfo(
                    SceneFile=instance.data["ifdFile"]
                )
                # Note: To use different versions of Redshift on Deadline
                #       set the `REDSHIFT_VERSION` env variable in the Tools
                #       settings in the AYON Application plugin. You will also
                #       need to set that version in `Redshift.param` file
                #       of the Redshift Deadline plugin:
                #           [Redshift_Executable_*]
                #           where * is the version number.
                if os.getenv("REDSHIFT_VERSION"):
                    plugin_info.Version = os.getenv("REDSHIFT_VERSION")
                else:
                    self.log.warning((
                        "REDSHIFT_VERSION env variable is not set"
                        " - using version configured in Deadline"
                    ))

            else:
                self.log.error(
                    "Product type '%s' not supported yet to split render job",
                    product_type
                )
                return
        else:
            driver = hou.node(instance.data["instance_node"])
            plugin_info = DeadlinePluginInfo(
                SceneFile=context.data["currentFile"],
                OutputDriver=driver.path(),
                Version=hou_major_minor,
                IgnoreInputs=True
            )

        return attr.asdict(plugin_info)

    def process(self, instance):
        if not instance.data["farm"]:
            self.log.debug("Render on farm is disabled. "
                           "Skipping deadline submission.")
            return

        super(HoudiniSubmitDeadline, self).process(instance)

        # TODO: Avoid the need for this logic here, needed for submit publish
        # Store output dir for unified publisher (filesequence)
        output_dir = os.path.dirname(instance.data["files"][0])
        instance.data["outputDir"] = output_dir
