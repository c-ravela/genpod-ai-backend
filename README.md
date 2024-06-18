# GenPod's LLM and AI backend codebase repo

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
docker exec -it <container_name>
```

Replace `<container_name>` with the name of your Docker container. You can find the name of the container using the `docker ps` command.

### Running Jupyter Notebooks in the Docker Container

You can run Jupyter notebooks from within the container using the following command:

```bash
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

### Helpful Docker Commands

Here are some additional Docker commands that you might find useful:

* **Remove/Delete a Docker container**:

    ```bash
    docker rm <container_name_or_id>
    ```

* **Remove/Delete a Docker image**:

    ```bash
    docker rmi <image_id_or_name>
    ```

* **Run a Docker image**:

    ```bash
    docker run -it <image_name>
    ```

* **Stop a Docker container**:

    ```bash
    docker stop <container_name_or_id>
    ```

---
