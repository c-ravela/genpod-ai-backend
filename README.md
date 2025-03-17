# GenPod's LLM and AI backend codebase repo

## **Installation**

Follow these steps to install GENPOD on your system:

### **Prerequisites**

Before installation, ensure the following dependencies are met:

- **Operating System:** Linux, macOS, or Windows (using [WSL](https://learn.microsoft.com/en-us/windows/wsl/) or [Git Bash](https://gitforwindows.org/)).
- **Required Tools:** `bash`, `python3` (version 3.6 or later), and `pip`.
- **Permissions:** Write access to the desired installation directory.

---

#### **Installation Steps**

1. **Clone the Repository**  
   Download the `Genpod` source code to your local machine:

   ```bash
   git clone git@github.com:intelops/genpod-ai-backend.git
   cd genpod-ai-backend
   ```

2. **Run the Installation Script**  
   Execute the `install.sh` script based on your setup:

   - **Default Installation** (to `/usr/local/bin`):

     ```bash
     bash install.sh
     ```

   - **Custom Installation Path**:
     Specify a writable installation directory:

     ```bash
     INSTALL_PATH=/custom/path bash install.sh
     ```

   - **System-Wide Installation** (requires `sudo`):

     ```bash
     sudo bash install.sh
     ```

3. **Verify Installation**
   Confirm the installation by running the `genpod` command:

   ```bash
   genpod --version
   ```

   If the application starts successfully, the installation is complete.

---

### **Troubleshooting**

- **Permission Issues:**  
  Run the installation script with `sudo`:

  ```bash
  sudo bash install.sh
  ```

- **Command Not Found:**  
  Add the installation directory to your `PATH`. For example, if installed in `$HOME/.local/bin`:

  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```

- **Dependency Issues:**  
  Verify your Python and pip versions:

  ```bash
  python3 --version
  pip --version
  ```

- **Custom Path Errors:**  
  Ensure the directory exists and is writable:

  ```bash
  mkdir -p /custom/path
  INSTALL_PATH=/custom/path bash install-genpod.sh
  ```

---

### **Uninstallation**

To uninstall GENPOD:

1. **System-Wide Installation (default path):**

   ```bash
   rm -rf /usr/local/bin/genpod /usr/local/bin/genpod_src
   ```

2. **Custom Path Installation:**

   ```bash
   rm -rf /custom/path/genpod /custom/path/genpod_src
   ```

## Docker-Based Development Setup

This guide provides steps to set up your development environment using Docker.

### Building the Docker Image and Starting the Container

Build the Docker image and start the container using the following command:

```bash
docker compose up --build
```

The Docker container is set to `sleep infinity`.

### Accessing the Docker Container

To get shell access to the running container, open a new terminal tab and run the following command:

```bash
docker exec -it <container_name> /bin/bash
```

Replace `<container_name>` with the name of your Docker container. You can find the name of the container using the `docker ps` command.

### Running Jupyter Notebooks in the Docker Container

You can run Jupyter notebooks from within the container using the following command:

```bash
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

### Helpful Docker Commands

Here are some additional Docker commands that you might find useful:

- **Remove/Delete a Docker container**:

    ```bash
    docker rm <container_name_or_id>
    ```

- **Remove/Delete a Docker image**:

    ```bash
    docker rmi <image_id_or_name>
    ```

- **Run a Docker image**:

    ```bash
    docker run -it <image_name>
    ```

- **Stop a Docker container**:

    ```bash
    docker stop <container_name_or_id>
    ```
