# NetBox Cisco CER

NetBox plugin for Cisco Emergency Responder (CER). Keeps Conventional ERL records in NetBox, tied to Sites, and pushes them to CER through its REST API.

## Features

- **ERL model**: Site, ERL name, ELIN and route pattern, ALI address fields, status. Includes list, filter, CSV import, REST API and change log.
- **Site tab ("Cisco CER")**:
  - lists the ERLs linked to the Site;
  - checks whether each is in CER's Conventional ERL list and whether the address matches;
  - **Push / Update CER** sends the ERL to CER;
  - **New ERL from site address** opens the add form prefilled from the Site's physical address;
  - **Link existing ERL** searches CER's Conventional ERLs by name, address or location. Address matches to the Site are suggested even when names differ.

### National E911 workflow

Cisco has no API for National E911 ERLs. As a workaround:

1. Create the ERL in NetBox and push it to CER as a Conventional ERL. Before step 2, give it a unique ELIN, either in NetBox or in the CER web page.
2. In CER, run **Migrate to National E911 Service Provider ERL**.
3. CER removes the Conventional ERL after migration. Set the NetBox record's status to *Migrated*.

## CER API notes

- `GET /cerappservices/service/cerl` returns every Conventional ERL. `?erlName=` is ignored.
- Failures come back as HTTP 200 with `"status": "Failure"`.
- Each ERL needs a unique ELIN, and the CER migration wizard fails without one. Pushing without an ELIN is allowed.
- The JSON GET drops the last character of `RoutePattern` (`#911` comes back as `#91`). The plugin reads route patterns from `/cerappservices/export/conventionalerl/info` instead.
- Onsite alert IDs come back padded with spaces.
- ALI Comments are limited to 30 characters. The plugin writes `NetBox site <id>` there.
- CER needs legacy TLS ciphers. The client uses `DEFAULT@SECLEVEL=0`.
- The CER application user needs the API role.

## Configuration

```python
PLUGINS = ["netbox_cisco_cer"]
PLUGINS_CONFIG = {
    "netbox_cisco_cer": {
        "cer_host": "cer.example.com",
        "cer_username": "api-user",
        "cer_password": "...",
        "verify_ssl": False,
        "default_route_pattern": "#911",
        "default_onsite_alerts": ["PublicSafety"],
        "tab_weight": 9008,
        "default_time_zone": "America/Los_Angeles",
        "default_cos": "Business PBX",
        "default_tos": "FX in 911 area",
        "default_customer_name": "",
        "default_company_id": "",
        "default_customer_code": "",
    },
}
```

Then run `manage.py migrate`.

## Support

If you find this plugin helpful, consider supporting development:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?style=flat&logo=buy-me-a-coffee)](https://buymeacoffee.com/automatebldrs)

## License

Apache-2.0
