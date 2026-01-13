"""
Metric collection commands.

Provides commands for collecting metrics from network devices
via NETCONF or SNMP for LogicMonitor.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import SecretStr
from rich.console import Console

from lmn_tools.core.config import NetconfCredentials
from lmn_tools.formatters.output import print_collection, print_collection_table

app = typer.Typer(help="Collect metrics from devices")
console = Console()


@app.command("netconf")
def collect_netconf(
    hostname: Annotated[
        str,
        typer.Argument(help="Device hostname or IP address"),
    ],
    username: Annotated[
        str,
        typer.Option("--user", "-u", envvar="NETCONF_USER", help="NETCONF username"),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--pass",
            "-p",
            envvar="NETCONF_PASS",
            prompt=True,
            hide_input=True,
            help="NETCONF password",
        ),
    ],
    port: Annotated[
        int,
        typer.Option("--port", help="NETCONF port"),
    ] = 830,
    device_type: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Device type (coriant, ciena, juniper)"),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Collection config YAML file"),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", "-j", help="Output in JSON format"),
    ] = False,
    output_table: Annotated[
        bool,
        typer.Option("--table", help="Output as ASCII table"),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", "-d", help="Enable debug output"),
    ] = False,
) -> None:
    """
    Collect metrics via NETCONF.

    Connects to a device using NETCONF and collects metrics
    based on the provided configuration file.

    Example:
        lmn collect netconf router1.example.com -u admin -c coriant-collect.yaml
    """
    # Load config if provided
    config: dict[str, Any] = {}
    if config_file:
        if not config_file.exists():
            console.print(f"[red]Config file not found: {config_file}[/red]")
            raise typer.Exit(1) from None
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

    if not config.get("netconf_filter"):
        console.print("[yellow]Warning: No netconf_filter in config[/yellow]")

    if not config.get("metrics"):
        console.print("[yellow]Warning: No metrics defined in config[/yellow]")

    # Create credentials
    credentials = NetconfCredentials(
        username=username,
        password=SecretStr(password),
        port=port,
        timeout=60,
    )

    try:
        from lmn_tools.collectors.netconf import NetconfCollector

        with NetconfCollector(
            hostname=hostname,
            credentials=credentials,
            device_type=device_type,
            debug=debug,
        ) as collector:
            # Auto-detect device type if not specified
            if not device_type and hasattr(collector, "detect_device_type"):
                detected = collector.detect_device_type()
                if detected and debug:
                    console.print(f"[dim]Detected device type: {detected}[/dim]")

            # Run collection
            metrics = collector.collect(config)

            # Output results
            if output_table:
                print_collection_table(metrics)
            else:
                print_collection(metrics, use_json=output_json)

            if debug:
                console.print(f"\n[dim]Collected {len(metrics)} metrics[/dim]")

    except ImportError:
        console.print("[red]NETCONF support not installed.[/red]")
        console.print("Install with: pip install lmn-tools[netconf]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if debug:
            console.print_exception()
        raise typer.Exit(1) from None


@app.command("coriant")
def collect_coriant(
    hostname: Annotated[str, typer.Argument(help="Device hostname or IP")],
    username: Annotated[str, typer.Option("--user", "-u", envvar="NETCONF_USER")],
    password: Annotated[
        str,
        typer.Option("--pass", "-p", envvar="NETCONF_PASS", prompt=True, hide_input=True),
    ],
    port: Annotated[int, typer.Option("--port")] = 830,
    config_file: Annotated[Path | None, typer.Option("--config", "-c")] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d")] = False,
) -> None:
    """
    Collect metrics from Coriant/Infinera devices.

    Shortcut for: lmn collect netconf --type coriant
    """
    collect_netconf(
        hostname=hostname,
        username=username,
        password=password,
        port=port,
        device_type="coriant",
        config_file=config_file,
        output_json=output_json,
        output_table=False,
        debug=debug,
    )


@app.command("ciena")
def collect_ciena(
    hostname: Annotated[str, typer.Argument(help="Device hostname or IP")],
    username: Annotated[str, typer.Option("--user", "-u", envvar="NETCONF_USER")],
    password: Annotated[
        str,
        typer.Option("--pass", "-p", envvar="NETCONF_PASS", prompt=True, hide_input=True),
    ],
    port: Annotated[int, typer.Option("--port")] = 830,
    config_file: Annotated[Path | None, typer.Option("--config", "-c")] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d")] = False,
) -> None:
    """
    Collect metrics from Ciena WaveServer devices.

    Shortcut for: lmn collect netconf --type ciena
    """
    collect_netconf(
        hostname=hostname,
        username=username,
        password=password,
        port=port,
        device_type="ciena",
        config_file=config_file,
        output_json=output_json,
        output_table=False,
        debug=debug,
    )


@app.command("snmp")
def collect_snmp(
    hostname: Annotated[str, typer.Argument(help="Device hostname or IP")],
    community: Annotated[
        str | None,
        typer.Option("--community", "-c", envvar="SNMP_COMMUNITY"),
    ] = None,
    version: Annotated[
        int,
        typer.Option("--version", "-v", help="SNMP version (2 or 3)"),
    ] = 2,
    username: Annotated[
        str | None,
        typer.Option("--user", "-u", envvar="SNMP_USER"),
    ] = None,
    auth_pass: Annotated[
        str | None,
        typer.Option("--auth-pass", envvar="SNMP_AUTH_PASS"),
    ] = None,
    priv_pass: Annotated[
        str | None,
        typer.Option("--priv-pass", envvar="SNMP_PRIV_PASS"),
    ] = None,
    port: Annotated[int, typer.Option("--port")] = 161,
    config_file: Annotated[Path | None, typer.Option("--config")] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d")] = False,
) -> None:
    """
    Collect metrics via SNMP.

    Example (v2c):
        lmn collect snmp router1 -c public --config snmp-collect.yaml

    Example (v3):
        lmn collect snmp router1 -v 3 -u admin --auth-pass secret --priv-pass secret
    """
    from pydantic import SecretStr

    # Load config
    config: dict[str, Any] = {}
    if config_file and config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

    try:
        from lmn_tools.collectors.snmp import SNMPCollector
        from lmn_tools.core.config import SNMPv2cCredentials, SNMPv3Credentials

        # Create credentials based on version
        snmp_credentials: SNMPv2cCredentials | SNMPv3Credentials
        if version == 2:
            if not community:
                community = "public"
            snmp_credentials = SNMPv2cCredentials(
                community=SecretStr(community),
                port=port,
                timeout=5,
                retries=2,
            )
        else:  # v3
            if not username or not auth_pass or not priv_pass:
                console.print("[red]SNMPv3 requires --user, --auth-pass, and --priv-pass[/red]")
                raise typer.Exit(1) from None
            snmp_credentials = SNMPv3Credentials(
                username=username,
                auth_password=SecretStr(auth_pass),
                priv_password=SecretStr(priv_pass),
                auth_protocol="SHA",
                priv_protocol="AES128",
                port=port,
                timeout=5,
                retries=2,
            )

        with SNMPCollector(hostname, snmp_credentials, debug=debug) as collector:
            metrics = collector.collect(config)
            print_collection(metrics, use_json=output_json)

            if debug:
                console.print(f"\n[dim]Collected {len(metrics)} metrics[/dim]")

    except ImportError:
        console.print("[red]SNMP support not installed.[/red]")
        console.print("Install with: pip install lmn-tools[snmp]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if debug:
            console.print_exception()
        raise typer.Exit(1) from None
