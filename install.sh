#!/bin/bash

# =========================
# UTILITY FUNCTIONS
# =========================
display_banner() {
    cat << EOF
 ██████╗ ███████╗███╗   ██╗██████╗  ██████╗ ██████╗ 
██╔════╝ ██╔════╝████╗  ██║██╔══██╗██╔═══██╗██╔══██╗
██║  ███╗█████╗  ██╔██╗ ██║██████╔╝██║   ██║██║  ██║
██║   ██║██╔══╝  ██║╚██╗██║██╔═══╝ ██║   ██║██║  ██║
╚██████╔╝███████╗██║ ╚████║██║     ╚██████╔╝██████╔╝
 ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚═════╝ 

EOF
}

display_success_message() {
    echo
    echo "✅ Installation complete!"
    echo "➡️  Run the CLI using: $TOOL --version"
    echo "🛠️  Test the application by entering '$TOOL'."
}

error_exit() {
    echo "❌ $1"
    exit 1
}

to_title_case() {
    local input="$1"
    echo "$input" | awk '{ for (i=1; i<=NF; i++) $i = toupper(substr($i,1,1)) tolower(substr($i,2)); print }'
}

# =========================
# VARIABLE DECLARATIONS
# =========================
TOOL="genpod"
TOOL_TITLE=$(to_title_case "$tool")
VERSION="0.0.2"
SCRIPT_NAME="$TOOL.sh"
SOURCE_DIR_NAME="${TOOL}_src"
DEFAULT_INSTALL_PATH="/usr/local/bin"
USER_INSTALL_PATH="$HOME/.local/bin"
CONFIG_FILE="$HOME/.config/$TOOL/config.yml"

# Determine the installation directory dynamically
if [ -w "$DEFAULT_INSTALL_PATH" ]; then
    INSTALL_PATH="$DEFAULT_INSTALL_PATH"
elif [ -w "$USER_INSTALL_PATH" ]; then
    INSTALL_PATH="$USER_INSTALL_PATH"
else
    error_exit "No writable directory found for installation. Run as sudo or set INSTALL_PATH."
fi

BIN_DIR="$INSTALL_PATH/$SOURCE_DIR_NAME"

# =========================
# CLEANUP PREVIOUS INSTALLATIONS
# =========================
cleanup_previous_installation() {
    echo "🗑️  Checking for previous installations..."
    removed_anything=false

    if [ -d "$BIN_DIR" ]; then
        echo "🔍 Found existing installation directory: $BIN_DIR"
        rm -rf "$BIN_DIR" && {
            echo "✅ Successfully removed installation directory."
            removed_anything=true
        } || error_exit "Failed to remove existing installation directory."
    fi

    if [ -f "$INSTALL_PATH/$TOOL" ]; then
        echo "🔍 Found existing global command: $INSTALL_PATH/$TOOL"
        rm -f "$INSTALL_PATH/$TOOL" && {
            echo "✅ Successfully removed global command."
            removed_anything=true
        } || error_exit "Failed to remove existing global command."
    fi

    if [ "$removed_anything" = true ]; then
        echo "✅ Previous installation cleaned up successfully."
    else
        echo "ℹ️  No previous installation found. Nothing to clean up."
    fi
}

# =========================
# SETUP FUNCTIONS
# =========================
setup_virtualenv() {
    echo "🐍 Setting up Python virtual environment..."
    python3 -m venv .venv || error_exit "Failed to create virtual environment."
    source .venv/bin/activate
    pip install --upgrade pip
    [ -f "requirements.txt" ] && pip install -r requirements.txt || echo "⚠️ No requirements.txt found. Skipping dependencies."
    deactivate
}

