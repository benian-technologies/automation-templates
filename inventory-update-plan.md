# Compare inventory snapshots and build a safe update CSV

Build a reviewable stock update plan from complete warehouse and store snapshots. The workflow joins exact SKUs, subtracts a safety buffer, keeps quantities at zero or above, and includes only approved SKUs within the allowed change size. It returns a CSV plus review reasons and counts. It does not update a store.

## Setup

1. Import `inventory-update-plan.json` into n8n. It imports inactive and uses only built-in nodes. No credential or paid service is required.
2. Run the supplied synthetic example. It should produce one update for SKU-A to quantity 10 and leave SKU-B unchanged at zero.
3. Replace the Example snapshots node with your complete, normalized snapshots. Preserve the input shape. Aggregate warehouse locations before this workflow if they share a SKU. Represent each store variant as a distinct row and exact SKU.
4. Set the exact `approvedSkus`, integer `safetyStock` and integer `maxAbsoluteChange`. Mark snapshot completion flags true only after your upstream integration has exhausted pagination.
5. Inspect `updates`, `review`, `summary` and the copyable `csv` value in the last node. Re-read current store quantities before applying any plan through a separate store integration.

## Input and behavior

`warehouse` contains `{sku, available}` rows. `catalog` contains `{id, sku, inventory, tracked}` rows. IDs are strings, quantities are nonnegative safe integers, and `tracked` is a boolean. SKU matching is case-sensitive after trimming. Duplicate SKUs or IDs, fractional quantities, missing arrays and incomplete snapshots stop the run. Each snapshot is limited to 10,000 rows.

Missing source or catalog rows, untracked stock, unapproved changes and changes above the configured maximum go to review. Missing source products are never assumed to have zero stock. The output CSV quotes fields and guards text cells against spreadsheet formulas. This planner does not resolve concurrent updates, reservations, currency, bundles or multi-location allocation.

## Validation

Synthetic logic and graph checks pass locally. The exact JSON imported successfully into an isolated n8n 2.41.6 container and the supplied synthetic example executed successfully through all five executable nodes. No customer snapshots or provider connections were used. Execution retention is disabled in the export; apply your own retention rules before handling production data.

## Related implementation

For adapting this pattern to your process, see [Benian's data cleansing approach](https://benian.ai/automations/data-cleansing?utm_source=github&utm_medium=referral&utm_campaign=automation_templates&utm_content=inventory_update_plan_guide).
