import os
import hou
import pyblish.api
from ayon_houdini.api import (
    lib,
    plugin
)


class CollectDataforCache(plugin.HoudiniInstancePlugin):
    """Collect data for caching to Deadline."""

    # Run after Collect Frames
    order = pyblish.api.CollectorOrder + 0.11
    families = ["ass", "pointcache", "redshiftproxy", "vdbcache", "model"]
    targets = ["local", "remote"]
    label = "Collect Data for Cache"

    def process(self, instance):
        creator_attribute = instance.data["creator_attributes"]
        farm_enabled = creator_attribute["farm"]
        instance.data["farm"] = farm_enabled
        if not farm_enabled:
            self.log.debug("Caching on farm is disabled. "
                           "Skipping farm collecting.")
            return
        # Why do we need this particular collector to collect the expected
        # output files from a ROP node. Don't we have a dedicated collector
        # for that yet?
        # Collect expected files
        ropnode = hou.node(instance.data["instance_node"])
        output_parm = lib.get_output_parameter(ropnode)
        expected_filepath = output_parm.eval()
        instance.data.setdefault("files", list())
        instance.data.setdefault("expectedFiles", list())
        if instance.data.get("frames"):
            files = self.get_files(instance, expected_filepath)
            # list of files
            instance.data["files"].extend(files)
        else:
            # single file
            instance.data["files"].append(output_parm.eval())
        cache_files = {"_": instance.data["files"]}
        # Convert instance family to pointcache if it is bgeo or abc
        # because ???
        self.log.debug(instance.data["families"])
        instance.data.update({
            "plugin": "Houdini",
            "publish": True
        })
        instance.data["families"].append("publish.hou")
        instance.data["expectedFiles"].append(cache_files)

        self.log.debug("{}".format(instance.data))

    def get_files(self, instance, output_parm):
        """Get the files with the frame range data

        Args:
            instance (_type_): instance
            output_parm (_type_): path of output parameter

        Returns:
            files: a list of files
        """
        directory = os.path.dirname(output_parm)

        files = [
            os.path.join(directory, frame).replace("\\", "/")
            for frame in instance.data["frames"]
        ]

        return files
