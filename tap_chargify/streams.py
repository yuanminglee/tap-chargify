#
# Module dependencies.
#

import os
import json
import datetime

import datetime as datetime

import dateutil
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

    def update_bookmark(self, state, value, name=None):
        name = self.name if not name else name
        # when `value` is None, it means to set the bookmark to None
        if value is None or self.is_bookmark_old(state, value, name):
            dt = dateutil.parser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            else:
                dt = dt.astimezone(pytz.utc)
            singer.write_bookmark(state, name, self.replication_key, dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def is_bookmark_old(self, state, value, name=None):
        current_bookmark = self.get_bookmark(state, name)
        # dt = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")
        dt = dateutil.parser.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        else:
            dt = dt.astimezone(pytz.utc)
        return dt > utils.strptime_with_tz(current_bookmark)

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
        for i in self.client.get("product_families.json"):
            for j in i:
                yield j["product_family"]


class Products(Stream):
    name = "products"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("product_families.json"):
            for k in i:
                for j in self.client.get("product_families/{product_family_id}/products.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        yield l["product"]


class PricePoints(Stream):
    name = "price_points"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("product_families.json"):
            for j in i:
                for k in self.client.get("product_families/{product_family_id}/products.json".format(
                        product_family_id=j["product_family"]["id"])):
                    for l in k:
                        for o in self.client.get(
                                "products/{product_id}/price_points.json".format(product_id=l["product"]["id"])):
                            for m in o["price_points"]:
                                yield m


class Coupons(Stream):
    name = "coupons"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("product_families.json"):
            for k in i:
                for j in self.client.get("product_families/{product_family_id}/coupons.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        yield l["coupon"]


class Components(Stream):
    name = "components"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("product_families.json"):
            for k in i:
                for j in self.client.get("product_families/{product_family_id}/components.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        yield l["component"]


class Subscriptions(Stream):
    name = "subscriptions"
    replication_method = "INCREMENTAL"
    replication_key = "updated_at"

    def get_data(self, bookmark=None):
        for i in self.client.get("subscriptions.json", start_datetime=bookmark, date_field="updated_at",
                                 direction="asc"):
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
        for i in self.client.get("transactions.json", since_date=since_date, direction="asc"):
            for j in i:
                yield j["transaction"]


class Statements(Stream):
    name = "statements"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("statements.json"):
            for j in i:
                yield j["statement"]


class Invoices(Stream):
    name = "invoices"
    replication_method = "FULL_TABLE"
    key_properties = ['uid']

    def get_data(self, bookmark=None):
        start_date = utils.strptime_with_tz(bookmark).strftime('%Y-%m-%d')
        for i in self.client.get("invoices.json", xpath="invoices", start_date=start_date,
                                 direction="asc",line_items="true",discounts="true",taxes="true",credits="true",
                                 refunds="true",payments="true"):
            for j in i["invoices"]:
                yield j


class Events(Stream):
    name = "events"
    replication_method = "INCREMENTAL"
    replication_key = "created_at"

    def get_data(self, bookmark=None):
        for i in self.client.get("events.json", start_datetime=bookmark, date_field="created_at",
                                 direction="asc"):
            for j in i:
                yield j["event"]


class CustomersMetadata(MetadataStream):
    name = "customers_metadata"
    replication_method = "INCREMENTAL"
    replication_key = "updated_at"

    def get_data(self, bookmark=None):
        xpath = "metadata"
        for i in self.client.get("customers/metadata.json", xpath=xpath, start_datetime=bookmark,
                                 date_field="updated_at",
                                 direction="asc"):
            for j in i[xpath]:
                yield j


class SubscriptionsMetadata(MetadataStream):
    name = "subscriptions_metadata"

    replication_method = "INCREMENTAL"
    replication_key = "updated_at"

    def get_data(self, bookmark=None):
        xpath = "metadata"
        for i in self.client.get("subscriptions/metadata.json", xpath=xpath, start_datetime=bookmark,
                                 date_field="updated_at",
                                 direction="asc"):
            for j in i[xpath]:
                yield j


class ComponentsPricePoints(Stream):
    name = "components_price_points"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("product_families.json"):
            for k in i:
                for j in self.client.get("product_families/{product_family_id}/components.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        for m in self.client.get(
                                "components/{component_id}/price_points.json".format(component_id=l["component"]["id"]),
                                xpath="price_points"):
                            for n in m["price_points"]:
                                yield n


class Offers(Stream):
    name = "offers"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("offers.json", xpath="offers"):
            for j in i["offers"]:
                yield j


class ProductPricePoints(Stream):
    name = "product_price_points"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("product_families.json"):
            for k in i:
                for j in self.client.get("product_families/{product_family_id}/products.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        for m in self.client.get(
                                "/products/{product_id}/price_points.json".format(product_id=l["product"]["id"]),
                                xpath="price_points"):
                            for n in m["price_points"]:
                                yield n


class SubscriptionsComponents(Stream):
    name = "subscriptions_components"
    replication_method = "INCREMENTAL"
    replication_key = "updated_at"

    def get_data(self, bookmark=None):
        for i in self.client.get("subscriptions_components.json",
                                    start_datetime=bookmark,
                                    date_field="updated_at",
                                    direction="asc"):
            yield i["subscriptions_components"]

class SubscriptionsComponentsAllocations(Stream):
    name = "subscriptions_components_allocations"
    replication_method = "FULL_TABLE"
    key_properties = ['component_id', 'subscription_id']

    def get_data(self, bookmark=None):
        for i in self.client.get("subscriptions.json"):
            for j in i:
                for k in self.client.get("subscriptions/{subscription_id}/components.json".format(
                        subscription_id=j["subscription"]["id"])):
                    for l in k:
                        for m in self.client.get(
                                "subscriptions/{subscription_id}/components/{component_id}/allocations.js".format(
                                    subscription_id=j["subscription"]["id"],
                                    component_id=l["component"]["component_id"])):
                            for n in m:
                                yield n["allocation"]


class CouponUsages(Stream):
    name = "coupon_usages"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("product_families.json"):
            for k in i:
                for j in self.client.get("product_families/{product_family_id}/coupons.json".format(
                        product_family_id=k["product_family"]["id"])):
                    for l in j:
                        for m in self.client.get(
                            "/product_families/{product_family_id}/coupons/{coupon_id}/usage.json".format(
                                product_family_id=k["product_family"]["id"], coupon_id=l["coupon"]["id"])):
                            for n in m:
                                yield n


class CreditNotes(Stream):
    name = "credit_notes"
    replication_method = "FULL_TABLE"
    key_properties = ["uid"]

    def get_data(self, bookmark=None):
        for i in self.client.get("credit_notes.json",xpath="credit_notes",line_items="true",discounts="true",
                                 taxes="true",applications="true",refunds="true"):
            for k in i["credit_notes"]:
                yield k


class AccountBalances(Stream):
    name = "account_balances"
    replication_method = "FULL_TABLE"
    key_properties = ["subscription_id"]

    def get_data(self, bookmark=None):
        for i in self.client.get("subscriptions.json", start_datetime=bookmark, date_field="updated_at",
                                 direction="asc"):
            for j in i:
                for k in self.client.get("subscriptions/{subscription_id}/account_balances.json".format(subscription_id=j["subscription"]["id"])):
                    k["subscription_id"] = j["subscription"]["id"]
                    yield k


class PaymentProfiles(Stream):
    name = "payment_profiles"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("payment_profiles.json"):
            for j in i:
                yield j["payment_profile"]


class ReasonCodes(Stream):
    name = "reason_codes"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("reason_codes.json"):
            for j in i:
                yield j["reason_code"]


class SubscriptionGroups(Stream):
    name = "subscription_groups"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("subscription_groups.json",xpath="subscription_groups", include="account_balances"):
            for j in i["subscription_groups"]:
                yield j


class ProformaInvoices(Stream):
    name = "proforma_invoices"
    replication_method = "FULL_TABLE"

    def get_data(self, bookmark=None):
        for i in self.client.get("subscriptions.json"):
            for j in i:
                for k in self.client.get("subscriptions/{subscription_id}/proforma_invoices.json"
                                                 .format(subscription_id=j["subscription"]["id"]),
                        xpath="proforma_invoices",line_items="true",discounts="true",taxes="true",credits="true",payments="true"):
                    for m in k["proforma_invoices"]:
                        yield m



STREAMS = {
    "customers": Customers,
    "product_families": ProductFamilies,
    "products": Products,
    # "price_points": PricePoints,
    "components_price_points": ComponentsPricePoints,
    "coupons": Coupons,
    "components": Components,
    "subscriptions": Subscriptions,
    "transactions": Transactions,
    "statements": Statements,
    "invoices": Invoices,
    "events": Events,
    "customers_metadata": CustomersMetadata,
    "subscriptions_metadata": SubscriptionsMetadata,
    "offers": Offers,
    "product_price_points": ProductPricePoints,
    "subscriptions_components": SubscriptionsComponents,
    # "subscriptions_components_allocations": SubscriptionsComponentsAllocations,
    "coupon_usages": CouponUsages,
    "credit_notes": CreditNotes,
    "account_balances": AccountBalances,
    "payment_profiles": PaymentProfiles,
    "reason_codes": ReasonCodes,
    "subscription_groups": SubscriptionGroups,
    "proforma_invoices": ProformaInvoices
}
