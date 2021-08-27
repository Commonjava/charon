from jinja2 import Template
import os

MVN_TEMPLATE = 'maven-metadata.xml.j2'
class MavenMetadata(object):
  def __init__(self, group_id: str, artifact_id: str):
    self.group_id = group_id
    self.artifact_id = artifact_id

  def generate_meta_file_content(self) -> str:
    template = Template(get_mvn_template())
    return template.render(meta=self)

  def versions(self, *vers: str):
    self.vers=list(vers)
    return self
  
  def latest_version(self, latest_version: str):
    self.latest_ver = latest_version
    return self
  
  def release_version(self, release_version: str):
    self.release_ver = release_version
    return self
  
  def __str__(self) -> str:
      return f'{self.group_id}:{self.artifact_id}\n{self.vers}\n\n'


def get_mvn_template() -> str:
  home = os.environ['HOME']
  template_file = os.path.join(home, '.mrrc/template', MVN_TEMPLATE)
  with open(template_file) as file_:
    return file_.read()

  

def parse_ga(full_ga_path: str, root="/"):
  slash_root = root
  if not root.endswith("/"):
    slash_root = slash_root + '/'
  
  ga_path = full_ga_path
  if ga_path.startswith(slash_root):
    ga_path = ga_path[len(slash_root):]
  if ga_path.endswith("/"):
    ga_path = ga_path[:-1]
  
  items = ga_path.split("/")
  artifact = items[len(items)-1]
  group=".".join(items[:-1])
  
  return group, artifact

def parse_gav(full_artifact_path: str, root="/"):
  slash_root = root
  if not root.endswith("/"):
    slash_root = slash_root + '/'
  
  ver_path = full_artifact_path
  if ver_path.startswith(slash_root):
    ver_path = ver_path[len(slash_root):]
  if ver_path.endswith("/"):
    ver_path = ver_path[:-1]
  
  items = ver_path.split("/")
  version = items[-2]
  artifact = items[-3]
  group=".".join(items[:-3])
  
  return group, artifact, version

def scan_for_poms(full_path: str):
  # collect poms
  all_pom_paths = list()
  for (dir,_,names) in os.walk(full_path):
    single_pom_paths=[os.path.join(dir,n) for n in names if n.endswith('.pom')]
    all_pom_paths.extend(single_pom_paths)
  return all_pom_paths

def parse_gavs(pom_paths:list, root='/') -> dict:  
  gavs = dict()
  for pom in pom_paths:
    (g, a, v) = parse_gav(pom, root)
    key = g + "." + a
    vers = gavs.get(key, list())
    vers.append(v)
    gavs[key]=vers
    
  return gavs


def gen_meta(ga: str, vers: list) -> MavenMetadata:  
  sorted_vers = sorted(vers)
  _ga = ga.split('.')
  g = '.'.join(_ga[:-1])
  a = _ga[-1]
  meta = MavenMetadata(g,a)
  meta.latest_version(sorted_vers[-1]).release_version(sorted_vers[-1]).versions(*sorted_vers)
  return meta
    