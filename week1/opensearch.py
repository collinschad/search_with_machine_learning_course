from flask import g, current_app
from opensearchpy import OpenSearch

# Create an OpenSearch client instance and put it into Flask shared space for use by the application
def get_opensearch():
    # Adapted from OpenSearch Revisited: https://corise.com/course/search-with-machine-learning/week/contentweek_ckxe4tene00211gcj0qoc7bxj/module/module_ckybcq1g10062149ndsu1d0bo
    host = 'localhost'
    port = 9200
    # For testing only. Don't store credentials in code.
    auth = ('admin', 'admin')

    if 'opensearch' not in g:
        # Implement a client connection to OpenSearch so that the rest of the application can communicate with OpenSearch
        g.opensearch = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_compress=True,  # enables gzip compression for request bodies
            http_auth=auth,
            # client_cert = client_cert_path,
            # client_key = client_key_path,
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False,
        )

    return g.opensearch
