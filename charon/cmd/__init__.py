"""
Copyright (C) 2022 Red Hat, Inc. (https://github.com/Commonjava/charon)

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
from click import group
from charon.cmd.cmd_upload import upload
from charon.cmd.cmd_delete import delete
from charon.cmd.cmd_index import index
from charon.cmd.cmd_checksum import validate
from charon.cmd.cmd_cache import clear_cf


@group()
def cli():
    """Charon is a tool to synchronize several types of
       artifacts repository data to Red Hat Ronda
       service (maven.repository.redhat.com).
    """


# init group command
cli.add_command(upload)
cli.add_command(delete)
cli.add_command(index)
cli.add_command(validate)
cli.add_command(clear_cf)
