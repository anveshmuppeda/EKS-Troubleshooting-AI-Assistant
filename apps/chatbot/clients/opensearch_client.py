from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3, os
from utils.logger import logger


class OpenSearchClient:
    """
    A client for interacting with OpenSearch, including querying documents with embeddings and credential management.

    Attributes:
        region (str): The AWS region in which OpenSearch is located.
        opensearch_endpoint (str): The endpoint URL for the OpenSearch service.
        client (OpenSearch): The OpenSearch client instance.
        credentials (boto3.Session.Credentials): The AWS credentials used for authentication.
    """
    def __init__(self):
        """
        Initializes the OpenSearch client by retrieving necessary environment variables and credentials.
        """
        self.region = os.environ.get('AWS_DEFAULT_REGION')
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.client = None
        self.credentials = None
        self.initialize_client()

    def initialize_client(self):
        """
        Initializes the OpenSearch client and sets up AWS authentication using AWS4Auth.
        Retrieves AWS credentials and refreshes the OpenSearch client connection with the updated credentials.
        """
        self.credentials = boto3.Session().get_credentials()
        logger.debug("Refreshing OpenSearch credentials")
        auth = AWS4Auth(
            self.credentials.access_key,
            self.credentials.secret_key,
            self.region,
            'aoss',
            session_token=self.credentials.token
        )

        self.client = OpenSearch(
            hosts=[{'host': self.opensearch_endpoint, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )

    def check_and_refresh_credentials(self):
        """
        Checks whether the AWS credentials need to be refreshed and refreshes them if necessary.

        This method will automatically call `initialize_client()` if the credentials are determined
        to be expired or invalid.
        """
        if self.credentials.refresh_needed():
            self.initialize_client()

    def retrieve_documents(self, query_embedding, index_name, top_k=5, min_score=0.4):
        """
        Retrieves documents from OpenSearch based on a query embedding.

        Parameters:
            query_embedding (list): The query embedding (vector) used for KNN search.
            index_name (str): The OpenSearch index to query.
            top_k (int, optional): The number of top results to retrieve. Default is 5.
            min_score (float, optional): The minimum score threshold for results. Default is 0.4.

        Returns:
            list: A list of document logs that match the query, or `None` if no results are found or an error occurs.
        """

        self.check_and_refresh_credentials()

        query_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_embedding,
                                    "k": top_k
                                }
                            }
                        }
                    ]
                }
            },
            "_source": False,
            "fields": ["id", "log"],
            "size": top_k,
            "min_score": min_score
        }

        try:
            results = self.client.search(
                body=query_body,
                index=index_name
            )

            if results["hits"]["total"]["value"] > 0:
                context = [hit["fields"]["log"][0] for hit in results["hits"]["hits"]]
                context_log = "\n".join(context)
                logger.debug(f"Context found in OpenSearch: \n{context_log}")
                return context
            else:
                logger.error("No match for the prompt found in the vector database")
                return None

        except Exception as e:
            logger.error(f"Error during OpenSearch query: {str(e)}")
            if "AuthenticationException" in str(e):
                self.initialize_client()
                results = self.client.search(
                    body=query_body,
                    index=index_name
                )
                if results["hits"]["total"]["value"] > 0:
                    return [hit["fields"]["log"][0] for hit in results["hits"]["hits"]]
            return None


