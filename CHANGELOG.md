# Changelog

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
- Pushing no longer requires an ELIN. An ELIN or onsite alerts added in the CER web page are kept when updating from NetBox.

### Fixed
- Route patterns are read from CER's XML export, because the JSON API drops the last character (`#911` comes back as `#91`).
