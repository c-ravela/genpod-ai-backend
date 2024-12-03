#!/bin/bash

GENPOD_VERSION="0.0.1"
CONFIG_FILE_PATH="$HOME/.config/genpod/config.yml"

temp_json_data='{
    "project_id": 1,
    "project_name": "Test Project",
    "license_text": "SPDX-License-Identifier: Apache-2.0\nCopyright 2024 Authors of CRBE & the Organization created CRBE",
    "license_url": "https://raw.githubusercontent.com/intelops/tarian-detector/8a4ff75fe31c4ffcef2db077e67a36a067f1437b/LICENSE",
    "user_id": 153
}'

# Function to locate the configuration file
locate_config_file() {
    if [ -f "$CONFIG_FILE_PATH" ]; then
        return 0
    else
        echo "❌ Configuration file not found at $CONFIG_FILE_PATH."
        echo "   Please ensure the configuration file is created during installation or run the setup again."
        exit 1
    fi
}

# Export the configuration file path for Python scripts
export_config_path() {
    export GENPOD_CONFIG="$CONFIG_FILE_PATH"
}

# Function to display the version
display_version() {
    echo "GENPOD CLI version v$GENPOD_VERSION"
}

# Function to display branding
display_branding() {
    echo " ██████╗ ███████╗███╗   ██╗██████╗  ██████╗ ██████╗ "
    echo "██╔════╝ ██╔════╝████╗  ██║██╔══██╗██╔═══██╗██╔══██╗"
    echo "██║  ███╗█████╗  ██╔██╗ ██║██████╔╝██║   ██║██║  ██║"
    echo "██║   ██║██╔══╝  ██║╚██╗██║██╔═══╝ ██║   ██║██║  ██║"
    echo "╚██████╔╝███████╗██║ ╚████║██║     ╚██████╔╝██████╔╝"
    echo " ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚═════╝ "
    echo "                                             v$GENPOD_VERSION"
    echo
}

# Function to display flag-based help (pre-interactive mode)
display_flag_help() {
    echo "📝 GENPOD CLI Help:"
    echo
    echo "Usage:"
    echo "   genpod [flags]"
    echo
    echo "Available Flags:"
    echo "   --version  - Display the GENPOD CLI version."
    echo "   --help     - Show this help message."
    echo
    echo "To enter interactive mode, simply run 'genpod' without any flags."
    echo
    echo "🙏 Thank you for using GENPOD! For more help, enter the CLI and type '.help'."
}

# Function to display interactive CLI help
display_cli_help() {
    echo "📝 GENPOD CLI Interactive Help:"
    echo
    echo "Available Commands:"
    echo "   .generate  - Generate a new project."
    echo "   .resume    - Resume an existing project."
    echo "   .version   - Display the version of GENPOD CLI."
    echo "   .clear     - Clear the terminal screen."
    echo "   .help      - Show this help message."
    echo "   .quit      - Exit the interactive session."
    echo "   .exit      - Exit the interactive session."
    echo
    echo "🙏 Thank you for using GENPOD! Type '.quit' or '.exit' to leave interactive mode."
}

tool="genpod"
DIR_NAME="genpod_src"
# Detect the directory where the script is installed
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_DIR="$SCRIPT_DIR/$DIR_NAME"

# Check for command-line arguments
if [[ "$1" == "--version" ]]; then
    display_version
    exit 0
elif [[ "$1" == "--help" ]]; then
    display_flag_help
    exit 0
elif [[ "$1" != "" ]]; then
    echo "❌ Unknown flag: $1"
    echo
    display_flag_help
    exit 1
fi

locate_config_file

# Export the configuration file path
export_config_path

# Display branding
display_branding
echo "Welcome to GENPOD v$GENPOD_VERSION!"
echo "Type '.help' to see a list of available commands."
echo

# Navigate to the dynamically detected project directory
cd "$PROJECT_DIR" || {
    echo "❌ Failed to navigate to the project directory: $PROJECT_DIR"
    exit 1
}

# Activate the virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found in $PROJECT_DIR. Please ensure it's set up."
    exit 1
fi

# Run a persistent loop
while true; do
    echo -n "$tool> "  # Interactive prompt
    read -r command  # Read user input

    # Handle empty input
    if [[ -z "$command" ]]; then
        continue  # Skip the loop iteration for empty input
    fi

    case "$command" in
        .generate)
            # Generate a new project
            python3 main.py generate "$temp_json_data"
            ;;
        .resume)
            # Resume a paused project
            python3 main.py resume 153
            ;;
        .version)
            # Display the version
            display_version
            ;;
        .clear)
            # Clear the terminal
            clear
            display_branding
            echo "Type '.help' to see a list of available commands."
            echo
            ;;
        .exit|.quit)
            echo "👋 Exiting GENPOD. Goodbye!"
            echo "🙏 Thank you for using GENPOD. Have a great day!"
            deactivate
            break
            ;;
        .help)
            # Display interactive CLI help
            display_cli_help
            ;;
        *)
            echo "❌ Unknown command: $command"
            echo "ℹ️  Type '.help' to see a list of available commands."
            ;;
    esac
done
