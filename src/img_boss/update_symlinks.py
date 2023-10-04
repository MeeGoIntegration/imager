#!/usr/bin/python
"""Updates symlinks to repositories for image building to stay in sync with
build paths.


:term:`Workitem` fields IN:

:Parameters:
    ev.namespace(string):
        Namespace to use, see here:
        http://wiki.meego.com/Release_Infrastructure/BOSS/OBS_Event_List
    project(string):
        Name of symlink project to get symlink target from

:term:`Workitem` fields OUT:

:Returns:
    result(Boolean):
        True if the update was successfull
    msg(list):
        List of error messages

"""
import os
from boss.obs import BuildServiceParticipant


class ParticipantHandler(BuildServiceParticipant):
    """Participant class as defined by the SkyNET API."""

    def __init__(self):
        """Initializator."""

        BuildServiceParticipant.__init__(self)
        self.prefix = None

    def handle_wi_control(self, ctrl):
        """Job control thread."""
        pass

    @BuildServiceParticipant.get_oscrc
    def handle_lifecycle_control(self, ctrl):
        """Participant control thread."""
        if ctrl.message == "start":
            self.prefix = ctrl.config.get("releases", "prefix")

    @BuildServiceParticipant.setup_obs
    def handle_wi(self, wid):
        """Actual job thread."""
        wid.result = False

        if not wid.fields.project:
            raise RuntimeError("Missing mandatory field 'project'")
        project = wid.fields.project

        prj_parts = project.split(":")
        if len(prj_parts) < 2 or len(prj_parts) > 3:
            raise RuntimeError("Don't know how to handle %s" % project)

        symlink = prj_parts[-1]
        depth = 2

        while depth > 0:
            release_id = None
            platform = None
            platform, release_id, next_project = self._get_plat_rel(project)

            self._update_symlink(platform, release_id, symlink)
            if next_project:
                project = next_project

            depth = depth - 1

    def _update_symlink(self, platform, release_id, symlink):

        symlink_path = os.path.join(self.prefix, platform, symlink)
        symlink_id_path = "%s.id" % symlink_path
        release_path = os.path.join(self.prefix, platform, release_id)

        if not os.path.isdir(release_path):
            raise RuntimeError(
                "Release %s doesn't exist at %s" % (release_id, release_path)
            )

        print("creating symlink %s -> %s" % (symlink_path, release_id))
        old_umask = os.umask(000)
        try:
            if os.path.lexists(symlink_path):
                os.unlink(symlink_path)
            os.symlink(release_id, symlink_path)

            with open(symlink_id_path, 'w') as id_file:
                id_file.write(release_id)
        finally:
            os.umask(old_umask)

    def _get_plat_rel(self, start_project):

        next_project = None

        for repo in self.obs.getProjectRepositories(start_project):
            for target in self.obs.getRepositoryTargets(start_project, repo):
                next_project = target.split("/")[0]
                platform = next_project.split(":")[0]
                release_id = next_project.split(":")[-1]
                break
            break

        if not release_id:
            raise RuntimeError(
                "Couldn't determine release ID for %s" % start_project
            )

        return platform, release_id, next_project
