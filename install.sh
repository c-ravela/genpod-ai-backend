#!/bin/bash

echo " ██████╗ ███████╗███╗   ██╗██████╗  ██████╗ ██████╗ ";
echo "██╔════╝ ██╔════╝████╗  ██║██╔══██╗██╔═══██╗██╔══██╗";
echo "██║  ███╗█████╗  ██╔██╗ ██║██████╔╝██║   ██║██║  ██║";
echo "██║   ██║██╔══╝  ██║╚██╗██║██╔═══╝ ██║   ██║██║  ██║";
echo "╚██████╔╝███████╗██║ ╚████║██║     ╚██████╔╝██████╔╝";
echo " ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚═════╝ ";
echo

create_or_update_config() {
    CONFIG_FILE="$HOME/.config/genpod/config.yml"

    # Ensure the directory exists
    mkdir -p "$(dirname "$CONFIG_FILE")"

    echo "🛠️  Setting up the configuration file at $CONFIG_FILE"
    echo "🔍 Please provide the following paths. These paths are crucial for Genpod to function correctly."
    echo

    # Prompt user for SQLite3 database path
    echo "💾 SQLite3 Database Path:"
    echo "   This is the file path where Genpod will save metadata related to generated code and system operations."
    echo "   The SQLite3 database stores the following types of information:"
    echo "     - Code generation logs and records"
    echo "     - SQL-based tables for indexing generated content"
    echo "     - Configuration or runtime statistics for debugging and optimization"
    echo "     - Historical data about previous operations (e.g., timestamps, generation IDs)"
    echo "   Why is this important?"
    echo "     - Ensures all operations are traceable and auditable"
    echo "     - Enables smooth retrieval and updates when working with generated files or settings"
    echo "   Default: $HOME/genpod/sqlite3.db (Press Enter to select default)"
    read -p "Enter SQLite3 database path: " SQLITE3_DB_PATH
    SQLITE3_DB_PATH=${SQLITE3_DB_PATH:-$HOME/genpod/sqlite3.db}
    echo

    # Prompt user for code output directory
    echo "📂 Code Output Directory Path:"
    echo "   This directory will store all the generated code files created by Genpod."
    echo "     - All generated Python, JSON, or other code files will be saved here."
    echo "     - The directory serves as the main workspace for reviewing and editing generated content."
    echo "     - Allows easy organization of files, ensuring a centralized location for all output."
    echo "   Why is this important?"
    echo "     - Ensures all generated outputs are easily accessible."
    echo "     - Simplifies integration with other tools or projects by maintaining a consistent location."
    echo "   Default: $HOME/genpod/output (Press Enter to select default)"
    read -p "Enter code output directory path: " CODE_OUTPUT_DIR
    CODE_OUTPUT_DIR=${CODE_OUTPUT_DIR:-$HOME/genpod/output}
    echo

    # Prompt user for Genpod configuration file path
    echo "⚙️  Genpod Configuration File Path:"
    echo "   This file contains settings for code generation, such as LLM (Language Model) configurations, limits, and other parameters."
    echo "   Details about this configuration file:"
    echo "     - Includes AI model configurations (e.g., OpenAI, Anthropic) and their specific settings."
    echo "     - Allows customization of generation limits, token usage, and retry mechanisms."
    echo "     - Serves as the central location for managing all Genpod-specific settings."
    echo "   Why is this important?"
    echo "     - Provides flexibility for advanced users to fine-tune Genpod behavior."
    echo "     - Ensures the application runs smoothly with tailored settings for specific use cases."
    echo "   Default: $HOME/genpod/genpod_config.yml (Press Enter to select default)"
    read -p "Enter Genpod configuration file path: " GENPOD_CONFIG_PATH
    GENPOD_CONFIG_PATH=${GENPOD_CONFIG_PATH:-$HOME/genpod/genpod_config.yml}
    echo

    # Prompt user for vector database path (mandatory field)
    echo "📊 Vector Database Path (Mandatory):"
    echo "   This is the file path to the vector data store, which holds documents for Retrieval-Augmented Generation (RAG)."
    echo "   Details about this database:"
    echo "     - The vector database enables efficient semantic search for documents or information."
    echo "     - Stores embeddings (numerical representations) of documents used by Genpod to find relevant content."
    echo "     - Key for advanced AI functionalities like answering queries or generating contextually accurate outputs."
    echo "   Why is this important?"
    echo "     - Enables powerful document retrieval capabilities in Genpod."
    echo "     - Ensures Genpod can access and utilize relevant data for enhanced output accuracy."
    echo "   This field is mandatory. Please provide a valid path."
    VECTOR_DB_PATH=""
    while [ -z "$VECTOR_DB_PATH" ]; do
        read -p "Enter vector database path: " VECTOR_DB_PATH
        if [ -z "$VECTOR_DB_PATH" ]; then
            echo "❌ Vector database path is mandatory. Please provide a valid path."
        fi
    done
    echo
    
    # Create or update the YAML configuration file
    cat <<EOL > "$CONFIG_FILE"
# Genpod Configuration File
# This file contains the key configuration paths required by Genpod.
# Each field is explained in detail below to help you understand its purpose.

# The absolute file path to the SQLite3 database where Genpod will store metadata.
# This metadata includes:
#   - Code generation logs and records
#   - SQL-based tables for indexing and querying generated content
#   - Historical data about operations such as timestamps and generation IDs
# Purpose:
#   - Ensures efficient storage and retrieval of generated code-related data.
sqlite3_database_path: '$SQLITE3_DB_PATH'

# Directory path for saving all the generated code files created by Genpod.
# This directory is used to:
#   - Store output files like Python scripts, JSON configurations, or other generated artifacts.
#   - Provide a centralized location for reviewing and managing generated outputs.
# Purpose:
#   - Ensures all generated content is easily accessible for editing, testing, and integration.
code_output_directory: '$CODE_OUTPUT_DIR'

# The file path to the vector data store, which is essential for Retrieval-Augmented Generation (RAG).
# This database contains:
#   - Embeddings (numerical representations) of documents
#   - Data used for semantic search and retrieval of relevant content
# Purpose:
#   - Supports Genpod's advanced AI capabilities, such as finding relevant documents or generating accurate responses.
# Note:
#   - This field is mandatory as it powers the core RAG functionality in Genpod.
vector_database_path: '$VECTOR_DB_PATH'

# The file path to the configuration file for Genpod's code generation settings.
# This configuration file includes:
#   - Language model (LLM) settings, such as provider details (e.g., OpenAI, Anthropic)
#   - Token limits for generated content
#   - Retry policies for handling generation errors
# Purpose:
#   - Allows fine-tuning of Genpod's behavior for specific use cases.
#   - Provides a single location to manage all code generation-related settings.
genpod_configuration_file_path: '$GENPOD_CONFIG_PATH'
EOL

    echo "✅ Configuration file created at $CONFIG_FILE"
    echo "   You can update these values later if needed by editing the file directly."
    echo
}

