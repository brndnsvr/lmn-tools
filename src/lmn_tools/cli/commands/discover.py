"""
Active Discovery commands.

Provides commands for running LogicMonitor Active Discovery
on network devices via NETCONF or SNMP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from pydantic import SecretStr
from rich.console import Console

from lmn_tools.core.config import NetconfCredentials
from lmn_tools.formatters.output import OutputFormatter, print_discovery, print_discovery_table

app = typer.Typer(help="Run Active Discovery on devices")
console = Console()


@app.command("netconf")
def discover_netconf(
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
        Optional[str],
        typer.Option("--type", "-t", help="Device type (coriant, ciena, juniper)"),
    ] = None,
    config_file: Annotated[
        Optional[Path],
        typer.Option("--config", "-c", help="Discovery config YAML file"),
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
    Run Active Discovery via NETCONF.

    Connects to a device using NETCONF and discovers instances
    based on the provided configuration file.

    Example:
        lmn discover netconf router1.example.com -u admin -c coriant.yaml
    """
    # Load config if provided
    config: dict = {}
    if config_file:
        if not config_file.exists():
            console.print(f"[red]Config file not found: {config_file}[/red]")
            raise typer.Exit(1)
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

    if not config.get("netconf_filter"):
        console.print("[yellow]Warning: No netconf_filter in config[/yellow]")
        console.print("Discovery will return empty results without a filter.")

    # Create credentials
    credentials = NetconfCredentials(
        username=username,
        password=SecretStr(password),
        port=port,
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
            if not device_type:
                detected = collector.detect_device_type()
                if detected and debug:
                    console.print(f"[dim]Detected device type: {detected}[/dim]", err=True)

            # Run discovery
            instances = collector.discover(config)

            # Output results
            if output_table:
                print_discovery_table(instances, show_properties=True)
            else:
                print_discovery(instances, use_json=output_json)

            if debug:
                console.print(f"\n[dim]Discovered {len(instances)} instances[/dim]", err=True)

    except ImportError:
        console.print("[red]NETCONF support not installed.[/red]")
        console.print("Install with: pip install lmn-tools[netconf]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if debug:
            console.print_exception()
        raise typer.Exit(1)


@app.command("coriant")
def discover_coriant(
    hostname: Annotated[str, typer.Argument(help="Device hostname or IP")],
    username: Annotated[str, typer.Option("--user", "-u", envvar="NETCONF_USER")],
    password: Annotated[
        str,
        typer.Option("--pass", "-p", envvar="NETCONF_PASS", prompt=True, hide_input=True),
    ],
    port: Annotated[int, typer.Option("--port")] = 830,
    config_file: Annotated[Optional[Path], typer.Option("--config", "-c")] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d")] = False,
) -> None:
    """
    Run Active Discovery on Coriant/Infinera devices.

    Shortcut for: lmn discover netconf --type coriant
    """
    # Delegate to netconf command with device_type preset
    discover_netconf(
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
def discover_ciena(
    hostname: Annotated[str, typer.Argument(help="Device hostname or IP")],
    username: Annotated[str, typer.Option("--user", "-u", envvar="NETCONF_USER")],
    password: Annotated[
        str,
        typer.Option("--pass", "-p", envvar="NETCONF_PASS", prompt=True, hide_input=True),
    ],
    port: Annotated[int, typer.Option("--port")] = 830,
    config_file: Annotated[Optional[Path], typer.Option("--config", "-c")] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d")] = False,
) -> None:
    """
    Run Active Discovery on Ciena WaveServer devices.

    Shortcut for: lmn discover netconf --type ciena
    """
    discover_netconf(
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
def discover_snmp(
    hostname: Annotated[str, typer.Argument(help="Device hostname or IP")],
    community: Annotated[
        Optional[str],
        typer.Option("--community", "-c", envvar="SNMP_COMMUNITY", help="SNMPv2c community string"),
    ] = None,
    version: Annotated[
        int,
        typer.Option("--version", "-v", help="SNMP version (2 or 3)"),
    ] = 2,
    username: Annotated[
        Optional[str],
        typer.Option("--user", "-u", envvar="SNMP_USER", help="SNMPv3 username"),
    ] = None,
    auth_pass: Annotated[
        Optional[str],
        typer.Option("--auth-pass", envvar="SNMP_AUTH_PASS", help="SNMPv3 auth password"),
    ] = None,
    priv_pass: Annotated[
        Optional[str],
        typer.Option("--priv-pass", envvar="SNMP_PRIV_PASS", help="SNMPv3 priv password"),
    ] = None,
    port: Annotated[int, typer.Option("--port")] = 161,
    config_file: Annotated[Optional[Path], typer.Option("--config")] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d")] = False,
) -> None:
    """
    Run Active Discovery via SNMP.

    Supports both SNMPv2c (community string) and SNMPv3 (USM) authentication.

    Example (v2c):
        lmn discover snmp router1 -c public --config snmp-discovery.yaml

    Example (v3):
        lmn discover snmp router1 -v 3 -u admin --auth-pass secret --priv-pass secret
    """
    from pydantic import SecretStr

    # Load config
    config: dict = {}
    if config_file and config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f) or {}

    try:
        from lmn_tools.collectors.snmp import SNMPCollector
        from lmn_tools.core.config import SNMPv2cCredentials, SNMPv3Credentials

        # Create credentials based on version
        if version == 2:
            if not community:
                community = "public"
            credentials = SNMPv2cCredentials(
                community=SecretStr(community),
                port=port,
            )
        else:  # v3
            if not username or not auth_pass or not priv_pass:
                console.print("[red]SNMPv3 requires --user, --auth-pass, and --priv-pass[/red]")
                raise typer.Exit(1)
            credentials = SNMPv3Credentials(
                username=username,
                auth_password=SecretStr(auth_pass),
                priv_password=SecretStr(priv_pass),
                port=port,
            )

        with SNMPCollector(hostname, credentials, debug=debug) as collector:
            instances = collector.discover(config)
            print_discovery(instances, use_json=output_json)

            if debug:
                console.print(f"\n[dim]Discovered {len(instances)} instances[/dim]", err=True)

    except ImportError:
        console.print("[red]SNMP support not installed.[/red]")
        console.print("Install with: pip install lmn-tools[snmp]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if debug:
            console.print_exception()
        raise typer.Exit(1)
