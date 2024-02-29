import pyblish.api

from ayon_core.pipeline import get_current_folder_path
from ayon_core.pipeline.publish import (
    ValidateContentsOrder,
    PublishXmlValidationError,
)
from ayon_core.hosts.aftereffects.api import get_stub


class ValidateInstanceAssetRepair(pyblish.api.Action):
    """Repair the instance asset with value from Context."""

    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):

        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
                    and result["instance"] not in failed):
                failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)
        stub = get_stub()
        for instance in instances:
            data = stub.read(instance[0])

            data["folderPath"] = get_current_folder_path()
            stub.imprint(instance[0].instance_id, data)


class ValidateInstanceAsset(pyblish.api.InstancePlugin):
    """Validate the instance asset is the current selected context asset.

        As it might happen that multiple worfiles are opened at same time,
        switching between them would mess with selected context. (From Launcher
        or Ftrack).

        In that case outputs might be output under wrong asset!

        Repair action will use Context asset value (from Workfiles or Launcher)
        Closing and reopening with Workfiles will refresh  Context value.
    """

    label = "Validate Instance Asset"
    hosts = ["aftereffects"]
    actions = [ValidateInstanceAssetRepair]
    order = ValidateContentsOrder

    def process(self, instance):
        instance_asset = instance.data["folderPath"]
        current_asset = get_current_folder_path()
        msg = (
            f"Instance asset {instance_asset} is not the same "
            f"as current context {current_asset}."
        )

        if instance_asset != current_asset:
            raise PublishXmlValidationError(self, msg)