generate_config() {
    echo "⚙️  Generating configuration file..."
    mkdir -p "$(dirname "$CONFIG_FILE")"

    echo "🛠️  Setting up the configuration file at $CONFIG_FILE"
    echo "🔍 Please provide the following paths. These paths are crucial for $TOOL_TITLE to function correctly."
    echo
    
    echo "💾 SQLite3 Database Path:"
    echo "   This is where $TOOL_TITLE saves metadata (logs, records, and indexes)."
    echo "   Default: $HOME/$TOOL/sqlite3.db (Press Enter to select default)."
    read -p "Enter SQLite3 database path: " SQLITE3_DB_PATH
    SQLITE3_DB_PATH=${SQLITE3_DB_PATH:-$HOME/$TOOL/sqlite3.db}
    echo

    echo "📂 Code Output Directory Path:"
    echo "   This is the workspace where $TOOL_TITLE saves generated code files (Python, JSON, etc.)."
    echo "   Default: $HOME/$TOOL/output (Press Enter to select default)."
    read -p "Enter code output directory path: " CODE_OUTPUT_DIR
    CODE_OUTPUT_DIR=${CODE_OUTPUT_DIR:-$HOME/$TOOL/output}
    echo

    echo "⚙️ $TOOL_TITLE Configuration File Path:"
    echo "   This file contains advanced code generation settings like:"
    echo "     - Language model configurations (e.g., OpenAI, Anthropic)."
    echo "     - Token limits, retry mechanisms, and behavior tuning."
    echo "   Default: $HOME/$TOOL/genpod_config.yml (Press Enter to select default)."
    read -p "Enter $TOOL_TITLE configuration file path: " GENPOD_CONFIG_PATH
    GENPOD_CONFIG_PATH=${GENPOD_CONFIG_PATH:-$HOME/$TOOL/genpod_config.yml}
    echo

    echo "📊 Vector Database Path (Mandatory):"
    echo "   This path points to the vector database (RAG store) used for semantic search and document retrieval."
    echo "   Mandatory: Please provide a valid file path."
    VECTOR_DB_PATH=""
    while [ -z "$VECTOR_DB_PATH" ]; do
        read -p "Enter vector database path: " VECTOR_DB_PATH
        if [ -z "$VECTOR_DB_PATH" ]; then
            echo "❌ Vector database path is mandatory. Please provide a valid path."
        fi
    done
    echo


    cat <<EOL > "$CONFIG_FILE"
# Genpod Configuration File
# This file contains key paths required by Genpod to function properly.

# SQLite3 Database Path
# Stores:
#   - Metadata (logs, generation records, indexes)
#   - Historical data like generation timestamps.
sqlite3_database_path: '$SQLITE3_DB_PATH'

# Code Output Directory Path
# Stores all generated code files such as Python, JSON, and configurations.
code_output_directory: '$CODE_OUTPUT_DIR'

# Genpod Configuration File Path
# Stores advanced settings for Genpod, including:
#   - Language model configurations
#   - Token usage limits and retry policies.
genpod_configuration_file_path: '$GENPOD_CONFIG_PATH'

# Vector Database Path
# The semantic search store required for Retrieval-Augmented Generation (RAG).
vector_database_path: '$VECTOR_DB_PATH'
EOL

    echo "✅ Configuration file successfully created at $CONFIG_FILE"
    echo "   You can edit this file later to update paths or settings."
}

install_files() {
    echo "📁 Copying source files..."
    mkdir -p "$BIN_DIR" || error_exit "Failed to create directory: $BIN_DIR"
    cp -r ./* "$BIN_DIR/" || error_exit "Failed to copy files to $BIN_DIR."
}

create_global_command() {
    echo "🔗 Setting up global command: $TOOL"
    cp "$SCRIPT_NAME" "$INSTALL_PATH/$TOOL" || error_exit "Failed to copy script to $INSTALL_PATH."
    chmod +x "$INSTALL_PATH/$TOOL" || error_exit "Failed to set executable permission."
}

# =========================
# MAIN INSTALLATION STEPS
# =========================
display_banner

echo "🛠️  Starting installation of $TOOL_TITLE CLI v$VERSION..."
cleanup_previous_installation
install_files

cd "$BIN_DIR" || error_exit "Failed to navigate to $BIN_DIR."

setup_virtualenv
generate_config
create_global_command

display_success_message
