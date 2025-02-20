import pyblish.api


from ayon_fusion.api.lib import get_current_comp
from ayon_core.pipeline.publish import get_errored_instances_from_context


class SelectInvalidAction(pyblish.api.Action):
    """Select invalid nodes in Fusion when plug-in failed.

    To retrieve the invalid nodes this assumes a static `get_invalid()`
    method is available on the plugin.

    """

    label = "Select invalid"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):
        errored_instances = get_errored_instances_from_context(
            context,
            plugin=plugin,
        )

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        invalid = list()
        for instance in errored_instances:
            invalid_nodes = plugin.get_invalid(instance)
            if invalid_nodes:
                if isinstance(invalid_nodes, (list, tuple)):
                    invalid.extend(invalid_nodes)
                else:
                    self.log.warning(
                        "Plug-in returned to be invalid, "
                        "but has no selectable nodes."
                    )

        if not invalid:
            # Assume relevant comp is current comp and clear selection
            self.log.info("No invalid tools found.")
            comp = get_current_comp()
            flow = comp.CurrentFrame.FlowView
            flow.Select()  # No args equals clearing selection
            return

        # Assume a single comp
        first_tool = invalid[0]
        comp = first_tool.Comp()
        flow = comp.CurrentFrame.FlowView
        flow.Select()  # No args equals clearing selection
        names = set()
        for tool in invalid:
            flow.Select(tool, True)
            comp.SetActiveTool(tool)
            names.add(tool.Name)
        self.log.info(
            "Selecting invalid tools: %s" % ", ".join(sorted(names))
        )


class SelectToolAction(pyblish.api.Action):
    """Select invalid output tool in Fusion when plug-in failed.

    """

    label = "Select saver"
    on = "failed"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):
        errored_instances = get_errored_instances_from_context(
            context,
            plugin=plugin,
        )

        # Get the invalid nodes for the plug-ins
        self.log.info("Finding invalid nodes..")
        tools = []
        for instance in errored_instances:

            tool = instance.data.get("tool")
            if tool is not None:
                tools.append(tool)
            else:
                self.log.warning(
                    "Plug-in returned to be invalid, "
                    f"but has no saver for instance {instance.name}."
                )

        if not tools:
            # Assume relevant comp is current comp and clear selection
            self.log.info("No invalid tools found.")
            comp = get_current_comp()
            flow = comp.CurrentFrame.FlowView
            flow.Select()  # No args equals clearing selection
            return

        # Assume a single comp
        first_tool = tools[0]
        comp = first_tool.Comp()
        flow = comp.CurrentFrame.FlowView
        flow.Select()  # No args equals clearing selection
        names = set()
        for tool in tools:
            flow.Select(tool, True)
            comp.SetActiveTool(tool)
            names.add(tool.Name)
        self.log.info(
            "Selecting invalid tools: %s" % ", ".join(sorted(names))
        )
