import ConfigParser
from collections import defaultdict
import glob
import os

from img_web import settings

# This is awful ... re-reading FEATURESDIR so often
# It should be a class too


# features are just a ConfigParser
def get_features():
    config = ConfigParser.ConfigParser()
    for feature in glob.glob(os.path.join(settings.FEATURESDIR, '*.feature')):
        config.read(feature)
    return config


# Return a list of
def list_features():
    features = get_features()
    choices = set()
    for name in features.sections():
        if name.startswith("repositories"):
            continue
        description = name
        if features.has_option(name, "description"):
            description = features.get(name, "description")
        choices.add((name, description))
    return sorted(choices, key=lambda c: c[1])


def expand_feature(name):
    features = get_features()
    repo_sections = [section for section in features.sections() if
                     section.startswith("repositories")]
    feat = defaultdict(set)

    if features.has_option(name, "pattern"):
        feat["pattern"].add("@%s" % features.get(name, "pattern"))

    if features.has_option(name, "packages"):
        feat["packages"].update(features.get(name, "packages").split(','))

    if features.has_option(name, "repos"):
        for repo in features.get(name, "repos").split(","):
            for section in repo_sections:
                if features.has_option(section, repo):
                    feat[section].add(features.get(section, repo))
    return dict(feat)


def get_repos_packages_for_feature(f, kstype=""):
    """kstype is 'rnd' or 'release'"""
    repos_type = 'repositories-%s' % kstype
    if not kstype or repos_type not in f:
        repos_type = 'repositories'

    extra_repos = f.get(repos_type, set())
    additional_packages = f.get('packages', set())

    return (extra_repos, additional_packages)
