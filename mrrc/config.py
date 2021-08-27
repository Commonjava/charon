import configparser

SECTION_AWS = 'aws'
SECTION_MRRC = 'mrrc'

AWS_KEY_ID = 'access_key_id'
AWS_KEY = 'secret_access_key'
AWS_ENDPOINT = 'endpoint_url'
AWS_REGION = 'region'
AWS_RETRY_MAX = 'retry_max_attempts'
AWS_RETRY_MODE = 'retry_mode'

class MrrcConfig(object):
  """ MrrcConfig is used to store all configurations for mrrc-uploader tools.
  The configuration file will be named as mrrc-uploader.conf, and will be stored 
  in $HOME/.mrrc/ folder by default.
  """
  def __init__(self, data: configparser.ConfigParser):
    self.aws_configs = {}
    self.aws_enabled = True
    self.aws_key_id = None
    self.aws_key = None
    aws_configs = data.options(SECTION_AWS)
    if aws_configs is not None:
      for option in aws_configs:
        val = data.get(SECTION_AWS, option, fallback=None)
        self.aws_configs[option] = val
        if option==AWS_KEY_ID:
          self.aws_key_id = val
        if option==AWS_KEY:
          self.aws_key = val
    else:
      self.aws_enabled=False

    if self.aws_key_id is None:
      logging('Warning: Missing AWS access key id, aws related function can not work.')
      self.aws_enabled=False
    if self.aws_key is None:
      logging('Warning: Missing AWS access secret key, aws related function can not work.')
      self.aws_enabled=False

  def get_aws_key_id(self) -> str:
    return self.aws_key_id
  
  def get_aws_key(self) -> str:
    return self.aws_key

  def get_aws_configs(self) -> dict:
    return self.aws_configs


def logging(msg):
  # TODO: Will use logging libs instead later
  print(msg)