# Display installation success message
display_success_message() {
    echo "✅ Installation complete!"
    echo "📂 Installed source files to: $GENPOD_BIN_DIR"
    echo "➡️  Run the application using the command: $GENPOD_GLOBAL_CMD"
    echo "🛠️  Test the installation by running: $GENPOD_GLOBAL_CMD --version"
    echo
    echo "Sample output:"
    echo "GENPOD CLI version vx.y.z"
}

FULL_COMMAND="$0 $@"

# Constants
GENPOD_SCRIPT_NAME="genpod.sh"
SOURCE_DIR_NAME="genpod_src" # Renamed source directory
GENPOD_GLOBAL_CMD="genpod"
DEFAULT_INSTALL_PATH="/usr/local/bin"
USER_INSTALL_PATH="$HOME/.local/bin"

# Determine the installation directory dynamically
INSTALL_PATH=""
if [ -w "$DEFAULT_INSTALL_PATH" ]; then
    INSTALL_PATH="$DEFAULT_INSTALL_PATH"
elif [ -w "$USER_INSTALL_PATH" ]; then
    INSTALL_PATH="$USER_INSTALL_PATH"
else
    echo "🚨 INSTALLATION ERROR: NO WRITABLE DIRECTORY FOUND 🚨"
    echo
    echo "Unfortunately, neither of the following directories is writable:"
    echo "- SYSTEM-WIDE DIRECTORY: $DEFAULT_INSTALL_PATH"
    echo "- USER-SPECIFIC DIRECTORY: $USER_INSTALL_PATH"
    echo
    echo "💡 HOW TO FIX THIS ISSUE:"
    echo
    echo "Try 'ONE' of the following options to resolve the issue:"
    echo
    echo "🔑 OPTION 1: RUN THE SCRIPT WITH ELEVATED PERMISSIONS"
    echo "   Grant necessary permissions for installation in the system-wide directory by running:"
    echo "      sudo bash $FULL_COMMAND"
    echo
    echo "📌 OPTION 2: SPECIFY A CUSTOM WRITABLE DIRECTORY"
    echo "   Set a writable installation directory using the INSTALL_PATH environment variable and rerun the script:"
    echo "      INSTALL_PATH=/opt/genpod bash $FULL_COMMAND"
    echo
    echo "🏡 OPTION 3: CREATE AND USE A USER-SPECIFIC DIRECTORY"
    echo "   Ensure the user-specific directory exists and is writable, then rerun the script:"
    echo "      mkdir -p $USER_INSTALL_PATH"
    echo "      bash $FULL_COMMAND"
    echo
    echo "❓ IF THESE OPTIONS DON'T RESOLVE THE ISSUE:"
    echo "   - Verify you have appropriate permissions for the target directory."
    echo "   - Ensure the INSTALL_PATH you provide is valid and writable."
    echo "   - Reach out to your system administrator for further assistance."
    echo
    echo "🌟 THANK YOU FOR USING GENPOD! We're here to make AI integration seamless for you."
    exit 1
