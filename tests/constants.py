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
import os

HERE = os.path.dirname(__file__)
INPUTS = os.path.join(HERE, 'input')

TEST_DS_CONFIG = {
        'CallerReference': 'test',
        "Aliases": {
            "Quantity": 1,
            "Items": [
                "maven.repository.redhat.com",
                "npm.registry.redhat.com"
            ]
        },
        "Origins": {
            "Quantity": 1,
            "Items": [
                {
                    "Id": "prod-maven-ga",
                    "DomainName": "prod-maven-ga.s3.us-east-1.amazonaws.com",
                    "OriginPath": "",
                    "CustomHeaders": {
                        "Quantity": 0
                    },
                }
            ]
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": "prod-maven-ga",
            "ViewerProtocolPolicy": "allow-all",
        },
        "Comment": "",
        "Enabled": True
    }
