
#
# Module dependencies.
#

import os
import json
import datetime

import datetime as datetime
import pytz
import singer
import time
from singer import metadata
from singer import utils
from tap_chargify.context import Context


logger = singer.get_logger()
KEY_PROPERTIES = ['id']


def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def epoch_to_datetime_string(milliseconds):
    datetime_string = None
    try:
        datetime_string = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(milliseconds / 1000))
    except TypeError:
        # If fails, it means format already datetime string.
        datetime_string = milliseconds
        pass
    return datetime_string


class Stream:
    name = None
    replication_method = None
    replication_key = None
    stream = None
    key_properties = KEY_PROPERTIES
    session_bookmark = None


    def __init__(self, client=None):
        self.client = client


    def is_session_bookmark_old(self, value):
        if self.session_bookmark is None:
            return True
        return utils.strptime_with_tz(value) > utils.strptime_with_tz(self.session_bookmark)


    def update_session_bookmark(self, value):
        # Assume value is epoch milliseconds.
        value_in_date_time = epoch_to_datetime_string(value)
        if self.is_session_bookmark_old(value_in_date_time):
            self.session_bookmark = value_in_date_time


    # Reads and converts bookmark from state.
    def get_bookmark(self, state, name=None):
        name = self.name if not name else name
        return (singer.get_bookmark(state, name, self.replication_key)) or Context.config["start_date"]


    # Converts and writes bookmark to state.
    def update_bookmark(self, state, value, name=None):
        name = self.name if not name else name
        # when `value` is None, it means to set the bookmark to None
        if value is None or self.is_bookmark_old(state, value, name):
            dt = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
            if dt.tzinfo:
                dt2 = dt.astimezone(pytz.utc)
            singer.write_bookmark(state, name, self.replication_key, dt2.strftime("%Y-%m-%dT%H:%M:%SZ"))


    def is_bookmark_old(self, state, value, name=None):
        current_bookmark = self.get_bookmark(state, name)
        return utils.strptime_with_tz(value) > utils.strptime_with_tz(current_bookmark)


    def load_schema(self):
        schema_file = "schemas/{}.json".format(self.name)
        with open(get_abs_path(schema_file)) as f:
            schema = json.load(f)
        return schema


    def load_metadata(self):
        return metadata.get_standard_metadata(schema=self.load_schema(),
                                              key_properties=self.key_properties,
                                              valid_replication_keys=[self.replication_key],
                                              replication_method=self.replication_method)


    # The main sync function.
    def sync(self, state):
        bookmark = self.get_bookmark(state)
        res = self.get_data(bookmark)

        if self.replication_method == "INCREMENTAL":
            # These streams results may not be ordered,
            # so store highest value bookmark in session.
            for item in res:
                # if item is bigger than bookmark, then
                if self.is_bookmark_old(state, item[self.replication_key]):
                    self.update_bookmark(state, item[self.replication_key])
                    yield (self.stream, item)
        else:
            for item in res:
                yield (self.stream, item)

    def get_data(self, bookmark=None):
        raise NotImplementedError

class MetadataStream(Stream):
    def sync(self, state):
        bookmark = self.get_bookmark(state)
        res = self.get_data(bookmark)
        for item in res:
            yield (self.stream, item)
        u = datetime.datetime.utcnow()
        self.update_bookmark(state, u.strftime("%Y-%m-%dT%H:%M:%SZ"))

class Customers(Stream):
    name = "customers"
    replication_method = "INCREMENTAL"
    replication_key = "updated_at"
    # incremental

    def get_data(self, bookmark=None):
        for i in self.client.get("customers.json", start_datetime=bookmark, date_field="updated_at", direction="asc"):
            for j in i:
                yield j["customer"]


class ProductFamilies(Stream):
    replication_method = "FULL_TABLE"
    name = "product_families"

    def get_data(self, bookmark=None):
        for i in self.get("product_families.json"):
            for j in i:
                yield j["product_family"]


