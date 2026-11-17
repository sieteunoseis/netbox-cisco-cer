"""Navigation menu items for NetBox Cisco CER plugin."""

from netbox.plugins import PluginMenuButton, PluginMenuItem

menu_items = (
    PluginMenuItem(
        link="plugins:netbox_cisco_cer:erl_list",
        link_text="CER ERLs",
        permissions=["netbox_cisco_cer.view_erl"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_cisco_cer:erl_add",
                title="Add",
                icon_class="mdi mdi-plus-thick",
                permissions=["netbox_cisco_cer.add_erl"],
            ),
            PluginMenuButton(
                link="plugins:netbox_cisco_cer:erl_bulk_import",
                title="Import",
                icon_class="mdi mdi-upload",
                permissions=["netbox_cisco_cer.add_erl"],
            ),
        ),
    ),
)
