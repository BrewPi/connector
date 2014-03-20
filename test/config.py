import os
import sys
import platform
from validate import Validator

__author__ = 'mat'

from configobj import ConfigObj, Section, SimpleVal, ConfigObjError, flatten_errors

config_extension = '.cfg'

def config_filename(name):
    filename = sys.modules[__name__].__file__
    dirname = os.path.dirname(os.path.abspath(filename))
    config_file = os.path.join(dirname, name + config_extension)
    return config_file

def load_config_file_base(file, must_exist=True):
    return ConfigObj(file, interpolation='Template') if must_exist or os.path.exists(file) else ConfigObj()

def config_flavor_file(name, subpart=None)->ConfigObj:
    configname = name if not subpart else name+'.'+subpart
    file = config_filename(configname)
    config = load_config_file_base(file)
    return config

def load_config(name):
    local_config = config_flavor_file(name)
    default_config = config_flavor_file(name, 'default')
    platform_config = config_flavor_file(name, platform.system().lower())
    user_config = load_config_file_base(os.path.expanduser('~/brewpi_'+name+config_extension), must_exist=False)
    config = ConfigObj()
    config.merge(default_config)
    config.merge(platform_config)
    config.merge(user_config)
    config.merge(local_config)

    config.configspec = config_flavor_file(name, 'schema')
    validator = Validator()
    result = config.validate(validator)
    if not result:
        for section_list, key, res in flatten_errors(config, result):
            print('result %s' % res)
            if key is not None:
                print('The "%s" key in the section "%s" failed validation' % (key, ', '.join(section_list)))
            else:
                print('The following section was missing:%s ' % ', '.join(section_list))
        raise ConfigObjError("the config failed validation %s" % result)
    return config


def apply(target, name, file='integration_test'):
    conf = load_config(file)
    name_parts = name.split('.')
    apply_conf_path(conf, name_parts, target)

def apply_conf_path(conf: Section, name_parts, target):
    for p in name_parts:    # lookup specific section
        conf = conf.get(p, None)
        if conf is None:
            return
    apply_conf(conf, target)

def apply_conf(conf: Section, target):
    for k,v in conf.items():
        if hasattr(target,k):
            setattr(target, k, v)

def apply_module(module):
    apply(module, module.__name__)

def apply_package(module):
    apply(module, module.__package__)
