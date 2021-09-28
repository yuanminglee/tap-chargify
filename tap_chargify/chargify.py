
#
# Module dependencies.
#

import backoff
import json
import requests
import logging
from urllib.parse import urlencode
from requests.auth import HTTPBasicAuth
from singer import utils
from datetime import datetime
from time import mktime


logger = logging.getLogger()


""" Simple wrapper for Chargify. """
class Chargify(object):

  def __init__(self, api_key, subdomain, start_date=None):
    self.api_key = api_key
    self.uri = "https://{subdomain}.chargify.com/".format(subdomain=subdomain)


  def retry_handler(details):
    logger.info("Received 429 -- sleeping for %s seconds",
                details['wait'])

  # 
  # The `get` request.
  # 
  
  @backoff.on_exception(backoff.expo,
                        requests.exceptions.HTTPError,
                        on_backoff=retry_handler,
                        max_tries=10)
  def get(self, path, stream=True, xpath=None, **kwargs):
    uri = "{uri}{path}".format(uri=self.uri, path=path)
    has_more = True
    page = 1
    per_page = 100
    while has_more:
      params = {
        "page": page,
        "per_page": per_page
      }
      for key, value in kwargs.items():
        params[key] = value
      final_uri = uri + "?{params}".format(params=urlencode(params))

      logger.info("GET request to {final_uri}".format(final_uri=final_uri))
      response = requests.get(final_uri, stream=stream, auth=HTTPBasicAuth(self.api_key, 'x'), proxies={"https": "http://localhost:8003"}, verify=False)
      response.raise_for_status()

      page += 1
      if len(response.json() if xpath is None else response.json()[xpath]) < per_page:
        has_more = False

      yield response.json()
