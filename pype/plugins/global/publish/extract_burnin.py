import os
import subprocess
import pype.api
import json
import pyblish


class ExtractBurnin(pype.api.Extractor):
    """
    Extractor to create video with pre-defined burnins from
    existing extracted video representation.

    It will work only on represenations having `burnin = True` or
    `tags` including `burnin`
    """

    label = "Quicktime with burnins"
    order = pyblish.api.ExtractorOrder + 0.03
    families = ["review", "burnin"]
    optional = True

    def process(self, instance):
        if "representations" not in instance.data:
            raise RuntimeError("Burnin needs already created mov to work on.")

        # TODO: expand burnin data list to include all usefull keys
        burnin_data = {
            "username": instance.context.data['user'],
            "asset": os.environ['AVALON_ASSET'],
            "task": os.environ['AVALON_TASK'],
            "start_frame": int(instance.data['startFrame']),
            "version": "v" + str(instance.context.data['version'])
        }
        self.log.debug("__ burnin_data1: {}".format(burnin_data))
        for i, repre in enumerate(instance.data["representations"]):
            self.log.debug("__ i: `{}`, repre: `{}`".format(i, repre))

            if "burnin" not in repre.get("tags", []):
                continue

            stagingdir = repre["stagingDir"]
            filename = "{0}".format(repre["files"])

            name = "_burnin"
            movieFileBurnin = filename.replace(".mov", "") + name + ".mov"

            full_movie_path = os.path.join(stagingdir, repre["files"])
            full_burnin_path = os.path.join(stagingdir, movieFileBurnin)
            self.log.debug("__ full_burnin_path: {}".format(full_burnin_path))

            burnin_data = {
                "input": full_movie_path.replace("\\", "/"),
                "output": full_burnin_path.replace("\\", "/"),
                "burnin_data": burnin_data
            }

            self.log.debug("__ burnin_data2: {}".format(burnin_data))

            json_data = json.dumps(burnin_data)
            scriptpath = os.path.join(os.environ['PYPE_MODULE_ROOT'],
                                      "pype",
                                      "scripts",
                                      "otio_burnin.py")

            self.log.debug("Burnin scriptpath: {}".format(scriptpath))

            try:
                p = subprocess.Popen(
                    [os.getenv("PYPE_PYTHON_EXE"), scriptpath, json_data]
                )
                p.wait()
                if not os.path.isfile(full_burnin_path):
                    self.log.error(
                        "Burnin file wasn't created succesfully")
            except Exception as e:
                raise RuntimeError("Burnin script didn't work: `{}`".format(e))

            if os.path.exists(full_burnin_path):
                repre_update = {
                    "files": movieFileBurnin,
                    "name": repre["name"] + name
                }
                instance.data["representations"][i].update(repre_update)
