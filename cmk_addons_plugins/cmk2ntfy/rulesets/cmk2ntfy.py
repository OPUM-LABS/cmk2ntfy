#!/usr/bin/env python3

import socket
from typing import Any, Literal

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    FixedValue,
    MultilineText,
    Password,
    Proxy,
    String,
    migrate_to_proxy,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, Url, UrlProtocol
from cmk.rulesets.v1.rule_specs import (
    NotificationParameters,
    Topic,
)
from cmk.utils import password_store


def local_site_url() -> str:
    return "https://" + socket.gethostname() + "/check_mk/"


def _migrate_url_prefix(p: object) -> tuple[str, str | None]:
    if isinstance(p, tuple):
        return p

    if isinstance(p, str):
        return ("manual", p)

    if isinstance(p, dict):
        for key, value in p.items():
            if key == "manual":
                return (key, value)
            return (f"{key}_{value}", None)

    raise ValueError(f"Invalid format for URL prefix: {p}")


def _get_url_prefix_setting(
    default_value: str = "automatic_https",
) -> DictElement[Any]:
    return DictElement(
        parameter_form=CascadingSingleChoice(
            title=Title("URL prefix for links to Checkmk"),
            help_text=Help(
                "If you use <b>Automatic HTTP/s</b>, the URL prefix for "
                "host and service links within the notification is filled "
                "automatically. If you specify an URL prefix here, then "
                "several parts of the notification are armed with hyperlinks "
                "to your Checkmk GUI. In both cases, the recipient of the "
                "notification can directly visit the host or service in "
                "question in Checkmk. Specify an absolute URL including the "
                "<tt>.../check_mk/</tt>."
            ),
            elements=[
                CascadingSingleChoiceElement(
                    name="automatic_http",
                    title=Title("Automatic HTTP"),
                    parameter_form=FixedValue(
                        value=None,
                    ),
                ),
                CascadingSingleChoiceElement(
                    name="automatic_https",
                    title=Title("Automatic HTTPs"),
                    parameter_form=FixedValue(
                        value=None,
                    ),
                ),
                CascadingSingleChoiceElement(
                    name="manual",
                    title=Title("Specify URL prefix"),
                    parameter_form=String(
                        prefill=DefaultValue(local_site_url()),
                        custom_validate=[Url([UrlProtocol.HTTP, UrlProtocol.HTTPS])],
                    ),
                ),
            ],
            migrate=_migrate_url_prefix,
            prefill=DefaultValue(default_value),
        ),
    )


def _migrate_to_password(
    password: object,
) -> tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[str, str],
]:
    if isinstance(password, tuple):
        if password[0] == "store":
            return ("cmk_postprocessed", "stored_password", (password[1], ""))

        if password[0] == "routing_key":
            return (
                "cmk_postprocessed",
                "explicit_password",
                (password_store.ad_hoc_password_id(), password[1]),
            )

        # Already migrated
        assert len(password) == 3
        return password

    raise ValueError(f"Invalid password format: {password}")


def _valuespec_cmk2ntfy() -> Dictionary:
    return Dictionary(
        title=Title("Create notification with the following parameters"),
        elements={
            "cmk2ntfy_topic": DictElement(
                parameter_form=String(
                    title=Title("Topic"),
                    help_text=Help("The Topic the Notifications should be posted in."),
                    prefill=DefaultValue("cmk"),
                ),
                required=True,
            ),
            "cmk2ntfy_instance": DictElement(
                parameter_form=String(
                    title=Title("ntfy Instance"),
                    help_text=Help("Change value if you run your own instance."),
                    prefill=DefaultValue("ntfy.sh"),
                ),
                required=True,
            ),
            "cmk2ntfy_access_token": DictElement(
                parameter_form=Password(
                    title=Title("ntfy access token"),
                    migrate=_migrate_to_password,
                    custom_validate=[
                        LengthInRange(
                            min_value=1,
                            error_msg=Message("Please enter an access token"),
                        ),
                    ],
                ),
                required=False,
            ),
            "cmk2ntfy_include_cmk_icon": DictElement(
                parameter_form=FixedValue(
                    title=Title("Include Check_mk icon in Notification Message"),
                    help_text=Help(
                        "Might be usefull if notifications are not send to an dedicated topic."
                    ),
                    value=True,
                    label=Label("Include Check_mk icon in Notification Message"),
                )
            ),
            "cmk2ntfy_host_msg_tmpl": DictElement(
                parameter_form=MultilineText(
                    title=Title("Host notification template"),
                    help_text=Help(
                        "Override default notification template. Note that first empty line seperates message title from body"
                    ),
                    prefill=DefaultValue(
                        "Host: $HOSTALIAS$ $HOSTSTATE$\n\n$HOSTOUTPUT$"
                    ),
                    macro_support=True,
                )
            ),
            "cmk2ntfy_svc_msg_tmpl": DictElement(
                parameter_form=MultilineText(
                    title=Title("Service notification template"),
                    help_text=Help(
                        "Override default notification template. Note that first empty line seperates message title from body"
                    ),
                    prefill=DefaultValue(
                        "Service: $HOSTALIAS$ / $SERVICEDESC$ $SERVICESTATE$\n\n$SERVICEOUTPUT$"
                    ),
                    macro_support=True,
                )
            ),
            "ignore_ssl": DictElement(
                parameter_form=FixedValue(
                    title=Title("Disable SSL certificate verification"),
                    label=Label("Disable SSL certificate verification"),
                    value=True,
                    help_text=Help(
                        "Ignore unverified HTTPS request warnings. Use with caution."
                    ),
                )
            ),
            "proxy_url": DictElement(
                parameter_form=Proxy(
                    migrate=migrate_to_proxy,
                ),
            ),
            "url_prefix": _get_url_prefix_setting(
                default_value="automatic_https",
            ),
        },
    )

rule_spec_notification_cmk2ntfy = NotificationParameters(
    title=Title("cmk2ntfy"),
    topic=Topic.NOTIFICATIONS,
    parameter_form=_valuespec_cmk2ntfy,
    name="cmk2ntfy",
)