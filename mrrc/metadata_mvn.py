from jinja2 import  Template
import os

MVN_TEMPLATE = 'maven-metadata.xml.j2'
class MavenMetadata(object):
  def __init__(self, group_id, artifact_id):
    self.group_id = group_id
    self.artifact_id = artifact_id

  def generate_meta_file(self):
    template = Template(get_mvn_template())
    return template.render(meta=self)

  def versions(self, *version):
    self.versions=version
    return self
  
  def latest_version(self, latest_version):
    self.latest_ver = latest_version
    return self
  
  def release_version(self, release_version):
    self.release_ver = release_version
    return self


def get_mvn_template():
  home = os.environ['HOME']
  template_file = os.path.join(home, '.mrrc', MVN_TEMPLATE)
  print(template_file)
  with open(template_file) as file_:
    return file_.read()

  
