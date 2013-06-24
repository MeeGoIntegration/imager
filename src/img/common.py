"""
Common Imager functions
"""

import os
import ConfigParser
import subprocess as sub
import random, socket, time

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
    for item in ["base_url", "base_dir", "mic_opts", "img_tmp", "vm_ssh_key", "ict",
                 "vm_base_img", "vm_kernel", "timeout", "mic_cachedir", "vm_wait"]:
        conf[item] = config.get(section, item)

    for item in ["use_kvm", "use_9p_cache"]:
        conf[item] = config.getboolean(section, item)

    if config.has_option(section, "mic_opts"):
        extra_opts = config.get(section, "mic_opts")
        extra_opts = extra_opts.split(",")
        conf["extra_opts"] = extra_opts

    return conf

def tester_config(config=None, conffile="/etc/imager/img.conf"):
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

    section = "tester"
    conf = {}
    for item in ["base_dir", "vm_kernel", "timeout", "vm_priv_ssh_key", "vm_pub_ssh_key", "vg_name", "vm_wait", "testtools_repourl", "test_script", "host_test_script", "test_user", "device_ip", "host_test_package_manager"]:
        conf[item] = config.get(section, item)

    for item in ["use_base_img", "host_based_testing"]:
        conf[item] = config.getboolean(section, item)

    return conf

def getport():
    """Gets a random port for the KVM virtual machine communtication, target 
    always being the SSH port.

    :returns: random port number between 49152 and 65535
    """
    return random.randint(49152, 65535)

def getmac():
    """Gets a random mac address for the KVM virtual machine communtication.

    :returns: random mac address
    """
    return 'DE:AD:BE:EF:%0.2X:%0.2X' % (random.randint(0, 32), random.randint(0, 32))

def fork(logfile, command, env=[]):
    with open(logfile, 'a+b') as logf:
        for e, v in env:
            os.environ[e] = v
        x = sub.check_call(command, shell=False, stdout=logf, 
                          stderr=logf, stdin=sub.PIPE)
        logf.flush()
        for e, v in env:
            if e in os.environ:
                del(os.environ[e])
	return x

def wait_for_vm_up(host, port, timeout):
    time.sleep(10)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(float(timeout))
    retries = 0
    while retries < timeout:
        try:
            retries = retries + 1
            s.connect((host, port))
        except:
            time.sleep(1)
        else:
            return True
    return False

def wait_for_vm_down(command, timeout):
    retries = 0
    while retries < timeout:
        print retries
        retries = retries + 1
        comm = ['pgrep', '-f']
        comm.extend([" ".join(command)])
        try:
            retcode = sub.check_call(comm)
            print retcode
        except sub.CalledProcessError, err:
            return True
        else:
            time.sleep(1)
    raise RuntimeError("VM not down after %s" % timeout)

