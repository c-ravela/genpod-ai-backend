ifneq (,$(wildcard .env))
    include .env
    export $(shell sed 's/=.*//' .env)
else
    $(error [ERROR] .env file not found. Please create a .env file to proceed.)
endif

# Specify the output directory for all generated files
OUTPUT_PATH = $(CURDIR)/"output"

# Define subdirectories within the output directory
DB_FOLDER_NAME = "databases"
OUTPUT_DB_PATH = $(OUTPUT_PATH)/$(DB_FOLDER_NAME)

PROJECTS_FOLDER_NAME = "projects"
OUTPUT_PROJECT_PATH = $(OUTPUT_PATH)/$(PROJECTS_FOLDER_NAME)

VECTOR_COLLECTIONS_FOLDER_NAME = "vector_collections"
VECTOR_COLLECTIONS_PATH = $(CURDIR)/$(VECTOR_COLLECTIONS_FOLDER_NAME)

LOGS_FOLDER_NAME = "logs"
OUTPUT_LOGS_PATH = $(OUTPUT_PATH)/$(LOGS_FOLDER_NAME)

# Get the current timestamp
current_time := $(shell date +'%Y-%m-%d_%H-%M-%S-%6N')

# Create a log file with the current timestamp
curr_log_file_name = "$(current_time).log"
CURR_LOG_FILE_PATH = $(OUTPUT_LOGS_PATH)/$(curr_log_file_name)

# Define a function to create a directory if it doesn't exist
define create_directory
    @mkdir -p $(1)
endef

# Target to run the main Python script
run:
	python3 main.py

# Target to run the main Python script and log the output to a file
log-run:
	$(call create_directory, $(OUTPUT_LOGS_PATH))
	python3 main.py 2> $(CURR_LOG_FILE_PATH)


# Clean targets to remove generated files
.PHONY: clean-logs clean-projects clean-databases clean

clean-logs:
	rm -rf $(OUTPUT_LOGS_PATH)/*

clean-projects:
	rm -rf $(OUTPUT_PROJECT_PATH)/*

clean-databases:
	rm -rf $(OUTPUT_DB_PATH)/*

clean: clean-projects clean-databases clean-logs