fi

GENPOD_BIN_DIR="$INSTALL_PATH/$SOURCE_DIR_NAME"

# Locate the current directory
CURRENT_DIR=$(pwd)

# Detect the operating system
OS_NAME=$(uname -s)
echo "🖥️  Detected OS: $OS_NAME"

# Remove any existing installation
if [ -d "$GENPOD_BIN_DIR" ]; then
    echo "🗑️  Removing previous installation source folder at $GENPOD_BIN_DIR..."
    rm -rf "$GENPOD_BIN_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to remove the source folder. Try running this script with 'sudo'."
        exit 1
    fi
fi

if [ -f "$INSTALL_PATH/$GENPOD_GLOBAL_CMD" ]; then
    echo "🗑️  Removing existing global command at $INSTALL_PATH/$GENPOD_GLOBAL_CMD..."
    rm -f "$INSTALL_PATH/$GENPOD_GLOBAL_CMD"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to remove the global command. Try running this script with 'sudo'."
        exit 1
    fi
fi


# Create the target directory
mkdir -p "$GENPOD_BIN_DIR"
if [ $? -ne 0 ]; then
    echo "❌ Failed to create installation directory at $GENPOD_BIN_DIR. Try running this script with 'sudo'."
    exit 1
fi

# Copy all source files to the bin directory
echo "📁 Copying source files to $GENPOD_BIN_DIR..."
cp -r "$CURRENT_DIR/"* "$GENPOD_BIN_DIR/"
if [ $? -ne 0 ]; then
    echo "❌ Failed to copy source files. Try running this script with 'sudo'."
    exit 1
fi

# Navigate to the bin directory
cd "$GENPOD_BIN_DIR" || exit

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "🐍 Installing Python dependencies..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Python dependencies. Try running this script with 'sudo'."
        exit 1
    fi
else
    echo "⚠️ No requirements.txt file found. Skipping Python dependency installation."
fi

# Create or update the YAML configuration file
echo
echo "⚙️  Generating configuration file for Genpod..."
create_or_update_config

# Make the genpod.sh script executable
echo
echo "🔗 Setting up the $GENPOD_GLOBAL_CMD command..."
if cp "$CURRENT_DIR/$GENPOD_SCRIPT_NAME" "$INSTALL_PATH/$GENPOD_GLOBAL_CMD"; then
    chmod +x "$INSTALL_PATH/$GENPOD_GLOBAL_CMD"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to set up the $GENPOD_GLOBAL_CMD command. Try running this script with 'sudo'."
        exit 1
    fi
else
    echo "❌ Failed to copy $GENPOD_SCRIPT_NAME to $INSTALL_PATH."
    exit 1
fi

display_success_message
