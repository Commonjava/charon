# For maven
TEST_BUCKET = "test_bucket"
COMMONS_CLIENT_456_FILES = [
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom.sha1",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.jar.sha1",
    "org/apache/httpcomponents/httpclient/4.5.6/httpclient-4.5.6.pom",
]
COMMONS_CLIENT_459_FILES = [
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.pom.sha1",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.jar",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.jar.sha1",
    "org/apache/httpcomponents/httpclient/4.5.9/httpclient-4.5.9.pom",
]
COMMONS_CLIENT_METAS = [
    "org/apache/httpcomponents/httpclient/maven-metadata.xml",
    "org/apache/httpcomponents/httpclient/maven-metadata.xml.md5",
    "org/apache/httpcomponents/httpclient/maven-metadata.xml.sha1",
    "org/apache/httpcomponents/httpclient/maven-metadata.xml.sha256",
]
COMMONS_LOGGING_FILES = [
    "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar",
    "commons-logging/commons-logging/1.2/commons-logging-1.2-sources.jar.sha1",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.jar",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.jar.sha1",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.pom",
    "commons-logging/commons-logging/1.2/commons-logging-1.2.pom.sha1",
]
COMMONS_LOGGING_METAS = [
    "commons-logging/commons-logging/maven-metadata.xml",
    "commons-logging/commons-logging/maven-metadata.xml.md5",
    "commons-logging/commons-logging/maven-metadata.xml.sha1",
    "commons-logging/commons-logging/maven-metadata.xml.sha256",
]
ARCHETYPE_CATALOG = "archetype-catalog.xml"
ARCHETYPE_CATALOG_FILES = [
    ARCHETYPE_CATALOG,
    "archetype-catalog.xml.sha1",
    "archetype-catalog.xml.md5",
    "archetype-catalog.xml.sha256",
]
NON_MVN_FILES = [
    "commons-client-4.5.6/example-settings.xml",
    "commons-client-4.5.6/licenses/gnu",
    "commons-client-4.5.6/licenses/licenses.txt",
    "commons-client-4.5.6/README.md",
    "commons-client-4.5.9/example-settings.xml",
    "commons-client-4.5.9/licenses/gnu",
    "commons-client-4.5.9/licenses/licenses.txt",
    "commons-client-4.5.9/README.md",
]
COMMONS_CLIENT_456_MVN_NUM = len(COMMONS_CLIENT_456_FILES) + len(COMMONS_LOGGING_FILES)
COMMONS_CLIENT_459_MVN_NUM = len(COMMONS_CLIENT_459_FILES) + len(COMMONS_LOGGING_FILES)
COMMONS_CLIENT_MVN_NUM = (
    len(COMMONS_CLIENT_456_FILES)
    + len(COMMONS_CLIENT_459_FILES)
    + len(COMMONS_LOGGING_FILES)
)
COMMONS_CLIENT_META_NUM = (
    len(COMMONS_CLIENT_METAS)
    + len(COMMONS_LOGGING_METAS)
    + len(ARCHETYPE_CATALOG_FILES)
)
# For maven indexes
COMMONS_CLIENT_456_INDEXES = [
    "index.html",
    "org/index.html",
    "org/apache/index.html",
    "org/apache/httpcomponents/index.html",
    "org/apache/httpcomponents/httpclient/index.html",
    "org/apache/httpcomponents/httpclient/4.5.6/index.html",
]
COMMONS_CLIENT_459_INDEXES = [
    "index.html",
    "org/index.html",
    "org/apache/index.html",
    "org/apache/httpcomponents/index.html",
    "org/apache/httpcomponents/httpclient/index.html",
    "org/apache/httpcomponents/httpclient/4.5.9/index.html",
]
COMMONS_LOGGING_INDEXES = [
    "commons-logging/index.html",
    "commons-logging/commons-logging/index.html",
    "commons-logging/commons-logging/1.2/index.html",
]
COMMONS_CLIENT_INDEX = "org/apache/httpcomponents/httpclient/index.html"
COMMONS_CLIENT_456_INDEX = "org/apache/httpcomponents/httpclient/4.5.6/index.html"
COMMONS_LOGGING_INDEX = "commons-logging/commons-logging/index.html"
COMMONS_ROOT_INDEX = "index.html"


# For npm
CODE_FRAME_7_14_5_FILES = [
    "@babel/code-frame/7.14.5/package.json",
    "@babel/code-frame/-/code-frame-7.14.5.tgz",
]
CODE_FRAME_7_15_8_FILES = [
    "@babel/code-frame/7.15.8/package.json",
    "@babel/code-frame/-/code-frame-7.15.8.tgz",
]
CODE_FRAME_META = "@babel/code-frame/package.json"

CODE_FRAME_7_14_5_META = "@babel/code-frame/7.14.5/package.json"
# For npm indexes
CODE_FRAME_7_14_5_INDEXES = [
    "@babel/code-frame/7.14.5/index.html",
    "@babel/code-frame/-/index.html",
]
CODE_FRAME_7_15_8_INDEXES = [
    "@babel/code-frame/7.15.8/index.html",
    "@babel/code-frame/-/index.html",
]
CODE_FRAME_7_14_5_INDEX = "@babel/code-frame/7.14.5/index.html"
CODE_FRAME_INDEX = "@babel/code-frame/index.html"
COMMONS_ROOT_INDEX = "index.html"


# For manifest
TEST_MANIFEST_BUCKET = "test_manifest_bucket"
TEST_TARGET = "stage"
COMMONS_CLIENT_456_MANIFEST = TEST_BUCKET + "/commons-client-4.5.6.txt"
CODE_FRAME_7_14_5_MANIFEST = TEST_BUCKET + "/code-frame-7.14.5.txt"

# For multi targets support
TEST_BUCKET_2 = "test_bucket_2"
