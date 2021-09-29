# tap-chargify

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from the [Chargify API](https://reference.chargify.com/v1/basics/introduction)
- Extracts the following resources:
  - [Components](https://reference.chargify.com/v1/components/components-intro)
  - [Coupons](https://reference.chargify.com/v1/coupons-editing/coupons-intro)
  - [Customers](https://reference.chargify.com/v1/customers/customers-intro)
  - [Events](https://reference.chargify.com/v1/events/events-intro)
  - [Invoices](https://reference.chargify.com/v1/relationship-invoicing/relationship-invoicing-intro)
  - [Price points](https://reference.chargify.com/v1/products-price-points/product-price-point-intro)
  - [Product families](https://reference.chargify.com/v1/product-families/product-family-intro)
  - [Products](https://reference.chargify.com/v1/products/products-intro)
  - [Statements](https://reference.chargify.com/v1/statements/statements-intro)
  - [Subscriptions](https://reference.chargify.com/v1/subscriptions/subscriptions-intro)
  - [Transactions](https://reference.chargify.com/v1/transactions/transactions-api)
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

---

## Streams

### [components](https://reference.chargify.com/v1/components/list-components-for-a-product-family)

- **Endpoint**: https://reference.chargify.com/v1/components/list-components-for-a-product-family
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [coupons](https://reference.chargify.com/v1/coupons-editing/list-product-family-coupons)

- **Endpoint**: https://reference.chargify.com/v1/coupons-editing/list-product-family-coupons
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [customers](https://reference.chargify.com/v1/customers/list-customers-for-a-site)

- **Endpoint**: https://reference.chargify.com/v1/customers/list-customers-for-a-site
- **Primary key field**: id
- **Replication strategy**: INCREMENTAL

### [events](https://reference.chargify.com/v1/events/list-events-for-a-site)

- **Endpoint**: https://reference.chargify.com/v1/events/list-events-for-a-site
- **Primary key field**: id
- **Replication strategy**: INCREMENTAL
- **Bookmark**: created_at

### [invoices](https://reference.chargify.com/v1/invoices-legacy/list-all-invoices-by-subscription)

- **Endpoint**: https://reference.chargify.com/v1/invoices-legacy/list-all-invoices-by-subscription
- **Primary key field**: id
- **Replication strategy**: INCREMENTAL
- **Bookmark**: due_date

### [components_price_points](https://reference.chargify.com/v1/components/list-price-points)

- **Endpoint**: https://reference.chargify.com/v1/components/list-price-points
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [product_families](https://reference.chargify.com/v1/product-families/list-product-family-via-site)

- **Endpoint**: https://reference.chargify.com/v1/product-families/list-product-family-via-site
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [products](https://reference.chargify.com/v1/products/list-products)

- **Endpoint**: https://reference.chargify.com/v1/products/list-products
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [statements](https://reference.chargify.com/v1/statements/list-statements-for-a-site)

- **Endpoint**: https://reference.chargifys.com/v1/statements/list-statements-for-a-site
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [subscriptions](https://reference.chargify.com/v1/subscriptions/list-subscriptions)

- **Endpoint**: https://reference.chargify.com/v1/subscriptions/list-subscriptions
- **Primary key field**: id
- **Replication strategy**: INCREMENTAL
- **Bookmark**: updated_at

### [transactions](https://reference.chargify.com/v1/transactions/list-transactions-for-the-site)

- **Endpoint**: https://reference.chargify.com/v1/transactions/list-transactions-for-the-site
- **Primary key field**: id
- **Replication strategy**: INCREMENTAL
- **Bookmark**: created_at

### [offers](https://reference.chargify.com/v1/offers/list-offers)

- **Endpoint**: https://reference.chargify.com/v1/offers/list-offers
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [product_price_points](https://reference.chargify.com/v1/products-price-points/read-product-price-points)

- **Endpoint**: https://reference.chargify.com/v1/products-price-points/read-product-price-points
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [subscriptions_components](https://reference.chargify.com/v1/subscriptions-components/list-components-for-a-subscription)

- **Endpoint**: https://reference.chargify.com/v1/subscriptions-components/list-components-for-a-subscription
- **Primary key field**: component_id,subscription_id
- **Replication strategy**: FULL_TABLE

### [coupon_usages](https://reference.chargify.com/v1/coupons/list-coupon-usages)

- **Endpoint**: https://reference.chargify.com/v1/coupons/list-coupon-usages
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [credit_notes](https://reference.chargify.com/v1/relationship-invoicing/read-all-credit-notes)

- **Endpoint**: https://reference.chargify.com/v1/relationship-invoicing/read-all-credit-notes 
- **Primary key field**: uid
- **Replication strategy**: FULL_TABLE

### [account_balances](https://reference.chargify.com/v1/relationship-invoicing/read-account-balances)

- **Endpoint**: https://reference.chargify.com/v1/relationship-invoicing/read-account-balances
- **Primary key field**: subscription_id
- **Replication strategy**: FULL_TABLE

### [payment_profiles](https://reference.chargify.com/v1/payment-profiles/list-payment-profiles)

- **Endpoint**: https://reference.chargify.com/v1/payment-profiles/list-payment-profiles
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [reason_codes](https://reference.chargify.com/v1/reason-codes/index-view)

- **Endpoint**: https://reference.chargify.com/v1/reason-codes/index-view
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [subscription_groups](https://reference.chargify.com/v1/subscription-groups/read-subscription-groups)

- **Endpoint**: https://reference.chargify.com/v1/subscription-groups/read-subscription-groups
- **Primary key field**: uid
- **Replication strategy**: FULL_TABLE

### [proforma_invoices](https://reference.chargify.com/v1/proforma-invoices/read-all-subscription-proforma-invoices )

- **Endpoint**: https://reference.chargify.com/v1/proforma-invoices/read-all-subscription-proforma-invoices 
- **Primary key field**: uid
- **Replication strategy**: FULL_TABLE
--- 

## Quick Start

1. Install the tap using the following command:

   ```
   > pip install tap-chargify
   ```

2. Create the config file, which is a JSON file named `config.json`. This file should contain the following properties:
   
   - `api_key` - A Chargify API key. Refer to the [Chargify documentation](https://help.chargify.com/integrations/api-keys-chargify-direct.html) for instructions on creating an API key.
   - `start_date` - The date from which the tap should begin replicating data. This value must be an ISO 8601-compliant date.
   - `subdomain` The subdomain of your Chargify site. For example: If the full URL were `https://test.my-chargify-site.com`, this value would be `test`.

   ```json
   {
     "api_key": "xx",
     "start_date": "2018-02-22T02:06:58.147Z",
     "subdomain": "test"
   }
   ```

3. Run the tap in Discovery Mode using the following command:

   ```
   > tap-chargify -c config.json -d
   ```

   See the Singer docs on discovery mode
   [here](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode).

4. Run the tap in Sync Mode using the following command:

   ```
   > tap-chargify -c config.json --catalog catalog-file.json
   ```

## Development

1. Clone this repository. 
2. In the directory, run the following command:

   ```
   > python -m venv tap-chargify
   > make dev
   ```

---

Copyright &copy; 2019 Stitch
