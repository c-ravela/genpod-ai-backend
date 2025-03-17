#!/bin/bash

# =========================
# UTILITY FUNCTIONS
# =========================
to_title_case() {
    local input="$1"
    echo "$input" | awk '{ for (i=1; i<=NF; i++) $i = toupper(substr($i,1,1)) tolower(substr($i,2)); print }'
}

# =========================
# GENPOD CLI CONFIGURATION
# =========================
tool="genpod"
TOOL_TITLE=$(to_title_case "$tool")

GENPOD_VERSION="0.0.2"
CONFIG_FILE_PATH="$HOME/.config/$tool/config.yml"
SESSION_FILE="$HOME/."$tool"_session"
USER_ID=""

DIR_NAME=$tool"_src"
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_DIR="$SCRIPT_DIR/$DIR_NAME"

# =========================
# UTILITY FUNCTIONS
# =========================
locate_config_file() {
    if [ -f "$CONFIG_FILE_PATH" ]; then
        return 0
    else
        echo "❌ Configuration file not found at $CONFIG_FILE_PATH."
        echo "   Please ensure the configuration file is created during installation or run the setup again."
        exit 1
    fi
}

export_config_path() {
    export GENPOD_CONFIG="$CONFIG_FILE_PATH"
}

display_version() {
    echo "$TOOL_TITLE CLI version v$GENPOD_VERSION"
}

display_branding() {
    cat << EOF
 ██████╗ ███████╗███╗   ██╗██████╗  ██████╗ ██████╗ 
██╔════╝ ██╔════╝████╗  ██║██╔══██╗██╔═══██╗██╔══██╗
██║  ███╗█████╗  ██╔██╗ ██║██████╔╝██║   ██║██║  ██║
██║   ██║██╔══╝  ██║╚██╗██║██╔═══╝ ██║   ██║██║  ██║
╚██████╔╝███████╗██║ ╚████║██║     ╚██████╔╝██████╔╝
 ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚═════╝ 
                                             v$GENPOD_VERSION

EOF
}


display_flag_help() {
    cat << EOF
📝  $TOOL_TITLE CLI Help:

Usage:
   $tool [flags]

Available Flags:
   --version  - Display the $TOOL_TITLE CLI version.
   --help     - Show this help message.

To enter interactive mode, simply run '$tool' without any flags.

🙏 Thank you for using $TOOL_TITLE! For more help, enter the CLI and type '.help'.
EOF
}

display_cli_help() {
    cat << EOF
📝 $TOOL_TITLE CLI Interactive Help:

Available Commands:

   .login
       Log in to the $TOOL_TITLE system.

   .logout
       Log out of the $TOOL_TITLE system.

   .generate <project_id>
       Generate a new service.

   .add_project
       Add a new project to the system.

   .resume
       Resume an existing service.

   .progress <project_id> <service_id>
       Display the real-time progress of a service by ID.

   .version
       Display the version of $TOOL_TITLE CLI.

   .clear
       Clear the terminal screen.

   .help
       Show this help message.

   .quit / .exit
       Exit the interactive session.

🙏 Thank you for using $TOOL_TITLE! Type '.quit' or '.exit' to leave interactive mode.
EOF
}

# =========================
# SESSION MANAGEMENT
# =========================
login_user() {
    echo -n "Enter your User ID to log in: "
    read -r user_id

    if [[ -z "$user_id" ]]; then
        echo "❌ User ID cannot be empty. Please try again."
        return 1
    fi

    if [[ "$user_id" =~ ^[0-9]+$ ]]; then
        echo "$user_id" > "$SESSION_FILE"
        USER_ID="$user_id"
        echo "✅ Successfully logged in as User ID: $USER_ID"
    else
        echo "❌ Invalid User ID. Please enter numeric values only."
        return 1
    fi
}

logout_user() {
    if [[ -f "$SESSION_FILE" ]]; then
        rm "$SESSION_FILE"
        USER_ID=""
        echo "👋 You have been logged out successfully."
    else
        echo "ℹ️  You are not logged in."
    fi
}

check_login() {
    if [[ -f "$SESSION_FILE" ]]; then
        USER_ID=$(cat "$SESSION_FILE")
        echo "🔐 Logged in as User ID: $USER_ID"
    else
        echo "❌ No active session found. Please log in to continue."
        login_user
        [[ $? -ne 0 ]] && exit 1
    fi
}

get_logged_in_user() {
    if [[ -f "$SESSION_FILE" ]]; then
        cat "$SESSION_FILE"
    else
        echo "❌ You are not logged in. Please log in to continue."
        return 1
    fi
}

validate_logged_in() {
    if [[ -z "$USER_ID" ]]; then
        echo "❌ You are not logged in. Please log in using '.login' before continuing."
        return 1
    fi
    return 0
}

# =========================
# MAIN LOOP
# =========================
main_loop() {
    echo Welcome to $TOOL_TITLE v$GENPOD_VERSION!
    echo "Type '.help' to see a list of available commands."
    echo

    while true; do
        echo -n "$tool> "
        read -r command input input2

        if [[ -z "$command" ]]; then
            continue
        fi

        case "$command" in
            .generate)
                validate_logged_in || continue
                [[ -z "$input" ]] && echo "❌ Missing project ID. Usage: .generate <project_id>" || python3 main.py generate "$input" "$USER_ID"
                ;;
            .resume)
                validate_logged_in || continue
                python3 main.py resume "$USER_ID"
                ;;
            .add_project)
                validate_logged_in || continue
                python3 main.py add_project "$USER_ID"
                ;;
            .progress)
                validate_logged_in || continue
                if [[ -z "$input" ]]; then
                    echo "❌ Missing project ID. Usage: .progress <project_id> <service_id>"
                elif [[ -z "$input2" ]]; then
                    echo "❌ Missing service ID. Usage: .progress <project_id> <service_id>"
                else
                    python3 main.py microservice_status "$input" "$input2" "$USER_ID"
                fi
                ;;
            .version)
                display_version
                ;;
            .clear)
                clear
                display_branding
                ;;
            .exit|.quit)
                echo "👋 Exiting $tool. Goodbye!"
                deactivate
                break
                ;;
            .help)
                display_cli_help
                ;;
            .login)
                login_user
                ;;
            .logout)
                logout_user
                ;;
            *)
                echo "❌ Unknown command: $command"
                echo "ℹ️  Type '.help' to see a list of available commands."
                ;;
        esac
    done
}

# =========================
# SCRIPT ENTRY POINT
# =========================
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
export_config_path
display_branding

cd "$PROJECT_DIR" || {
    echo "❌ Failed to navigate to the project directory: $PROJECT_DIR"
    exit 1
}

if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found in $PROJECT_DIR. Please ensure it's set up."
    exit 1
fi

check_login
main_loop