class Products(Stream):
    name = "products"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.get("product_families.json"):
            for k in i:
                for j in self.get("product_families/{product_family_id}/products.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        yield l["product"]


class PricePoints(Stream):
    name = "price_points"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.get("product_families.json"):
            for j in i:
                for k in self.get("product_families/{product_family_id}/products.json".format(
                        product_family_id=j["product_family"]["id"])):
                    for l in k:
                        for o in self.get(
                                "products/{product_id}/price_points.json".format(product_id=l["product"]["id"])):
                            for m in o["price_points"]:
                                yield m

class Coupons(Stream):
    name = "coupons"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.get("product_families.json"):
            for k in i:
                for j in self.get("product_families/{product_family_id}/coupons.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        yield l["coupon"]


class Components(Stream):
    name = "components"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.get("product_families.json"):
            for k in i:
                for j in self.get("product_families/{product_family_id}/components.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        yield l["component"]

class Subscriptions(Stream):
    name = "subscriptions"
    replication_method = "FULL_TABLE"
    # replication_key = "updated_at"

    def get_data(self, bookmark=None):
        for i in self.get("subscriptions.json", start_datetime=bookmark, date_field="updated_at", direction="asc"):
            for j in i:
                yield j["subscription"]


class Transactions(Stream):
    name = "transactions"
    replication_method = "INCREMENTAL"
    replication_key = "created_at"
    # since API endpoint filter is only on date (and not datetime),
    # make sure to filter out redundant rows.

    def get_data(self, bookmark=None):
        since_date = utils.strptime_with_tz(bookmark).strftime('%Y-%m-%d')
        for i in self.get("transactions.json", since_date=since_date, direction="asc"):
            for j in i:
                yield j["transaction"]


class Statements(Stream):
    name = "statements"
    replication_method = "FULL_TABLE"
    # replication_key = "updated_at"
    def get_data(self, bookmark=None):
        settled_since = time.mktime(utils.strptime_with_tz(bookmark).timetuple())
        for i in self.get("statements.json", sort="settled_at", direction="asc", settled_since=settled_since):
            for j in i:
                yield j["statement"]


class Invoices(Stream):
    name = "invoices"
    replication_method = "INCREMENTAL"
    # replication_key = "updated_at"
    replication_key = "due_date"
    # API endpoint filters only on `due_date`.

    def get_data(self, bookmark=None):
        start_date = utils.strptime_with_tz(bookmark).strftime('%Y-%m-%d')
        for i in self.get("invoices.json", start_date=start_date, direction="asc"):
            for j in i:
                yield j["invoice"]



class Events(Stream):
    name = "events"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.get("events.json"):
            for j in i:
                yield j["event"]


class CustomersMetadata(MetadataStream):
    name = "customers_metadata"
    replication_method = "INCREMENTAL"
    replication_key = "updated_at"

    def get_data(self, bookmark=None):
        xpath = "metadata"
        for i in self.get("customers/metadata.json", xpath=xpath, start_datetime=bookmark, date_field="updated_at",
                          direction="asc"):
            for j in i[xpath]:
                yield j

class SubsctiptionsMetadata(MetadataStream):
    name = "subscriptions_metadata"

    replication_method = "INCREMENTAL"
    replication_key = "updated_at"

    def get_data(self, bookmark=None):
        xpath = "metadata"
        for i in self.get("subscriptions/metadata.json", xpath=xpath, start_datetime=bookmark, date_field="updated_at",
                          direction="asc"):
            for j in i[xpath]:
                yield j

STREAMS = {
    "customers": Customers,
    "product_families": ProductFamilies,
    "products": Products,
    "price_points": PricePoints,
    "coupons": Coupons,
    "components": Components,
    "subscriptions": Subscriptions,
    "transactions": Transactions,
    "statements": Statements,
    "invoices": Invoices,
    "events": Events,
    "customers_metadata": CustomersMetadata,
    "subscriptions_metadata": SubsctiptionsMetadata,
}
