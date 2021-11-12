"""
Copyright (C) 2021 Red Hat, Inc. (https://github.com/Commonjava/hermes)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

         http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
# Logging format used
HERMES_LOGGING_FMT = '%(asctime)s - %(levelname)s - %(message)s'
DESCRIPTION = "hermes is a tool to synchronize several types of artifacts "
"repository data to RedHat Ronda service (maven.repository.redhat.com)."
PROG = 'hermes'
META_FILE_GEN_KEY = "Generate"
META_FILE_DEL_KEY = "Delete"
MAVEN_METADATA_TEMPLATE = '''
<metadata>
  {%- if meta.group_id is defined %}
  <groupId>{{ meta.group_id }}</groupId>
  {%- endif %}
  {%- if meta.artifact_id is defined %}
  <artifactId>{{ meta.artifact_id }}</artifactId>
  {%- endif %}
  {%- if meta.versioned is defined %}
  <version>{{ meta.versioned }}</version>
  {%- endif %}
  {%- if meta.versions is defined or meta.snapshoted is defined %}
  <versioning>
    {%- if meta.latest_version is defined %}
    <latest>{{ meta.latest_version }}</latest>
    {%- endif %}
    {%- if meta.release_version is defined %}
    <release>{{ meta.release_version }}</release>
    {%- endif %}
    {%- if meta.versions is defined %}
    <versions>
      {% for ver in meta.versions -%}
      <version>{{ ver }}</version>
      {% endfor %}
    </versions>
    {%- endif %}
    {%- if meta.last_upd_time is defined %}
    <lastUpdated>{{ meta.last_upd_time }}</lastUpdated>
    {%- endif %}
    {%- if meta.snapshoted is defined %}
    <snapshot>
      {%- if meta.snapshoted.time is defined %}
      <timestamp>{{ meta.snapshoted.time }}</timestamp>
      {%- endif %}
      {%- if meta.snapshoted.build is defined %}
      <buildNumber>{{ meta.snapshoted.build }}</buildNumber>
      {%- endif %}
      {%- if meta.snapshoted.localcopy is defined %}
      <localCopy>{{ meta.snapshoted.localcopy }}</localCopy>
      {%- endif %}
    </snapshot>
    {%- endif %}
    {%- if meta.snapshot_versions is defined %}
    <snapshotVersions>
      {% for snapshot_ver in meta.snapshot_versions -%}
      <snapshotVersion>
        {%- if snapshot_ver.classifier is defined %}
        <classifier>{{ snapshot_ver.classifier }}</classifier>
        {%- endif %}
        {%- if snapshot_ver.ext is defined %}
        <extension>{{ snapshot_ver.ext }}</extension>
        {%- endif %}
        {%- if snapshot_ver.val is defined %}
        <value>{{ snapshot_ver.val }}</value>
        {%- endif %}
        {%- if snapshot_ver.upd is defined %}
        <updated>{{ snapshot_ver.upd }}</updated>
        {%- endif %}
      </snapshotVersion>
      {% endfor %}
    </snapshotVersions>
    {%- endif %}
  </versioning>
  {%- endif %}

  {%- if meta.plugins is defined %}
  <plugins>
    {% for plugin in meta.plugins -%}
    <plugin>
      <name>{{ plugin.name }}</name>
      <prefix>{{ plugin.prefix }}</prefix>
      <artifactId>{{ plugin.artifact_id }}</artifactId>
    </plugin>
    {% endfor %}
  </plugins>
  {%- endif %}
</metadata>
'''
INDEX_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
  <title>{{ index.title }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
body {
  background: #fff;
}
  </style>
</head>
<body>
  <header>
    <h1>{{ index.header }}</h1>
  </header>
  <hr/>
  <main>
    <pre id="contents">
    {% for item in index.items %}
          <a href="{{ item }}" title="{{ item }}">{{ item }}</a>
    {% endfor%}
    </pre>
  </main>
  <hr/>
</body>
</html>
'''
