"""
Cobbler Module that manages the cluster configuration tool from CHAOS. For more information please see:
`GitHub - chaos/genders <https://github.com/chaos/genders>`_
"""

import distutils.sysconfig
import logging
import sys
import os
import time
from cobbler.templar import Templar

plib = distutils.sysconfig.get_python_lib()
mod_path = f"{plib}/cobbler"
sys.path.insert(0, mod_path)
TEMPLATE_FILE = "/etc/cobbler/genders.template"
SETTINGS_FILE = "/etc/genders"

logger = logging.getLogger()


def register() -> str:
    """
    We should run anytime something inside of Cobbler changes.

    :return: Always ``/var/lib/cobbler/triggers/change/*``
    """
    return "/var/lib/cobbler/triggers/change/*"


def write_genders_file(config, profiles_genders, distros_genders, mgmtcls_genders):
    """
    Genders file is over-written when ``manage_genders`` is set in our settings.

    :param config: The API instance to template the data with.
    :param profiles_genders: The profiles which should be included.
    :param distros_genders: The distros which should be included.
    :param mgmtcls_genders: The management classes which should be included.
    :raises OSError: Raised in case the template could not be read.
    """
    try:
        with open(TEMPLATE_FILE, "r", encoding="UTF-8") as template_fd:
            template_data = template_fd.read()
    except Exception as error:
        raise OSError(f"error reading template: {TEMPLATE_FILE}") from error

    metadata = {
        "date": time.asctime(time.gmtime()),
        "profiles_genders": profiles_genders,
        "distros_genders": distros_genders,
        "mgmtcls_genders": mgmtcls_genders,
    }

    templar_inst = Templar(config)
    templar_inst.render(template_data, metadata, SETTINGS_FILE)


def run(api, args) -> int:
    """
    Mandatory Cobbler trigger hook.

    :param api: The api to resolve information with.
    :param args: For this implementation unused.
    :return: ``0`` or ``1``, depending on the outcome of the operation.
    """
    # do not run if we are not enabled.
    if not api.settings().manage_genders:
        return 0

    profiles_genders = {}
    distros_genders = {}
    mgmtcls_genders = {}

    # let's populate our dicts

    # TODO: the lists that are created here are strictly comma separated.
    # /etc/genders allows for host lists that are in the notation similar to: node00[01-07,08,09,70-71] at some point,
    # need to come up with code to generate these types of lists.

    # profiles
    for prof in api.profiles():
        # create the key
        profiles_genders[prof.name] = ""
        for system in api.find_system(profile=prof.name, return_list=True):
            profiles_genders[prof.name] += system.name + ","
        # remove a trailing comma
        profiles_genders[prof.name] = profiles_genders[prof.name][:-1]
        if profiles_genders[prof.name] == "":
            profiles_genders.pop(prof.name, None)

    # distros
    for dist in api.distros():
        # create the key
        distros_genders[dist.name] = ""
        for system in api.find_system(distro=dist.name, return_list=True):
            distros_genders[dist.name] += system.name + ","
        # remove a trailing comma
        distros_genders[dist.name] = distros_genders[dist.name][:-1]
        if distros_genders[dist.name] == "":
            distros_genders.pop(dist.name, None)

    # mgmtclasses
    for mgmtcls in api.mgmtclasses():
        # create the key
        mgmtcls_genders[mgmtcls.name] = ""
        for system in api.find_system(mgmt_classes=mgmtcls.name, return_list=True):
            mgmtcls_genders[mgmtcls.name] += system.name + ","
        # remove a trailing comma
        mgmtcls_genders[mgmtcls.name] = mgmtcls_genders[mgmtcls.name][:-1]
        if mgmtcls_genders[mgmtcls.name] == "":
            mgmtcls_genders.pop(mgmtcls.name, None)
    # The file doesn't exist and for some reason the template engine won't create it, so spit out an error and tell the
    # user what to do.
    if not os.path.isfile(SETTINGS_FILE):
        logger.info("Error: %s does not exist.", SETTINGS_FILE)
        logger.info("Please run: touch %s as root and try again.", SETTINGS_FILE)
        return 1

    write_genders_file(api, profiles_genders, distros_genders, mgmtcls_genders)
    return 0
