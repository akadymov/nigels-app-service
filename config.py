import yaml

def get_settings(section=None):
    with open("config.yml", "r") as configfile:
        cfg = yaml.load(configfile, Loader=yaml.FullLoader)
        if section:
            return cfg[section]
        return cfg['FLASK']


def get_environment():
    with open("config.yml", "r") as configfile:
        return yaml.load(configfile, Loader=yaml.FullLoader)['ENVIRONMENT']
