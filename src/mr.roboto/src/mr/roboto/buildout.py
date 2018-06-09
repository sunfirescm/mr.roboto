# -*- coding: utf-8 -*-
from collections import OrderedDict
from collections import UserDict
from configparser import ConfigParser
from configparser import ExtendedInterpolation
from tempfile import mkdtemp

import git
import logging
import pickle
import re
import shutil


logger = logging.getLogger('mr.roboto')

PATH_RE = re.compile(
    '(\w+://)(.+@)*([\w\d\.]+)(:[\d]+){0,1}/(?P<path>.+(?=\.git))(\.git)',
)


class Source(object):

    def __init__(self, protocol=None, url=None, push_url=None, branch=None):
        self.protocol = protocol
        self.url = url
        self.pushurl = push_url
        self.branch = branch

    def create_from_string(self, source_string):
        protocol, url, extra_1, extra_2, extra_3 = (
            lambda a, b, c=None, d=None, e=None: (a, b, c, d, e)
        )(*source_string.split())
        for param in [extra_1, extra_2, extra_3]:
            if param is not None:
                key, value = param.split('=')
                setattr(self, key, value)
        self.protocol = protocol
        self.url = url
        if self.pushurl is not None:
            self.pushurl = self.pushurl.split('=')[-1]
        if self.branch is None:
            self.branch = 'master'
        else:
            self.branch = self.branch.split('=')[-1]
        return self

    @property
    def path(self):
        if self.url:
            match = PATH_RE.match(self.url)
            if match:
                return match.groupdict()['path']
        return None


class SourcesFile(UserDict):

    def __init__(self, file_location):
        self.file_location = file_location

    @property
    def data(self):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        config.optionxform = str
        with open(self.file_location) as f:
            config.read_file(f)
        sources_dict = OrderedDict()
        for name, value in config['sources'].items():
            source = Source().create_from_string(value)
            sources_dict[name] = source
        return sources_dict

    def __iter__(self):
        return self.data.__iter__()


class CheckoutsFile(UserDict):

    def __init__(self, file_location):
        self.file_location = file_location

    @property
    def data(self):
        config = ConfigParser(interpolation=ExtendedInterpolation())
        with open(self.file_location) as f:
            config.read_file(f)
        checkouts = config.get('buildout', 'auto-checkout')
        checkout_list = checkouts.split('\n')
        return checkout_list


class PloneCoreBuildout(object):
    PLONE_COREDEV_LOCATION = 'git://github.com/plone/buildout.coredev.git'

    def __init__(self, core_version=None):
        self.core_version = core_version
        self.location = mkdtemp()
        self.clone()
        self.sources = SourcesFile(
            '{0}/sources.cfg'.format(self.location),
        )
        self.checkouts = CheckoutsFile(
            '{0}/checkouts.cfg'.format(self.location),
        )

    def clone(self):
        logger.info(
            'Commit: cloning github repository {0}, branch={1}'.format(
                self.location,
                self.core_version,
            ),
        )
        git.Repo.clone_from(
            self.PLONE_COREDEV_LOCATION,
            self.location,
            branch=self.core_version,
            depth=1,
        )

    def cleanup(self):
        shutil.rmtree(self.location)


def get_sources_and_checkouts(request):
    """Get sources.cfg and checkouts.cfg from buildout.coredev

    Get them for all major plone releases
    (see plone_versions on mr.roboto's configuration),
    process and store their data on pickle files for later usage.
    """
    sources_dict = {}
    checkouts_dict = {}

    actual_plone_versions = request.registry.settings['plone_versions']

    for plone_version in actual_plone_versions:
        msg = 'Commit: checking sources and checkouts from plone {0}'
        logger.info(msg.format(plone_version))
        buildout = PloneCoreBuildout(plone_version)

        for source in buildout.sources:
            source_obj = buildout.sources[source]
            if source_obj.path:
                key = (source_obj.path, source_obj.branch)
                if key not in sources_dict:
                    sources_dict[key] = [plone_version]
                else:
                    sources_dict[key].append(plone_version)

        checkouts_dict[plone_version] = []
        for checkout in buildout.checkouts.data:
            if checkout:
                checkouts_dict[plone_version].append(checkout)

        buildout.cleanup()

    sources_file = request.registry.settings['sources_file']
    with open(sources_file, 'w') as sf:
        sf.write(pickle.dumps(sources_dict))

    checkouts_file = request.registry.settings['checkouts_file']
    with open(checkouts_file, 'w') as sf:
        sf.write(pickle.dumps(checkouts_dict))
