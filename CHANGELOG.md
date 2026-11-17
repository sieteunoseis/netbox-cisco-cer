# Changelog

## [0.2.0] - 2026-11-17

### Added
- **CER Import / Sync** page (dry run by default):
  - **National ERL export:** upload CER's export CSV unchanged. ERLs are matched by name, so re-importing updates them in place. Imported ERLs are marked Migrated (National E911) with a "last seen in export" date. The results list migrated ERLs that are missing from the newer export.
  - **ELIN tracking sheet:** loads a new **ELIN Pool**. The results report sheet-vs-ERL mismatches: names that differ, "Available" numbers already in use, and "In Use" numbers with no ERL.
- New ERLs are matched to a Site by name prefix, then by unique street address.
- ERLs can exist without a site (filter: Has site = No).
- The ERL form shows the next available ELIN from the pool and rejects duplicate ELINs.
- New ERL fields: ALI comments, ERL type, last seen in export.
- CER Class/Type of Service codes (NENA) are mapped to CER's display names.
- ELIN API: `/api/plugins/cisco-cer/elins/`.

### Changed
- Deleting a Site keeps its ERLs, which become "no site", instead of deleting them.

## [0.1.0] - 2026-11-16

### Added
- ERL model tied to NetBox Sites, with ELIN, route pattern, ALI address fields and status.
- "Cisco CER" Site tab:
  - shows linked ERLs and their status in CER;
  - pushes or updates ERLs in CER;
  - opens a new-ERL form prefilled from the site address;
  - searches CER to link existing Conventional ERLs.
- ERL list, detail, edit, CSV import and REST API.
- Address lookup for Sites without an address (US Census geocoder and OpenStreetMap Nominatim). Picking a result saves the address and coordinates on the Site.
- "Link all address matches" button, to link several floor ERLs at once.
- Onsite alerts per ERL. A `default_onsite_alerts` setting attaches IDs (e.g. `PublicSafety`) to every pushed ERL.
- Off-Premises ERL status, for records only; pushing is disabled for it.
- `tab_weight` setting controls where the Site tab appears among other plugin tabs (default 9008).
- New ERLs always start as Planned; pushing or linking sets In CER.
- Pushing no longer requires an ELIN. An ELIN or onsite alerts added in the CER web page are kept when updating from NetBox.

### Fixed
- Route patterns are read from CER's XML export, because the JSON API drops the last character (`#911` comes back as `#91`).
