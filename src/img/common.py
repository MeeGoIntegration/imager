"""
Common Imager functions
"""

from urlparse import urlparse

try:
    import pykickstart.parser as ksparser
    import pykickstart.version as ksversion
    from pykickstart.handlers.control import commandMap
    from pykickstart.handlers.control import dataMap
except:
    import mic.3rdparty.pykickstart.parser as ksparser
    import mic.3rdpary.pykickstart.version as ksversion
    from mic.3rdparty.pykickstart.handlers.control import commandMap
    from mic.3rdparty.pykickstart.handlers.control import dataMap

try:
    from mic.imgcreate.kscommands import desktop
    from mic.imgcreate.kscommands import moblinrepo
    from mic.imgcreate.kscommands import micboot
except:
    from mic.kickstart.custom_commands import desktop
    from mic.kickstart.custom_commands import moblinrepo
    from mic.kickstart.custom_commands import micboot

import ConfigParser

KSCLASS = ksversion.returnClassForVersion(version=ksversion.DEVEL)

class KSHandlers(KSCLASS):
    """Helper class for parsing a kickstart file"""
    def __init__(self):
        ver = ksversion.DEVEL
        commandMap[ver]["desktop"] = desktop.Moblin_Desktop
        commandMap[ver]["repo"] = moblinrepo.Moblin_Repo
        commandMap[ver]["bootloader"] = micboot.Moblin_Bootloader
        dataMap[ver]["RepoData"] = moblinrepo.Moblin_RepoData
        KSCLASS.__init__(self, mapping=commandMap[ver])
    
def build_kickstart(base_ks, packages=[], groups=[], projects=[]):
    """Build a kickstart file using the handler class, with custom kickstart,
    packages, groups and projects.

    :param base_ks: Full path to the original kickstart file
    :param packages: list of packagenames
    :param groups: list of groupnames
    :param projects: list of rpm repository URLs

    :returns: Validated kickstart with any extra packages, groups or repourls
       added
    """
    ks = ksparser.KickstartParser(KSHandlers())
    ks.readKickstart(base_ks)
    ks.handler.packages.add(packages)
    ks.handler.packages.add(groups)
    for prj in projects:
        name = urlparse(prj).path
        name = name.replace(":/","_")
        name = name.replace("/","_")
        repo = moblinrepo.Moblin_RepoData(baseurl=prj, name=name)
        ks.handler.repo.repoList.append(repo)
    ks_txt = str(ks.handler)
    return ks_txt

def worker_config(config=None, conffile="/etc/imager/img.conf"):
    """Utility function which parses the either given or  imager configuration
        file and passes a dictionary proxy containing the configuration keys
        and values in return.

    :param config: initialized ConfigParser object
    :param conffile: Full path to ini style config file

    :returns: configuration dict
    """
    if not config:
        config = ConfigParser.ConfigParser()
        config.read(conffile)

    section = "worker"
    conf = {}
    for item in ["base_url", "base_dir", "mic_opts", "img_tmp", "vm_ssh_key",
                 "vm_base_img", "vm_kernel", "timeout", "mic_cachedir", "vm_wait"]:
        conf[item] = config.get(section, item)

    for item in ["use_kvm", "use_9p_cache"]:
        conf[item] = config.getboolean(section, item)

    if config.has_option(section, "mic_opts"):
        extra_opts = config.get(section, "mic_opts")
        extra_opts = extra_opts.split(",")
        conf["extra_opts"] = extra_opts

    return conf

