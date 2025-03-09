import sys
import argparse
import platform
from pathlib import Path
from .help import show_welcome_help
from .scripts.node_installer import install_node


def main():
    """Main command entry (supports subcommands like streamget install-node)"""
    if is_main_help_request():
        show_welcome_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(
        prog='streamget',
        add_help=False
    )

    # Manually add help option
    parser.add_argument(
        '-h', '--help',
        action='help',
        default=argparse.SUPPRESS,
        help='Show help message'
    )

    subparsers = parser.add_subparsers(
        title="Available Commands",
        dest="command",
        required=True,
        help="Node.js runtime installation"
    )

    # install-node subcommand
    node_parser = subparsers.add_parser(
        'install-node',
        description='Install specific Node.js version to custom path',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''Example usage:
  streamget install-node                     # Install default version
  streamget install-node --version 20.0.0    # Specify version
  streamget install-node --path ./node_dir   # Custom install path

  Version reference: https://nodejs.org/dist/
  ''',
        add_help=False
    )
    node_parser.add_argument(
        '--version',
        default='22.14.0',
        help='Node.js version (default: %(default)s)'
    )
    node_parser.add_argument(
        '--path',
        type=Path,
        default=None,
        help='Custom installation path (default: ~/.streamget_node)'
    )
    node_parser.add_argument(
        '-h', '--help',
        action='help',
        help='Show this help message'
    )
    node_parser.set_defaults(func=handle_install_node)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        show_welcome_help()


def is_main_help_request():
    """Check if it's a global help request (not subcommand level)"""
    # Case 1: streamget -h/--help
    if len(sys.argv) == 2 and sys.argv[1] in ('-h', '--help'):
        return True
    # Case 2: streamget (no arguments)
    if len(sys.argv) == 1:
        return True
    return False


def handle_install_node(args):
    """Handle install-node subcommand"""
    try:
        # Parameter validation
        if args.path and not args.path.parent.exists():
            raise ValueError(f"Path {args.path.parent} does not exist")

        if args.path and not args.path.parent.is_dir():
            raise ValueError(f"{args.path.parent} is not a valid directory")

        # Version format validation
        if not all(c.isdigit() or c == '.' for c in args.version):
            raise ValueError("Invalid version format, should be like 20.0.0")

        # Execute installation
        install_node(
            version=args.version,
            install_path=args.path.expanduser() if args.path else None
        )

        print("✅  Node.js installed successfully!\n")

    except Exception as e:
        print(f"❌ Installation failed: {str(e)}\n")
        print("💡 Try adding --help for usage\n")
        sys.exit(1)


def get_bin_path(version, custom_path):
    """Generate Node.js binary path"""
    system = platform.system().lower()
    base_dir = custom_path or Path.home() / ".streamget_node"
    return base_dir / f"node-v{version}-{system}-x64" / ("bin" if system != 'windows' else "")
